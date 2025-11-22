# backupmate

Simple, safe incremental backups with content hashing. Implemented using only the Python standard library.

## Features
- Incremental mode that skips unchanged files using SHA-256 hashes
- Full mode that copies everything
- Optional glob excludes
- State file stored alongside backups (configurable path)
- Dry-run and JSON reporting

## Installation
Requires Python 3.10+.

```
python backupmate.py --help
```

## Usage
```
python backupmate.py SRC_DIR DEST_DIR [--mode full|incremental] \
    [--exclude PATTERN ...] [--state-file PATH] [--dry-run] [--json-report PATH]
```

- `SRC_DIR` and `DEST_DIR` are required positional paths.
- `--mode` defaults to `incremental`.
- `--exclude` can be repeated to skip matching relative paths.
- `--state-file` defaults to `.backupmate_state.json` inside `DEST_DIR`.
- `--dry-run` shows planned copies without writing files or state.
- `--json-report` writes a summary with files/bytes copied, skipped count, and duration.

Exit codes: 0 success, 1 invalid arguments, 2 runtime error.

## Development
Run the tests with:

```
python -m unittest tests_backupmate.py
```
