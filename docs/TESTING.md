# Verification

## Offline checks

Run `python -m unittest discover -s tests -v` and `node --check static/app.js` (Node is only needed for this development syntax check, not for running the app).

Tests use mocked Fathom/Ollama responses. They cover transcript timestamps/speakers, API errors, pagination, missing credentials, .env loading, duplicate imports, persistence, safe retry, quote validation, local deletion and origin rejection.

## Live acceptance checklist — still requires your account

- [ ] Install/sign into Fathom desktop and Chrome extension.
- [ ] Join your own Meet; verify the correct recording setting and admit Fathom.
- [ ] Speak a clear problem and task, then end the recording in Fathom.
- [ ] Wait until Fathom displays a transcript and summary.
- [ ] Configure FATHOM_API_KEY locally and start the Python app without Docker.
- [ ] Load recordings and import the test meeting.
- [ ] Confirm transcript, speaker names and Fathom summary match the original.
- [ ] Import again and verify only one local entry exists.
- [ ] Download the notes and check the exported text.
- [ ] Install native Ollama, download the configured model, and analyze pain points.
- [ ] Check each extracted claim and quote against the transcript.
- [ ] Delete the local entry; confirm the original Fathom recording remains.

No live account test is claimed by the offline tests. Never use real meeting content or real API keys as public test fixtures.
