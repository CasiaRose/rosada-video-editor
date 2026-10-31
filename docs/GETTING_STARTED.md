# Getting started

You do not need to know how to code. You need this folder on your computer and an AI assistant that can work in that folder (Cursor, Claude Code, Codex, or a Grok assistant with access to your files). The assistant reads `AGENTS.md` and does the technical steps. You make the creative decisions.

## 1. Download the project

**Easiest:** on the GitHub page, click the green **Code** button, then **Download ZIP**. Unzip it. You will get a folder named `rosada-video-editor`.

**If you already use Git:** on that same **Code** button, copy the HTTPS address. In a terminal:

```bash
git clone <paste the address here>
cd rosada-video-editor
```

Put the folder somewhere you can find, such as Documents. Remember the location.

## 2. Open it with an assistant

- **Cursor:** File → Open Folder, and choose the unzipped folder. Start a chat in that window.
- **Claude Code:** open a terminal in that folder and run `claude`.
- **Codex or another desktop agent:** open the same folder as the workspace so the assistant can see `AGENTS.md` and `README.md`.

The assistant should be allowed to run commands on your computer. Installing ffmpeg and Python packages needs that.

## 3. Paste this as your first message

Copy everything in the box, paste it into the chat, and send it.

```text
I'm a creator, not a programmer. This folder is the short-form video editor.

Please do these steps in order, and stop to ask me whenever you need a decision:

1. Check that ffmpeg and Python 3.10 or newer are installed. If something is missing, tell me the exact install step for my computer and wait until I confirm it works.
2. Install the Python packages from requirements.txt in a virtual environment.
3. Help me create my style profile before any editing. Ask me the questionnaire, or measure a reference video if I attach one. Show me the result in plain language and wait for my OK.
4. Ask how I want the video to sound. If I want ElevenLabs, tell me how to set ELEVENLABS_API_KEY in my environment myself. Do not ask me to paste the key in this chat.
5. When I give you raw footage, show me an edit plan and wait for my OK before you render.
6. Then edit, run the checks, and show me the report. If a check failed or did not run, say so. Do not call the video done.
7. Help me leave review notes and tell me where the exported file is.
```

Then answer its questions. Have a sample of your own footage ready, or a short video whose pacing you like, if you want the style drafted from a reference.

## 4. What you decide

The assistant should not pick your look for you. You decide:

- Colors, fonts, captions, and where the opening text sits
- How fast the edit feels and how much b-roll you want
- Whether music and sound effects are the simple built-in sounds or ElevenLabs
- When a cut is actually finished

Your footage stays on your computer. It is not part of this project’s files on GitHub.

## If something goes wrong

**“ffmpeg: command not found” or “ffprobe: command not found”**

The video tools are not installed.

- Mac: install Homebrew from https://brew.sh if you do not have it, then run `brew install ffmpeg`
- Windows: install ffmpeg from https://www.gyan.dev/ffmpeg/builds/ (release essentials) and follow their steps to add it to PATH, or `winget install Gyan.FFmpeg`
- Linux: `sudo apt install ffmpeg` (Debian or Ubuntu) or the equivalent for your distro

Close the terminal or chat tool and open it again, then ask the assistant to run `ffmpeg -version`. You should see a version number.

**“python: command not found” or the version is older than 3.10**

- Mac: `brew install python@3.12`
- Windows: install Python 3.12 from https://www.python.org/downloads/ and tick “Add python.exe to PATH”
- Linux: `sudo apt install python3 python3-venv python3-pip`

Ask the assistant to run `python3 --version`. The number should start with 3.10 or higher.

**“No module named …” after install**

The assistant used the system Python instead of the virtual environment. Ask it to run commands with `.venv/bin/python` (Mac or Linux) or `.venv\Scripts\python` (Windows), from this project folder.

**The assistant starts rendering immediately**

Stop it. Tell it to follow `AGENTS.md`: style profile first, then a plan, and no render until you say yes.

**You do not want to pay for sound**

Say “use the local sound.” Leave `ELEVENLABS_API_KEY` unset. The editor will synthesize a simple bed and effects.

**A check says it did not run**

The video is not finished. Ask the assistant which check did not run and to fix that before exporting.
