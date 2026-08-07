# yt-factory

Personal AI-powered YouTube video automation pipeline. Generates educational
explainer videos end to end: topic → research → script → narration → visuals →
assembly → thumbnail → metadata → upload. Human review gates before publishing.

See [PLAN.md](PLAN.md) for the full architecture.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # fill in API keys as phases require them
```

## Usage

```bash
ytf new --topic "How WiFi Works"   # create a video workspace
ytf run <video-id>                 # run pipeline (pauses at review gates)
ytf status <video-id>              # stage-by-stage status
ytf retry <video-id> <stage>       # re-run one stage
ytf list                           # all videos
```

The pipeline pauses at the review gates configured in `config/settings.yaml`
(`automation.gates`). Inspect/edit the artifacts in the video's folder under
`videos/`, then `ytf run <video-id>` again to continue.

## Development

```bash
pytest        # tests
ruff check .  # lint
mypy src      # types
```

## Status

- [x] Phase 1 — skeleton: config, logging, workspace/manifest, pipeline, CLI
- [x] Phase 2 — content: topic, research, script, metadata (Gemini free tier)
- [x] Phase 3 — media: narration (edge-tts), visuals (Pexels), thumbnail (Pillow)
- [x] Phase 4 — video assembly (MoviePy + bundled ffmpeg, Ken Burns slideshow)
- [ ] Phase 5 — YouTube upload (OAuth)
- [ ] Phase 6 — automation: scheduler, notifications
