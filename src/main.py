import sys
import os
import multiprocessing

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def record_user(config):
    from core.tiktok_recorder import TikTokRecorder
    from utils.logger_manager import logger

    try:
        TikTokRecorder(config).run()
    except KeyboardInterrupt:
        logger.info("Recording stopped by user.")
    except Exception as e:
        logger.error(f"{e}", exc_info=True)


def _build_config(args, mode, cookies, user=None):
    from utils.recorder_config import RecorderConfig

    return RecorderConfig(
        url=args.url,
        user=user,
        room_id=args.room_id,
        mode=mode,
        automatic_interval=args.automatic_interval,
        cookies=cookies,
        proxy=args.proxy,
        output=args.output,
        duration=args.duration,
        use_telegram=args.telegram,
        bitrate=args.bitrate,
        ffmpeg_path=args.ffmpeg_path,
    )


def run_recordings(args, mode, cookies):
    from utils.logger_manager import logger

    if isinstance(args.user, list):
        processes = []
        for user in args.user:
            config = _build_config(args, mode, cookies, user=user)
            p = multiprocessing.Process(target=record_user, args=(config,))
            p.start()
            processes.append(p)
        try:
            for p in processes:
                p.join()
        except KeyboardInterrupt:
            logger.info("Ctrl-C detected. Waiting for recording processes to stop...")
            try:
                for p in processes:
                    p.join()
            except KeyboardInterrupt:
                logger.warning("Forcefully terminating all recording processes.")
                for p in processes:
                    if p.is_alive():
                        p.terminate()
    else:
        config = _build_config(args, mode, cookies, user=args.user)
        record_user(config)


def _get_error_tip(message: str) -> str | None:
    msg = message.lower()
    if "not hosting a live" in msg or "not currently live" in msg:
        return (
            "Run with '-mode automatic' to record automatically when creator is live."
        )
    if "country is blacklisted" in msg or "blacklisted" in msg:
        return "TikTok restricted your region. Use '-proxy http://<ip>:<port>' or cookies.json."
    if "cookies.json" in msg or "login required" in msg or "private" in msg:
        return "Configure your session cookies in cookies.json (see docs/GUIDE.md)."
    if (
        "roomid" in msg
        or "username / roomid not found" in msg
        or "never been in live" in msg
    ):
        return (
            "Verify that username/URL is correct and the user has hosted a TikTok LIVE."
        )
    if "waf" in msg:
        return "TikTok WAF blocked your IP. Switch network or use an HTTP proxy."
    if "ffmpeg" in msg:
        return (
            "Ensure FFmpeg is installed or specify path via '-ffmpeg-path <binary>'."
        )
    if "missing url" in msg or "incorrect mode" in msg or "provide only one" in msg:
        return "Run 'uv run python src/main.py --help' to see command-line usage."
    return None


def main():
    from utils.args_handler import validate_and_parse_args
    from utils.utils import read_cookies
    from utils.logger_manager import logger
    from utils.custom_exceptions import TikTokRecorderError
    from utils.dependencies import check_ffmpeg
    from utils.terminal_ui import display_error_card

    try:
        # validate and parse command line arguments
        args, mode = validate_and_parse_args()

        # check ffmpeg binary (supports custom path via -ffmpeg-path)
        check_ffmpeg(args.ffmpeg_path or "ffmpeg")

        # check for updates
        if args.update_check is True:
            logger.info("Checking for updates...\n")
            from check_updates import check_updates

            if check_updates():
                exit()
        else:
            logger.info("Skipped update check\n")

        # read cookies from the config file
        cookies = read_cookies()

        # run the recordings based on the parsed arguments
        run_recordings(args, mode, cookies)

    except TikTokRecorderError as ex:
        tip = _get_error_tip(str(ex))
        display_error_card("APPLICATION ERROR", str(ex), tip=tip)
        logger.error(f"Application Error: {ex}")

    except KeyboardInterrupt:
        logger.info("Execution stopped by user.")
        sys.exit(0)

    except Exception as ex:
        tip = "Check tiktok-recorder.log for full diagnostic trace."
        display_error_card("UNEXPECTED ERROR", str(ex), tip=tip)
        logger.critical(f"Generic Error: {ex}", exc_info=True)


def _run_in_venv(venv_python):
    import signal
    import subprocess

    # Ignore SIGINT in parent process so the child (which gets its own console Ctrl+C)
    # can finish in-flight stream writes, convert FLV to MP4, show the summary, and exit.
    try:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
    except Exception:
        pass

    try:
        proc = subprocess.Popen([str(venv_python)] + sys.argv)
        ret = proc.wait()
        sys.exit(ret)
    except KeyboardInterrupt:
        try:
            ret = proc.wait()
            sys.exit(ret)
        except KeyboardInterrupt:
            try:
                proc.terminate()
            except OSError:
                pass
            sys.exit(130)


def _ensure_venv():
    from pathlib import Path
    import platform

    project_root = Path(__file__).resolve().parent.parent
    venv_python = (
        project_root / ".venv" / "Scripts" / "python.exe"
        if platform.system().lower() == "windows"
        else project_root / ".venv" / "bin" / "python"
    )
    if (
        venv_python.exists()
        and Path(sys.executable).resolve() != venv_python.resolve()
    ):
        _run_in_venv(venv_python)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    _ensure_venv()

    # Fast-path for version and help without running dependency checks
    if any(arg in sys.argv for arg in ["-v", "--version"]):
        main()
        sys.exit(0)

    from utils.utils import banner

    banner()

    if any(arg in sys.argv for arg in ["-h", "--help"]):
        main()
        sys.exit(0)

    # check and install dependencies
    from utils.dependencies import check_and_install_dependencies

    check_and_install_dependencies()

    # run
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
