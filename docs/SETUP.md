# Fathom setup and troubleshooting

## How joining works

Use your chosen Google account to sign into Fathom. Install its desktop app and Google Meet Chrome extension from Fathom Settings → Fathom Apps. Enable the extension in the Chrome profile you use for calls and permit it on meet.google.com. Keep the Fathom app open.

Under Settings → Video Conferencing, review the Google Meet toggle for impromptu/unscheduled auto-recording. When you open a Meet link, the extension can trigger Fathom. If it does not, use Start Recording in Meet or paste the URL into the desktop app's Add to Meeting control. The meeting host may have to admit the notetaker. Your email alone is not an auto-join trigger.

Fathom handles recording notices and meeting controls. Review recording and sharing settings yourself; this project never changes them. For Zoom, connect Zoom through Fathom and follow its own app setup. The dashboard imports completed Fathom records regardless of their meeting platform.

## Connect this dashboard

1. Generate a key under Fathom User Settings → API Access.
2. Put it in local `.env` as `FATHOM_API_KEY=...`.
3. Stop any old server with Ctrl+C. Start `py -3 -m app.server` from the project folder.
4. Open localhost:8000. Load recordings, select one, and import.
5. Use optional native Ollama for the extra pain-point section.

## Troubleshooting

| Problem | Action |
|---|---|
| Localhost refuses connection | Keep the Python terminal open. Start the app from the repository folder. |
| Old join-bot page is visible | Stop the old Python server, run git pull, restart and refresh the browser. |
| Key not configured | Add FATHOM_API_KEY to .env, save, and restart. Existing old .env files may have only Docker settings. |
| HTTP 401 | Replace an incorrect or revoked Fathom key locally. Do not share it in screenshots. |
| HTTP 403 / missing recording | Confirm you can view the recording in the account that generated the key. |
| No recordings | Record a short call with Fathom and wait for its processing. Use Load more for older results. |
| Transcript not ready | Wait and import again. This integration is post-meeting only. |
| Summary not available | The transcript remains usable; refresh the recording later. |
| Rate limit | Wait a minute. Avoid repeatedly clicking import. |
| Pain-point analysis fails | Start native Ollama and run ollama pull qwen2.5:3b. Retry analysis; the imported transcript is retained. |
| Python launcher missing | Try python -m app.server, or install Python with its Windows launcher. |

## Migration

The previous experimental Docker bot lives in Git history. The current app no longer captures audio itself. Existing local meeting JSON remains readable; Docker volume contents are not automatically copied into the new local `data/` directory. No user recording data is removed by the update.

## Sources

- https://help.fathom.video/en/articles/449472
- https://help.fathom.video/en/articles/640576
- https://help.fathom.video/en/articles/3239617
- https://developers.fathom.ai/quickstart
