# yt-factory — Complete Project Guide & New Machine Setup

AI-powered YouTube video factory for the **Simply Decode** channel. One command
chain takes a topic from idea to uploaded YouTube video: research, script,
narration, stock footage, assembly, thumbnail, metadata, upload — with human
review gates in between. Runs locally, costs ~$0 (all free-tier services).

---

## 1. What this project is

```
ytf new                    creates videos/<date>_<topic>/ workspace
   TopicStage        Gemini suggests scored topics (or use --topic "...")
   ResearchStage     Gemini writes a fact brief           -> research.md
   ScriptStage       Gemini writes narration script       -> script.md
   MetadataStage     Gemini writes title/description/tags -> metadata.json
   NarrationStage    edge-tts speaks each paragraph       -> narration/*.mp3
   VisualsStage      Pexels clips matched per paragraph   -> visuals/*.mp4
   AssemblyStage     MoviePy renders synced montage       -> video.mp4
   ThumbnailStage    Pillow composes thumbnail            -> thumbnail.png
   UploadStage       YouTube Data API, private upload     -> upload.json
```

Key design points:

- **File-based workspaces**: every video is a folder under `videos/` with a
  `manifest.json` tracking per-stage status. Any stage can be re-run alone
  (`ytf retry <id> <stage>`); a crash resumes where it stopped.
- **Paragraph-unit sync**: the script's `[VISUAL: ...]` cues pair 1:1 with
  narration paragraphs, so footage changes exactly when the words change.
  No clip repeats (global dedup), nothing on screen longer than 6s.
- **Review gates** (`config/settings.yaml` → `automation.gates`): the pipeline
  pauses after `script`, `assembly`, and before finishing `upload` so you can
  inspect/edit artifacts, then continue with `ytf run <id>`.
- **Swappable providers**: LLM / TTS / images / upload each sit behind a small
  interface in `src/yt_factory/providers/`. Changing provider = config edit.
- Uploads default to **private** — you publish manually from YouTube Studio.

Costs: Gemini free tier (~6 LLM calls/video), edge-tts free, Pexels free
(20k requests/month), YouTube API free (10k quota units/day; upload = 1600).

---

## 2. New machine setup

Works on macOS, Windows, and Linux. No system ffmpeg needed (bundled via
`imageio-ffmpeg`). Requires **Python 3.12+** and **git**.

### 2.1 Clone and install

```bash
git clone https://github.com/Merrine/ai-youtube-automation.git
cd ai-youtube-automation
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest                           # 34 tests should pass
```

### 2.2 Secrets — copy from the old laptop (NOT in git)

Three secret files are gitignored and must be transferred manually
(AirDrop/USB — avoid email/cloud for these):

| File | What it is | If lost |
|---|---|---|
| `.env` | API keys | Recreate from `.env.example`; keys below |
| `client_secret.json` | Google OAuth desktop client | Re-download: console.cloud.google.com → project `ai-youtube-automation` → APIs & Services → Credentials |
| `youtube.token.json` | YouTube authorization token | Delete it; next upload opens the browser once to re-authorize |

Keys in `.env`:

- `GEMINI_API_KEY` — free, https://aistudio.google.com/apikey (account: merrine165@gmail.com)
- `PEXELS_API_KEY` — free, https://www.pexels.com/api/

All three files go in the repo root, same names.

### 2.3 Google/YouTube context (already done once, reference only)

- Google Cloud project: `ai-youtube-automation-504813` on merrine165@gmail.com
- YouTube Data API v3: enabled
- OAuth consent: External, testing mode, test user merrine165@gmail.com
- Channel: **Simply Decode** — when the OAuth browser window asks which
  account, always pick **Simply Decode** (not the personal channel)
- Channel is not yet phone-verified → custom thumbnails are skipped until
  verification at youtube.com/verify

### 2.4 Git identity + push access (this repo only)

```bash
git config user.name "Merrine"
git config user.email "merrin165@gmail.com"
```

Pushing uses the personal GitHub account **Merrine**. With GitHub CLI:

```bash
gh auth login --hostname github.com --git-protocol https --web   # login as Merrine
git config --add credential.helper ''
git config --add credential.helper '!f() { echo username=Merrine; echo "password=$(gh auth token --user Merrine)"; }; f'
```

(The two credential lines make this repo always push as Merrine even if the
machine's default GitHub identity is a work account.)

### 2.5 Verify everything

```bash
source .venv/bin/activate
ytf list                                  # shows existing video workspaces
ytf new --topic "Test Topic"              # exercises Gemini key
ytf run <video-id> --until research       # topic + research stages
```

---

## 3. Daily usage

```bash
ytf new                      # LLM proposes topics, picks best (or --topic "...")
ytf run <video-id>           # runs until next review gate
#   gate 1: read/edit script.md, then run again
#   gate 2: watch video.mp4, then run again -> uploads PRIVATE
ytf status <video-id>        # stage-by-stage table
ytf retry <video-id> <stage> # redo one stage (e.g. narration after voice change)
ytf list                     # all videos + progress
```

After upload: open YouTube Studio → review → set public manually.

Config lives in `config/settings.yaml`: channel lanes, video length,
max seconds per visual, review gates, upload visibility, TTS voice.
Prompt templates live in `config/prompts/*.md` — edit freely, no code changes.

---

## 4. Repo layout

```
config/
  settings.yaml        non-secret config (lanes, video specs, gates, providers)
  prompts/             LLM prompt templates (topic, research, script, metadata,
                       visual queries)
src/yt_factory/
  cli.py               Typer CLI (ytf ...)
  config.py            pydantic settings + secrets loading
  workspace.py         per-video folder + manifest (resume machinery)
  pipeline.py          stage orchestration + review gates
  script_parse.py      script.md -> paragraph units with visual cues
  stages/              one module per pipeline stage
  providers/           llm.py (Gemini), tts.py (edge-tts), images.py (Pexels),
                       youtube.py (upload + OAuth)
tests/                 34 tests, all providers faked
videos/                video workspaces (gitignored, stays local)
PLAN.md                original architecture plan
```

---

## 5. Troubleshooting

- **Gemini 503 Service Unavailable** — free-tier congestion, transient.
  `ytf run <id>` again; it resumes at the failed stage.
- **`invalidTags` on upload** — handled: tags auto-trimmed to a 400-char
  budget (YouTube hard limit is ~500 incl. quotes).
- **Thumbnail skipped on upload** — channel not phone-verified; verify at
  youtube.com/verify. Upload still succeeds.
- **OAuth browser says "access denied"** — the Google account isn't in the
  consent screen's test users; add it (console → Audience → Test users).
- **Push rejected / repo not found** — credential helper lines from 2.4
  missing; macOS keychain is serving a work token.
- **Windows**: everything works the same; scheduler (when built) uses Task
  Scheduler instead of launchd. Thumbnail fonts fall back to
  `C:/Windows/Fonts/arialbd.ttf` automatically.

## 6. Roadmap / not built yet

- Phase 6 automation: `ytf auto` + daily scheduler + failure notifications
  (user deferred)
- Sentence-level visual sync via edge-tts word timestamps
- Shorts auto-cut from the hook section (9:16 + burned captions)
- Caption/key-term overlays; set-thumbnail command for already-uploaded videos
- Pexels attribution block appended to video descriptions
