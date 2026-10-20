import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from app import server, fathom
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

    def seed(self):
        key='a'*32
        server.store.put(dict(id=key,title='Test',created='2026-01-01',recording_id='123',status='importing',segments=[],report=None))
        return key

    def test_cross_origin_and_invalid_id(self):
        self.assertEqual(self.request('/api/fathom/import', {'recording_id':'123'}, 'https://evil.test')[0],403)
        self.assertEqual(self.request('/api/fathom/import', {'recording_id':'../secret'})[0],400)

    def test_key_not_exposed(self):
        with patch.dict(os.environ, {'FATHOM_API_KEY':'secret-test-value'}):
            _, data = self.request('/api/health')
        self.assertTrue(data['fathom_configured'])
        self.assertNotIn('secret-test-value',json.dumps(data))

    def test_busy_prevents_import(self):
        server.busy.acquire()
        try: self.assertEqual(self.request('/api/fathom/import', {'recording_id':'123'})[0],409)
        finally: server.busy.release()

    def test_import_persists_then_analysis_retry(self):
        key=self.seed()
        segments=[dict(id=0,start=1,text='We miss calls.',speaker='Ali')]
        server.busy.acquire()
        with patch.object(fathom,'get_recording',return_value=(segments,'Summary',None)): server.process(key)
        self.assertEqual(server.store.get(key)['status'],'imported')
        self.assertEqual(server.store.get(key)['fathom_summary'],'Summary')
        server.busy.acquire()
        with patch.object(server,'analyze',side_effect=ConnectionError('secret-test-value')): server.process(key,True)
        item=server.store.get(key)
        self.assertEqual(item['segments'],segments)
        self.assertNotIn('secret-test-value',item['error'])
        server.busy.acquire()
        with patch.object(server,'analyze',return_value={'summary':[],'actions':[],'pain_points':[]}): server.process(key,True)
        self.assertEqual(server.store.get(key)['status'],'completed')
        self.assertFalse(server.busy.locked())

    def test_import_is_idempotent(self):
        def inline(key,analysis=False): server.process(key,analysis)
        segments=[dict(id=0,start=1,text='Text',speaker='A')]
        with patch.object(server,'start_job',side_effect=inline), patch.object(fathom,'get_recording',return_value=(segments,'Summary',None)):
            for _ in range(2): self.assertEqual(self.request('/api/fathom/import', {'recording_id':'123'})[0],202)
        self.assertEqual(len(server.store.all()),1)

    def test_missing_key_readable(self):
        with patch.dict(os.environ, {'FATHOM_API_KEY':''}):
            code, data=self.request('/api/fathom/meetings',{})
        self.assertEqual(code,502)
        self.assertIn('FATHOM_API_KEY',data['error'])

    def test_delete_local_only(self):
        key=self.seed()
        with patch.object(fathom,'request') as remote:
            self.assertEqual(self.request(f'/api/meetings/{key}/delete',{})[0],200)
        remote.assert_not_called()
        self.assertEqual(server.store.all(),[])

if __name__ == '__main__': unittest.main()
