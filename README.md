# AI Meeting Notes Bot

**Paste a Google Meet link → admit your bot → get a transcript, summary and pain points.**

Built by **Ali Ahmed Khoso**. A local, single-user project with no calendar integration and no paid AI API requirement.

> **Experimental preview:** The application and offline tests are implemented. A real Google Meet admission/audio test and the full Docker build have not been verified in the development environment. Google can block guest/automated entry and change its interface. This is not a production meeting service or a guarantee that every meeting will accept the bot.

## What it does

- Joins a Google Meet link as a visibly named recording bot, subject to host admission and guest-access settings.
- Captures meeting audio only after admission, using an isolated virtual audio output.
- Transcribes after you click **Stop & generate notes**, with local faster-whisper on CPU.
- Produces separate **Transcript**, **Summary & actions**, and **Pain points** tabs.
- Requires extracted notes to include a matching transcript quote. Incorrect evidence references are discarded.
- Saves meeting history locally, exports notes, retries analysis and deletes meeting data.
- Handles a denied/timed-out join, empty speech, failed model requests and interrupted jobs visibly.

**Not included:** Zoom, calendar auto-join, detecting when you personally enter a meeting, live transcription, reliable speaker names, meeting text-chat capture, automatic email delivery, or public multi-user hosting. “Full transcript” means captured spoken audio, not chat messages. Only speech after the bot is admitted is available.

## Why this version does not use Recall.ai or Vexa

This implementation uses a small Playwright Google Meet guest adapter and PulseAudio/FFmpeg capture directly, so it does not require a bot provider subscription or a GPU transcription server. The tradeoff is that Meet browser changes and guest restrictions can break joining. It never bypasses sign-in, CAPTCHA or host controls. Vexa can be considered later for a more extensive provider integration.

## Run on Windows, macOS or Linux with Docker

Install Git and Docker Engine + Compose (or Docker Desktop where its license applies). On Windows, use Linux containers / WSL 2. Start Docker first.

```bash
git clone https://github.com/Ali-Khoso/ai-meeting-notes-bot.git
cd ai-meeting-notes-bot
```

Create the settings file:

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```

```bash
# macOS / Linux
cp .env.example .env
```

Then run:

```bash
docker compose up --build -d
docker compose exec ollama ollama pull qwen2.5:3b
```

Open **http://localhost:8000**. The Ollama model must finish downloading before analysis can work. The first transcription also downloads the Whisper model; later runs reuse the cache. Internet is required for the meeting and initial downloads. There is no cloud AI API fallback.

### First real test (use your own short meeting)

1. Start a Google Meet meeting that allows guest requests. Explain the recording to participants and obtain agreement.
2. Paste its `https://meet.google.com/abc-defg-hij` link into the app. Give the meeting a title and confirm the recording checkbox.
3. Click **Join meeting**, then admit **Ali’s AI Notes Bot (recording)** in Google Meet.
4. Wait for the app to show **recording** before speaking. Say a clear problem and an action, for example: “We miss after-hours calls. Ali will check the voicemail process tomorrow.”
5. After 30–60 seconds, click **Stop & generate notes**. Keep Docker and the computer running.
6. Review the transcript first, then the summary and pain points. Check that evidence quotes match what was actually said.

Always use the Stop button at the end. The bot notices removal/disconnection and has a two-hour default limit, but may remain alone in a meeting after others leave. Stop during waiting cancels entry; it cannot immediately interrupt a browser navigation. Analysis and transcription finish in the background and may be slow on CPU.

## Hardware and cost

No paid Recall.ai, speech-to-text or LLM API is required. You supply hardware, internet, storage and electricity. Start with a short meeting; **16 GB RAM is a practical target, not a tested minimum or performance guarantee**. A small laptop may struggle with Docker, Chromium and models together. Try `WHISPER_MODEL=tiny` for lower transcription resource use (less accurate). Models and container images require several GB of disk space. This app processes one meeting at a time to prevent audio mixing.

## Architecture

| Component | Role |
|---|---|
| Python local HTTP server | Dashboard API, history and background jobs |
| Playwright Chromium | Requests guest entry into Google Meet |
| PulseAudio + FFmpeg | Captures the isolated browser audio to a WAV file |
| faster-whisper (CPU, int8) | Produces timestamped transcript segments |
| Ollama + Qwen 2.5 3B | Extracts notes from transcript chunks |
| Docker volumes | Persist models, audio and notes |

Long transcripts are processed in chunks, without silently dropping the remainder. The summary is a combined set of chunk-level notes, not a second global synthesis. Transcript prompts are treated as untrusted data. Quote validation helps review but does **not** prove that a model's interpretation, owner or deadline is correct. Verify important decisions manually. Mixed Urdu/English accuracy depends on the audio and model.

## Local data and privacy

- Participants must know and agree to recording. The bot's display name includes “recording”. The app does not send a separate in-meeting announcement.
- Audio and notes stay in the `meeting-data` Docker volume. AI inference stays in the Compose network. Google still receives the browser connection as part of the meeting.
- Delete removes the selected meeting folder, including audio and notes. Export downloads a plain-text report.
- The UI has no user accounts: it is for your own computer. Compose binds port 8000 to `127.0.0.1`. Do not publicly expose it or remove the host/origin checks.
- Secrets, recordings, transcripts and `.env` are excluded from Git. Model caches persist in separate volumes.
- `docker compose down` stops services and keeps data. Adding `-v` permanently removes all these volumes, including your recordings and models.

## Troubleshooting

See [setup and troubleshooting](docs/SETUP.md) and the [live acceptance checklist](docs/TESTING.md).

```bash
docker compose logs --tail=100 app
docker compose logs --tail=100 ollama
```

## Development checks

Core and API tests use Python's standard library; they do not download models or join meetings:

```bash
python -m unittest discover -s tests -v
```

To preview the dashboard without Docker: `python -m app.server`, then open localhost:8000. **Joining meetings still requires the Docker audio/browser environment.** No fake meeting results are shown by default.

## References

- [Playwright Docker documentation](https://playwright.dev/python/docs/docker)
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- [Ollama chat API](https://docs.ollama.com/api/chat)

The existing repository license is retained. Third-party tools and models have their own licenses.
