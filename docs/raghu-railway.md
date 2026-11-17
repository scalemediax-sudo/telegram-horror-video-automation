# Raghu production on Railway or localhost

Deploy one Docker service with a persistent volume mounted at `/data`. Keep one replica when using SQLite. Allow at least 1 GB of persistent capacity for a ten-minute production with room to save sources and retakes. The Telegram bot accepts a story title, `/generate`, or “start the mission”. It delivers the finished video back to the requesting private chat. YouTube publishing is separate and disabled unless explicitly configured.

For localhost, install Python 3.11, FFmpeg/FFprobe, and OpenSSH. Run `python -m pip install -r requirements.txt vastai==1.9.1`, put the variables below in the ignored `.env` or `.env.telegram`, and run `python run.py`. Keep that process running while using Telegram. With the default SQLite setup, save and keep the local `data/` folder. The app uses Vast for image and motion generation. Use a separate Telegram bot token for each concurrently running installation.

## Service variables

Use the [Vast-backed environment template](../.env.raghu.example). Paid generation starts disabled in the template. Enable it after configuring your own credentials and checking the rental limits. Start with **Other → 30 seconds** for the first live test. The 10-minute option needs a host and budget that cover the full job.

```dotenv
MEDIA_BACKEND=raghu
TELEGRAM_PRODUCTION_MODE=live
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=
TELEGRAM_ALLOWED_USER_IDS=
ALLOW_PAID_GENERATION=false
DEEPSEEK_API_KEY=
DEEPSEEK_MODEL=deepseek-flash
RAGHU_PLANNER=clone
GEMINI_API_KEY=
GEMINI_VISION_MODEL=
GEMINI_TTS_MODEL=gemini-3.8-flash-tts
GEMINI_TTS_VOICE=Riko
RAGHU_NARRATION_PROVIDER=edge
VAST_API_KEY=
VAST_SSH_PRIVATE_KEY=
HF_TOKEN=
RAGHU_GPU=RTX_5090
RAGHU_MOTION_MODEL=ltx
RAGHU_LTX_END_FRAME=false
RAGHU_QUANTIZATION=fp8
RAGHU_TARGET_SECONDS=600
RAGHU_MAX_RENTAL_MINUTES=150
RAGHU_MAX_HOURLY_USD=0.77
RAGHU_MAX_JOB_USD=2.00
```

Use a dedicated SSH key and paste its full private-key text into Railway. The Hugging Face read token must have access to the pinned LTX-2.5 weights. Select a Gemini model with image input and JSON output that is enabled on your API key. The Vast spend limit screens offers using the estimated rent and transfer cost and sets a runtime deadline. Vast's final invoice can vary. Use a short target such as 30 seconds for a first end-to-end integration test.

## SSH from both installations

The app opens an outbound SSH connection to the rented Vast instance and uses SCP to copy files. Railway includes OpenSSH in the Docker image. Locally, check `ssh -V`, `ffmpeg -version`, and `vastai --version` in the terminal that runs the app. Add the dedicated public key to the Vast account. Locally set `VAST_SSH_KEY_PATH` to the private-key file. On Railway set `VAST_SSH_PRIVATE_KEY` to the full private key. The unattended worker requires a key that can authenticate in batch mode. A public inbound port on the local computer is unnecessary for the polling Telegram bot.

The worker tries both the direct endpoint and the SSH endpoint Vast reports when they differ. If a live rental is available, use the SSH host and port shown in Vast to test from the same environment that runs the bot. A refused port or a startup timeout can indicate a Vast host problem. An authentication error calls for checking the key and the Vast account.

With `RAGHU_PLANNER=clone`, DeepSeek uses the Clone YouTube automation repo's literal templates in the order hook, short Hindi story, character sheets, empty backgrounds, and scene prompts. The narration and occasional character lines are locked before the scene prompts. Each scene gets one visible beat, an opening pose and a camera instruction. Existing saved plans remain usable. FLUX.2 Klein creates the canonical and scene images. Production uses LTX 2.5 Distilled with FP8 casting and CPU offload at 1280×768, 121 frames and 24 fps. Each request contains one reviewed opening image, and the written prompt provides the ending. The job's `raghu-generation-plan.json` records the generation inputs. Dialogue in this LTX path is dubbed and has no native lip-sync guarantee.

The worker checks stills, shot continuity, and rendered motion. It checks every decoded frame for technical defects and uses samples plus direct video review when the first review disputes the action. In new clone runs, opening images and motion clips get up to two targeted retakes. Reviews can still miss defects. Keep the data directory or Railway volume attached so retries can reuse the saved work and startup can reconcile the rental.

## Recover a job from Telegram

1. Run `/setup` to check required settings and tools without renting a GPU. Use `/raghu_review_check` to exercise the review API without a GPU.
2. Use `/status` to see the last error and the available recovery buttons. **Retry this step** resumes the same job using saved scripts, images, and clips. For exhausted asset retakes, it opens another bounded round. A saved clip awaiting its first review is checked before the GPU starts. **Start new video** requests a duration for a separate production.
3. If a new rental fails to establish SSH because its endpoint is unreachable, the worker verifies that contract has stopped before trying another eligible host within budget. If a previously working host cannot restart, retry when capacity returns. Check the existing contract in Vast before abandoning it. A stopped contract can still accrue disk charges.
4. Credentials, access or credit errors need a fix in the provider account or deployment settings. Resolve the error before retrying the same job. For a deadline or budget error, check the rental limits against the remaining work. Retry preserves those limits. If Telegram itself is offline, check the local process or Railway logs and the bot token, then use `/status` again.

If Gemini stays unavailable after its request retries, the worker stops the current Vast instance and preserves its disk. After Vast confirms the stop, the worker checks saved assets again at 15-second intervals between attempts, up to three recovery checks. It restarts the same GPU only after reviews respond and remaining work still needs it. An ongoing outage leaves the instance stopped and the job available for a later Telegram retry.

After the approved source assets are copied, the service checks that the Vast rental is stopped or released. With `RAGHU_NARRATION_PROVIDER=edge`, it uses Madhur for Hindi narration and chooses the character voice from the script. Use `gemini` for the Gemini narrator. Chatterbox is optional and requires a usable narrator-only WAV on persistent storage, set with `RAGHU_NARRATOR_REFERENCE`. LTX opening-only scenes preserve five seconds of picture and fit their own narration. An original synthesized horror bed is ducked beneath the narrator. The 6.5-second opening includes the Kaali Kitaab intro and a Hindi fiction disclaimer. Editing scratch is on the container filesystem, and the full-quality export stays on the volume. Optional S3 storage enables a private full-quality link for Telegram files above its upload limit.

## Timing benchmark

From this repository, with Vast, Hugging Face, and the rental limit variables configured:

```bash
python -m tools.benchmark_raghu /path/to/render-plan.json /path/to/approved-stills /path/to/new-benchmark-dir
```

This reuses the exact stills, motion prompts, seeds and frame counts from Raghu. It records per-clip timings and a separate warm average. The renderer uses the configured quantization and defaults to CPU offload. Only use the `--offload none` comparison on a GPU with enough memory.

## One-image production checks

- `/raghu_image` rents Vast, generates one still, and calls the configured vision API from Railway. It saves the reviewer’s observations and latency, verifies Vast teardown, then sends the original PNG and verdict to Telegram. A failed verdict is also a valid result for this check.
- `/raghu_motion` starts a separate rental and generates and reviews one new still. If it passes, it renders exactly one five-second LTX shot, copies and verifies the MP4, and destroys the rental before Telegram delivery. A rejected still ends the run without motion.
- The two checks bypass DeepSeek and narration. They still require the Telegram, Gemini vision, Vast, and SSH variables. The motion check also needs the Hugging Face token. The setup, image, vision and animation times are separate.

## Generated image review

Use `/image_review still-001.png` in Telegram to see the original image, verdict, style classification and visible evidence. Use `/image_review rejected-still-001.png` to inspect a candidate saved before its retake. Character sheets and backgrounds can be opened by their generated filenames.

Railway sends the candidate and its references to Gemini Vision. It computes the pass decision from style, content match, and visible defects. A 3D-looking, mixed, unclear, or mismatched image is flagged. A persistent failure stops the job before motion. The classification describes appearance. It cannot identify the software that rendered a PNG.

The next independent image begins rendering immediately after the previous image is saved. Railway reviews completed images concurrently while Vast continues rendering. After the batch, failed images get a retake. Motion still waits for all required starting images to pass.

Use `/raghu_review_check` to run the review-only check from Telegram. It reuses the original approved Raghu gate image and logged prompt, then asks the same reviewer to evaluate the image against a deliberately different scene. Success requires the reviewer to recognize the 2D style, flag the visible unheld flashlight against the original prompt, and reject the unrelated scene. This check uses the Railway and Gemini setup and does not rent a Vast GPU.
