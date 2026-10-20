# TikTok Live Recorder

CLI tool to record TikTok live streams, remux FLV streams to MP4 via FFmpeg, and optionally upload to Telegram.

## Commands

- **Sync dependencies**: `uv sync`
- **Run recorder (Manual)**: `uv run python src/main.py -user <username>`
- **Run recorder (Automatic)**: `uv run python src/main.py -user <username> -mode automatic -automatic_interval 5`
- **Run recorder (Followers)**: `uv run python src/main.py -mode followers`
- **Run full test suite**: `uv run pytest`
- **Run targeted test**: `uv run pytest tests/test_tiktok_recorder.py -v`
- **Run linter**: `uv run ruff check .`
- **Format code**: `uv run ruff format .`

## Gotchas

- **TLS Fingerprint Blocking**: TikTok blocks standard HTTP clients; `curl_cffi` with Chrome impersonation (`chrome136`) is used in `src/http_utils/http_client.py`. Do not replace with plain `requests` outside Termux.
- **Regional / Login Restrictions**: TikTok redirects requests from certain regions to login (`StatusCode.REDIRECT`). Provide an HTTP proxy via `-proxy` or configure valid session cookies in `cookies.json`.
- **FFmpeg File Locking on Windows**: Background write buffers can retain file handles. Ensure `VideoManagement.wait_for_file_release()` verifies the file handle is freed before invoking FFmpeg remuxing.
- **Multi-user vs URL/Room ID**: Passing multiple comma-separated users (`-user a,b`) forks separate worker processes via `multiprocessing`. Never combine multi-user input with `-room_id` or `-url`.
- **Stream Extension Pattern**: Recorder saves temporary streams as `*_flv.mp4` before remuxing to clean `.mp4`. Do not alter this naming suffix without updating `convert_flv_to_mp4` in `src/utils/video_management.py`.

## Conventions

- **Python Version**: Requires Python >= 3.11.
- **Exceptions**: All application exceptions must inherit from `TikTokRecorderError` in `src/utils/custom_exceptions.py`.
- **Import Resolution**: `src/` is added to `sys.path` in `src/main.py`; internal imports are absolute relative to `src/` (e.g., `from core.tiktok_recorder import TikTokRecorder`).
- **Version Tracking**: Version changes must be synced across `pyproject.toml` and `src/utils/enums.py` using `bump-my-version`.
