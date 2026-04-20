#!/usr/bin/env python3
"""CLI tool for searching, inspecting, and downloading Bilibili videos."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from html import unescape
from typing import Any
from urllib.parse import parse_qs, urlparse


SEARCH_API = "https://api.bilibili.com/x/web-interface/search/type"
VIEW_API = "https://api.bilibili.com/x/web-interface/view"


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

        return YoutubeDL
    except ImportError as exc:
        raise CliError("Missing dependency: yt-dlp. Run `pip install -r requirements.txt`.") from exc


def resolve_redirect(url: str) -> str:
    requests = _require_requests()
    try:
        response = requests.get(url, timeout=10, allow_redirects=True)
        response.raise_for_status()
        return response.url
    except Exception:
        return url


def extract_video_id(url: str) -> VideoId:
    """Extract BV or av id from any supported Bilibili URL."""
    normalized = resolve_redirect(url)

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


def _clean_title(raw: str) -> str:
    return unescape(re.sub(r"<[^>]+>", "", raw)).strip()


def search_videos(keyword: str, page: int, page_size: int) -> list[dict[str, Any]]:
    requests = _require_requests()
    params = {
        "search_type": "video",
        "keyword": keyword,
        "page": page,
        "page_size": page_size,
    }

    response = requests.get(SEARCH_API, params=params, timeout=10)
    response.raise_for_status()

    payload = response.json()
    if payload.get("code") != 0:
        raise CliError(f"Bilibili search API error: {payload.get('message', 'unknown error')}")

    result = payload.get("data", {}).get("result", [])
    output = []
    for item in result:
        bvid = item.get("bvid")
        output.append(
            {
                "title": _clean_title(item.get("title", "")),
                "author": item.get("author", ""),
                "duration": item.get("duration", ""),
                "play": item.get("play", 0),
                "danmaku": item.get("video_review", 0),
                "bvid": bvid,
                "url": f"https://www.bilibili.com/video/{bvid}" if bvid else "",
            }
        )
    return output


def fetch_basic_video_info(url: str) -> dict[str, Any]:
    requests = _require_requests()
    video_id = extract_video_id(url)
    params = {video_id.kind: video_id.value}

    response = requests.get(VIEW_API, params=params, timeout=10)
    response.raise_for_status()

    payload = response.json()
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


def download_video(url: str, output_dir: str, quality: str, container: str) -> None:
    YoutubeDL = _require_yt_dlp()
    os.makedirs(output_dir, exist_ok=True)

    if quality == "best":
        format_selector = "bestvideo+bestaudio/best"
    else:
        format_selector = f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]"

    options = {
        "format": format_selector,
        "outtmpl": os.path.join(output_dir, "%(title).120s [%(id)s].%(ext)s"),
        "merge_output_format": container,
        "noplaylist": False,
    }

    with YoutubeDL(options) as ydl:
        ydl.download([url])


def download_audio(url: str, output_dir: str, audio_format: str, audio_quality: str) -> None:
    YoutubeDL = _require_yt_dlp()
    os.makedirs(output_dir, exist_ok=True)

    options = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(output_dir, "%(title).120s [%(id)s].%(ext)s"),
        "noplaylist": False,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": audio_format,
                "preferredquality": audio_quality,
            }
        ],
    }

    with YoutubeDL(options) as ydl:
        ydl.download([url])


def _print_json(obj: Any) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def _print_search_results(results: list[dict[str, Any]]) -> None:
    if not results:
        print("No search results.")
        return

    for idx, item in enumerate(results, start=1):
        print(f"[{idx}] {item['title']}")
        print(f"    author: {item['author']} | duration: {item['duration']}")
        print(f"    play: {item['play']} | danmaku: {item['danmaku']}")
        print(f"    url: {item['url']}")


def _interactive_action(results: list[dict[str, Any]]) -> None:
    if not results:
        return

    while True:
        raw = input("Pick result index (or q): ").strip()
        if raw.lower() == "q":
            return
        if not raw.isdigit() or int(raw) < 1 or int(raw) > len(results):
            print("Invalid index.")
            continue

        chosen = results[int(raw) - 1]
        url = chosen.get("url")
        if not url:
            print("Cannot resolve video url for this result.")
            return

        action = input("Action [i=info, dv=download video, da=download audio, q=quit]: ").strip().lower()
        if action == "q":
            return
        if action == "i":
            _print_json(fetch_basic_video_info(url))
            return
        if action == "dv":
            download_video(url=url, output_dir="downloads/video", quality="best", container="mp4")
            print("Video download finished.")
            return
        if action == "da":
            download_audio(url=url, output_dir="downloads/audio", audio_format="mp3", audio_quality="192")
            print("Audio download finished.")
            return

        print("Unknown action.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bilibili CLI downloader")
    sub = parser.add_subparsers(dest="command", required=True)

    p_search = sub.add_parser("search", help="Search videos by keyword")
    p_search.add_argument("keyword", help="Keyword or sentence to search")
    p_search.add_argument("--page", type=int, default=1, help="Page index")
    p_search.add_argument("--limit", type=int, default=10, help="Results per page")
    p_search.add_argument("--json", action="store_true", help="Output JSON")
    p_search.add_argument("--interactive", action="store_true", help="Select next action after search")

    p_info = sub.add_parser("info", help="Fetch basic metadata by video URL")
    p_info.add_argument("url", help="Bilibili video URL")
    p_info.add_argument("--json", action="store_true", help="Output JSON")

    p_video = sub.add_parser("download-video", help="Download video by URL")
    p_video.add_argument("url", help="Bilibili video URL")
    p_video.add_argument("--quality", default="best", choices=["best", "1080", "720", "480", "360"], help="Video quality target")
    p_video.add_argument("--format", default="mp4", choices=["mp4", "mkv", "webm"], help="Video container")
    p_video.add_argument("--output", default="downloads/video", help="Output directory")

    p_audio = sub.add_parser("download-audio", help="Download audio by URL")
    p_audio.add_argument("url", help="Bilibili video URL")
    p_audio.add_argument("--audio-format", default="mp3", choices=["mp3", "m4a", "aac", "wav", "flac"], help="Audio format")
    p_audio.add_argument("--audio-quality", default="192", help="Audio quality kbps")
    p_audio.add_argument("--output", default="downloads/audio", help="Output directory")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "search":
            results = search_videos(keyword=args.keyword, page=args.page, page_size=args.limit)
            if args.json:
                _print_json(results)
            else:
                _print_search_results(results)
            if args.interactive:
                _interactive_action(results)
            return 0

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
            download_video(url=args.url, output_dir=args.output, quality=args.quality, container=args.format)
            print("Video download finished.")
            return 0

        if args.command == "download-audio":
            download_audio(url=args.url, output_dir=args.output, audio_format=args.audio_format, audio_quality=args.audio_quality)
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

