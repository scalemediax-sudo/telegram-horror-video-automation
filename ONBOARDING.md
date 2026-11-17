# Onboarding

In Codex, say **“Clone this repository”** and paste its GitHub URL. After opening the checkout, say **“onboarding.”** The first question is **Railway or localhost?** Codex prepares only the selected host, then walks you through the credentials and asks for two media paths.

## 1. Pick where the bot runs

- **Localhost.** Install Python 3.11, FFmpeg (including FFprobe) and the OpenSSH client. From the repo, run `python -m pip install -r requirements.txt vastai==1.9.1`. Copy `.env.raghu.example` to `.env`. Run `python run.py` after entering credentials and installing the assets. Keep that process and the computer running when you use Telegram. Keep the generated `data/` folder so jobs can resume.
- **Railway.** In Railway, choose **New Project → Deploy from GitHub Repo** and select your fork. Keep one replica and attach a persistent volume at `/data`. Copy the settings from `.env.raghu.example` into the service’s **Variables** tab. The Docker image installs Python, FFmpeg, OpenSSH and the Vast CLI. [Volumes](https://docs.railway.com/volumes)

Both hosts use the same writer, motion model, review, voice clone and editor. The AI weights are downloaded to the rented Vast GPU host in both modes. Localhost installs the controller and editing tools on your computer.

## 2. Enter your own credentials

- **Telegram.** Open **BotFather**, send `/newbot`, and follow its prompts. Paste the token as `TELEGRAM_BOT_TOKEN`. After the service starts, send `/id` to your new bot in a private chat. Put the number it returns in `TELEGRAM_ALLOWED_USER_IDS` and restart or redeploy. Use one running deployment per bot token. [BotFather](https://t.me/BotFather)
- **DeepSeek.** Open **API Keys**, click **Create new API key**, and paste it as `DEEPSEEK_API_KEY`. Keep `DEEPSEEK_MODEL=deepseek-flash`. Ensure the account has API credit. [DeepSeek API Keys](https://platform.deepseek.com/api_keys)
- **Gemini.** Open **API Keys** in Google AI Studio, click **Create API key**, and paste it as `GEMINI_API_KEY`. The template uses `GEMINI_VISION_MODEL=gemini-3.1-flash-lite`, the model used on the approved setup. Run the review check below to verify access. If the model is unavailable, use a Flash Lite model ID with images, video and structured JSON enabled for your project. [Google AI Studio API Keys](https://aistudio.google.com/app/apikey)
- **Vast.ai.** In **Manage Keys**, create an API key with access to list offers and create, start, stop and release instances. Paste it as `VAST_API_KEY`. Fund your Vast account and set the hourly rate, job estimate cap and rental window in the template. [Vast Manage Keys](https://cloud.vast.ai/manage-keys/)
- **Vast SSH.** Run `ssh-keygen -t ed25519 -f path/to/vast-worker` and use a dedicated key that can run in batch mode. Add the contents of `vast-worker.pub` in Vast’s SSH keys section. On localhost set `VAST_SSH_KEY_PATH` to the full path of the private key file. On Railway paste the full private-key text into `VAST_SSH_PRIVATE_KEY`. [Vast SSH setup](https://github.com/vast-ai/docs/blob/main/guides/get-started/quickstart.mdx)
- **Hugging Face.** Open the LTX model page, sign in and request access if prompted. Go to **Settings → Access Tokens → Create new token**, select read access for the model, and paste it as `HF_TOKEN`. [LTX-2.5 weights](https://huggingface.co/Lightricks/LTX-2.5) · [Hugging Face tokens](https://huggingface.co/settings/tokens)

Use the ignored `.env` locally or Railway Variables. When asking Codex for a setup check, say which step is done and keep the credential values in those settings.

## 3. Give Codex your media paths

- Provide the path to your **combined intro and disclaimer video** (at least six seconds). If they’re two files, tell Codex their order so it can join them first. The editor prepends the result to every story.
- Provide the path to a **6–30-second narrator-only sample** you’re authorized to use. For the same narrator on both hosts, use the same sample, including for the approved Web 6 voice if you have that file. Use speech with minimal music or other voices. The clone applies to narration; characters keep their own dialogue voices.
- On **localhost**, Codex can install them with `python -m app.install_assets opening "PATH_TO_INTRO"` and `python -m app.install_assets narrator "PATH_TO_NARRATOR"`.
- On **Railway**, use the service’s SSH connection to stream each file to the same installer on its volume. In a shell with binary-safe stdin redirection, use `ssh -T SERVICE_SSH_DESTINATION "cd /app && python -m app.install_assets opening -" < intro.mp4` and the equivalent `narrator -` command for the audio. Use the destination and SSH key from your own service. On Windows, Codex can pass file bytes to the SSH subprocess directly. [Railway SSH](https://docs.railway.com/cli/ssh)

Voice cloning is enabled in the template. The setup asks for the sample so it can keep the narrator consistent across installs.

## 4. Check it from your phone

- Send `/setup`. Fix missing variables and tools first. Then send `/raghu_review_check` to check Gemini without a GPU.
- When ready to spend on a first run, set `ALLOW_PAID_GENERATION=true`, restart the app, then tap **Generate → Other → 30 seconds**. The selected time is the full story. The opening video is added separately. Longer options give a complete story with a final payoff.
- If a run stops, send `/status` and select **Retry this step**. The bot uses saved work and shows the reason if it needs you to fix credentials, budget, or provider access. See the [recovery guide](docs/raghu-railway.md).
