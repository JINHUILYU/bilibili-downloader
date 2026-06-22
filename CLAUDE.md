# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies (uses uv)
uv venv && source .venv/bin/activate && uv pip install -r requirements.txt

# Run all tests
python3 -m unittest discover -s tests -p "test_*.py"

# Run a single test
python3 -m unittest tests.test_bili_cli.TestExtractVideoId.test_extract_bvid_from_standard_url
```

There is no lint step configured.

## Architecture

Single-entry CLI: `bili_cli.py`. Three subcommands via `argparse`:

- `info` — query video metadata via Bilibili view API (`VIEW_API`)
- `download-video` — download video via `yt-dlp`
- `download-audio` — download audio via `yt-dlp` + FFmpeg post-processing

`main()` routes parsed args to feature functions and normalizes exit codes: `CliError` → 2, `KeyboardInterrupt` → 130.

## Key conventions

- **Lazy imports**: `_require_requests()` / `_require_yt_dlp()` import on first use and raise `CliError` with install hints if missing — never import `requests` or `yt_dlp` at module level.
- **Error handling**: feature functions raise `CliError` for expected failures; `main()` handles stderr output and exit code mapping. Use `CliError` for user-facing errors, not bare exceptions.
- **URL handling pipeline** (layered, each step builds on the prior):
  1. `_sanitize_input_url()` — strip shell escapes (`\?`, `\&`, `\=`) from pasted links
  2. `resolve_redirect()` — follow short-link redirects (b23.tv etc.)
  3. `_validate_video_url()` — enforce `bilibili.com` / `b23.tv` hosts only
  4. `extract_video_id()` — parse `bvid` or `aid` from the normalized URL
- **Download format strategy**: quality-first with descending fallback chain. Video: `_build_video_format_selector` builds `bestvideo[height<=N]+bestaudio` candidates ending in `best`. Audio: `_build_audio_format_selector` tries `bestaudio[abr>=320]` down to `best`.
- **Multi-part handling**: default is single-part (`noplaylist=True`); `--all-parts` downloads the full playlist.
- **Cookie support**: `--cookies-from-browser` (e.g. `chrome`, `firefox`, `safari`) passes cookies to yt-dlp to bypass Bilibili's 412/geo-restriction.
- **Defaults**: video output → `downloads/video`, audio output → `downloads/audio`, audio format → `mp3` @ 192kbps, video container → `mp4`.
- **JSON output**: use `_print_json(obj)` (sets `ensure_ascii=False`).
- **Keep artifacts untracked**: `downloads/`, caches, venv, IDE files are in `.gitignore`.
