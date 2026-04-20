# Bilibili 命令行下载器（MVP）

这是一个 Python 命令行工具，支持以下能力：

- 获取视频基础信息（标题、简介、播放数、弹幕数）
- 下载视频（可配置清晰度与封装格式）
- 下载音频（可配置音频格式与码率）

## 主要文件

- `bili_cli.py`：CLI 入口与核心逻辑
- `tests/test_bili_cli.py`：单元测试
- `requirements.txt`：依赖列表

## 快速开始（使用 uv 管理环境）

```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
python3 bili_cli.py --help
```

## 使用示例

```bash
python3 bili_cli.py info "https://www.bilibili.com/video/BV1HcQxBuEBp"
python3 bili_cli.py download-video "https://www.bilibili.com/video/BV1HcQxBuEBp" --quality 1080 --format mp4
python3 bili_cli.py download-audio "https://www.bilibili.com/video/BV1HcQxBuEBp" --audio-format mp3 --audio-quality 192
```

## 测试

```bash
# 全量测试
python3 -m unittest discover -s tests -p "test_*.py"

# 单个测试
python3 -m unittest tests.test_bili_cli.TestFormatFallbackStrategy.test_video_format_prefers_high_then_fallback
```

## 说明

- 下载依赖网络环境及 Bilibili 可访问性。
- 音频转换由 `yt-dlp` + ffmpeg 后处理完成。
- 仅下载你有合法权限访问与保存的内容。
- 仅接受 `bilibili.com` 或 `b23.tv` 链接，非法链接会被显式拒绝。
- 下载策略已实现为“高质量优先，失败后按链路降级”（视频与音频均适用）。
