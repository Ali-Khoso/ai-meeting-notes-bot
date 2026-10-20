# Verification

## Automated, offline

Run `python -m unittest discover -s tests -v`. Tests cover URL allowlisting, path traversal rejection, transcript chunk coverage, quote validation, restart recovery, request origin checks, exclusive audio jobs, persisted processing results and recoverable analysis failures. Browser/audio/model dependencies are mocked where needed; these tests do not prove live meeting compatibility.

## Manual acceptance (must run on your machine)

- [ ] Docker build completes and both services run.
- [ ] Ollama model pulls successfully; dashboard opens on localhost.
- [ ] Bot asks to join a guest-accessible Google Meet with the visible recording name.
- [ ] Host admits it; app switches from waiting to recording.
- [ ] Microphone and camera are off in the participant list.
- [ ] Record a 30-second spoken problem and named action; stop from the dashboard.
- [ ] Transcript includes the spoken words and timestamps.
- [ ] Summary/actions/pain points appear separately, with matching quotes.
- [ ] A meeting with no stated problem yields no invented pain points.
- [ ] Denied admission times out with a useful error.
- [ ] Stop while waiting cancels without generating fake notes.
- [ ] An unavailable Ollama preserves the transcript and retry works later.
- [ ] Restart retains meeting history; export works; delete removes audio and notes.

No boxes above are pre-checked: live Google Meet, full Docker build, real transcription and local-model output have not been validated during initial development.
