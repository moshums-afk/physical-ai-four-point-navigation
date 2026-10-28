"""Regression tests for odd desktop sizes and falsely successful captures."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from recording_checks import recording_geometry, validate_recording


class RecordingTests(unittest.TestCase):
    def test_empty_capture_is_not_success(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)/'empty.mp4'
            p.touch()
            with self.assertRaisesRegex(RuntimeError, 'empty'):
                validate_recording(p, 255, (982, 584))

    def test_encoder_failure_is_not_success(self):
        with self.assertRaisesRegex(RuntimeError, 'code 1'):
            validate_recording(Path('unused.mp4'), 1, (982, 584))

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'Needs ffmpeg and ffprobe')
    def test_odd_desktop_can_be_encoded_and_probed(self):
        # testsrc emits an odd RGB frame; using a YUV color source can silently
        # round its size and would fail to exercise the reported 981-pixel bug.
        with tempfile.TemporaryDirectory() as folder:
            video = Path(folder)/'odd.mp4'
            size = recording_geometry(981, 585)
            subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-f', 'lavfi',
                '-i', 'testsrc=size=981x585:rate=1', '-frames:v', '2',
                '-vf', f'pad={size[0]}:{size[1]}:0:0', '-c:v', 'libx264',
                '-threads', '1', '-pix_fmt', 'yuv420p', str(video)], check=True)
            metadata = validate_recording(video, 0, size)
            self.assertEqual((metadata['width'], metadata['height']), (982, 586))
            self.assertGreater(metadata['duration_seconds'], 0)
            self.assertGreater(metadata['bytes'], 0)


if __name__ == '__main__':
    unittest.main()
