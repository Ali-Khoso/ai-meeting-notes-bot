## Vercel + database version

The new [`cloud/`](cloud/README.md) app stores imported Fathom transcripts and summaries in Supabase, with private sign-in. For Vercel deployment, set **Root Directory to `cloud`** and follow its setup guide. Imports are manual after meetings finish; automatic webhook syncing is not included. The Python version below remains available for local Ollama pain-point analysis.

# AI Meeting Notes Bot — Fathom Edition

**Fathom records your meeting. This app imports the transcript and summary, then extracts evidence-linked pain points with optional local AI.**

Built by **Ali Ahmed Khoso**. Runs directly in Windows Python. **No Docker, browser automation, FFmpeg or pip installation required.**

## What changed

The original experimental guest bot has been replaced with a read-only Fathom integration. Fathom handles admission, capture and transcription. Its API provides finished meeting content; it does not expose a public send-bot/join endpoint. You start or auto-record meetings through Fathom's app/extension, not this dashboard.

## Features

- Browse your accessible Fathom recordings, including additional pages.
- Import a selected recording's full spoken transcript, timestamps, supplied speaker names and Fathom summary.
- View separate **Transcript**, **Summary & actions**, and **Pain points** tabs.
- Optionally generate local notes/actions/pain points with Ollama; each retained note must cite a matching transcript quote.
- Re-import without creating duplicate meetings. If the transcript changes, stale local analysis is cleared.
- Retry failed analysis, export notes and delete local copies.
- API key stays in the Python process; it is not sent to the browser, written into meeting data, or committed to Git.

## 1. Set up Fathom

Create/sign into [Fathom](https://www.fathom.ai/) with the Google account you want to use for meetings. Install its Windows desktop app and Chrome extension through **Settings → Fathom Apps**. Keep the desktop app running and use the Chrome profile containing that extension.

For your desired **join when I enter a Google Meet** flow, enable impromptu/unscheduled Google Meet auto-recording under **Settings → Video Conferencing**. The extension detects Meet links; email sign-in alone does not detect meeting entry. If auto-record does not activate, use **Start Recording** in Meet, or **Add to Meeting** in Fathom's desktop drawer and paste the Meet link. Host admission and recording permissions still apply. Inform participants before recording.

This app does not require calendar integration. Configure Fathom's scheduled-meeting and sharing preferences separately to suit you. It does not change your account settings or send messages to attendees.

## 2. Run the dashboard on Windows

Install Python **3.10 or later** from [python.org](https://www.python.org/downloads/windows/) and Git if needed. In PowerShell:

```powershell
git clone https://github.com/Ali-Khoso/ai-meeting-notes-bot.git
cd ai-meeting-notes-bot
Copy-Item .env.example .env
notepad .env
```

Already cloned? Open the existing project folder, run `git pull`, and create `.env` only if it does not exist:

```powershell
git pull
if (!(Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

In Fathom, go to **User Settings → API Access**, generate a key, and add it to your **local** `.env` file:

```dotenv
FATHOM_API_KEY=your_actual_key_here
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b
```

Never paste your real key into chat, source code or GitHub. API access is documented as available on all Fathom plans, with account permissions and rate limits. The free plan and feature availability remain subject to Fathom's terms.

Start the app:

```powershell
py -3 -m app.server
```

Open **http://localhost:8000** and leave the terminal running. You can also double-click `start-windows.bat`. If `py` is unavailable but Python is on PATH, use `python -m app.server`.

After Fathom finishes processing a recording, click **Load my Fathom recordings → Import**. The transcript and Fathom summary work without Ollama or a GPT/Gemini key. Click **Load more recordings** for older calls. **Refresh from Fathom** fetches updates for the selected recording. This version uses manual import, not automatic webhook syncing.

## 3. Optional pain-point analysis — no Docker

Install the native [Ollama app](https://ollama.com/download) on your computer, then run:

```powershell
ollama pull qwen2.5:3b
```

Keep Ollama running. Select an imported meeting in the dashboard and click **Analyze pain points (Ollama)**. This also generates local summary/action notes. The Fathom summary remains separately labelled in the Summary tab. If Ollama is unavailable, imported content is preserved and analysis can be retried.

The model download is several GB and CPU analysis may be slow. Hardware, internet and electricity are your own costs; no paid AI API is used. Optional local analysis is not a claim that Fathom's paid AI features are free.

## Data and limitations

- Fathom processes and stores the original recording/transcript in its service. The imported copies and local analysis are saved in `data/` on your computer. This is **not** an entirely offline recording workflow.
- Deleting here removes only local copies. It does not delete the original in Fathom. Old Docker volumes, if any, are not migrated or deleted.
- The app binds to `127.0.0.1` and checks request hosts/origins. There is no login system: do not expose it publicly or deploy this unchanged as a multi-user site.
- Transcript means captured speech, not meeting text-chat messages. Speaker names come from Fathom and can be missing or wrong.
- Imported Fathom Markdown is displayed as plain text for safety. It is not passed to an HTML renderer.
- AI interpretation can still be wrong even with a matching quote. Verify decisions, owners and deadlines. Empty pain-point lists are valid.
- Long transcripts are processed in chunks and notes combined; this is not a global second-pass synthesis.
- No live transcript streaming, calendar access, meeting-join API or background auto-import is included.

## Tests and validation

```powershell
py -3 -m unittest discover -s tests -v
```

20 offline tests passed during this update: API shape normalization, pagination, duplicate imports, missing-key handling, secret redaction, cross-origin rejection, local deletion, saved-content recovery and evidence validation. Provider calls are mocked. **A live Fathom import and actual Ollama inference have not been tested with your account or hardware.** See [setup](docs/SETUP.md) and [acceptance checklist](docs/TESTING.md).

## API and setup references

- [Fathom API FAQ](https://developers.fathom.ai/faq)
- [API quickstart](https://developers.fathom.ai/quickstart)
- [Meeting listing](https://developers.fathom.ai/api-reference/meetings/list-meetings)
- [Transcript endpoint](https://developers.fathom.ai/api-reference/recordings/get-transcript)
- [Summary endpoint](https://developers.fathom.ai/api-reference/recordings/get-summary)
- [Google Meet setup](https://help.fathom.video/en/articles/449472)
- [Chrome extension](https://help.fathom.video/en/articles/640576)
- [Recording settings](https://help.fathom.video/en/articles/3239617)

The repository's existing license is retained. Fathom and Ollama are independent services/tools with their own terms and model licenses.
