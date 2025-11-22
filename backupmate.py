import argparse
import json
import sys
from typing import List

from backup_core import BackupError, run_backup


EXIT_INVALID_ARGS = 1
EXIT_RUNTIME_ERROR = 2


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simple incremental backup tool")
    parser.add_argument("src_dir", help="Source directory")
    parser.add_argument("dest_dir", help="Destination directory")
    parser.add_argument(
        "--mode",
        choices=["full", "incremental"],
        default="incremental",
        help="Backup mode (default: incremental)",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Glob pattern to exclude (can be repeated)",
    )
    parser.add_argument(
        "--state-file",
        dest="state_file",
        help="Path to state file (default: .backupmate_state.json under destination)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show actions without copying files",
    )
    parser.add_argument(
        "--json-report",
        dest="json_report",
        help="Write JSON summary to the given path",
    )

    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    try:
        args = parse_args(argv)
    except SystemExit:
        return EXIT_INVALID_ARGS

    try:
        stats = run_backup(
            args.src_dir,
            args.dest_dir,
            mode=args.mode,
            excludes=args.exclude,
            state_file=args.state_file,
            dry_run=args.dry_run,
        )
    except BackupError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR
    except Exception as exc:  # pragma: no cover - unexpected errors
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR

    summary = stats.to_dict()
    print(
        f"Completed in {summary['duration']:.2f}s — "
        f"copied {summary['files_copied']} files ({summary['bytes_copied']} bytes), "
        f"skipped {summary['skipped']}"
    )

    if args.json_report:
        try:
            with open(args.json_report, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, sort_keys=True)
        except OSError as exc:
            print(f"Failed to write JSON report: {exc}", file=sys.stderr)
            return EXIT_RUNTIME_ERROR

    return 0


if __name__ == "__main__":
    sys.exit(main())
