"""Decide what ``run-sync-dependabot-alerts.sh`` does to each of a repo's Dependabot alerts.

The scanners' exception files are the record of which vulnerabilities a repo
accepts, and the sync mirrors them onto its Dependabot alerts: an alert for an
accepted vulnerability is dismissed, with the exception's comment, and is
reopened once the exception is removed or expires. The sync only ever reopens
or changes an alert it dismissed itself, which its comment's MARKER shows.

The script fetches the alerts and applies the changes; this module reads the
alerts it fetched and the exception files, and runs no subprocess. Usage::

    python -I -m jetstream.alerts plan ALERTS_JSON

prints one change per line, tab-separated: the alert's number, the action
(``dismiss``, ``update``, ``reopen`` or ``leave``), its GHSA ID, and the
dismissal comment (for ``leave``, how it was dismissed).
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Final

# Every exception file, jetstream's and the repo's, for every scanner.
EXCEPTION_FILES: Final[tuple[str, ...]] = (".jetstream/trivyignore", ".trivyignore", ".jetstream/pip-audit-ignore", ".pip-audit-ignore")

# The start of every comment the sync writes, so it knows its own dismissals.
MARKER: Final[str] = "[jetstream exceptions]"
COMMENT_LIMIT: Final[int] = 280  # GitHub's limit for a dismissal comment

EXPIRES: Final[re.Pattern[str]] = re.compile(r"^exp:\d{4}-\d{2}-\d{2}$")

EXIT_OK: Final[int] = 0
EXIT_ERROR: Final[int] = 2


class AlertsError(Exception):
    """A problem with the exceptions or alerts, reported in one line."""


@dataclass(frozen=True)
class Accepted:
    """One exception: a vulnerability ID, whether it still applies, and how it's described in a comment."""

    vuln_id: str
    current: bool
    note: str


@dataclass(frozen=True)
class Change:
    """What to do to one alert."""

    number: int
    action: str
    ghsa: str
    comment: str


def read_exceptions(root: Path, today: date) -> dict[str, list[Accepted]]:
    """Return every exception in ``root``'s exception files, by vulnerability ID."""
    found: dict[str, list[Accepted]] = {}
    for name in EXCEPTION_FILES:
        path: Path = root / name
        if not path.is_file():
            continue
        for line in path.read_text().splitlines():
            head: str
            comment: str
            head, _, comment = line.partition("#")
            vuln_id: str
            expires: date | None
            match head.split():
                case []:
                    continue
                case [vuln_id]:
                    expires = None
                case [vuln_id, field] if EXPIRES.match(field):
                    expires = date.fromisoformat(field.removeprefix("exp:"))
                case _:
                    msg: str = f"{name}: '{head.strip()}': expected exp:YYYY-MM-DD after the ID"
                    raise AlertsError(msg)
            note: str = f"{name} (exp {expires or 'none'})" + (f": {comment.strip()}" if comment.strip() else "")
            found.setdefault(vuln_id, []).append(Accepted(vuln_id, expires is None or today < expires, note))
    return found


def plan(alerts: list[dict[str, Any]], exceptions: dict[str, list[Accepted]]) -> list[Change]:
    """Return the changes that make ``alerts`` match ``exceptions``."""
    changes: list[Change] = []
    for alert in alerts:
        ids: list[str] = [identifier["value"] for identifier in alert["security_advisory"]["identifiers"]]
        entries: list[Accepted] = [entry for vuln_id in ids for entry in exceptions.get(vuln_id, [])]
        # Every exception for it must still apply, in whichever files it's in.
        accepted: bool = bool(entries) and all(entry.current for entry in entries)
        comment: str = f"{MARKER} {'; '.join(sorted({entry.note for entry in entries}))}"[:COMMENT_LIMIT]
        dismissed_comment: str = alert.get("dismissed_comment") or ""
        ours: bool = dismissed_comment.startswith(MARKER)
        number: int = alert["number"]
        ghsa: str = alert["security_advisory"]["ghsa_id"]
        match alert["state"], accepted, ours:
            case "open", True, _:
                changes.append(Change(number, "dismiss", ghsa, comment))
            case "dismissed", True, True if dismissed_comment != comment:
                changes.append(Change(number, "update", ghsa, comment))
            case "dismissed", False, True:
                changes.append(Change(number, "reopen", ghsa, ""))
            case "dismissed", _, False:
                changes.append(Change(number, "leave", ghsa, alert.get("dismissed_reason") or "no reason"))
            case _:
                pass  # open and not accepted, or already dismissed with this comment
    return changes


def tsv(change: Change) -> str:
    """Return ``change`` as one tab-separated line, with any tab or newline in its comment made a space."""
    comment: str = re.sub(r"[\t\r\n]+", " ", change.comment)
    return f"{change.number}\t{change.action}\t{change.ghsa}\t{comment}"


def main(argv: list[str] | None = None) -> int:
    """Run ``python -m jetstream.alerts`` and return its exit status."""
    alerts_json: str
    match sys.argv[1:] if argv is None else argv:
        case ["plan", alerts_json]:
            pass
        case _:
            sys.stderr.write("usage: python -m jetstream.alerts plan ALERTS_JSON\n")
            return EXIT_ERROR
    try:
        alerts: list[dict[str, Any]] = json.loads(Path(alerts_json).read_text())
        changes: list[Change] = plan(alerts, read_exceptions(Path.cwd(), datetime.now(UTC).date()))
    except AlertsError as e:
        sys.stderr.write(f"*** jetstream alerts: {e}\n")
        return EXIT_ERROR
    for change in changes:
        sys.stdout.write(f"{tsv(change)}\n")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
