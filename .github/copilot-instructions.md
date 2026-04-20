# Copilot Instructions for `bilibili-downloader`

## Build, test, and lint commands

This repository is a Python CLI project and currently has no dedicated build step.

```bash
# install dependencies
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# run CLI help
python3 bili_cli.py --help

# run full test suite
python3 -m unittest discover -s tests -p "test_*.py"

# run a single test
python3 -m unittest tests.test_bili_cli.TestExtractVideoId.test_extract_bvid_from_standard_url
```

There is no lint command configured in the repository at this time.

## High-level architecture

- The project is centered on a single entry module: `bili_cli.py`.
- `build_parser()` defines three subcommands: `info`, `download-video`, `download-audio`.
- `main()` routes parsed args to domain functions and normalizes process exit behavior:
  - expected user/dependency/runtime issues raise `CliError` and return exit code `2`
  - `KeyboardInterrupt` returns `130`
- Network and external integrations are separated by function:
  - metadata: Bilibili view API (`VIEW_API`)
  - media download: `yt-dlp` wrapper functions (`download_video`, `download_audio`)
- URL normalization and ID extraction are centralized in `extract_video_id()` + `resolve_redirect()`.
- Tests currently focus on video ID parsing behavior (`tests/test_bili_cli.py`).

## Key conventions in this codebase

- Keep dependencies lazily imported through `_require_requests()` / `_require_yt_dlp()` and surface missing dependencies as `CliError` with actionable install hints.
- For user-facing error paths, prefer raising `CliError` in feature functions and letting `main()` handle final stderr output and exit code mapping.
- Input links should be validated as Bilibili URLs (`bilibili.com` / `b23.tv`) before metadata or download actions.
- Maintain output compatibility:
  - JSON output must use `_print_json(..., ensure_ascii=False)` behavior.
  - Human-readable output is plain text with stable field names used in existing commands.
- Preserve current CLI defaults unless explicitly changing behavior:
  - video output default: `downloads/video`
  - audio output default: `downloads/audio`
  - video quality choices: `best`, `1080`, `720`, `480`, `360`
- Download format strategy should stay "quality-first with fallback chain" for both `download_video` and `download_audio`.
- Keep these URLs as the current manual download regression examples:
  - `https://www.bilibili.com/video/BV1NGHGzJEfx/`
  - `https://www.bilibili.com/video/BV1KgSdBZELv/`
- Generated/runtime artifacts should remain untracked, especially `downloads/`, caches, and local IDE/venv files as defined in `.gitignore`.
