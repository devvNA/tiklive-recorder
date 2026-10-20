import sys
import time
from http.client import HTTPException
from pathlib import Path
from threading import Thread

from requests import RequestException

from core.tiktok_api import TikTokAPI
from utils.logger_manager import logger
from utils.recorder_config import RecorderConfig
from utils.video_management import VideoManagement
from utils.custom_exceptions import LiveNotFound, UserLiveError, TikTokRecorderError
from utils.enums import Mode, Error, TimeOut, TikTokError
from utils.terminal_ui import display_success_card


class TikTokRecorder:
    def __init__(self, config: RecorderConfig):
        self.tiktok = TikTokAPI(proxy=config.proxy, cookies=config.cookies)

        self.url = config.url
        self.user = config.user
        self.room_id = config.room_id
        self.mode = config.mode
        self.automatic_interval = config.automatic_interval
        self.duration = config.duration
        self.output = config.output
        self.bitrate = config.bitrate
        self.ffmpeg_path = config.ffmpeg_path
        self.use_telegram = config.use_telegram
        self._proxy = config.proxy
        self._cookies = config.cookies
        self._interrupted = False

    def _setup(self):
        """Resolve user/room data and validate prerequisites via network calls."""
        if self.mode == Mode.FOLLOWERS:
            self.check_country_blacklisted()

            self.sec_uid = self.tiktok.get_sec_uid()
            if self.sec_uid is None:
                raise TikTokRecorderError("Failed to retrieve sec_uid.")

            logger.info("Followers mode activated\n")
        else:
            if self.url:
                self.user, self.room_id = self.tiktok.get_room_and_user_from_url(
                    self.url
                )

            if not self.user:
                self.user = self.tiktok.get_user_from_room_id(self.room_id)

            if not self.room_id:
                self.room_id = self.tiktok.get_room_id_from_user(self.user)

            self.check_country_blacklisted()

            logger.info(f"USERNAME: {self.user}" + ("\n" if not self.room_id else ""))
            if self.room_id:
                logger.info(
                    f"ROOM_ID:  {self.room_id}"
                    + ("\n" if not self.tiktok.is_room_alive(self.room_id) else "")
                )

        # If proxy was used for the initial checks, switch to a direct connection
        # for the actual stream download to avoid proxy bottlenecks
        if self._proxy:
            self.tiktok = TikTokAPI(proxy=None, cookies=self._cookies)

        if self.output:
            Path(self.output).mkdir(parents=True, exist_ok=True)

    def run(self):
        """
        Resolves prerequisites and runs the recorder in the selected mode.

        If the mode is MANUAL, it checks if the user is currently live and
        if so, starts recording.

        If the mode is AUTOMATIC, it continuously checks if the user is live
        and if not, waits for the specified timeout before rechecking.
        If the user is live, it starts recording.

        if the mode is FOLLOWERS, it continuously checks the followers of
        the authenticated user. If any follower is live, it starts recording
        their live stream in a separate process.
        """
        self._setup()

        if self.mode == Mode.MANUAL:
            self.manual_mode()

        elif self.mode == Mode.AUTOMATIC:
            self.automatic_mode()

        elif self.mode == Mode.FOLLOWERS:
            self.followers_mode()

    def manual_mode(self):
        if not self.tiktok.is_room_alive(self.room_id):
            raise UserLiveError(f"@{self.user}: {TikTokError.USER_NOT_CURRENTLY_LIVE}")

        self.start_recording(self.user, self.room_id)

    def _wait_countdown(self, minutes: int, reason: str = ""):
        """Wait for the specified interval with an in-place countdown timer."""
        total_seconds = minutes * TimeOut.ONE_MINUTE
        if reason:
            logger.info(f"{reason} - Waiting {minutes} minutes before next check...")
        else:
            logger.info(f"Waiting {minutes} minutes before next check...")

        is_tty = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
        try:
            for remaining in range(total_seconds, 0, -1):
                if is_tty:
                    mins, secs = divmod(remaining, 60)
                    print(
                        f"\r\033[K[*] [WAITING] Recheck in {mins:02d}:{secs:02d} (Ctrl+C to stop)...",
                        end="",
                        flush=True,
                    )
                time.sleep(1)
        except KeyboardInterrupt:
            if is_tty:
                print("\r\033[K", end="", flush=True)
            logger.info("Wait interrupted by user.")
            raise
        finally:
            if is_tty:
                print("\r\033[K", end="", flush=True)

    def automatic_mode(self):
        while not getattr(self, "_interrupted", False):
            try:
                self.room_id = self.tiktok.get_room_id_from_user(self.user)
                self.manual_mode()
                if getattr(self, "_interrupted", False):
                    logger.info("Automatic recording stopped by user.")
                    break

            except (UserLiveError, LiveNotFound) as ex:
                logger.info(ex)
                self._wait_countdown(self.automatic_interval)

            except (ConnectionError, RequestException, HTTPException):
                logger.error(Error.CONNECTION_CLOSED_AUTOMATIC)
                self._wait_countdown(TimeOut.CONNECTION_CLOSED)

            except KeyboardInterrupt:
                logger.info("Automatic mode stopped by user.")
                break

    def followers_mode(self):
        active_recordings = {}  # follower -> Thread

        while True:
            try:
                followers = self.tiktok.get_followers_list(self.sec_uid)

                for follower in followers:
                    if follower in active_recordings:
                        if not active_recordings[follower].is_alive():
                            logger.info(f"Recording of @{follower} finished.")
                            del active_recordings[follower]
                        else:
                            continue

                    try:
                        room_id = self.tiktok.get_room_id_from_user(follower)

                        if not room_id or not self.tiktok.is_room_alive(room_id):
                            continue

                        logger.info(f"@{follower} is live. Starting recording...")

                        thread = Thread(
                            target=self.start_recording,
                            args=(follower, room_id),
                            daemon=True,
                        )
                        thread.start()
                        active_recordings[follower] = thread

                        time.sleep(2.5)

                    except TikTokRecorderError as e:
                        logger.error(f"Error while processing @{follower}: {e}")
                        continue

                    except Exception as e:
                        logger.error(
                            f"Unexpected error processing @{follower}: {e}",
                            exc_info=True,
                        )
                        continue

                self._wait_countdown(
                    self.automatic_interval, reason="Followers scan finished"
                )

            except (UserLiveError, LiveNotFound) as ex:
                logger.info(ex)
                self._wait_countdown(self.automatic_interval)

            except (ConnectionError, RequestException, HTTPException):
                logger.error(Error.CONNECTION_CLOSED_AUTOMATIC)
                self._wait_countdown(TimeOut.CONNECTION_CLOSED)

            except KeyboardInterrupt:
                logger.info("Followers mode stopped by user.")
                break

    def _build_output_path(self, user: str) -> str:
        filename = (
            f"TK_{user}_{time.strftime('%Y.%m.%d_%H-%M-%S', time.localtime())}_flv.mp4"
        )
        if self.output:
            output_dir = Path(self.output)
            output_dir.mkdir(parents=True, exist_ok=True)
            return str(output_dir / filename)
        return filename

    def start_recording(self, user, room_id):
        """
        Start recording live
        """
        live_urls = self.tiktok.get_live_url_candidates(room_id, user=user)
        if not live_urls:
            raise LiveNotFound(TikTokError.RETRIEVE_LIVE_URL)

        output = self._build_output_path(user)

        min_stream_bytes = 4096
        for index, live_url in enumerate(live_urls, start=1):
            if self.duration:
                logger.info(
                    f"Started recording for {self.duration} seconds "
                    f"(stream {index}/{len(live_urls)})"
                )
            else:
                logger.info(f"Started recording (stream {index}/{len(live_urls)})...")

            buffer_size = 512 * 1024  # 512 KB buffer
            buffer = bytearray()
            bytes_written = 0
            total_elapsed = 0.0

            logger.info("[PRESS CTRL + C ONCE TO STOP]")
            is_tty = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
            with open(output, "wb") as out_file:
                stop_recording = False
                stream_ended = False
                while not stop_recording:
                    try:
                        if not self.tiktok.is_room_alive(room_id):
                            if is_tty:
                                print("\r\033[K", end="", flush=True)
                            logger.info("User is no longer live. Stopping recording.")
                            break

                        start_time = time.time()
                        last_status_time = start_time
                        for chunk in self.tiktok.download_live_stream(live_url):
                            buffer.extend(chunk)
                            bytes_written += len(chunk)
                            if len(buffer) >= buffer_size:
                                out_file.write(buffer)
                                buffer.clear()

                            now = time.time()
                            elapsed_time = now - start_time
                            total_elapsed = elapsed_time

                            if is_tty and (now - last_status_time >= 1.5):
                                mb_written = bytes_written / (1024 * 1024)
                                speed_kb = (bytes_written / 1024) / max(
                                    elapsed_time, 0.001
                                )
                                if speed_kb >= 1024:
                                    speed_str = f"{speed_kb / 1024:.2f} MB/s"
                                else:
                                    speed_str = f"{speed_kb:.0f} KB/s"
                                duration_str = time.strftime(
                                    "%H:%M:%S", time.gmtime(elapsed_time)
                                )
                                print(
                                    f"\r\033[K\033[32m● RECORDING\033[0m @{user} | "
                                    f"\033[1m{mb_written:.2f} MB\033[0m | "
                                    f"Duration: {duration_str} | Speed: {speed_str}",
                                    end="",
                                    flush=True,
                                )
                                last_status_time = now

                            if self.duration and elapsed_time >= self.duration:
                                stop_recording = True
                                break
                        else:
                            stream_ended = True

                        if stream_ended and bytes_written < min_stream_bytes:
                            break

                    except ConnectionError:
                        if is_tty:
                            print("\r\033[K", end="", flush=True)
                        if self.mode == Mode.AUTOMATIC:
                            logger.error(Error.CONNECTION_CLOSED_AUTOMATIC)
                            self._wait_countdown(TimeOut.CONNECTION_CLOSED)

                    except (RequestException, HTTPException) as ex:
                        if is_tty:
                            print("\r\033[K", end="", flush=True)
                        logger.warning(f"Network hiccup, retrying: {ex}")
                        time.sleep(2)

                    except KeyboardInterrupt:
                        if is_tty:
                            print("\r\033[K", end="", flush=True)
                        logger.info("Recording stopped by user.")
                        self._interrupted = True
                        stop_recording = True

                    except Exception as ex:
                        if is_tty:
                            print("\r\033[K", end="", flush=True)
                        logger.error(
                            f"Unexpected error during recording: {ex}",
                            exc_info=True,
                        )
                        stop_recording = True

                    finally:
                        if is_tty:
                            print("\r\033[K", end="", flush=True)
                        if buffer:
                            out_file.write(buffer)
                            buffer.clear()
                        out_file.flush()

            if bytes_written >= min_stream_bytes:
                break

            logger.warning(
                f"Stream {index}/{len(live_urls)} returned only {bytes_written} bytes. "
                "Trying another CDN/quality..."
            )
        else:
            Path(output).unlink(missing_ok=True)
            raise LiveNotFound(TikTokError.RETRIEVE_LIVE_URL)

        logger.info(f"Recording finished: {Path(output).resolve()}\n")
        converted_file = VideoManagement.convert_flv_to_mp4(
            output, self.bitrate, self.ffmpeg_path
        )
        final_file = converted_file or output

        file_size_mb = 0.0
        try:
            file_size_mb = Path(final_file).stat().st_size / (1024 * 1024)
        except OSError:
            pass

        duration_formatted = time.strftime("%H:%M:%S", time.gmtime(total_elapsed))

        display_success_card(
            "RECORDING COMPLETED",
            {
                "Creator": f"@{user}",
                "Room ID": str(room_id),
                "Duration": duration_formatted,
                "File Size": f"{file_size_mb:.2f} MB",
                "Saved File": str(Path(final_file).resolve()),
            },
        )

        if self.use_telegram:
            try:
                from upload.telegram import Telegram

                Telegram().upload(final_file)
            except Exception as e:
                logger.error(f"Telegram upload failed: {e}")

    def check_country_blacklisted(self):
        is_blacklisted = self.tiktok.is_country_blacklisted()
        if not is_blacklisted:
            return False

        if self.room_id is None:
            raise TikTokRecorderError(TikTokError.COUNTRY_BLACKLISTED)

        if self.mode == Mode.AUTOMATIC:
            raise TikTokRecorderError(TikTokError.COUNTRY_BLACKLISTED_AUTO_MODE)

        elif self.mode == Mode.FOLLOWERS:
            raise TikTokRecorderError(TikTokError.COUNTRY_BLACKLISTED_FOLLOWERS_MODE)

        return is_blacklisted
