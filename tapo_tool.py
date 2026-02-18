import argparse
import asyncio
import datetime
import getpass
import sys
from pathlib import Path

import argcomplete
from pytapo import Tapo
from pytapo.media_stream.downloader import Downloader

DATETIME_FORMATS = (
    "%Y-%m-%d",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
)


def parse_datetime(value: str) -> datetime.datetime:
    for fmt in DATETIME_FORMATS:
        try:
            parsed = datetime.datetime.strptime(value, fmt)
            if fmt == "%Y-%m-%d":
                return datetime.datetime.combine(parsed.date(), datetime.time.min)
            return parsed
        except ValueError:
            continue
    raise argparse.ArgumentTypeError(
        "Invalid datetime format. Use YYYY-MM-DD, YYYY-MM-DDTHH:MM[:SS], or "
        '"YYYY-MM-DD HH:MM[:SS]".'
    )


def default_start_of_today() -> datetime.datetime:
    return datetime.datetime.combine(datetime.date.today(), datetime.time.min)


def default_end_of_today() -> datetime.datetime:
    return datetime.datetime.combine(
        datetime.date.today(), datetime.time.max.replace(microsecond=0)
    )


async def download_async(args: argparse.Namespace) -> None:
    print("Connecting to camera...")
    tapo = Tapo(args.host, args.user, args.password, args.password)

    output_dir = Path(args.output)
    if not output_dir.exists() or not output_dir.is_dir():
        raise SystemExit("ERROR: --output must point to an existing directory")

    if args.end <= args.start:
        raise SystemExit("ERROR: End date cannot be before start date")

    print("Getting recordings...")
    date = args.start.strftime("%Y%m%d")
    recordings = tapo.getRecordings(date)
    time_correction = tapo.getTimeCorrection()

    for recording in recordings:
        for key in recording:
            start_time = datetime.datetime.fromtimestamp(int(recording[key]["startTime"]))
            end_time = datetime.datetime.fromtimestamp(int(recording[key]["endTime"]))
            if start_time > args.end or end_time < args.start:
                print(
                    f"Skipping recording: {key}, out of time range, is {start_time} - {end_time}"
                )
                continue

            downloader = Downloader(
                tapo,
                recording[key]["startTime"],
                recording[key]["endTime"],
                time_correction,
                str(output_dir) + "/",
                None,
                False,
                args.window,
            )
            async for status in downloader.download():
                status_string = status["currentAction"] + " " + status["fileName"]
                if status["progress"] > 0:
                    status_string += (
                        ": "
                        + str(round(status["progress"], 2))
                        + " / "
                        + str(status["total"])
                    )
                else:
                    status_string += "..."
                print(status_string + (" " * 10) + "\r", end="")
            print("")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tapo-tool",
        description="Tools for Tapo camera recordings.",
        add_help=False,
    )
    parser.add_argument("-?", "--help", action="help", help="show this help message and exit")

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--host", "-h", required=True, help="camera host/IP")
    common.add_argument(
        "--password",
        "-p",
        help='camera password, use "-" to read password from stdin; if omitted, prompt in terminal',
    )
    common.add_argument(
        "--user", "-u", default="admin", help='camera username (default: "admin")'
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    download_parser = subparsers.add_parser(
        "download",
        parents=[common],
        add_help=False,
        help="download recordings from camera",
    )
    download_parser.add_argument(
        "-?",
        "--help",
        action="help",
        help="show this help message and exit",
    )
    download_parser.add_argument(
        "--output",
        "-o",
        default=".",
        help="existing output directory for downloaded recordings",
    )
    download_parser.add_argument(
        "--start",
        "-s",
        type=parse_datetime,
        default=default_start_of_today(),
        help='start datetime (default: today 00:00:00), format: YYYY-MM-DD | YYYY-MM-DDTHH:MM[:SS] | "YYYY-MM-DD HH:MM[:SS]"',
    )
    download_parser.add_argument(
        "--end",
        "-e",
        type=parse_datetime,
        default=default_end_of_today(),
        help='end datetime (default: today 23:59:59), format: YYYY-MM-DD | YYYY-MM-DDTHH:MM[:SS] | "YYYY-MM-DD HH:MM[:SS]"',
    )
    download_parser.add_argument(
        "--window",
        "-w",
        type=int,
        default=50,
        help="window size in seconds (default: 50)",
    )

    return parser


def main() -> None:
    parser = build_parser()
    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    if args.password is None:
        args.password = getpass.getpass("Password: ")
    elif args.password == "-":
        args.password = sys.stdin.readline().rstrip("\r\n")
        if not args.password:
            raise SystemExit("ERROR: No password received on stdin")

    if args.command == "download":
        asyncio.run(download_async(args))


if __name__ == "__main__":
    main()
