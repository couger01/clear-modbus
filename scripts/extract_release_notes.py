"""Extract one Towncrier changelog section for GitHub Releases."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = ROOT / "CHANGELOG.md"


def extract_release_notes(changelog: str, version: str) -> str:
    """Return the changelog section for version.

    Parameters
    ----------
    changelog : `str`
        Full changelog text.
    version : `str`
        Release version without the leading ``v`` tag prefix.

    Returns
    -------
    notes : `str`
        The matching Markdown section.

    Raises
    ------
    ValueError
        If no changelog section matches the version.

    """
    heading = re.compile(rf"^## {re.escape(version)} \(.+\)\s*$")
    lines = changelog.splitlines()
    start = next(
        (index for index, line in enumerate(lines) if heading.match(line)),
        None,
    )
    if start is None:
        msg = f"No changelog section found for version {version}"
        raise ValueError(msg)

    end = next(
        (
            index
            for index, line in enumerate(lines[start + 1 :], start + 1)
            if line.startswith("## ")
        ),
        len(lines),
    )
    return "\n".join(lines[start:end]).strip() + "\n"


def main() -> int:
    """Extract release notes and write them to a Markdown file.

    Returns
    -------
    exit_code : `int`
        Zero on success, non-zero when the changelog section is missing.

    """
    parser = argparse.ArgumentParser()
    parser.add_argument("version", help="Release version without the leading v")
    parser.add_argument("output", type=Path, help="Path for extracted notes")
    args = parser.parse_args()

    try:
        notes = extract_release_notes(
            CHANGELOG.read_text(encoding="utf-8"),
            args.version,
        )
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1

    args.output.write_text(notes, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
