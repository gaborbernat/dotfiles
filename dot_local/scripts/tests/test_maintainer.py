from __future__ import annotations

import subprocess
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from private_maintainer import check_pr_status, display_failed_prs, display_mergeable_prs, get_token


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


def test_display_mergeable_prs_links_pr() -> None:
    console = Console(file=StringIO(), force_terminal=True, record=True)
    pr = MagicMock(number=1, html_url="https://github.com/example/repo/pull/1", title="Update", user=None)

    display_mergeable_prs(console, [("repo", pr, "head")])

    assert 'href="https://github.com/example/repo/pull/1"' in console.export_html()


@pytest.mark.parametrize(
    ("reason_url", "expected_url"),
    [
        pytest.param(
            "https://github.com/example/repo/actions/runs/1",
            "https://github.com/example/repo/actions/runs/1",
            id="failed check",
        ),
        pytest.param(None, "https://github.com/example/repo/pull/1/checks", id="checks fallback"),
    ],
)
def test_display_failed_prs_links_reason(reason_url: str | None, expected_url: str) -> None:
    console = Console(file=StringIO(), force_terminal=True, record=True)
    pr = MagicMock(number=1, html_url="https://github.com/example/repo/pull/1", title="Update")

    display_failed_prs(console, [("repo", pr, "Check failed", reason_url)])

    assert f'href="{expected_url}"' in console.export_html()


def test_display_failed_prs_links_pr() -> None:
    console = Console(file=StringIO(), force_terminal=True, record=True)
    pr = MagicMock(number=1, html_url="https://github.com/example/repo/pull/1", title="Update")

    display_failed_prs(console, [("repo", pr, "Check failed", None)])

    assert 'href="https://github.com/example/repo/pull/1"' in console.export_html()


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


def test_check_pr_status_returns_failed_check_url() -> None:
    check_run = _check_run(1, 1, "failure")
    check_run.details_url = "https://github.com/example/repo/actions/runs/1"
    pr = MagicMock(mergeable=True, mergeable_state="clean", head=MagicMock(sha="head"))
    pr.base.repo.get_commit.return_value.get_combined_status.return_value.statuses = []
    pr.base.repo.get_commit.return_value.get_check_runs.return_value = [check_run]

    assert check_pr_status(pr)[3] == check_run.details_url


def test_check_pr_status_ignores_superseded_workflow() -> None:
    old = _action_check_run(1, 10, "cancelled")
    old.configure_mock(name="unexpanded matrix")
    current = _action_check_run(2, 20, "success")
    pr = MagicMock(mergeable=True, mergeable_state="clean", head=MagicMock(sha="head"))
    pr.base.repo.get_commit.return_value.get_combined_status.return_value.statuses = []
    pr.base.repo.get_commit.return_value.get_check_runs.return_value = [old, current]
    pr.base.repo.get_workflow_runs.return_value = [
        _workflow_run(1, 10, "cancelled"),
        _workflow_run(2, 20, "success"),
    ]

    assert check_pr_status(pr)[0] == "success"


def test_check_pr_status_keeps_other_current_workflows() -> None:
    current = _action_check_run(2, 20, "success")
    failing = _action_check_run(3, 30, "failure")
    pr = MagicMock(mergeable=True, mergeable_state="clean", head=MagicMock(sha="head"))
    pr.base.repo.get_commit.return_value.get_combined_status.return_value.statuses = []
    pr.base.repo.get_commit.return_value.get_check_runs.return_value = [current, failing]
    pr.base.repo.get_workflow_runs.return_value = [
        _workflow_run(2, 20, "success"),
        _workflow_run(3, 30, "failure", workflow_id=2),
    ]

    assert check_pr_status(pr)[0] == "failed"


def test_check_pr_status_waits_for_latest_workflow() -> None:
    current = _action_check_run(2, 20, "success")
    pr = MagicMock(mergeable=True, mergeable_state="clean", head=MagicMock(sha="head"))
    pr.base.repo.get_commit.return_value.get_combined_status.return_value.statuses = []
    pr.base.repo.get_commit.return_value.get_check_runs.return_value = [current]
    workflow = _workflow_run(2, 20, None)
    workflow.status = "in_progress"
    pr.base.repo.get_workflow_runs.return_value = [workflow]

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


def _action_check_run(run_id: int, suite_id: int, conclusion: str) -> MagicMock:
    check_run = _check_run(run_id, 1, conclusion)
    check_run.app.slug = "github-actions"
    check_run.check_suite.id = suite_id
    return check_run


def _workflow_run(run_id: int, suite_id: int, conclusion: str | None, *, workflow_id: int = 1) -> MagicMock:
    workflow = MagicMock(
        id=run_id,
        workflow_id=workflow_id,
        event="pull_request",
        check_suite_id=suite_id,
        status="completed",
        conclusion=conclusion,
        html_url=f"https://github.com/example/repo/actions/runs/{run_id}",
    )
    workflow.configure_mock(name="PR gate")
    return workflow
