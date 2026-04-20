import unittest

from bili_cli import CliError, extract_video_id


class TestExtractVideoId(unittest.TestCase):
    def test_extract_bvid_from_standard_url(self):
        video_id = extract_video_id("https://www.bilibili.com/video/BV1xx411c7mD")
        self.assertEqual(video_id.kind, "bvid")
        self.assertEqual(video_id.value, "BV1xx411c7mD")

    def test_extract_aid_from_standard_url(self):
        video_id = extract_video_id("https://www.bilibili.com/video/av170001")
        self.assertEqual(video_id.kind, "aid")
        self.assertEqual(video_id.value, "170001")

    def test_raise_on_invalid_url(self):
        with self.assertRaises(CliError):
            extract_video_id("https://example.com/not-bilibili")


if __name__ == "__main__":
    unittest.main()

