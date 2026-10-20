# Product Requirements Document (PRD): TikTok Live Recorder

## 1. Executive Summary

- **Problem Statement**: Content creators, researchers, and archivists need a reliable, automated way to capture and preserve ephemeral TikTok live streams without manual screen recording or quality degradation.
- **Proposed Solution**: A lightweight CLI and daemon application that detects when specified TikTok creators are broadcasting live, streams raw video/audio chunks directly from TikTok CDNs, remuxes them to MP4 via FFmpeg, and optionally uploads finished recordings to Telegram.
- **Success Criteria**:
  - Live stream capture success rate >= 95% on public, accessible live streams without captchas.
  - Video remuxing overhead <= 30 seconds for 1-hour streams using direct stream-copy (`-c copy`).
  - Zero packet drop / data corruption under stable network conditions (> 10 Mbps).
  - CLI argument validation responds within < 100ms.

---

## 2. User Experience & Functionality

### User Personas
- **Content Archivist**: Needs to monitor creators 24/7 and auto-record streams as soon as they go live.
- **Media Researcher**: Downloads live sessions for sociological or media analysis, requiring original stream quality and exact timestamps.
- **Casual Viewer**: Wants to record a specific scheduled live stream manually by username or room ID.

### User Stories & Acceptance Criteria

- **Story 1 (Manual Recording)**:
  - *As a* user, *I want to* specify a TikTok username, URL, or room ID *so that* I can record an ongoing live broadcast immediately.
  - *Acceptance Criteria*:
    - Accepts `-user <username>`, `-url <url>`, or `-room_id <id>`.
    - Returns error within 3 seconds if target user is not currently broadcasting.
    - Saves output file with naming pattern `TK_<user>_<YYYY.MM.DD_HH-MM-SS>_flv.mp4` then converts to `.mp4`.

- **Story 2 (Automatic Monitoring Mode)**:
  - *As an* archivist, *I want to* poll a creator at set intervals *so that* recording starts automatically whenever they go live.
  - *Acceptance Criteria*:
    - Polling interval defaults to 5 minutes, configurable via `-automatic_interval <min>`.
    - Handles network reconnections and stream end gracefully without crashing the daemon process.

- **Story 3 (Followers Auto-Record Mode)**:
  - *As a* creator manager, *I want to* record all live streams from accounts followed by my profile *so that* I do not have to enter usernames manually.
  - *Acceptance Criteria*:
    - Uses session cookies from `cookies.json` to retrieve `sec_uid` and followed accounts.
    - Spawns background recording threads for live accounts, capped to avoid resource exhaustion.

- **Story 4 (Telegram Backup)**:
  - *As a* remote user, *I want* completed recordings sent to my Telegram chat *so that* I can view them on mobile.
  - *Acceptance Criteria*:
    - Triggered via `-telegram` flag and credentials in `telegram.json`.
    - Enforces Telegram size limits (2 GB for regular accounts, 4 GB for Telegram Premium).

### Non-Goals
- **In-App Video Editing**: No trimming, filtering, or subtitle editing beyond FFmpeg remuxing and bitrate capping.
- **GUI / Web Dashboard**: Project is strictly a CLI utility and daemon runner; no web interface in core scope.
- **Bypassing Paid / Subscriber-Only Lives**: Only publicly accessible or authenticated cookie-accessible sessions are captured.

---

## 3. AI System Requirements

- **Tool Requirements**: N/A (Rule-based HTTP scraper and stream downloader; no LLM/AI model runtime required).
- **Evaluation Strategy**: N/A.

---

## 4. Technical Specifications

### Architecture Overview
1. **CLI Layer (`src/main.py`, `src/utils/args_handler.py`)**: Parses CLI flags, validates parameter combinations, checks dependencies (FFmpeg, Python libraries).
2. **Network & Scraping Engine (`src/core/tiktok_api.py`, `src/http_utils/http_client.py`)**:
   - Uses `curl_cffi` to impersonate browser TLS signatures (`chrome136`) to bypass cloud anti-scraping blocks.
   - Extracts live room status, `sec_uid`, and CDN pull URLs (FLV/HLS).
3. **Recording & Stream Engine (`src/core/tiktok_recorder.py`)**:
   - Streams incoming bytes into a 512 KB chunk buffer.
   - Writes directly to temporary disk file to keep memory consumption < 100 MB.
4. **Media Processing Engine (`src/utils/video_management.py`)**:
   - Invokes FFmpeg via `ffmpeg-python` or custom path.
   - Remuxes FLV container to standard H.264/AAC MP4 without re-encoding unless `-bitrate` is specified.
5. **Storage & Delivery Layer (`src/upload/telegram.py`)**:
   - Telethon client for asynchronous file delivery to designated Telegram `chat_id`.

### Integration Points
- **TikTok Webcast & Web API**: Webcast room check API (`https://webcast.tiktok.com/webcast/room/info/`), HTML scraping for user room ID.
- **Third-Party Fallbacks**: EulerStream API (`https://tiktok.eulerstream.com`) and TikRec (`https://tikrec.com`) when direct scraping fails.
- **Telegram MTProto API**: via Telethon for post-recording delivery.

### Security & Privacy
- **Local Credentials**: `cookies.json` and `telegram.json` contain sensitive session tokens; ignored in `.gitignore`.
- **Proxy Support**: Native HTTP/HTTPS proxy support (`-proxy`) for regional restrictions and privacy masking.

---

## 5. Risks & Roadmap

### Phased Rollout
- **Phase 1 (Core CLI & Stability - Current)**: CLI arguments, multi-process user recording, FLV stream capture, FFmpeg MP4 remuxing.
- **Phase 2 (Resilience & Proxy Rotation - v7.8)**: Dynamic proxy rotation pool, automatic retry on stream stalls, automated headless cookie refresher.
- **Phase 3 (Alerts & Webhooks - v8.0)**: Discord/Slack webhook notifications upon recording start/stop.

### Technical Risks
- **TikTok API Breaking Changes**: Frequent obfuscation of room info endpoints and CDN tokens.
  - *Mitigation*: Fallback mechanisms through secondary scrapers (EulerStream/TikRec) and TLS fingerprint impersonation (`curl_cffi`).
- **Disk Saturation**: High-bitrate 1080p60 streams can generate ~2-4 GB per hour.
  - *Mitigation*: Optional duration limits (`-duration <sec>`) and post-processing bitrate compression (`-bitrate`).
