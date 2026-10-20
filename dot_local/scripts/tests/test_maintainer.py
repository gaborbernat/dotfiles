from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from private_maintainer import check_pr_status


@pytest.mark.parametrize(
    ("older", "newer", "expected"),
    [
        pytest.param("cancelled", "success", "success", id="replacement passes"),
        pytest.param("failure", "success", "success", id="rerun passes"),
        pytest.param("success", "failure", "failed", id="rerun fails"),
    ],
)
def test_check_pr_status_uses_latest_run(older: str, newer: str, expected: str) -> None:
    runs = [
        _check_run(1, 1, older),
        _check_run(2, 1, newer),
    ]
    pr = MagicMock(mergeable=True, mergeable_state="clean", head=MagicMock(sha="head"))
    pr.base.repo.get_commit.return_value.get_combined_status.return_value.statuses = []
    pr.base.repo.get_commit.return_value.get_check_runs.return_value = runs

    assert check_pr_status(pr)[0] == expected


def test_check_pr_status_keeps_checks_from_distinct_apps() -> None:
    runs = [
        _check_run(1, 1, "failure"),
        _check_run(2, 2, "success"),
    ]
    pr = MagicMock(mergeable=True, mergeable_state="clean", head=MagicMock(sha="head"))
    pr.base.repo.get_commit.return_value.get_combined_status.return_value.statuses = []
    pr.base.repo.get_commit.return_value.get_check_runs.return_value = runs

    assert check_pr_status(pr)[0] == "failed"


def test_check_pr_status_uses_latest_legacy_status() -> None:
    statuses = [
        MagicMock(id=1, context="ci", state="failure"),
        MagicMock(id=2, context="ci", state="success"),
    ]
    pr = MagicMock(mergeable=True, mergeable_state="clean", head=MagicMock(sha="head"))
    pr.base.repo.get_commit.return_value.get_combined_status.return_value.statuses = statuses
    pr.base.repo.get_commit.return_value.get_check_runs.return_value = []

    assert check_pr_status(pr)[0] == "success"


def _check_run(run_id: int, app_id: int, conclusion: str) -> MagicMock:
    check_run = MagicMock(id=run_id, app=MagicMock(id=app_id), status="completed", conclusion=conclusion)
    check_run.configure_mock(name="test")
    return check_run
