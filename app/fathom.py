"""Read-only Fathom API client. No bot-join endpoint is claimed or emulated."""
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

BASE = 'https://api.fathom.ai/external/v1'

class FathomError(RuntimeError):
    pass

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward the private API key to a redirect destination.


def request(path, params=None):
    key = os.getenv('FATHOM_API_KEY', '').strip()
    if not key:
        raise FathomError('Add FATHOM_API_KEY to your local .env file and restart the app.')
    url = BASE + path + ('?' + urllib.parse.urlencode(params) if params else '')
    req = urllib.request.Request(url, headers={'X-Api-Key': key, 'Accept': 'application/json'})
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=45) as response:
            body = response.read(20_000_001)
            if len(body) > 20_000_000:
                raise FathomError('Fathom response is too large for this local preview.')
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        messages = {401: 'Fathom rejected the API key. Check .env and restart.',
                    403: 'Your Fathom account cannot access this recording.',
                    404: 'Recording not found or not ready in Fathom.',
                    429: 'Fathom rate limit reached. Wait a minute, then try again.'}
        raise FathomError(messages.get(exc.code, f'Fathom returned HTTP {exc.code}. Try again later.')) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise FathomError('Cannot reach Fathom. Check your internet connection and try again.') from None
    except (ValueError, KeyError):
        raise FathomError('Fathom returned an unexpected response.') from None


def recording_id(value):
    value = str(value)
    if not re.fullmatch(r'[1-9][0-9]{0,19}', value):
        raise ValueError('Select a recording from Fathom; its recording ID must be numeric.')
    return value


def list_meetings(cursor=''):
    if not isinstance(cursor, str) or len(cursor) > 2000:
        raise ValueError('Invalid page cursor.')
    raw = request('/meetings', {'cursor': cursor} if cursor else None)
    if not isinstance(raw, dict) or not isinstance(raw.get('items'), list):
        raise FathomError('Fathom returned an invalid meetings list.')
    items = []
    for row in raw['items']:
        if not isinstance(row, dict):
            continue
        items.append({'recording_id': recording_id(row.get('recording_id')),
                      'title': str(row.get('title') or row.get('meeting_title') or 'Untitled meeting'),
                      'created': str(row.get('created_at') or ''),
                      'recorded_by': (row.get('recorded_by') or {}).get('email', '')})
    return {'items': items, 'next_cursor': raw.get('next_cursor')}


def seconds(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d+:\d{2}:\d{2}(?:\.\d+)?', value):
        raise ValueError('Transcript has an invalid timestamp.')
    h, m, s = value.split(':')
    if int(m) >= 60 or float(s) >= 60:
        raise ValueError('Transcript has an invalid timestamp.')
    return int(h) * 3600 + int(m) * 60 + float(s)


def normalize_transcript(raw):
    if not isinstance(raw, dict) or not isinstance(raw.get('transcript'), list):
        raise FathomError('Transcript is not ready. Wait for Fathom processing, then import again.')
    segments = []
    for i, row in enumerate(raw['transcript']):
        if not isinstance(row, dict) or not isinstance(row.get('text'), str):
            raise FathomError('Fathom returned an invalid transcript segment.')
        if not row['text'].strip():
            continue
        speaker = row.get('speaker') or {}
        segments.append(dict(id=i, start=seconds(row.get('timestamp')), text=row['text'],
                             speaker=str(speaker.get('display_name') or 'Unknown speaker')))
    return segments


def get_recording(value):
    rid = recording_id(value)
    segments = normalize_transcript(request(f'/recordings/{rid}/transcript'))
    if not segments:
        raise FathomError('No transcript is available yet. Wait for processing or check the recording in Fathom.')
    warning = None
    summary = ''
    try:
        raw = request(f'/recordings/{rid}/summary')
        summary = (raw.get('summary') or {}).get('markdown_formatted') or ''
        if not isinstance(summary, str):
            raise FathomError('Fathom summary has an unexpected format.')
    except (FathomError, AttributeError):
        warning = 'Transcript imported, but the Fathom summary is not available. Import again later.'
    return segments, summary, warning
