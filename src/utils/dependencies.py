import platform
import signal
import subprocess
import sys
from pathlib import Path
from subprocess import SubprocessError

from .logger_manager import logger


def check_ffmpeg_binary(ffmpeg_path="ffmpeg"):
    try:
        subprocess.run(
            [ffmpeg_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )
        return True
    except FileNotFoundError:
        logger.error("FFmpeg binary is not installed")
        return False


def install_ffmpeg_binary():
    try:
        logger.error("Please, install FFmpeg with this command:")
        if platform.system().lower() == "linux":
            import distro

            linux_family = distro.like()
            if linux_family == "debian":
                logger.info("sudo apt install ffmpeg")
            elif linux_family == "redhat":
                logger.info("sudo dnf install ffmpeg / sudo yum install ffmpeg")
            elif linux_family == "arch":
                logger.info("sudo pacman -S ffmpeg")
            elif linux_family == "":  # Termux
                logger.info("pkg install ffmpeg")
            else:
                logger.info(f"Distro linux not supported (family: {linux_family})")

        elif platform.system().lower() == "windows":
            logger.info(
                "choco install ffmpeg or follow: https://phoenixnap.com/kb/ffmpeg-windows"
            )

        elif platform.system().lower() == "darwin":
            logger.info("brew install ffmpeg")

        else:
            logger.info(f"OS not supported: {platform}")

    except Exception as e:
        logger.error(f"Error: {e}")

    exit(1)


def check_distro_library():
    try:
        import distro

        _ = distro  # to avoid linting issues

        return True
    except ModuleNotFoundError:
        logger.error("distro library is not installed")
        return False


def check_ffmpeg_library():
    try:
        import ffmpeg

        _ = ffmpeg  # to avoid linting issues

        return True
    except ModuleNotFoundError:
        logger.error("ffmpeg-python library is not installed")
        return False


def check_argparse_library():
    try:
        import argparse

        _ = argparse  # to avoid linting issues

        return True
    except ModuleNotFoundError:
        logger.error("argparse library is not installed")
        return False


def check_curl_cffi_library():
    try:
        from .utils import is_termux

        if is_termux():
            return True

        import curl_cffi

        _ = curl_cffi  # to avoid linting issues

        return True
    except ModuleNotFoundError:
        logger.error("curl_cffi library is not installed")
        return False


def check_requests_library():
    try:
        import requests

        _ = requests  # to avoid linting issues

        return True
    except ModuleNotFoundError:
        logger.error("requests library is not installed")
        return False


def check_telethon_library():
    try:
        import telethon

        _ = telethon  # to avoid linting issues

        return True
    except ModuleNotFoundError:
        logger.error("telethon library is not installed")
        return False


def install_requirements():
    try:
        print()
        logger.error("Installing requirements...\n")

        subprocess.run(
            ["uv", "sync", "--no-dev"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            check=True,
        )
        logger.info("Requirements installed successfully\n")
    except (SubprocessError, FileNotFoundError, OSError) as e:
        logger.error(f"Error: {e}")
        logger.error("Please run the recorder using: uv run python src/main.py")
        sys.exit(1)


def _run_in_venv(venv_python):
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


def check_and_install_dependencies():
    project_root = Path(__file__).resolve().parent.parent.parent
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

    logger.info("Checking dependencies...")

    dependencies = [
        check_distro_library(),
        check_ffmpeg_library(),
        check_argparse_library(),
        check_curl_cffi_library(),
        check_requests_library(),
        check_telethon_library(),
    ]

    if False in dependencies:
        install_requirements()


def check_ffmpeg(ffmpeg_path="ffmpeg"):
    if not check_ffmpeg_binary(ffmpeg_path):
        install_ffmpeg_binary()
