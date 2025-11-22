import fnmatch
import hashlib
import json
import os
import time
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional


HASH_CHUNK_SIZE = 1024 * 1024  # 1 MB


def compute_file_hash(path: str, chunk_size: int = HASH_CHUNK_SIZE) -> str:
    """Compute the SHA-256 hash for a file using chunked reads."""
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            sha.update(chunk)
    return sha.hexdigest()


def load_state(path: str) -> Dict[str, str]:
    """Load the backup state file if present."""
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("files", {})


def save_state(path: str, state: Dict[str, str]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"files": state}, f, indent=2, sort_keys=True)


def _is_excluded(relative_path: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch.fnmatch(relative_path, pattern) for pattern in patterns)


@dataclass
class BackupStats:
    files_copied: int = 0
    bytes_copied: int = 0
    skipped: int = 0
    duration: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "files_copied": self.files_copied,
            "bytes_copied": self.bytes_copied,
            "skipped": self.skipped,
            "duration": self.duration,
        }


class BackupError(Exception):
    """Raised when backup fails."""


def _copy_file(src: str, dest: str) -> int:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    bytes_copied = 0
    with open(src, "rb") as fsrc, open(dest, "wb") as fdst:
        for chunk in iter(lambda: fsrc.read(HASH_CHUNK_SIZE), b""):
            fdst.write(chunk)
            bytes_copied += len(chunk)
    return bytes_copied


def run_backup(
    src_dir: str,
    dest_dir: str,
    *,
    mode: str = "incremental",
    excludes: Optional[List[str]] = None,
    state_file: Optional[str] = None,
    dry_run: bool = False,
) -> BackupStats:
    """Run a backup from src_dir to dest_dir.

    Args:
        src_dir: Source directory path.
        dest_dir: Destination directory path.
        mode: "full" or "incremental".
        excludes: Optional list of glob patterns to exclude (applied to relative paths).
        state_file: Path to metadata file. Defaults to `.backupmate_state.json` inside dest_dir.
        dry_run: If True, report actions without copying or writing state.
    """
    if mode not in {"full", "incremental"}:
        raise BackupError(f"Invalid mode: {mode}")

    excludes = excludes or []
    src_dir = os.path.abspath(src_dir)
    dest_dir = os.path.abspath(dest_dir)

    if not os.path.isdir(src_dir):
        raise BackupError(f"Source directory does not exist: {src_dir}")

    os.makedirs(dest_dir, exist_ok=True)

    state_path = (
        os.path.abspath(state_file)
        if state_file
        else os.path.join(dest_dir, ".backupmate_state.json")
    )

    previous_state = load_state(state_path)
    new_state: Dict[str, str] = {}
    stats = BackupStats()

    start_time = time.time()
    try:
        for root, _, files in os.walk(src_dir):
            files.sort()
            rel_root = os.path.relpath(root, src_dir)
            rel_root = "" if rel_root == "." else rel_root
            for name in sorted(files):
                src_path = os.path.join(root, name)
                rel_path = os.path.normpath(os.path.join(rel_root, name))

                if _is_excluded(rel_path, excludes):
                    continue

                file_hash = compute_file_hash(src_path)
                new_state[rel_path] = file_hash

                if mode == "incremental" and previous_state.get(rel_path) == file_hash:
                    stats.skipped += 1
                    continue

                dest_path = os.path.join(dest_dir, rel_path)
                print(("DRY-RUN " if dry_run else "") + f"COPY {rel_path}")
                if not dry_run:
                    stats.bytes_copied += _copy_file(src_path, dest_path)
                stats.files_copied += 1
    finally:
        stats.duration = time.time() - start_time

    if not dry_run:
        save_state(state_path, new_state)

    return stats
