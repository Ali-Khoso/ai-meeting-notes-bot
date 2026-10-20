import tempfile
import unittest
from app.core import Store, chunks, meeting_url, validate_notes, transcript_text

class CoreTests(unittest.TestCase):
    def test_meet_url_allowlist(self):
        self.assertEqual(meeting_url(' https://meet.google.com/abc-defg-hij?authuser=1 '), 'https://meet.google.com/abc-defg-hij')
        for u in ['https://meet.google.com.evil.test/abc-defg-hij', 'http://meet.google.com/abc-defg-hij', 'https://evil@meet.google.com/abc-defg-hij', 'https://meet.google.com:444/abc-defg-hij', 'https://zoom.us/j/1', 'https://meet.google.com/../../etc', None]:
            with self.subTest(u=u), self.assertRaises(ValueError): meeting_url(u)

    def test_grounding_rejects_fake_quote_and_id(self):
        segments = [dict(id=0, start=12, text='We miss calls at night.')]
        rows = [dict(text='Missed calls', evidence_id=0, quote='miss calls'), dict(text='Invented', evidence_id=2, quote='miss calls'), dict(text='Invented', evidence_id=0, quote='lost a million'), dict(text='Invented', evidence_id=False, quote='miss calls')]
        result, rejected = validate_notes({'pain_points': rows}, segments)
        self.assertEqual(rejected, 3)
        self.assertEqual(result['pain_points'][0]['start'], 12)
        self.assertEqual(len(result['pain_points']), 1)

    def test_empty_report_and_invalid_types(self):
        self.assertEqual(validate_notes({}, [])[0]['pain_points'], [])
        with self.assertRaises(ValueError): validate_notes({'summary': 'bad'}, [])

    def test_chunks_keep_all_text(self):
        segments = [dict(id=i, start=i, text='x' * 10001) for i in range(4)]
        batches = list(chunks(segments))
        for i in range(4): self.assertEqual(''.join(s['text'] for b in batches for s in b if s['id'] == i), 'x' * 10001)
        self.assertGreater(len(batches), 1)

    def test_store_recovers_and_rejects_paths(self):
        with tempfile.TemporaryDirectory() as d:
            s = Store(d)
            s.put(dict(id='a'*32, created='2026-01-01', status='recording'))
            s.recover()
            self.assertEqual(s.get('a'*32)['status'], 'interrupted')
            with self.assertRaises(ValueError): s.get('../secret')

    def test_export_timestamps(self):
        self.assertEqual(transcript_text([dict(start=65, text='Hello')]), '[00:01:05] Hello')

if __name__ == '__main__': unittest.main()
