from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from private_maintainer import check_pr_status, get_token


def test_get_token_prefers_environment() -> None:
    with (
        patch.dict("os.environ", {"GITHUB_TOKEN": "environment-token"}),
        patch("private_maintainer.subprocess.run") as gh,
    ):
        assert get_token() == "environment-token"
    gh.assert_not_called()


def test_get_token_uses_gh_auth() -> None:
    completed = subprocess.CompletedProcess(("gh", "auth", "token"), 0, stdout="gh-token\n")
    with (
        patch.dict("os.environ", {"GITHUB_TOKEN": ""}),
        patch("private_maintainer.subprocess.run", return_value=completed),
    ):
        assert get_token() == "gh-token"


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(FileNotFoundError(), id="gh missing"),
        pytest.param(subprocess.CalledProcessError(1, ("gh", "auth", "token")), id="gh not authenticated"),
    ],
)
def test_get_token_handles_gh_failure(error: OSError | subprocess.CalledProcessError) -> None:
    with patch.dict("os.environ", {"GITHUB_TOKEN": ""}), patch("private_maintainer.subprocess.run", side_effect=error):
        assert get_token() is None


def test_get_token_rejects_empty_gh_output() -> None:
    completed = subprocess.CompletedProcess(("gh", "auth", "token"), 0, stdout="\n")
    with (
        patch.dict("os.environ", {"GITHUB_TOKEN": ""}),
        patch("private_maintainer.subprocess.run", return_value=completed),
    ):
        assert get_token() is None


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
