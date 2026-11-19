"""Tests for jetstream.alerts, which decides what the Dependabot alert sync changes."""

import json
from datetime import date
from pathlib import Path
from typing import Any, Final

import pytest

from jetstream import alerts

TODAY: Final[date] = date(2026, 11, 19)


def alert(number: int, state: str, ids: tuple[str, ...], dismissed_comment: str | None = None) -> dict[str, Any]:
    """Return a Dependabot alert, as the API returns it, with just the fields the sync reads."""
    return {
        "number": number,
        "state": state,
        "dismissed_comment": dismissed_comment,
        "dismissed_reason": "tolerable_risk" if state == "dismissed" else None,
        "security_advisory": {"ghsa_id": ids[0], "identifiers": [{"type": "GHSA" if i.startswith("GHSA") else "CVE", "value": i} for i in ids]},
    }


def exceptions(tmp_path: Path, files: dict[str, str]) -> dict[str, list[alerts.Accepted]]:
    """Write ``files`` into ``tmp_path`` and return the exceptions read from it."""
    for name, content in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(content)
    return alerts.read_exceptions(tmp_path, TODAY)


def test_exceptions_are_read_from_every_file(tmp_path: Path) -> None:
    """Each file's exceptions are read, comments and blank lines skipped, with whether each still applies."""
    found: dict[str, list[alerts.Accepted]] = exceptions(
        tmp_path,
        {
            ".trivyignore": "# a comment\n\nCVE-2026-1 exp:2026-11-26  # fixed in foo 1.2.3\n",
            ".jetstream/pip-audit-ignore": "CVE-2026-2 exp:2026-11-19\nCVE-2026-3\n",
        },
    )
    assert found == {
        "CVE-2026-1": [alerts.Accepted("CVE-2026-1", current=True, note=".trivyignore (exp 2026-11-26): fixed in foo 1.2.3")],
        "CVE-2026-2": [alerts.Accepted("CVE-2026-2", current=False, note=".jetstream/pip-audit-ignore (exp 2026-11-19)")],  # expires on its date
        "CVE-2026-3": [alerts.Accepted("CVE-2026-3", current=True, note=".jetstream/pip-audit-ignore (exp none)")],
    }


@pytest.mark.parametrize("line", ["CVE-2026-1 2026-11-26", "CVE-2026-1 exp:2026-11-26 extra"])
def test_a_malformed_exception_is_an_error(tmp_path: Path, line: str) -> None:
    """Anything but an ID, then an optional exp:YYYY-MM-DD, is an error naming the file."""
    with pytest.raises(alerts.AlertsError, match=r"^\.trivyignore: .*expected exp:YYYY-MM-DD"):
        exceptions(tmp_path, {".trivyignore": f"{line}\n"})


def test_plan_follows_the_table(tmp_path: Path) -> None:
    """Each alert gets the change dependabot-alerts.md's table gives it."""
    accepted: dict[str, list[alerts.Accepted]] = exceptions(tmp_path, {".trivyignore": "CVE-2026-1 exp:2026-11-26  # why\nCVE-2026-9 exp:2026-11-01\n"})
    comment: str = f"{alerts.MARKER} .trivyignore (exp 2026-11-26): why"
    changes: list[alerts.Change] = alerts.plan(
        [
            alert(1, "open", ("GHSA-1", "CVE-2026-1")),  # accepted, by its CVE: dismiss
            alert(2, "dismissed", ("GHSA-2", "CVE-2026-1"), dismissed_comment=comment),  # already as it should be: nothing
            alert(3, "dismissed", ("GHSA-3", "CVE-2026-1"), dismissed_comment=f"{alerts.MARKER} an old comment"),  # update
            alert(4, "dismissed", ("GHSA-4", "CVE-2026-4"), dismissed_comment=f"{alerts.MARKER} gone"),  # no exception now: reopen
            alert(5, "dismissed", ("GHSA-5", "CVE-2026-9"), dismissed_comment=f"{alerts.MARKER} expired"),  # expired: reopen
            alert(6, "dismissed", ("GHSA-6", "CVE-2026-1"), dismissed_comment="by hand"),  # someone else's: leave
            alert(7, "open", ("GHSA-7", "CVE-2026-7")),  # not accepted: nothing
        ],
        accepted,
    )
    assert changes == [
        alerts.Change(1, "dismiss", "GHSA-1", comment),
        alerts.Change(3, "update", "GHSA-3", comment),
        alerts.Change(4, "reopen", "GHSA-4", ""),
        alerts.Change(5, "reopen", "GHSA-5", ""),
        alerts.Change(6, "leave", "GHSA-6", "tolerable_risk"),
    ]


def test_every_exception_for_a_vulnerability_must_apply(tmp_path: Path) -> None:
    """A vulnerability excepted in two files is accepted only while both exceptions apply."""
    accepted: dict[str, list[alerts.Accepted]] = exceptions(tmp_path, {".trivyignore": "CVE-2026-1 exp:2026-11-26\n", ".pip-audit-ignore": "GHSA-1 exp:2026-11-01\n"})
    assert alerts.plan([alert(1, "open", ("GHSA-1", "CVE-2026-1"))], accepted) == []


def test_a_comment_is_cut_to_githubs_limit(tmp_path: Path) -> None:
    """A dismissal comment is at most COMMENT_LIMIT characters, and a tab in it can't split its line."""
    accepted: dict[str, list[alerts.Accepted]] = exceptions(tmp_path, {".trivyignore": f"CVE-2026-1  # {'x' * 400}\n"})
    change: alerts.Change = alerts.plan([alert(1, "open", ("GHSA-1", "CVE-2026-1"))], accepted)[0]
    assert len(change.comment) == alerts.COMMENT_LIMIT
    assert alerts.tsv(alerts.Change(1, "dismiss", "GHSA-1", "a\tb\nc")) == "1\tdismiss\tGHSA-1\ta b c"


def test_main_prints_the_changes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """``plan ALERTS_JSON`` reads the exceptions in the current directory and prints one change per line."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".trivyignore").write_text("CVE-2099-1\n")
    (tmp_path / "alerts.json").write_text(json.dumps([alert(1, "open", ("GHSA-1", "CVE-2099-1"))]))
    assert alerts.main(["plan", "alerts.json"]) == alerts.EXIT_OK
    assert capsys.readouterr().out == f"1\tdismiss\tGHSA-1\t{alerts.MARKER} .trivyignore (exp none)\n"


def test_main_reports_a_bad_command(capsys: pytest.CaptureFixture[str]) -> None:
    """Anything but ``plan ALERTS_JSON`` is an error with the usage."""
    assert alerts.main(["plan"]) == alerts.EXIT_ERROR
    assert "usage: python -m jetstream.alerts plan ALERTS_JSON" in capsys.readouterr().err
