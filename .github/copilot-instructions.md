# Copilot Instructions for `bilibili-downloader`

## Build, test, and lint commands

This repository is a Python CLI project with `uv` for environment setup and `unittest` for tests.

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
- `build_parser()` defines three CLI subcommands only: `info`, `download-video`, `download-audio` (search was intentionally removed).
- `main()` routes parsed args to domain functions and normalizes process exit behavior:
  - expected user/dependency/runtime issues raise `CliError` and return exit code `2`
  - `KeyboardInterrupt` returns `130`
- Network and external integrations are separated by function:
  - metadata: Bilibili view API (`VIEW_API`) through `_api_get_json(...)`
  - media download: `yt-dlp` wrapper functions (`download_video`, `download_audio`)
- URL handling is layered:
  - `resolve_redirect(...)` normalizes short/redirect links
  - `_validate_video_url(...)` enforces allowed hosts (`bilibili.com`, `b23.tv`)
  - `extract_video_id(...)` extracts `bvid`/`aid`
- Tests in `tests/test_bili_cli.py` cover URL parsing/validation, removed search command, and media format fallback selectors.

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
- Download format strategy is intentionally "quality-first with fallback chain":
  - video: `_build_video_format_selector(...)` builds descending quality candidates
  - audio: `_build_audio_format_selector(...)` tries high bitrate first, then fallback
- Generated/runtime artifacts should remain untracked, especially `downloads/`, caches, and local IDE/venv files as defined in `.gitignore`.
