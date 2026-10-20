# Setup and troubleshooting

## Before starting

Use Docker's Linux container mode. The app needs a guest-accessible Google Meet URL; it does not sign into your Google account. A school/company host may block guests. Use a personal test meeting if your administrator does not allow guest access. Never try to circumvent administrator restrictions.

The exact supported URL format is `https://meet.google.com/abc-defg-hij`. Query strings are removed. Short URLs, arbitrary websites and Zoom URLs are rejected.

## Problems

| Symptom | What to check |
|---|---|
| Browser never requests admission | Guest access may be blocked, Google may require sign-in, or Meet's page may have changed. The bot reports failure rather than bypassing controls. Check `app/bot.py` against the current English Meet UI. |
| Waiting | Admit the named bot from your host meeting. Default timeout is five minutes. |
| No speech | Confirm status was recording before talking. Check that the remote participants were audible and not muted. |
| FFmpeg failure | Use `docker compose logs app`. The detailed log is in `/app/data/<meeting-id>/audio.ffmpeg.log` inside the app container. |
| Transcription takes time | First run downloads the model. CPU transcription may be slower than the meeting duration. Try a shorter meeting or change `WHISPER_MODEL=base` to `tiny`. |
| Analysis failed / model missing | Run `docker compose exec ollama ollama pull qwen2.5:3b`. After it finishes, select the saved meeting and click Analyze transcript again. |
| Container exits / memory pressure | Close other apps, increase Docker memory or use smaller models. This has not been benchmarked on your laptop. |
| Bot stays after everyone leaves | Use Stop & generate notes. The maximum recording limit defaults to two hours. |
| App restarted during a job | The job is marked interrupted. Saved transcript can be re-analyzed. Partial audio is retained, but automatic audio recovery is not implemented. |

After changing `.env`, recreate the app: `docker compose up -d --force-recreate app`.

## Language and accuracy

The default `base` Whisper model is multilingual. Set `TRANSCRIPT_LANGUAGE=en` for English or `ur` for Urdu; leave blank for automatic detection. Urdu/English code-switching can be inaccurate. Transcription does not identify people: do not assume a generated name identifies a speaker.

## Local file layout

Each meeting has `meeting.json`, `audio.wav` and an FFmpeg diagnostic log. Never commit this directory. Exported notes contain private meeting content too.

## Expected limitations

This is browser automation, not Google's official meeting recording API. Live admission/audio must be tested on your meeting/account. Browser layouts, anti-bot protections and organization policies can prevent it from working. Zoom is a separate future adapter, not an implemented feature.
