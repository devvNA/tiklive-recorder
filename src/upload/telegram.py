import asyncio
import sys
from pathlib import Path

from telethon import TelegramClient

from utils.logger_manager import logger
from utils.utils import read_telegram_config


FREE_USER_MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024
PREMIUM_USER_MAX_FILE_SIZE = 4 * 1024 * 1024 * 1024


class Telegram:
    def __init__(self):
        config = read_telegram_config()

        self.api_id = config["api_id"]
        self.api_hash = config["api_hash"]
        self.chat_id = config["chat_id"]

        self.client = TelegramClient(
            "tiktok_live_recorder_session",
            api_id=self.api_id,
            api_hash=self.api_hash,
        )

    def upload(self, file_path: str):
        """
        Upload a file to the user's Saved Messages via Telethon.
        """

        async def _upload():
            try:
                await self.client.connect()

                if not await self.client.is_user_authorized():
                    await self.client.start()

                me = await self.client.get_me()
                is_premium = me.premium
                max_size = (
                    PREMIUM_USER_MAX_FILE_SIZE
                    if is_premium
                    else FREE_USER_MAX_FILE_SIZE
                )

                file_size = Path(file_path).stat().st_size
                logger.info(
                    f"File to upload: {Path(file_path).name} "
                    f"({round(file_size / (1024 * 1024))} MB)"
                )

                if file_size > max_size:
                    logger.warning(
                        "The file is too large to be uploaded "
                        "with this type of account."
                    )
                    return

                logger.info(
                    "Uploading video on Telegram... "
                    "This may take a while depending on file size."
                )

                is_tty = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

                def _upload_progress(current, total):
                    if is_tty and total > 0:
                        pct = (current / total) * 100
                        curr_mb = current / (1024 * 1024)
                        tot_mb = total / (1024 * 1024)
                        print(
                            f"\r\033[K[*] [TELEGRAM] Uploading: {pct:5.1f}% "
                            f"({curr_mb:.1f} / {tot_mb:.1f} MB)",
                            end="",
                            flush=True,
                        )

                await self.client.send_file(
                    entity=self.chat_id,
                    file=file_path,
                    caption=(
                        "🎥 <b>Video recorded via "
                        '<a href="https://github.com/Michele0303/'
                        'tiktok-live-recorder">'
                        "TikTok Live Recorder</a></b>"
                    ),
                    parse_mode="html",
                    force_document=True,
                    progress_callback=_upload_progress if is_tty else None,
                )

                if is_tty:
                    print("\r\033[K", end="", flush=True)

                logger.info("File successfully uploaded to Telegram.\n")

            except Exception as e:
                logger.error(f"Error during Telegram upload: {e}\n", exc_info=True)

            finally:
                await self.client.disconnect()

        asyncio.run(_upload())
