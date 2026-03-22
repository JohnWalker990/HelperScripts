#!/usr/bin/env python3
"""
Download YouTube audio or video in the highest available quality.

By default, watch URLs that include playlist parameters are treated as a single
video download. Use --playlist to download an actual playlist.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse


SUPPORTED_AUDIO_FORMATS = (
    "aac",
    "alac",
    "flac",
    "m4a",
    "mp3",
    "opus",
    "vorbis",
    "wav",
    "best",
)

SUPPORTED_COOKIE_BROWSERS = (
    "brave",
    "chrome",
    "chromium",
    "edge",
    "firefox",
    "opera",
    "safari",
    "vivaldi",
    "whale",
)

BROWSER_PRIORITY = {
    "firefox": 0,
    "edge": 1,
    "chrome": 2,
    "brave": 3,
    "chromium": 4,
    "opera": 5,
    "vivaldi": 6,
    "whale": 7,
    "safari": 8,
}

ARCHIVE_ID_PATTERN = re.compile(r"\[(?P<video_id>[^\[\]]+)\]\.[^.]+$")


class SuccessfulVideoCounter:
    def __init__(self) -> None:
        self.successful_videos = 0

    def mark_successful_video(self) -> None:
        self.successful_videos += 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download YouTube audio or video in the highest available quality.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python download-youtube-audio.py https://www.youtube.com/watch?v=BaW_jenozKc\n"
            "  python download-youtube-audio.py --video https://www.youtube.com/watch?v=BaW_jenozKc\n"
            "  python download-youtube-audio.py --cookies-from-browser edge:Default https://youtu.be/BaW_jenozKc\n"
            "  python download-youtube-audio.py --playlist https://www.youtube.com/playlist?list=...\n"
            "  python download-youtube-audio.py -o D:/Music https://youtu.be/BaW_jenozKc"
        ),
    )
    parser.add_argument(
        "url",
        nargs="?",
        help="YouTube video URL. If omitted, the script prompts for one.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=None,
        help="Directory where downloaded files are saved. Default depends on mode.",
    )
    playlist_group = parser.add_mutually_exclusive_group()
    playlist_group.add_argument(
        "--playlist",
        dest="download_playlist",
        action="store_true",
        default=None,
        help="Download the whole playlist instead of only the current video.",
    )
    playlist_group.add_argument(
        "--single",
        dest="download_playlist",
        action="store_false",
        help="Force a single-video download even when the URL includes playlist information.",
    )
    media_group = parser.add_mutually_exclusive_group()
    media_group.add_argument(
        "--video",
        dest="download_video",
        action="store_true",
        default=None,
        help="Download the full video in best available quality as MP4.",
    )
    media_group.add_argument(
        "--audio-only",
        dest="download_video",
        action="store_false",
        help="Force audio-only mode.",
    )
    parser.add_argument(
        "--audio-format",
        default="mp3",
        choices=SUPPORTED_AUDIO_FORMATS,
        help="Audio format after extraction in audio-only mode. Default: mp3.",
    )
    parser.add_argument(
        "--audio-quality",
        default="0",
        help="ffmpeg audio quality for transcoding: 0-10 or a bitrate such as 320K.",
    )
    parser.add_argument(
        "--cookies",
        type=Path,
        help="Path to a Netscape-format cookies.txt file for authenticated downloads.",
    )
    parser.add_argument(
        "--cookies-from-browser",
        type=parse_cookies_from_browser,
        metavar="BROWSER[:PROFILE]",
        help="Load cookies directly from a local browser profile, for example edge:Default.",
    )
    parser.add_argument(
        "--list-browser-profiles",
        action="store_true",
        help="List detected local browser profiles for use with --cookies-from-browser.",
    )
    args = parser.parse_args()

    if args.cookies and args.cookies_from_browser:
        parser.error("Use either --cookies or --cookies-from-browser, not both.")

    return args


def parse_cookies_from_browser(value: str) -> tuple[str, str | None, str | None, str | None]:
    match = re.fullmatch(
        r"""(?x)
        (?P<name>[^+:]+)
        (?:\s*\+\s*(?P<keyring>[^:]+))?
        (?:\s*:\s*(?!:)(?P<profile>.+?))?
        (?:\s*::\s*(?P<container>.+))?
        """,
        value,
    )
    if match is None:
        raise argparse.ArgumentTypeError(
            "Invalid browser cookie format. Use BROWSER or BROWSER:PROFILE."
        )

    browser_name, keyring, profile, container = match.group("name", "keyring", "profile", "container")
    browser_name = browser_name.lower()

    if browser_name not in SUPPORTED_COOKIE_BROWSERS:
        raise argparse.ArgumentTypeError(
            f"Unsupported browser '{browser_name}'. Supported browsers: {', '.join(SUPPORTED_COOKIE_BROWSERS)}."
        )

    return browser_name, profile, keyring, container


def detect_browser_profiles() -> list[tuple[str, str]]:
    local_app_data = Path(os.environ.get("LOCALAPPDATA", ""))
    roaming_app_data = Path(os.environ.get("APPDATA", ""))

    profile_roots = {
        "edge": local_app_data / "Microsoft" / "Edge" / "User Data",
        "chrome": local_app_data / "Google" / "Chrome" / "User Data",
        "brave": local_app_data / "BraveSoftware" / "Brave-Browser" / "User Data",
        "firefox": roaming_app_data / "Mozilla" / "Firefox" / "Profiles",
    }

    detected_profiles: list[tuple[str, str]] = []

    for browser_name, profile_root in profile_roots.items():
        if not profile_root.is_dir():
            continue

        for child in sorted(profile_root.iterdir()):
            if not child.is_dir():
                continue

            profile_name = child.name
            if browser_name == "firefox":
                if (
                    profile_name.endswith((".default", ".default-release", ".default-esr"))
                    and (child / "cookies.sqlite").is_file()
                ):
                    detected_profiles.append((browser_name, profile_name))
                continue

            has_cookie_db = (child / "Network" / "Cookies").is_file() or (child / "Cookies").is_file()
            if has_cookie_db and (profile_name == "Default" or profile_name.startswith("Profile ")):
                detected_profiles.append((browser_name, profile_name))

    return sorted(
        detected_profiles,
        key=lambda item: (
            BROWSER_PRIORITY.get(item[0], 99),
            0 if item[1] == "Default" or item[1].endswith(".default-release") else 1,
            item[1].lower(),
        ),
    )


def print_detected_browser_profiles() -> int:
    detected_profiles = detect_browser_profiles()
    if not detected_profiles:
        print("No common browser profiles detected.")
        return 0

    print("Detected browser profiles:")
    for browser_name, profile_name in detected_profiles:
        print(f"  {browser_name}:{profile_name}")
    return 0


def resolve_output_dir(custom_output_dir: Path | None, download_video: bool) -> Path:
    if custom_output_dir is not None:
        return custom_output_dir.expanduser().resolve()

    default_folder = "youtube-video" if download_video else "youtube-audio"
    return (Path(__file__).resolve().parent / "downloads" / default_folder).resolve()


def build_download_archive_path(output_dir: Path, download_video: bool, audio_format: str) -> Path:
    archive_suffix = "video-mp4" if download_video else f"audio-{audio_format}"
    return output_dir / f".download-archive-{archive_suffix}.txt"


def load_download_archive_ids(archive_path: Path) -> set[str]:
    if not archive_path.is_file():
        return set()

    return {
        line.strip()
        for line in archive_path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.strip()
    }


def get_expected_completed_suffixes(download_video: bool, audio_format: str) -> set[str]:
    if download_video:
        return {".mp4"}

    if audio_format == "best":
        return {".aac", ".alac", ".flac", ".m4a", ".mp3", ".ogg", ".opus", ".vorbis", ".wav", ".webm"}

    return {f".{audio_format}"}


def sync_download_archive_from_existing_files(output_dir: Path, download_video: bool, audio_format: str) -> int:
    archive_path = build_download_archive_path(output_dir, download_video, audio_format)
    expected_suffixes = get_expected_completed_suffixes(download_video, audio_format)

    existing_archive_ids = load_download_archive_ids(archive_path)
    discovered_archive_ids: list[str] = []
    if output_dir.is_dir():
        for child in output_dir.iterdir():
            if child.is_dir() or child.name.startswith("."):
                continue
            if child.suffix.lower() not in expected_suffixes:
                continue

            match = ARCHIVE_ID_PATTERN.search(child.name)
            if match is None:
                continue

            archive_id = f"youtube {match.group('video_id')}"
            if archive_id in existing_archive_ids:
                continue

            existing_archive_ids.add(archive_id)
            discovered_archive_ids.append(archive_id)

    if discovered_archive_ids:
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(archive_path, "a", encoding="utf-8", newline="\n") as archive_file:
            for archive_id in discovered_archive_ids:
                archive_file.write(archive_id + "\n")

    return len(discovered_archive_ids)


def maybe_print_resume_hint(output_dir: Path, download_video: bool, audio_format: str, synced_count: int) -> None:
    archive_path = build_download_archive_path(output_dir, download_video, audio_format)
    if archive_path.is_file():
        if synced_count > 0:
            print(
                f"Added {synced_count} existing item(s) to the resume archive: {archive_path}",
                file=sys.stderr,
            )
        print(
            f"Resume archive found. Already completed items will be skipped: {archive_path}",
            file=sys.stderr,
        )


def can_prompt_user() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def prompt_yes_no(question: str, default: bool) -> bool:
    prompt_suffix = " [Y/n]: " if default else " [y/N]: "
    while True:
        answer = input(f"{question}{prompt_suffix}").strip().lower()
        if not answer:
            return default
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Please answer with y or n.")


def prompt_download_video() -> bool:
    while True:
        answer = input("Download video or audio only? [v/a]: ").strip().lower()
        if not answer:
            return False
        if answer in {"v", "video"}:
            return True
        if answer in {"a", "audio", "audio-only"}:
            return False
        print("Please answer with v for video or a for audio.")


def analyze_url(url: str) -> tuple[bool, bool]:
    parsed_url = urlparse(url)
    query = parse_qs(parsed_url.query)
    has_video = bool(query.get("v"))
    has_playlist = bool(query.get("list"))
    playlist_only = has_playlist and not has_video and parsed_url.path.rstrip("/").endswith("/playlist")
    return has_playlist, playlist_only


def prompt_for_url(url: str | None) -> str:
    if url:
        return url.strip()

    try:
        pasted_url = input("Paste YouTube URL: ").strip()
    except EOFError:
        print("No URL provided.", file=sys.stderr)
        raise SystemExit(1)

    if pasted_url:
        return pasted_url

    print("No URL provided.", file=sys.stderr)
    raise SystemExit(1)


def ensure_requirements() -> None:
    problems: list[str] = []

    if importlib.util.find_spec("yt_dlp") is None:
        problems.append("Missing Python package: yt-dlp")

    for executable in ("ffmpeg", "ffprobe"):
        if shutil.which(executable) is None:
            problems.append(f"Missing executable in PATH: {executable}")

    if not problems:
        return

    print("Cannot start download because required tools are missing:", file=sys.stderr)
    for problem in problems:
        print(f"  - {problem}", file=sys.stderr)

    print("\nInstall yt-dlp with:", file=sys.stderr)
    print("  python -m pip install --user yt-dlp", file=sys.stderr)
    print("\nInstall ffmpeg/ffprobe and make sure both are available in PATH.", file=sys.stderr)
    raise SystemExit(1)


def build_format_selector(download_video: bool) -> str:
    if download_video:
        return "bestvideo*+bestaudio/best"
    return "bestaudio/best"


def build_runtime_opts() -> dict[str, object]:
    runtime_opts: dict[str, object] = {}
    js_runtimes = build_js_runtimes()
    if js_runtimes is not None:
        runtime_opts["js_runtimes"] = js_runtimes
        if should_enable_remote_components():
            runtime_opts["remote_components"] = ["ejs:github"]

    return runtime_opts


def build_cookie_source_opts(
    cookie_file: Path | None,
    cookies_from_browser: tuple[str, str | None, str | None, str | None] | None,
) -> dict[str, object]:
    cookie_opts: dict[str, object] = {}
    if cookie_file is not None:
        cookie_opts["cookiefile"] = str(cookie_file)

    if cookies_from_browser is not None:
        cookie_opts["cookiesfrombrowser"] = cookies_from_browser

    return cookie_opts


def build_js_runtimes() -> dict[str, dict[str, str]] | None:
    runtime_candidates = (
        ("node", "node"),
        ("deno", "deno"),
        ("bun", "bun"),
        ("quickjs", "qjs"),
    )

    for runtime_name, executable in runtime_candidates:
        runtime_path = shutil.which(executable)
        if runtime_path:
            return {runtime_name: {"path": runtime_path}}

    return None


def should_enable_remote_components() -> bool:
    return importlib.util.find_spec("yt_dlp_ejs") is None


def resolve_playlist_choice(url: str, requested_download_playlist: bool | None) -> bool:
    has_playlist, playlist_only = analyze_url(url)

    if requested_download_playlist is not None:
        if playlist_only and not requested_download_playlist:
            print(
                "This URL points only to a playlist. Paste a specific watch URL or use --playlist.",
                file=sys.stderr,
            )
            raise SystemExit(1)
        return requested_download_playlist

    if not has_playlist:
        return False

    if not can_prompt_user():
        return playlist_only

    if playlist_only:
        wants_playlist = prompt_yes_no("Playlist URL detected. Download the whole playlist?", True)
        if wants_playlist:
            return True
        print(
            "This URL points only to a playlist. Paste a specific watch URL if you want a single video.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    return prompt_yes_no("Playlist detected. Download the whole playlist?", False)


def resolve_download_mode(url: str, requested_download_video: bool | None) -> bool:
    if requested_download_video is not None:
        return requested_download_video

    has_playlist, _ = analyze_url(url)
    if has_playlist and can_prompt_user():
        return prompt_download_video()

    return False


def is_bot_challenge_error(message: str) -> bool:
    normalized = message.lower().replace("’", "'")
    return "confirm you're not a bot" in normalized


def is_dpapi_cookie_error(message: str) -> bool:
    normalized = message.lower()
    return "failed to decrypt with dpapi" in normalized


def print_cookie_help(url: str, cookies_argument_used: bool) -> None:
    print("\nYouTube blocked the request with its anti-bot check.", file=sys.stderr)

    if cookies_argument_used:
        print(
            "The supplied cookie source was not enough for this video. Try a different logged-in browser "
            "profile or an exported cookies.txt file.",
            file=sys.stderr,
        )
        return

    print("Retry with browser cookies or an exported cookies.txt file.", file=sys.stderr)

    detected_profiles = detect_browser_profiles()
    if detected_profiles:
        browser_name, profile_name = detected_profiles[0]
        print("\nTry this first:", file=sys.stderr)
        print(
            f'  python .\\download-youtube-audio.py --cookies-from-browser {browser_name}:{profile_name} "{url}"',
            file=sys.stderr,
        )
    else:
        print("\nExample:", file=sys.stderr)
        print(
            f'  python .\\download-youtube-audio.py --cookies-from-browser edge:Default "{url}"',
            file=sys.stderr,
        )

    print("\nOr list local profiles with:", file=sys.stderr)
    print("  python .\\download-youtube-audio.py --list-browser-profiles", file=sys.stderr)
    print("\nOr use an exported cookies file with:", file=sys.stderr)
    print(
        f'  python .\\download-youtube-audio.py --cookies "C:\\path\\to\\cookies.txt" "{url}"',
        file=sys.stderr,
    )


def print_dpapi_help(url: str) -> None:
    print(
        "\nChromium-based browser cookies could not be decrypted with Windows DPAPI.",
        file=sys.stderr,
    )
    print(
        "This is a known yt-dlp / Chromium issue path on some Windows setups. "
        "Try Firefox cookies or an exported cookies.txt file instead.",
        file=sys.stderr,
    )

    detected_profiles = detect_browser_profiles()
    firefox_profiles = [profile for profile in detected_profiles if profile[0] == "firefox"]
    if firefox_profiles:
        browser_name, profile_name = firefox_profiles[0]
        print("\nTry this first:", file=sys.stderr)
        print(
            f'  python .\\download-youtube-audio.py --cookies-from-browser {browser_name}:{profile_name} "{url}"',
            file=sys.stderr,
        )

    print("\nList detected profiles with:", file=sys.stderr)
    print("  python .\\download-youtube-audio.py --list-browser-profiles", file=sys.stderr)
    print("\nOr use an exported cookies file with:", file=sys.stderr)
    print(
        f'  python .\\download-youtube-audio.py --cookies "C:\\path\\to\\cookies.txt" "{url}"',
        file=sys.stderr,
    )


def format_browser_profile_label(browser_name: str, profile_name: str) -> str:
    return f"{browser_name}:{profile_name}"


def build_saved_media_label(download_video: bool) -> str:
    return "video" if download_video else "audio"


def find_first_unfinished_playlist_index(
    url: str,
    archive_ids: set[str],
    cookie_file: Path | None,
    cookies_from_browser: tuple[str, str | None, str | None, str | None] | None,
) -> tuple[int | None, int | None]:
    import yt_dlp

    if not archive_ids:
        return None, None

    probe_opts: dict[str, object] = {
        "extract_flat": "in_playlist",
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": False,
    }
    probe_opts.update(build_runtime_opts())
    probe_opts.update(build_cookie_source_opts(cookie_file, cookies_from_browser))

    with yt_dlp.YoutubeDL(probe_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not isinstance(info, dict) or info.get("_type") not in {"playlist", "multi_video"}:
        return None, None

    playlist_count = info.get("playlist_count")
    total_entries = playlist_count if isinstance(playlist_count, int) and playlist_count > 0 else 0
    first_unfinished_index: int | None = None
    entries = info.get("entries") or ()
    for position, entry in enumerate(entries, start=1):
        total_entries = max(total_entries, position)
        if not isinstance(entry, dict):
            first_unfinished_index = first_unfinished_index or position
            continue

        video_id = entry.get("id")
        if not video_id:
            first_unfinished_index = first_unfinished_index or position
            continue

        if f"youtube {video_id}" not in archive_ids:
            first_unfinished_index = first_unfinished_index or position

    if total_entries == 0:
        return None, 0

    if first_unfinished_index is not None:
        return first_unfinished_index, total_entries

    return total_entries + 1, total_entries


def try_auto_cookie_profiles(
    url: str,
    output_dir: Path,
    download_playlist: bool,
    download_video: bool,
    audio_format: str,
    audio_quality: str,
) -> tuple[int, str] | None:
    detected_profiles = detect_browser_profiles()
    if not detected_profiles:
        return None

    print(
        "\nYouTube blocked the guest session. Retrying automatically with detected browser profiles...",
        file=sys.stderr,
    )

    failures: list[tuple[str, str]] = []

    for browser_name, profile_name in detected_profiles:
        label = format_browser_profile_label(browser_name, profile_name)
        print(f"Trying browser profile: {label}", file=sys.stderr)
        try:
            exit_code = download_audio(
                url=url,
                output_dir=output_dir,
                download_playlist=download_playlist,
                download_video=download_video,
                audio_format=audio_format,
                audio_quality=audio_quality,
                cookie_file=None,
                cookies_from_browser=(browser_name, profile_name, None, None),
            )
            return exit_code, label
        except Exception as exc:
            failures.append((label, str(exc)))
            print(f"  Failed with {label}: {exc}", file=sys.stderr)

    print("\nAutomatic browser profile selection failed.", file=sys.stderr)
    for label, message in failures:
        print(f"  - {label}: {message}", file=sys.stderr)
    return None


def download_audio(
    url: str,
    output_dir: Path,
    download_playlist: bool,
    download_video: bool,
    audio_format: str,
    audio_quality: str,
    cookie_file: Path | None,
    cookies_from_browser: tuple[str, str | None, str | None, str | None] | None,
) -> int:
    import yt_dlp
    from yt_dlp.postprocessor.common import PostProcessor

    output_dir.mkdir(parents=True, exist_ok=True)
    successful_video_counter = SuccessfulVideoCounter()
    using_authenticated_source = cookie_file is not None or cookies_from_browser is not None
    download_archive = build_download_archive_path(output_dir, download_video, audio_format)
    archive_ids = load_download_archive_ids(download_archive)
    resume_index: int | None = None
    playlist_count: int | None = None

    if download_playlist and archive_ids:
        resume_index, playlist_count = find_first_unfinished_playlist_index(
            url=url,
            archive_ids=archive_ids,
            cookie_file=cookie_file,
            cookies_from_browser=cookies_from_browser,
        )

        if resume_index is not None and playlist_count is not None and resume_index > playlist_count:
            print(
                "Resume scan found no unfinished playlist items. Nothing to download.",
                file=sys.stderr,
            )
            return 0

        if resume_index is not None and resume_index > 1:
            if playlist_count:
                print(
                    f"Resuming playlist from item {resume_index} of {playlist_count}.",
                    file=sys.stderr,
                )
            else:
                print(f"Resuming playlist from item {resume_index}.", file=sys.stderr)

    ydl_opts = {
        "format": build_format_selector(download_video),
        "noplaylist": not download_playlist,
        "outtmpl": str(output_dir / "%(title)s [%(id)s].%(ext)s"),
        "windowsfilenames": True,
        "continuedl": True,
        "download_archive": str(download_archive),
    }

    if resume_index is not None and resume_index > 1:
        ydl_opts["playlist_items"] = f"{resume_index}:"

    if download_playlist and using_authenticated_source:
        ydl_opts["ignoreerrors"] = "only_download"

    if download_video:
        ydl_opts["merge_output_format"] = "mp4"
        ydl_opts["remuxvideo"] = "mp4"
        ydl_opts["format_sort"] = [
            "vcodec:h264",
            "lang",
            "quality",
            "res",
            "fps",
            "hdr:12",
            "acodec:aac",
        ]
    elif audio_format != "best":
        ydl_opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": audio_format,
                "preferredquality": audio_quality,
            }
        ]

    ydl_opts.update(build_runtime_opts())
    ydl_opts.update(build_cookie_source_opts(cookie_file, cookies_from_browser))

    class SuccessfulVideoPostProcessor(PostProcessor):
        def run(self, information: dict) -> tuple[list[str], dict]:
            successful_video_counter.mark_successful_video()
            return [], information

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.add_post_processor(SuccessfulVideoPostProcessor(ydl), when="after_video")
        exit_code = ydl.download([url])

    if download_playlist and using_authenticated_source:
        if successful_video_counter.successful_videos > 0:
            if exit_code != 0:
                print(
                    "Playlist completed with some skipped or unavailable items.",
                    file=sys.stderr,
                )
            return 0

        if exit_code != 0:
            raise RuntimeError("No playlist items could be downloaded with the selected cookie source.")

    return exit_code


def main() -> int:
    args = parse_args()

    if args.list_browser_profiles:
        return print_detected_browser_profiles()

    cookie_file = args.cookies.expanduser().resolve() if args.cookies else None
    if cookie_file is not None and not cookie_file.is_file():
        print(f"Cookies file not found: {cookie_file}", file=sys.stderr)
        return 1

    url = prompt_for_url(args.url)
    download_playlist = resolve_playlist_choice(url, args.download_playlist)
    download_video = resolve_download_mode(url, args.download_video)
    output_dir = resolve_output_dir(args.output_dir, download_video)
    saved_media_label = build_saved_media_label(download_video)

    ensure_requirements()
    synced_count = sync_download_archive_from_existing_files(output_dir, download_video, args.audio_format)
    maybe_print_resume_hint(output_dir, download_video, args.audio_format, synced_count)

    try:
        exit_code = download_audio(
            url=url,
            output_dir=output_dir,
            download_playlist=download_playlist,
            download_video=download_video,
            audio_format=args.audio_format,
            audio_quality=args.audio_quality,
            cookie_file=cookie_file,
            cookies_from_browser=args.cookies_from_browser,
        )
    except KeyboardInterrupt:
        print("\nDownload cancelled.", file=sys.stderr)
        return 130
    except Exception as exc:
        message = str(exc)
        if (
            cookie_file is None
            and args.cookies_from_browser is None
            and is_bot_challenge_error(message)
        ):
            auto_cookie_result = try_auto_cookie_profiles(
                url=url,
                output_dir=output_dir,
                download_playlist=download_playlist,
                download_video=download_video,
                audio_format=args.audio_format,
                audio_quality=args.audio_quality,
            )
            if auto_cookie_result is not None:
                exit_code, used_profile = auto_cookie_result
                print(f"Used browser profile: {used_profile}")
                print(f"Saved {saved_media_label} to: {output_dir}")
                return exit_code

        print(f"Download failed: {message}", file=sys.stderr)
        if is_dpapi_cookie_error(message):
            print_dpapi_help(url)
        elif is_bot_challenge_error(message):
            print_cookie_help(url, cookie_file is not None or args.cookies_from_browser is not None)
        return 1

    print(f"Saved {saved_media_label} to: {output_dir}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
