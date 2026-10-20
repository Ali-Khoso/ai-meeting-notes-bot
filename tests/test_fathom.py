import io
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch, MagicMock
from app import fathom
from app.config import load_env

class FathomTests(unittest.TestCase):
    def test_transcript_preserves_speaker_text_time(self):
        result=fathom.normalize_transcript({'transcript':[{'speaker':{'display_name':'Ali'},'text':'We need help.','timestamp':'00:05:32'}]})
        self.assertEqual(result,[dict(id=0,start=332,text='We need help.',speaker='Ali')])

    def test_invalid_timestamp_rejected(self):
        for v in ['nonsense','00:99:00',None]:
            with self.assertRaises(ValueError): fathom.seconds(v)

    def test_pending_transcript(self):
        with self.assertRaises(fathom.FathomError): fathom.normalize_transcript({'status':'pending'})

    def test_summary_failure_keeps_transcript(self):
        raw={'transcript':[{'text':'Problem','timestamp':'00:00:01'}]}
        with patch.object(fathom,'request',side_effect=[raw,fathom.FathomError('Not ready')]):
            segments,summary,warning=fathom.get_recording('123')
        self.assertEqual(len(segments),1)
        self.assertEqual(summary,'')
        self.assertIsNotNone(warning)

    def test_pagination_cursor(self):
        raw={'items':[{'recording_id':123,'title':'Meeting'}],'next_cursor':'next'}
        with patch.object(fathom,'request',return_value=raw) as req:
            result=fathom.list_meetings('previous')
        req.assert_called_once_with('/meetings',{'cursor':'previous'})
        self.assertEqual(result['next_cursor'],'next')
        self.assertEqual(result['items'][0]['recording_id'],'123')

    def test_error_body_not_exposed(self):
        error=urllib.error.HTTPError('url',401,'Unauthorized',{},io.BytesIO(b'secret-response'))
        opener=MagicMock();opener.open.side_effect=error
        with patch.dict(os.environ,{'FATHOM_API_KEY':'private-key'}),patch('urllib.request.build_opener',return_value=opener):
            with self.assertRaises(fathom.FathomError) as exc: fathom.request('/meetings')
        self.assertNotIn('private-key',str(exc.exception))
        self.assertNotIn('secret-response',str(exc.exception))

    def test_no_redirect(self):
        self.assertIsNone(fathom.NoRedirect().redirect_request(None,None,302,'',{},'https://evil.test'))

    def test_env_bom_quotes_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ,{'OLLAMA_MODEL':'existing'}):
            p=Path(d)/'.env';p.write_text('\ufeffOLLAMA_MODEL=other\nFATHOM_API_KEY="test"\nUNSAFE_SETTING=x\n',encoding='utf-8')
            with patch.dict(os.environ,{},clear=False):
                os.environ.pop('FATHOM_API_KEY',None)
                load_env(p)
                self.assertEqual(os.environ['OLLAMA_MODEL'],'existing')
                self.assertEqual(os.environ['FATHOM_API_KEY'],'test')
                self.assertNotIn('UNSAFE_SETTING',os.environ)

if __name__ == '__main__': unittest.main()
