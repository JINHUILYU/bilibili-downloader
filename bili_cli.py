#!/usr/bin/env python3
"""CLI tool for inspecting and downloading Bilibili videos."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlparse


VIEW_API = "https://api.bilibili.com/x/web-interface/view"
VIDEO_QUALITY_ORDER = ["2160", "1440", "1080", "720", "480", "360"]
ALLOWED_VIDEO_HOSTS = {"www.bilibili.com", "bilibili.com", "b23.tv", "www.b23.tv"}
BILIBILI_API_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com/",
    "Origin": "https://www.bilibili.com",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


@dataclass
class VideoId:
    kind: str
    value: str


class CliError(RuntimeError):
    """Expected runtime error caused by invalid input or dependency issues."""


def _require_requests():
    try:
        import requests

        return requests
    except ImportError as exc:
        raise CliError("Missing dependency: requests. Run `pip install -r requirements.txt`.") from exc


def _require_yt_dlp():
    try:
        from yt_dlp import YoutubeDL
        from yt_dlp.utils import DownloadError

        return YoutubeDL, DownloadError
    except ImportError as exc:
        raise CliError("Missing dependency: yt-dlp. Run `pip install -r requirements.txt`.") from exc


def resolve_redirect(url: str) -> str:
    requests = _require_requests()
    try:
        response = requests.get(url, timeout=10, allow_redirects=True)
        response.raise_for_status()
        return response.url
    except requests.RequestException:
        return url


def extract_video_id(url: str) -> VideoId:
    """Extract BV or av id from any supported Bilibili URL."""
    normalized = resolve_redirect(_sanitize_input_url(url))

    bv_match = re.search(r"(BV[0-9A-Za-z]{10})", normalized)
    if bv_match:
        return VideoId(kind="bvid", value=bv_match.group(1))

    av_match = re.search(r"av(\d+)", normalized, flags=re.IGNORECASE)
    if av_match:
        return VideoId(kind="aid", value=av_match.group(1))

    parsed = urlparse(normalized)
    query = parse_qs(parsed.query)
    if "bvid" in query and query["bvid"]:
        return VideoId(kind="bvid", value=query["bvid"][0])
    if "aid" in query and query["aid"]:
        return VideoId(kind="aid", value=query["aid"][0])

    raise CliError("Cannot parse BV/av from URL. Please provide a valid Bilibili video URL.")


def _sanitize_input_url(url: str) -> str:
    stripped = url.strip()
    # Support pasted shell-escaped links like "...\\?a\\=1\\&b\\=2"
    return re.sub(r"\\([?&=])", r"\1", stripped)


def _validate_video_url(url: str) -> str:
    normalized = resolve_redirect(_sanitize_input_url(url))
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or parsed.netloc not in ALLOWED_VIDEO_HOSTS:
        raise CliError("Invalid Bilibili URL. Please provide a bilibili.com or b23.tv link.")
    return normalized


def _quality_fallback_chain(quality: str) -> list[str]:
    if quality == "best":
        return VIDEO_QUALITY_ORDER
    if quality not in VIDEO_QUALITY_ORDER:
        raise CliError(f"Unsupported quality value: {quality}")
    return VIDEO_QUALITY_ORDER[VIDEO_QUALITY_ORDER.index(quality) :]


def _build_video_format_selector(quality: str) -> str:
    heights = _quality_fallback_chain(quality)
    parts: list[str] = []
    for height in heights:
        parts.append(f"bestvideo[height<={height}]+bestaudio")
    for height in heights:
        parts.append(f"best[height<={height}]")
    parts.append("best")
    return "/".join(parts)


def _build_audio_format_selector() -> str:
    return "/".join(
        [
            "bestaudio[abr>=320]",
            "bestaudio[abr>=256]",
            "bestaudio[abr>=192]",
            "bestaudio[abr>=128]",
            "bestaudio",
            "best[height<=1080]",
            "best[height<=720]",
            "best[height<=480]",
            "best",
        ]
    )


def _api_get_json(api_url: str, params: dict[str, Any], api_name: str) -> dict[str, Any]:
    requests = _require_requests()
    try:
        response = requests.get(api_url, params=params, headers=BILIBILI_API_HEADERS, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise CliError(f"{api_name} request failed: {exc}") from exc
    except ValueError as exc:
        raise CliError(f"{api_name} returned invalid JSON.") from exc


def fetch_basic_video_info(url: str) -> dict[str, Any]:
    normalized = _validate_video_url(url)
    video_id = extract_video_id(normalized)
    params = {video_id.kind: video_id.value}

    payload = _api_get_json(VIEW_API, params=params, api_name="Bilibili view API")
    if payload.get("code") != 0:
        raise CliError(f"Bilibili view API error: {payload.get('message', 'unknown error')}")

    data = payload.get("data", {})
    stat = data.get("stat", {})
    return {
        "title": data.get("title", ""),
        "description": data.get("desc", ""),
        "play_count": stat.get("view", 0),
        "danmaku_count": stat.get("danmaku", 0),
        "bvid": data.get("bvid", ""),
        "aid": data.get("aid", 0),
        "url": f"https://www.bilibili.com/video/{data.get('bvid', '')}" if data.get("bvid") else url,
    }


def download_video(
    url: str,
    output_dir: str,
    quality: str,
    container: str,
    all_parts: bool = False,
    cookies_from_browser: str | None = None,
) -> None:
    YoutubeDL, DownloadError = _require_yt_dlp()
    normalized = _validate_video_url(url)
    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as exc:
        raise CliError(f"Cannot create output directory `{output_dir}`: {exc}") from exc

    options = {
        "format": _build_video_format_selector(quality),
        "outtmpl": os.path.join(output_dir, "%(title).120s [%(id)s].%(ext)s"),
        "merge_output_format": container,
        "noplaylist": not all_parts,
    }
    if cookies_from_browser:
        options["cookiesfrombrowser"] = (cookies_from_browser,)

    try:
        with YoutubeDL(options) as ydl:
            ydl.download([normalized])
    except DownloadError as exc:
        raise CliError(f"Video download failed: {exc}") from exc


def download_audio(
    url: str,
    output_dir: str,
    audio_format: str,
    audio_quality: str,
    all_parts: bool = False,
    cookies_from_browser: str | None = None,
) -> None:
    YoutubeDL, DownloadError = _require_yt_dlp()
    normalized = _validate_video_url(url)
    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as exc:
        raise CliError(f"Cannot create output directory `{output_dir}`: {exc}") from exc

    options = {
        "format": _build_audio_format_selector(),
        "outtmpl": os.path.join(output_dir, "%(title).120s [%(id)s].%(ext)s"),
        "noplaylist": not all_parts,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": audio_format,
                "preferredquality": audio_quality,
            }
        ],
    }
    if cookies_from_browser:
        options["cookiesfrombrowser"] = (cookies_from_browser,)

    try:
        with YoutubeDL(options) as ydl:
            ydl.download([normalized])
    except DownloadError as exc:
        raise CliError(f"Audio download failed: {exc}") from exc


def _print_json(obj: Any) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Bilibili CLI downloader\n"
            "支持视频信息查询、视频下载、音频下载。"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=(
            "示例:\n"
            "  python3 bili_cli.py info \"https://www.bilibili.com/video/BV1xx411c7mD\"\n"
            "  python3 bili_cli.py download-video \"https://www.bilibili.com/video/BV1Dk4y1j7oj?p=6\" --quality 1080 --format mp4\n"
            "  python3 bili_cli.py download-video \"https://www.bilibili.com/video/BV1Dk4y1j7oj\" --all-parts\n"
            "  python3 bili_cli.py download-audio \"https://www.bilibili.com/video/BV1xx411c7mD\" --audio-format mp3 --audio-quality 192\n"
            "  python3 bili_cli.py download-audio \"https://www.bilibili.com/video/BV1GQXBYTEtR\" --cookies-from-browser chrome\n\n"
            "说明:\n"
            "  1. 默认仅下载单个分P；使用 --all-parts 才会下载整套分P。\n"
            "  2. 支持输入带 shell 转义的链接（例如包含 \\? \\& \\=）。\n"
            "  3. 如遇 HTTP 412 错误，加 --cookies-from-browser 从浏览器提取 Cookie 绕过限制。"
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_info = sub.add_parser(
        "info",
        help="查询视频基础信息",
        description="根据 Bilibili 视频链接查询标题、简介、播放数、弹幕数等信息。",
    )
    p_info.add_argument("url", help="Bilibili video URL")
    p_info.add_argument("--json", action="store_true", help="Output JSON")

    p_video = sub.add_parser(
        "download-video",
        help="下载视频",
        description="下载视频（默认仅单个分P）。如需整套分P请加 --all-parts。",
    )
    p_video.add_argument("url", help="Bilibili video URL")
    p_video.add_argument("--quality", default="best", choices=["best", "1080", "720", "480", "360"], help="Video quality target")
    p_video.add_argument("--format", default="mp4", choices=["mp4", "mkv", "webm"], help="Video container")
    p_video.add_argument("--output", default="downloads/video", help="Output directory")
    p_video.add_argument("--all-parts", action="store_true", help="Download all parts for multi-part videos")
    p_video.add_argument(
        "--cookies-from-browser",
        default=None,
        metavar="BROWSER",
        help="Extract cookies from the given browser (e.g. chrome, firefox, safari) to bypass restrictions",
    )

    p_audio = sub.add_parser(
        "download-audio",
        help="下载音频",
        description="下载音频（默认仅单个分P）。如需整套分P请加 --all-parts。",
    )
    p_audio.add_argument("url", help="Bilibili video URL")
    p_audio.add_argument("--audio-format", default="mp3", choices=["mp3", "m4a", "aac", "wav", "flac"], help="Audio format")
    p_audio.add_argument("--audio-quality", default="192", help="Audio quality kbps")
    p_audio.add_argument("--output", default="downloads/audio", help="Output directory")
    p_audio.add_argument("--all-parts", action="store_true", help="Download all parts for multi-part videos")
    p_audio.add_argument(
        "--cookies-from-browser",
        default=None,
        metavar="BROWSER",
        help="Extract cookies from the given browser (e.g. chrome, firefox, safari) to bypass restrictions",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "info":
            info = fetch_basic_video_info(args.url)
            if args.json:
                _print_json(info)
            else:
                print(f"title: {info['title']}")
                print(f"description: {info['description']}")
                print(f"play_count: {info['play_count']}")
                print(f"danmaku_count: {info['danmaku_count']}")
                print(f"url: {info['url']}")
            return 0

        if args.command == "download-video":
            download_video(
                url=args.url,
                output_dir=args.output,
                quality=args.quality,
                container=args.format,
                all_parts=args.all_parts,
                cookies_from_browser=args.cookies_from_browser,
            )
            print("Video download finished.")
            return 0

        if args.command == "download-audio":
            download_audio(
                url=args.url,
                output_dir=args.output,
                audio_format=args.audio_format,
                audio_quality=args.audio_quality,
                all_parts=args.all_parts,
                cookies_from_browser=args.cookies_from_browser,
            )
            print("Audio download finished.")
            return 0

        parser.print_help()
        return 1
    except CliError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
