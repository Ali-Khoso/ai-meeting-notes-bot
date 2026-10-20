"""Experimental Google Meet guest bot. Runs inside the Linux audio container."""
import os
import re
import signal
import subprocess
import time


def capture(url, output, stop, status):
    from playwright.sync_api import sync_playwright
    recorder = None
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=[
            '--autoplay-policy=no-user-gesture-required',
            '--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream',
            '--disable-dev-shm-usage',
        ])
        try:
            context = browser.new_context(locale='en-US', permissions=['microphone', 'camera'])
            page = context.new_page()
            page.goto(url, wait_until='domcontentloaded', timeout=60000)
            # Meet may show permission/continue dialogs. Do not bypass sign-in or CAPTCHA.
            for label in ['Continue without microphone and camera', 'Use without an account']:
                button = page.get_by_role('button', name=label, exact=False)
                if button.count() and button.first.is_visible():
                    button.first.click()
            name = page.get_by_role('textbox', name=re.compile('your name', re.I))
            try:
                name.wait_for(state='visible', timeout=25000)
            except Exception as exc:
                raise RuntimeError('Meet did not offer guest entry. Check that the meeting allows guests; sign-in or a changed Meet layout may block this bot.') from exc
            name.fill(os.getenv('BOT_NAME', 'Ali’s AI Notes Bot (recording)'))
            for pattern in [r'Turn off microphone', r'Turn off camera']:
                control = page.get_by_role('button', name=re.compile(pattern, re.I))
                if control.count() and control.first.is_visible():
                    control.first.click()
            for pattern in [r'Turn on microphone', r'Turn on camera']:
                try:
                    page.get_by_role('button', name=re.compile(pattern, re.I)).first.wait_for(state='visible', timeout=5000)
                except Exception as exc:
                    raise RuntimeError('Could not confirm microphone and camera are off; the bot will not join.') from exc
            join = page.get_by_role('button', name=re.compile(r'^(Ask to join|Join now|Join meeting)$', re.I))
            join.first.click(timeout=15000)
            status('waiting')
            leave = page.get_by_role('button', name=re.compile(r'Leave call', re.I))
            deadline = time.monotonic() + int(os.getenv('ADMISSION_TIMEOUT', '300'))
            while not stop.is_set() and time.monotonic() < deadline:
                if leave.count() and leave.first.is_visible():
                    break
                page.wait_for_timeout(1000)
            else:
                if stop.is_set():
                    return False
                raise RuntimeError('Bot was not admitted within the waiting limit. Admit the bot or enable guest access and retry.')
            # Record only after admission; capture Chromium's isolated output sink.
            log = open(output.with_suffix('.ffmpeg.log'), 'wb')
            try:
                recorder = subprocess.Popen([
                    'ffmpeg', '-y', '-nostdin', '-f', 'pulse', '-i', 'meet.monitor',
                    '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', str(output)
                ], stdout=subprocess.DEVNULL, stderr=log)
                time.sleep(.5)
                if recorder.poll() is not None:
                    raise RuntimeError('Audio capture failed. Check the local ffmpeg log and PulseAudio setup.')
                status('recording')
                deadline = time.monotonic() + int(os.getenv('MAX_MEETING_SECONDS', '7200'))
                missing = 0
                while not stop.is_set() and time.monotonic() < deadline:
                    if recorder.poll() is not None:
                        raise RuntimeError('Audio recording stopped unexpectedly. See the local ffmpeg log.')
                    visible = not page.is_closed() and leave.count() and leave.first.is_visible()
                    missing = 0 if visible else missing + 1
                    if missing >= 5:
                        break
                    page.wait_for_timeout(1000)
            finally:
                if recorder and recorder.poll() is None:
                    recorder.send_signal(signal.SIGINT)
                    try:
                        recorder.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        recorder.kill()
                        recorder.wait()
                log.close()
            return output.exists() and output.stat().st_size > 44
        finally:
            browser.close()


def transcribe(path):
    from faster_whisper import WhisperModel
    model = WhisperModel(os.getenv('WHISPER_MODEL', 'base'), device='cpu', compute_type='int8')
    lang = os.getenv('TRANSCRIPT_LANGUAGE', '').strip() or None
    segments, _ = model.transcribe(str(path), language=lang, vad_filter=True, beam_size=5)
    return [dict(id=i, start=s.start, end=s.end, text=s.text.strip())
            for i, s in enumerate(segments) if s.text.strip()]
