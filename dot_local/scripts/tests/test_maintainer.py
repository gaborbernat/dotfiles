import subprocess
from io import StringIO
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from rich.console import Console

from private_maintainer import check_pr_status, display_failed_prs, display_mergeable_prs, get_token

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture
def console() -> Console:
    return Console(file=StringIO(), force_terminal=True, record=True)


@pytest.fixture
def pr() -> MagicMock:
    pr = MagicMock(
        number=1,
        html_url="https://github.com/example/repo/pull/1",
        title="Update",
        user=MagicMock(login="dependabot[bot]"),
        mergeable=True,
        mergeable_state="clean",
        head=MagicMock(sha="head"),
    )
    pr.base.repo.get_commit.return_value.get_combined_status.return_value.statuses = []
    pr.base.repo.get_commit.return_value.get_check_runs.return_value = []
    return pr


def test_get_token_prefers_environment(monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "environment-token")
    gh = mocker.patch("private_maintainer.subprocess.run", autospec=True)

    assert get_token() == "environment-token"
    gh.assert_not_called()


@pytest.mark.parametrize(
    ("stdout", "expected"),
    [
        pytest.param("gh-token\n", "gh-token", id="gh token"),
        pytest.param("\n", None, id="empty gh output"),
    ],
)
def test_get_token_uses_gh_auth(
    monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture, stdout: str, expected: str | None
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "")
    completed = subprocess.CompletedProcess(("gh", "auth", "token"), 0, stdout=stdout)
    mocker.patch("private_maintainer.subprocess.run", autospec=True, return_value=completed)

    assert get_token() == expected


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(FileNotFoundError(), id="gh missing"),
        pytest.param(subprocess.CalledProcessError(1, ("gh", "auth", "token")), id="gh not authenticated"),
    ],
)
def test_get_token_handles_gh_failure(
    monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture, error: OSError | subprocess.CalledProcessError
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "")
    mocker.patch("private_maintainer.subprocess.run", autospec=True, side_effect=error)

    assert get_token() is None


def test_display_mergeable_prs_links_pr(console: Console, pr: MagicMock) -> None:
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
def test_display_failed_prs_links_reason(
    console: Console, pr: MagicMock, reason_url: str | None, expected_url: str
) -> None:
    display_failed_prs(console, [("repo", pr, "Check failed", reason_url)])

    assert f'href="{expected_url}"' in console.export_html()


def test_display_failed_prs_links_pr(console: Console, pr: MagicMock) -> None:
    display_failed_prs(console, [("repo", pr, "Check failed", None)])

    assert 'href="https://github.com/example/repo/pull/1"' in console.export_html()


@pytest.mark.parametrize(
    ("conclusions", "expected"),
    [
        pytest.param([(1, "cancelled"), (1, "success")], None, id="replacement passes"),
        pytest.param([(1, "failure"), (1, "success")], None, id="rerun passes"),
        pytest.param(
            [(1, "success"), (1, "failure")],
            ("Check failed: test (failure)", "https://github.com/example/repo/actions/runs/2"),
            id="rerun fails",
        ),
        pytest.param(
            [(1, "failure"), (2, "success")],
            ("Check failed: test (failure)", "https://github.com/example/repo/actions/runs/1"),
            id="distinct apps keep the failure",
        ),
    ],
)
def test_check_pr_status_uses_latest_run(
    pr: MagicMock, conclusions: list[tuple[int, str]], expected: tuple[str, str] | None
) -> None:
    pr.base.repo.get_commit.return_value.get_check_runs.return_value = [
        _check_run(run_id, app_id, conclusion) for run_id, (app_id, conclusion) in enumerate(conclusions, 1)
    ]

    assert check_pr_status(pr) == expected


@pytest.mark.parametrize(
    ("check_runs", "workflow_runs", "expected"),
    [
        pytest.param(
            [(1, 10, "cancelled", "unexpanded matrix"), (2, 20, "success", "test")],
            [(1, 10, 1, "completed", "cancelled"), (2, 20, 1, "completed", "success")],
            None,
            id="superseded workflow ignored",
        ),
        pytest.param(
            [(2, 20, "success", "test"), (3, 30, "failure", "test")],
            [(2, 20, 1, "completed", "success"), (3, 30, 2, "completed", "failure")],
            ("Check failed: test (failure)", "https://github.com/example/repo/actions/runs/3"),
            id="other current workflow kept",
        ),
        pytest.param(
            [(2, 20, "success", "test")],
            [(2, 20, 1, "in_progress", None)],
            ("Workflow not completed: PR gate", "https://github.com/example/repo/actions/runs/2"),
            id="latest workflow still running",
        ),
    ],
)
def test_check_pr_status_workflow_runs(
    pr: MagicMock,
    check_runs: list[tuple[int, int, str, str]],
    workflow_runs: list[tuple[int, int, int, str, str | None]],
    expected: tuple[str, str] | None,
) -> None:
    pr.base.repo.get_commit.return_value.get_check_runs.return_value = [
        _action_check_run(run_id, suite_id, conclusion, name) for run_id, suite_id, conclusion, name in check_runs
    ]
    pr.base.repo.get_workflow_runs.return_value = [_workflow_run(*workflow_run) for workflow_run in workflow_runs]

    assert check_pr_status(pr) == expected


def test_check_pr_status_uses_latest_legacy_status(pr: MagicMock) -> None:
    pr.base.repo.get_commit.return_value.get_combined_status.return_value.statuses = [
        MagicMock(id=1, context="ci", state="failure"),
        MagicMock(id=2, context="ci", state="success"),
    ]

    assert check_pr_status(pr) is None


def _check_run(run_id: int, app_id: int, conclusion: str) -> MagicMock:
    check_run = MagicMock(
        id=run_id,
        app=MagicMock(id=app_id),
        status="completed",
        conclusion=conclusion,
        details_url=f"https://github.com/example/repo/actions/runs/{run_id}",
    )
    check_run.configure_mock(name="test")
    return check_run


def _action_check_run(run_id: int, suite_id: int, conclusion: str, name: str) -> MagicMock:
    check_run = MagicMock(
        id=run_id,
        app=MagicMock(id=1, slug="github-actions"),
        check_suite=MagicMock(id=suite_id),
        status="completed",
        conclusion=conclusion,
        details_url=f"https://github.com/example/repo/actions/runs/{run_id}",
    )
    check_run.configure_mock(name=name)
    return check_run


def _workflow_run(run_id: int, suite_id: int, workflow_id: int, status: str, conclusion: str | None) -> MagicMock:
    workflow = MagicMock(
        id=run_id,
        workflow_id=workflow_id,
        event="pull_request",
        check_suite_id=suite_id,
        status=status,
        conclusion=conclusion,
        html_url=f"https://github.com/example/repo/actions/runs/{run_id}",
    )
    workflow.configure_mock(name="PR gate")
    return workflow
