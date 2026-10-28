"""Geometry and output checks for real desktop recordings."""
import json
import math
from pathlib import Path
import subprocess


def recording_geometry(width, height):
    """Capture the full desktop and pad odd dimensions to even H.264 dimensions."""
    if width < 1 or height < 1:
        raise ValueError('Desktop dimensions must be positive')
    return width + width % 2, height + height % 2


def validate_recording(path, recorder_exit_code, expected_size):
    path = Path(path)
    # ffmpeg normally returns 255 when it finishes in response to SIGINT.
    if recorder_exit_code not in (0, 255):
        raise RuntimeError(f'ffmpeg exited with code {recorder_exit_code}')
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError('Video is missing or empty')
    probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'format=duration:stream=codec_name,width,height',
        '-of', 'json', str(path)], capture_output=True, text=True, timeout=20)
    if probe.returncode:
        raise RuntimeError('ffprobe cannot read the recorded video')
    try:
        data = json.loads(probe.stdout)
        stream = data['streams'][0]
        duration = float(data['format']['duration'])
        size = (int(stream['width']), int(stream['height']))
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise RuntimeError('Video metadata is incomplete') from exc
    if not math.isfinite(duration) or duration <= 0:
        raise RuntimeError('Video duration is not positive')
    if stream['codec_name'] != 'h264' or size != tuple(expected_size):
        raise RuntimeError(f'Unexpected codec or dimensions: {stream}')
    return {'codec': stream['codec_name'], 'width': size[0], 'height': size[1],
            'duration_seconds': duration, 'bytes': path.stat().st_size}
