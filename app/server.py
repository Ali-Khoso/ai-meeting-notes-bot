"""Fathom-backed, localhost-only notes app. Python 3.10+, no pip install required."""
import json
import os
import shutil
import threading
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from app.config import load_env
from app import fathom
from app.core import Store, analyze, transcript_text

ROOT = Path(__file__).resolve().parent.parent
load_env(ROOT / '.env')
store = Store(os.getenv('DATA_DIR', str(ROOT / 'data')))
busy = threading.Lock()


def process(key, analysis=False):
    try:
        item = store.get(key)
        if analysis:
            report = analyze(item['segments'])
            store.update(key, status='completed', report=report, error=None)
        else:
            segments, summary, warning = fathom.get_recording(item['recording_id'])
            same = item.get('segments') == segments
            store.update(key, status='imported', segments=segments,
                         fathom_summary=summary or (item.get('fathom_summary', '') if same else ''),
                         report=item.get('report') if same else None, error=None, warning=warning)
    except Exception as exc:
        # Provider response bodies and credentials are never returned to the browser.
        message = str(exc) if isinstance(exc, fathom.FathomError) else (
            'Local analysis failed. Check that Ollama is running and the selected model is downloaded; then retry.'
            if analysis else 'Import failed. Check the recording in Fathom and try again.')
        store.update(key, status='failed', error=message)
    finally:
        busy.release()


def start_job(key, analysis=False):
    try:
        threading.Thread(target=process, args=(key, analysis), daemon=True).start()
    except Exception:
        busy.release()
        raise


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def send(self, code, body, kind='application/json'):
        if kind == 'application/json':
            body = json.dumps(body, ensure_ascii=False).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header('Content-Type', kind + ('; charset=utf-8' if kind.startswith('text/') else ''))
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(body)

    def local(self):
        try:
            host = urlsplit('http://' + self.headers.get('Host', '')).hostname
        except ValueError:
            return False
        return host in {'localhost', '127.0.0.1', '::1'}

    def do_GET(self):
        if not self.local():
            return self.send(403, {'error': 'Use localhost to access this app.'})
        path = urlsplit(self.path).path
        try:
            assets = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'), '/style.css': ('style.css', 'text/css')}
            if path in assets:
                name, kind = assets[path]
                return self.send(200, (ROOT / 'static' / name).read_bytes(), kind)
            if path == '/api/meetings':
                return self.send(200, store.all())
            if path == '/api/health':
                return self.send(200, {'status': 'ok', 'busy': busy.locked(),
                                      'fathom_configured': bool(os.getenv('FATHOM_API_KEY', '').strip())})
            parts = path.strip('/').split('/')
            if len(parts) == 4 and parts[:2] == ['api', 'meetings'] and parts[3] == 'export':
                item = store.get(parts[2])
                body = (item['title'] + '\n\nTRANSCRIPT\n' + transcript_text(item.get('segments', []))
                        + '\n\nFATHOM SUMMARY\n' + item.get('fathom_summary', '')
                        + '\n\nLOCAL ANALYSIS\n' + json.dumps(item.get('report'), ensure_ascii=False, indent=2))
                return self.send(200, body, 'text/plain')
            return self.send(404, {'error': 'Not found.'})
        except (FileNotFoundError, ValueError):
            return self.send(404, {'error': 'Meeting not found.'})

    def do_POST(self):
        if not self.local() or self.headers.get('Origin') != 'http://' + self.headers.get('Host', ''):
            return self.send(403, {'error': 'Open the app on localhost before making changes.'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 1_000_000:
                return self.send(413, {'error': 'Request must be under 1 MB.'})
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError('Expected a JSON object.')
            parts = urlsplit(self.path).path.strip('/').split('/')
            if parts == ['api', 'fathom', 'meetings']:
                return self.send(200, fathom.list_meetings(data.get('cursor', '')))
            if parts == ['api', 'fathom', 'import']:
                rid = fathom.recording_id(data.get('recording_id'))
                if not busy.acquire(blocking=False):
                    return self.send(409, {'error': 'Another import or analysis is running.'})
                key = uuid.uuid5(uuid.NAMESPACE_URL, 'fathom-recording:' + rid).hex
                try:
                    try:
                        item = store.get(key)
                    except FileNotFoundError:
                        item = dict(id=key, title=str(data.get('title') or 'Fathom recording ' + rid)[:120],
                                    created=datetime.now(timezone.utc).isoformat(), recording_id=rid,
                                    source='fathom', segments=[], report=None, fathom_summary='')
                    item.update(status='importing', error=None, warning=None)
                    store.put(item)
                except Exception:
                    busy.release()
                    raise
                start_job(key)
                return self.send(202, item)
            if len(parts) == 4 and parts[:2] == ['api', 'meetings']:
                key, action = parts[2:]
                item = store.get(key)
                if action == 'analyze':
                    if not item.get('segments'):
                        raise ValueError('Import a transcript before analyzing.')
                    if not busy.acquire(blocking=False):
                        return self.send(409, {'error': 'Another job is running.'})
                    try:
                        store.update(key, status='analyzing', error=None)
                    except Exception:
                        busy.release()
                        raise
                    start_job(key, analysis=True)
                    return self.send(202, {'status': 'analyzing'})
                if action == 'delete':
                    if not busy.acquire(blocking=False):
                        return self.send(409, {'error': 'Wait until the current job finishes before deleting.'})
                    try:
                        shutil.rmtree(store.folder(key))
                    finally:
                        busy.release()
                    return self.send(200, {'status': 'deleted'})
            return self.send(404, {'error': 'Not found.'})
        except fathom.FathomError as exc:
            return self.send(502, {'error': str(exc)})
        except FileNotFoundError:
            return self.send(404, {'error': 'Meeting not found.'})
        except (ValueError, TypeError) as exc:
            return self.send(400, {'error': str(exc)})
        except Exception:
            return self.send(500, {'error': 'Local operation failed. Check available disk space and restart the app.'})


if __name__ == '__main__':
    store.recover()
    print('Meeting Notes is ready at http://localhost:8000 — press Ctrl+C to stop.', flush=True)
    ThreadingHTTPServer(('127.0.0.1', 8000), Handler).serve_forever()
