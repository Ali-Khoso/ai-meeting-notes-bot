import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from app import server
from app.core import Store

class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous = server.store
        server.store = Store(self.temp.name)
        self.http = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()
        self.url = f'http://127.0.0.1:{self.http.server_port}'

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join()
        server.store = self.previous
        self.temp.cleanup()

    def request(self, path, data=None, origin=None):
        headers = {'Origin': self.url if origin is None else origin, 'Content-Type': 'application/json'}
        req = urllib.request.Request(self.url + path, data=json.dumps(data).encode() if data is not None else None, headers=headers)
        try: response = urllib.request.urlopen(req)
        except urllib.error.HTTPError as e: response = e
        with response: return response.status, json.loads(response.read())

    def test_origin_and_consent_required(self):
        payload = dict(url='https://meet.google.com/abc-defg-hij', consent=True)
        self.assertEqual(self.request('/api/meetings', payload, 'https://evil.test')[0], 403)
        payload['consent'] = False
        self.assertEqual(self.request('/api/meetings', payload)[0], 400)
        self.assertEqual(self.request('/api/meetings', dict(url='https://evil.test'))[0], 400)

    def test_busy_prevents_second_capture(self):
        server.busy.acquire()
        try:
            code, _ = self.request('/api/meetings', dict(url='https://meet.google.com/abc-defg-hij', consent=True))
            self.assertEqual(code, 409)
        finally: server.busy.release()

    def seed(self):
        item = dict(id='a'*32, title='Test', created='2026-01-01', url='https://meet.google.com/abc-defg-hij', status='starting', segments=[])
        server.store.put(item)
        return item['id']

    def test_full_pipeline_mocked(self):
        key = self.seed()
        segments = [dict(id=0, start=0, end=3, text='We miss calls.')]
        report = dict(summary=[], actions=[], pain_points=[], rejected_items=0)
        server.busy.acquire()
        with patch.object(server.bot, 'capture', return_value=True), patch.object(server.bot, 'transcribe', return_value=segments), patch.object(server, 'analyze', return_value=report): server.process(key, threading.Event())
        item = server.store.get(key)
        self.assertEqual(item['status'], 'completed')
        self.assertEqual(item['segments'], segments)
        self.assertFalse(server.busy.locked())

    def test_analysis_failure_keeps_transcript_then_retry(self):
        key = self.seed()
        segments = [dict(id=0, start=0, text='A problem.')]
        server.store.update(key, segments=segments)
        server.busy.acquire()
        with patch.object(server, 'analyze', side_effect=ConnectionError('Ollama unavailable')): server.process(key, threading.Event(), retry=True)
        self.assertEqual(server.store.get(key)['segments'], segments)
        self.assertEqual(server.store.get(key)['status'], 'failed')
        server.busy.acquire()
        with patch.object(server, 'analyze', return_value={'summary': [], 'actions': [], 'pain_points': []}): server.process(key, threading.Event(), retry=True)
        self.assertEqual(server.store.get(key)['status'], 'completed')

    def test_cancel_does_not_analyze(self):
        key = self.seed()
        server.busy.acquire()
        with patch.object(server.bot, 'capture', return_value=False), patch.object(server, 'analyze') as analyze: server.process(key, threading.Event())
        analyze.assert_not_called()
        self.assertEqual(server.store.get(key)['status'], 'cancelled')

    def test_stop_and_delete(self):
        key = self.seed()
        event = threading.Event()
        server.events[key] = event
        try:
            self.assertEqual(self.request(f'/api/meetings/{key}/stop', {})[0], 200)
            self.assertTrue(event.is_set())
        finally: server.events.pop(key)
        server.store.update(key, status='cancelled')
        self.assertEqual(self.request(f'/api/meetings/{key}/delete', {})[0], 200)
        self.assertEqual(server.store.all(), [])

if __name__ == '__main__': unittest.main()
