# AI YouTube Automation — Architecture Plan

Personal automation system for one educational YouTube channel. Python. Human review before publish. MVP goal: one video, end-to-end, uploaded.

---

## 1. Core Design Decisions

### 1.1 Pipeline as a sequence of stages
The workflow is a linear pipeline. Each stage is a class with one job, a common interface, and file-based inputs/outputs:

```
TopicStage → ResearchStage → ScriptStage → NarrationStage → VisualsStage
           → AssemblyStage → ThumbnailStage → MetadataStage → UploadStage
```

Every stage:
- reads its inputs from the **project workspace** (a per-video folder on disk),
- writes its outputs back to the workspace,
- records success/failure in a **manifest** (`manifest.json`) inside that folder.

Why file-based instead of in-memory: any stage can be re-run in isolation, the pipeline is resumable after a crash, and a human can inspect/edit any intermediate artifact (e.g. fix the script by hand) before the next stage runs. This is the single most important decision for reliability and for the "human review before publishing" requirement.

### 1.2 Per-video workspace layout
```
videos/
  2026-08-07_how-wifi-works/
    manifest.json          # stage statuses, timestamps, config snapshot
    topic.json             # chosen topic + category + angle
    research.md            # gathered facts + sources
    script.md              # narration script, sectioned
    narration/             # audio files (per-section + combined)
    visuals/               # images / clips, keyed to script sections
    video.mp4              # assembled output
    thumbnail.png
    metadata.json          # title, description, tags
    upload.json            # YouTube video ID, status, publish time
```

### 1.3 Providers behind interfaces
Every external service sits behind a small abstract interface (Python `Protocol` or ABC), with concrete implementations selected via config:

| Interface        | MVP implementation            | Later options                |
|------------------|-------------------------------|------------------------------|
| `LLMProvider`    | Claude API                    | others                       |
| `TTSProvider`    | ElevenLabs or OpenAI TTS      | Azure, local (Kokoro/Piper)  |
| `ImageProvider`  | Stock photos (Pexels API, free) | AI images (DALL·E/SDXL)    |
| `VideoAssembler` | MoviePy (ffmpeg under hood)   | direct ffmpeg templates      |
| `Uploader`       | YouTube Data API v3           | —                            |

Why: providers are the most likely thing to change (cost, quality, rate limits). Swapping must be a config edit, not a refactor.

### 1.4 Human review gates
The pipeline has named checkpoints where it can pause and wait for approval:
- after **script** (most important — cheapest point to fix quality),
- after **assembly** (watch the video),
- before **upload** (final gate; upload defaults to `private` visibility anyway).

MVP: gates are manual — the CLI stops and you re-run with `--continue` after reviewing files. Automation phase can relax them per-config.

---

## 2. Package Structure

```
ai-youtube-automation/
├── pyproject.toml               # deps, tooling config (ruff, mypy, pytest)
├── .env.example                 # documented env vars, no secrets in repo
├── config/
│   ├── settings.yaml            # non-secret config: providers, paths, video specs
│   └── prompts/                 # LLM prompt templates, one file per task
├── src/yt_factory/
│   ├── __init__.py
│   ├── cli.py                   # Typer CLI — entry point
│   ├── config.py                # pydantic-settings: loads yaml + env vars
│   ├── logging.py               # structured logging setup
│   ├── workspace.py             # per-video folder + manifest management
│   ├── pipeline.py              # stage orchestration, resume logic
│   ├── stages/                  # one module per stage
│   │   ├── base.py              # Stage ABC: name, run(workspace), inputs/outputs
│   │   ├── topic.py
│   │   ├── research.py
│   │   ├── script.py
│   │   ├── narration.py
│   │   ├── visuals.py
│   │   ├── assembly.py
│   │   ├── thumbnail.py
│   │   ├── metadata.py
│   │   └── upload.py
│   └── providers/               # external service adapters
│       ├── llm.py               # LLMProvider protocol + Claude impl
│       ├── tts.py
│       ├── images.py
│       └── youtube.py
├── tests/
│   ├── test_config.py
│   ├── test_workspace.py
│   └── stages/                  # per-stage tests with mocked providers
└── videos/                      # workspaces (gitignored)
```

Notes:
- `src/` layout (not flat) — standard for installable, testable packages.
- Prompts live in `config/prompts/*.md`, not in code — editing prompt quality shouldn't require touching Python.
- History/logging: `manifest.json` per video is the history; a top-level `videos/index.json` (or SQLite later) lists all runs.

---

## 3. Key Technology Choices

| Concern         | Choice                     | Why |
|-----------------|----------------------------|-----|
| CLI             | **Typer**                  | Typed, minimal boilerplate, subcommands map to pipeline verbs |
| Config          | **pydantic-settings + YAML** | Validated typed config, env-var overrides for secrets |
| Logging         | stdlib `logging` + rich console handler + per-video file handler | No heavy deps; logs land in workspace too |
| LLM             | **Claude API** (`anthropic` SDK) | Script quality is the product; strongest writing model |
| TTS             | ElevenLabs (quality) — decide at Phase 3 | Cost vs quality tradeoff, isolated behind interface |
| Video           | **MoviePy** | Pythonic, good enough for slideshow-style: images + Ken Burns pans + crossfades + narration audio |
| YouTube         | **google-api-python-client** OAuth flow | Only real option; one-time browser auth, refresh token stored locally |
| Testing         | pytest, providers mocked   | Stages are unit-testable because providers are injected |
| Lint/format     | ruff (+ mypy)              | One fast tool |

Video style for MVP: narrated slideshow — stock/AI images with slow zoom/pan, crossfade transitions, text overlays for key terms, background music bed. This is achievable and looks respectable; motion-graphic animation is a future enhancement.

---

## 4. CLI Surface (MVP)

```
ytf new [--topic "How WiFi Works"]     # create workspace, run topic stage (or accept given topic)
ytf run <video-id> [--until script]    # run pipeline stages until a gate or given stage
ytf status <video-id>                  # show manifest: which stages done/pending/failed
ytf retry <video-id> <stage>           # re-run one stage
ytf upload <video-id>                  # final gate, explicit command
ytf list                               # all video workspaces + statuses
```

`--until` + `retry` + file-based workspace = the whole human-review story with no extra machinery.

---

## 5. Build Order (maps to your phases)

**Phase 1 — Skeleton (first PR)**
1. `pyproject.toml`, `src/` layout, ruff/mypy/pytest config
2. `config.py` — settings model, `.env` + YAML loading
3. `logging.py`
4. `workspace.py` + `manifest` — create/read/update per-video folders
5. `cli.py` — `new`, `status`, `list` working against empty stages
6. `stages/base.py` + `pipeline.py` with a no-op dummy stage to prove orchestration

**Phase 2 — Words:** topic → research → script → metadata stages (all LLM; prompts in `config/prompts/`)

**Phase 3 — Media:** narration (TTS), visuals (stock images keyed to script sections), thumbnail

**Phase 4 — Video:** assembly stage with MoviePy

**Phase 5 — YouTube:** OAuth setup, upload stage (defaults to `private`)

**Phase 6 — Automation:** scheduler, retries, notifications — reuses `retry`/manifest machinery already built.

Automation design:
- `ytf auto` command: runs the full pipeline with no gates, uploads as **private** (or with a `publishAt` scheduled time), then sends a notification (email/Telegram) with a review link.
- Automation level is a config setting, not code: `automation.gates: [script, assembly, upload]` (manual) → `[]` + private upload (semi-auto) → `[]` + public upload (full auto). Recommended progression: semi-auto first — AI does all the work, human keeps a 30-second publish approval on the phone.
- Scheduler is a thin trigger around `ytf auto`:
  - Mac available daily → `launchd` job (macOS-native cron), $0.
  - Needs to run unattended with the Mac off → small VPS (~€4/mo Hetzner) or GitHub Actions cron. Pipeline is file-based and stateless between stages, so relocating later is copy + `.env`, no refactor.
- Failure handling: any stage failure leaves the manifest at the failed stage; the next scheduled run retries from there instead of starting a new video. Notification on failure includes the stage name and log tail.

Each phase ends with something runnable. After Phase 2 you can already read generated scripts; after Phase 4 you have watchable MP4s locally.

---

## 6. Risks / Things to Decide Later

- **YouTube API quota**: uploads cost 1600 units of a 10,000/day default quota — fine for 1–2 videos/day, but the OAuth consent screen setup (Google Cloud project) is fiddly one-time work.
- **TTS cost**: ElevenLabs ~$5–22/mo depending on volume; decide when Phase 3 starts.
- **Visuals quality** is the biggest "looks cheap" risk. Stock-photo slideshow is the MVP; budget iteration time here.
- **Fact accuracy**: research stage should capture sources in `research.md`; script prompt instructed to only use researched facts. Full fact-verification is a listed future enhancement.
- **Copyright**: stock sources must be license-safe (Pexels/Pixabay OK); background music from YouTube Audio Library.
