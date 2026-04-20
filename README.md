# Bilibili CLI Downloader (MVP)

This repository now includes a Python command-line MVP for:

- Searching Bilibili videos by keyword.
- Fetching basic video metadata (title, description, play count, danmaku count).
- Downloading video with configurable quality and container.
- Downloading audio with configurable format and quality.

## Files

- `bili_cli.py`: CLI entry script.
- `tests/test_bili_cli.py`: unit tests for URL id parsing.
- `requirements.txt`: Python dependencies.

## Quick start

```bash
python3 -m pip install -r requirements.txt
python3 bili_cli.py --help
```

## Usage examples

```bash
python3 bili_cli.py search "python 教程" --limit 5
python3 bili_cli.py info "https://www.bilibili.com/video/BV1xx411c7mD"
python3 bili_cli.py download-video "https://www.bilibili.com/video/BV1xx411c7mD" --quality 1080 --format mp4
python3 bili_cli.py download-audio "https://www.bilibili.com/video/BV1xx411c7mD" --audio-format mp3 --audio-quality 192
```

## Test

```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

## Notes

- Downloading depends on network availability and Bilibili access conditions.
- Audio conversion is handled by `yt-dlp` with ffmpeg-backed post-processing.
- Use this tool only for content you are legally allowed to access and store.

