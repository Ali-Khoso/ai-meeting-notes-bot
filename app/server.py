"""Single-user localhost app. Run one server process per audio container."""
import json
import os
import shutil
import threading
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from app import bot
from app.core import Store, analyze, meeting_url, transcript_text

ROOT = Path(__file__).resolve().parent.parent
store = Store(os.getenv('DATA_DIR', str(ROOT / 'data')))
busy = threading.Lock()
events = {}


def process(key, stop, retry=False):
    try:
        if not retry:
            item = store.get(key)
            output = store.folder(key) / 'audio.wav'
            ok = bot.capture(item['url'], output, stop, lambda s: store.update(key, status=s))
            if not ok:
                store.update(key, status='cancelled', error='Stopped before audio was captured.')
                return
            store.update(key, status='transcribing')
            segments = bot.transcribe(output)
            store.update(key, segments=segments)
        else:
            segments = store.get(key)['segments']
        if not segments:
            store.update(key, status='no_speech', error='No speech was detected. Check meeting audio and retry.')
            return
        store.update(key, status='analyzing')
        report = analyze(segments)
        store.update(key, status='completed', report=report, error=None)
    except Exception as exc:
        # No credentials are used. Keep a concise failure visible; retain transcript for retry.
        store.update(key, status='failed', error=str(exc)[:600])
    finally:
        events.pop(key, None)
        busy.release()


def start_job(key, retry=False):
    stop = threading.Event()
    events[key] = stop
    try:
        threading.Thread(target=process, args=(key, stop, retry), daemon=True).start()
    except Exception:
        events.pop(key, None)
        busy.release()
        raise


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass  # Avoid meeting URLs or private transcript content in access logs.

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
                return self.send(200, {'status': 'ok', 'busy': busy.locked()})
            parts = path.strip('/').split('/')
            if len(parts) == 4 and parts[:2] == ['api', 'meetings'] and parts[3] == 'export':
                item = store.get(parts[2])
                return self.send(200, transcript_text(item.get('segments', [])) + '\n\n' + json.dumps(item.get('report', {}), ensure_ascii=False, indent=2), 'text/plain')
            return self.send(404, {'error': 'Not found.'})
        except (FileNotFoundError, ValueError):
            return self.send(404, {'error': 'Meeting not found.'})

    def do_POST(self):
        # Reject cross-origin writes, including malicious web pages targeting localhost.
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
            if parts == ['api', 'meetings']:
                url = meeting_url(data.get('url'))
                if data.get('consent') is not True:
                    raise ValueError('Confirm that participants know and agree to recording.')
                if not busy.acquire(blocking=False):
                    return self.send(409, {'error': 'One meeting at a time. Wait for the current job to finish.'})
                key = uuid.uuid4().hex
                item = dict(id=key, title=str(data.get('title') or 'Untitled meeting')[:120], url=url,
                            created=datetime.now(timezone.utc).isoformat(), status='starting',
                            consent=True, segments=[], report=None, error=None)
                try:
                    store.put(item)
                except Exception:
                    busy.release()
                    raise
                start_job(key)
                return self.send(201, item)
            if len(parts) == 4 and parts[:2] == ['api', 'meetings']:
                key, action = parts[2:]
                item = store.get(key)
                if action == 'stop':
                    if item['status'] not in {'starting', 'waiting', 'recording'} or key not in events:
                        return self.send(409, {'error': 'This meeting is not currently recording or waiting.'})
                    events[key].set()
                    return self.send(200, {'status': 'stopping'})
                if action == 'analyze':
                    if not item.get('segments'):
                        raise ValueError('No saved transcript is available.')
                    if not busy.acquire(blocking=False):
                        return self.send(409, {'error': 'Another job is running.'})
                    try:
                        store.update(key, status='analyzing', error=None)
                    except Exception:
                        busy.release()
                        raise
                    start_job(key, retry=True)
                    return self.send(202, {'status': 'analyzing'})
                if action == 'delete':
                    # Global lock prevents deleting data used by the worker.
                    if not busy.acquire(blocking=False):
                        return self.send(409, {'error': 'Wait until the current job finishes before deleting.'})
                    try:
                        shutil.rmtree(store.folder(key))
                    finally:
                        busy.release()
                    return self.send(200, {'status': 'deleted'})
            return self.send(404, {'error': 'Not found.'})
        except FileNotFoundError:
            return self.send(404, {'error': 'Meeting not found.'})
        except (ValueError, TypeError) as exc:
            return self.send(400, {'error': str(exc)})
        except Exception:
            return self.send(500, {'error': 'Local operation failed. Check available disk space and restart the app.'})


if __name__ == '__main__':
    store.recover()
    host = os.getenv('BIND_HOST', '127.0.0.1')
    print('Meeting Notes is ready at http://localhost:8000', flush=True)
    ThreadingHTTPServer((host, 8000), Handler).serve_forever()
