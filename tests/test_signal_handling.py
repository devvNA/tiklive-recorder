import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.tiktok_recorder import TikTokRecorder  # noqa: E402
from main import _run_in_venv, record_user  # noqa: E402
from utils.enums import Mode  # noqa: E402
from utils.recorder_config import RecorderConfig  # noqa: E402


def test_run_in_venv_propagates_normal_exit():
    fake_proc = MagicMock()
    fake_proc.wait.return_value = 0

    with patch("subprocess.Popen", return_value=fake_proc):
        with pytest.raises(SystemExit) as exc_info:
            _run_in_venv("python")
        assert exc_info.value.code == 0


def test_run_in_venv_handles_keyboard_interrupt_gracefully():
    fake_proc = MagicMock()
    # First wait raises KeyboardInterrupt (simulating Ctrl+C), second wait returns 0 after child finishes
    fake_proc.wait.side_effect = [KeyboardInterrupt, 0]

    with patch("subprocess.Popen", return_value=fake_proc):
        with pytest.raises(SystemExit) as exc_info:
            _run_in_venv("python")
        assert exc_info.value.code == 0


def test_run_in_venv_force_terminates_on_second_keyboard_interrupt():
    fake_proc = MagicMock()
    # User hits Ctrl+C twice
    fake_proc.wait.side_effect = [KeyboardInterrupt, KeyboardInterrupt]

    with patch("subprocess.Popen", return_value=fake_proc):
        with pytest.raises(SystemExit) as exc_info:
            _run_in_venv("python")
        fake_proc.terminate.assert_called_once()
        assert exc_info.value.code == 130


def test_automatic_mode_exits_on_interrupted_flag():
    config = RecorderConfig(mode=Mode.AUTOMATIC, user="test_user", cookies={})
    recorder = TikTokRecorder(config)
    recorder.tiktok = MagicMock()
    recorder.tiktok.get_room_id_from_user.return_value = "123456"

    # Simulate manual_mode setting _interrupted to True (as happens on Ctrl+C during recording)
    def fake_manual_mode():
        recorder._interrupted = True

    recorder.manual_mode = fake_manual_mode
    recorder.automatic_mode()
    assert recorder._interrupted is True


def test_automatic_mode_exits_on_keyboard_interrupt():
    config = RecorderConfig(mode=Mode.AUTOMATIC, user="test_user", cookies={})
    recorder = TikTokRecorder(config)
    recorder.tiktok = MagicMock()
    recorder.tiktok.get_room_id_from_user.side_effect = KeyboardInterrupt

    # Should exit cleanly without raising
    recorder.automatic_mode()


def test_record_user_catches_keyboard_interrupt():
    config = RecorderConfig(mode=Mode.MANUAL, user="test_user", cookies={})
    with patch("core.tiktok_recorder.TikTokRecorder.run", side_effect=KeyboardInterrupt):
        # Should catch KeyboardInterrupt and not raise
        record_user(config)
