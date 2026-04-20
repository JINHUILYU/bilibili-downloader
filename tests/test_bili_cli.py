import unittest

from bili_cli import (
    CliError,
    _build_audio_format_selector,
    _build_video_format_selector,
    _validate_video_url,
    build_parser,
    extract_video_id,
)


class TestExtractVideoId(unittest.TestCase):
    def test_extract_bvid_from_standard_url(self):
        video_id = extract_video_id("https://www.bilibili.com/video/BV1xx411c7mD")
        self.assertEqual(video_id.kind, "bvid")
        self.assertEqual(video_id.value, "BV1xx411c7mD")

    def test_extract_aid_from_standard_url(self):
        video_id = extract_video_id("https://www.bilibili.com/video/av170001")
        self.assertEqual(video_id.kind, "aid")
        self.assertEqual(video_id.value, "170001")

    def test_extract_bvid_with_long_query_params(self):
        video_id = extract_video_id(
            "https://www.bilibili.com/video/BV1NGHGzJEfx/?trackid=abc&track_id=def&source_id=5637"
        )
        self.assertEqual(video_id.kind, "bvid")
        self.assertEqual(video_id.value, "BV1NGHGzJEfx")

    def test_raise_on_invalid_url(self):
        with self.assertRaises(CliError):
            extract_video_id("https://example.com/not-bilibili")


class TestFormatFallbackStrategy(unittest.TestCase):
    def test_video_format_prefers_high_then_fallback(self):
        selector = _build_video_format_selector("1080")
        self.assertTrue(selector.startswith("bestvideo[height<=1080]+bestaudio"))
        self.assertIn("/bestvideo[height<=720]+bestaudio", selector)
        self.assertIn("/bestvideo[height<=480]+bestaudio", selector)
        self.assertIn("/bestvideo[height<=360]+bestaudio", selector)
        self.assertTrue(selector.endswith("/best"))

    def test_audio_format_prefers_high_then_fallback(self):
        selector = _build_audio_format_selector()
        self.assertTrue(selector.startswith("bestaudio[abr>=320]"))
        self.assertIn("/bestaudio[abr>=192]", selector)
        self.assertIn("/best[height<=720]", selector)
        self.assertTrue(selector.endswith("/best"))


class TestInputValidation(unittest.TestCase):
    def test_validate_bilibili_url(self):
        self.assertIn("BV1xx411c7mD", _validate_video_url("https://www.bilibili.com/video/BV1xx411c7mD"))

    def test_validate_reject_non_bilibili_url(self):
        with self.assertRaises(CliError):
            _validate_video_url("https://example.com/video/BV1xx411c7mD")

    def test_search_command_removed(self):
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["search", "python"])


if __name__ == "__main__":
    unittest.main()
