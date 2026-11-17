# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "pygithub>=2.10.0",
#     "rich>=15.0.0",
#     "rich-argparse>=1.8.0",
#     "truststore>=0.10.4",
# ]
# ///

import re
import webbrowser
from argparse import ArgumentParser, Namespace
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING, Final

from github import Github
from github.GithubException import GithubException
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text
from rich_argparse import RichHelpFormatter

from _github import get_auth  # ruff: ignore[import-private-name]  # standalone scripts share this helper

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from github.Auth import Token
    from github.CheckRun import CheckRun
    from github.CommitStatus import CommitStatus
    from github.PullRequest import PullRequest
    from github.WorkflowRun import WorkflowRun


def main() -> None:
    opts: Final = parse_cli()
    console: Final = Console()
    if not (auth := get_auth()):
        console.print("[red]No GitHub token found. Set GITHUB_TOKEN or run gh auth login.[/red]")
        raise SystemExit(1)
    try:
        run(console, auth, opts)
    except KeyboardInterrupt:
        console.print("[red]Interrupted by user (Ctrl+C)[/red]")
    except GithubException as exc:
        console.print(f"[red]GitHub API error: {exc}[/red]")
        raise SystemExit(1) from exc


def parse_cli() -> Options:
    parser: Final = ArgumentParser(
        description="Review and auto-merge PRs across maintained repositories.",
        formatter_class=RichHelpFormatter,
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without actually merging")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    return parser.parse_args(namespace=Options())


class Options(Namespace):
    dry_run: bool
    verbose: bool


def run(console: Console, auth: Token, opts: Options) -> None:
    console.print("[bold cyan]🔍 Scanning repositories for open PRs...[/bold cyan]")
    mergeable_prs, failed_prs = scan_repositories(console, auth)
    console.print()
    console.print(f"[bold]Found {len(mergeable_prs)} mergeable PRs and {len(failed_prs)} failed PRs[/bold]")
    console.print()
    if mergeable_prs:
        display_mergeable_prs(console, mergeable_prs)
        process_mergeable_prs(console, opts, mergeable_prs)
    if failed_prs:
        display_failed_prs(console, failed_prs)
        if not opts.dry_run:
            open_failed_prs(console, failed_prs)
    if not mergeable_prs and not failed_prs:
        console.print("[green]✨ No open PRs found![/green]")


def scan_repositories(
    console: Console, auth: Token
) -> tuple[list[tuple[str, PullRequest, str]], list[tuple[str, PullRequest, str, str | None]]]:
    # Every repository linked from https://bernat.tech/oss, plus pytest-memray and the shared github-workflows, which
    # the page leaves out; keep them in sync. toml-fmt covers its monorepo components; pyproject-fmt and tox-toml-fmt
    # are listed separately because the pre-commit hook mirrors are their own repos and get their own bot PRs.
    repositories: Final = (
        "tox-dev/platformdirs",
        "tox-dev/filelock",
        "pypa/virtualenv",
        "pypa/get-virtualenv",
        "tox-dev/tox",
        "tox-dev/pyproject-api",
        "pytest-dev/pytest-env",
        "tox-dev/pipdeptree",
        "tox-dev/sphinx-autodoc-typehints",
        "tox-dev/pre-commit-uv",
        "tox-dev/action-pre-commit-uv",
        "tox-dev/github-workflows",
        "tox-dev/tox-uv",
        "tox-dev/toml-fmt",
        "tox-dev/pyproject-fmt",
        "tox-dev/tox-toml-fmt",
        "pytest-dev/pytest-print",
        "tox-dev/tox-gh",
        "tox-dev/sphinx-argparse-cli",
        "tox-dev/python-discovery",
        "tox-dev/devpi-process",
        "tox-dev/tox-ini-fmt",
        "gaborbernat/bump-deps-index",
        "gaborbernat/pypi-changes",
        "gaborbernat/mdformat-hugo",
        "tox-dev/xml-fmt",
        "tox-dev/turbohtml",
        "tox-dev/peryx",
        "tox-dev/mdformat-zola",
        "tox-dev/PyVenvManage",
        "tox-dev/jetbrains-fish",
        "pypa/build",
        "pypa/pipx",
        "bloomberg/pytest-memray",
        "gaborbernat/all-repos-self",
        "gaborbernat/bernat-tech",
        "gaborbernat/cv",
        "gaborbernat/ropi_jegyzet_latex",
        "gaborbernat/dotfiles",
        "gaborbernat/gaborbernat",
        "gaborbernat/simplint",
        "tox-dev/python-sbom",
        "quotaline/quotaline",
    )
    with console.status("Searching for bot PRs..."):
        bot_prs: Final = find_bot_prs(Github(auth=auth), repositories)
    mergeable_prs: Final[list[tuple[str, PullRequest, str]]] = []
    failed_prs: Final[list[tuple[str, PullRequest, str, str | None]]] = []
    with (
        Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress,
        ThreadPoolExecutor(max_workers=16) as executor,
    ):
        task = progress.add_task("Checking bot PRs...", total=len(bot_prs))
        future_to_pr = {executor.submit(_check_single_pr, auth, *bot_pr): bot_pr for bot_pr in bot_prs}
        for future in as_completed(future_to_pr):
            try:
                pr, failure = future.result()
            except (GithubException, OSError, ValueError) as exc:
                repo_path, number = future_to_pr[future]
                console.print(f"[yellow]⚠ {repo_path}#{number}: Could not check PR ({exc})[/yellow]")
            else:
                if failure is None:
                    mergeable_prs.append((pr.base.repo.name, pr, pr.head.sha))
                else:
                    failed_prs.append((pr.base.repo.name, pr, *failure))
                console.print(f"[green]✓[/green] {pr.base.repo.name}#{pr.number} [dim]{pr.title}[/dim]")
            progress.advance(task)
    # Threads finish in any order; sort so the tables read the same on every run
    return sorted(mergeable_prs, key=_repo_and_number), sorted(failed_prs, key=_repo_and_number)


def _repo_and_number(entry: tuple[str, PullRequest, *tuple[str | None, ...]]) -> tuple[str, int]:
    return entry[0], entry[1].number


def find_bot_prs(client: Github, repositories: Iterable[str]) -> list[tuple[str, int]]:
    # One search across every repository replaces a pull listing per repository; the index lags by seconds at most
    query: Final = " ".join(("is:pr is:open draft:false sort:created-asc", *(f"repo:{repo}" for repo in repositories)))
    search_query: Final[str] = """
query($query: String!, $cursor: String) {
  search(query: $query, type: ISSUE, first: 100, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    nodes { ... on PullRequest { number author { __typename login } repository { nameWithOwner } } }
  }
}
"""
    bot_prs: Final[list[tuple[str, int]]] = []
    cursor: str | None = None
    while True:
        _, data = client.requester.graphql_query(search_query, {"query": query, "cursor": cursor})
        search = data["data"]["search"]
        bot_prs.extend(
            (node["repository"]["nameWithOwner"], node["number"])
            for node in search["nodes"]
            if (author := node["author"]) and author["__typename"] == "Bot" and _UPDATE_BOT.fullmatch(author["login"])
        )
        if not search["pageInfo"]["hasNextPage"]:
            return bot_prs
        cursor = search["pageInfo"]["endCursor"]


_UPDATE_BOT: Final[re.Pattern[str]] = re.compile(
    r"""
    dependabot
    | pre-commit-ci
    | [\w-]+-release  # each project's own GitHub App, which opens lock refresh and release PRs
    """,
    re.VERBOSE,
)


def _check_single_pr(auth: Token, repo_path: str, number: int) -> tuple[PullRequest, tuple[str, str | None] | None]:
    # A client per thread, since PyGithub sessions are not safe to share across threads. Lazy skips fetching the repo
    # and head commit, which only build URLs here, and full pages keep busy check-run lists to one request.
    pr: Final = Github(auth=auth, lazy=True, per_page=100).get_repo(repo_path).get_pull(number)
    return pr, check_pr_status(pr)


def check_pr_status(pr: PullRequest) -> tuple[str, str | None] | None:
    # mergeable is None while GitHub is still computing it, so do not act on stale data
    if pr.mergeable is not True or pr.mergeable_state in {"unknown", "dirty"}:
        return f"Not mergeable (mergeable={pr.mergeable}, state={pr.mergeable_state})", None
    # get_commits()[-1] is truncated past 250 commits, so read CI from the head commit itself
    head_commit: Final = pr.base.repo.get_commit(pr.head.sha)
    if (current := current_check_runs(pr, list(head_commit.get_check_runs()))) is None:
        return "No GitHub Actions runs found", None
    check_runs, workflows = current
    combined_status: Final = head_commit.get_combined_status()
    latest_statuses: Final = {
        status.context: status for status in sorted(combined_status.statuses, key=lambda item: item.id)
    }
    latest_check_runs: Final = {
        (check_run.app.id, check_run.name): check_run for check_run in sorted(check_runs, key=lambda item: item.id)
    }
    return check_failure(list(latest_statuses.values()), list(latest_check_runs.values())) or workflow_failure(
        workflows
    )


def current_check_runs(pr: PullRequest, check_runs: list[CheckRun]) -> tuple[list[CheckRun], list[WorkflowRun]] | None:
    if not any(check_run.app.slug == "github-actions" for check_run in check_runs):
        return check_runs, []
    latest: Final[dict[tuple[int, str], WorkflowRun]] = {}
    for workflow in sorted(pr.base.repo.get_workflow_runs(head_sha=pr.head.sha), key=lambda item: item.id):
        latest[workflow.workflow_id, workflow.event] = workflow
    if not latest:
        return None
    suites: Final = {workflow.check_suite_id for workflow in latest.values()}
    return (
        [
            check_run
            for check_run in check_runs
            if check_run.app.slug != "github-actions" or check_run.check_suite.id in suites
        ],
        list(latest.values()),
    )


def check_failure(statuses: list[CommitStatus], check_runs: list[CheckRun]) -> tuple[str, str | None] | None:
    if not statuses and not check_runs:
        return "No CI checks found", None
    for status in statuses:
        if status.state in {"error", "failure"}:
            return f"Check failed: {status.context}", status.target_url
        if status.state == "pending":
            return f"Check pending: {status.context}", status.target_url
    for check_run in check_runs:
        if check_run.status != "completed":
            return f"Check not completed: {check_run.name}", check_run.details_url
        if check_run.conclusion not in {"success", "neutral", "skipped"}:
            return f"Check failed: {check_run.name} ({check_run.conclusion})", check_run.details_url
    return None


def workflow_failure(workflows: list[WorkflowRun]) -> tuple[str, str] | None:
    for workflow in workflows:
        if workflow.status != "completed":
            return f"Workflow not completed: {workflow.name}", workflow.html_url
        if workflow.conclusion not in {"success", "neutral", "skipped"}:
            return f"Workflow failed: {workflow.name} ({workflow.conclusion})", workflow.html_url
    return None


def display_mergeable_prs(console: Console, mergeable_prs: list[tuple[str, PullRequest, str]]) -> None:
    console.print("[bold green]✅ Mergeable PRs (all checks passing):[/bold green]")
    table: Final = Table(show_header=True)
    table.add_column("Repository", style="cyan")
    table.add_column("PR #", style="magenta")
    table.add_column("Title", style="yellow")
    table.add_column("Author", style="blue")
    for repo_name, pr, _ in mergeable_prs:
        table.add_row(repo_name, Text(f"#{pr.number}", style=f"link {pr.html_url}"), pr.title, pr.user.login)
    console.print(table)
    console.print()


def process_mergeable_prs(
    console: Console, opts: Options, mergeable_prs: Sequence[tuple[str, PullRequest, str]]
) -> None:
    if opts.dry_run:
        for repo_name, pr, _ in mergeable_prs:
            console.print(f"[dim][DRY RUN] Would approve and merge {repo_name}#{pr.number}[/dim]")
        return
    by_repo: Final[dict[str, list[tuple[str, PullRequest, str]]]] = defaultdict(list)
    for entry in sorted(mergeable_prs, key=lambda item: item[1].number):
        by_repo[entry[0]].append(entry)
    # Merging one PR can leave a sibling in the same repository behind, so each repository merges in order
    with ThreadPoolExecutor(max_workers=16) as executor:
        for future in [executor.submit(_merge_in_order, console, entries) for entries in by_repo.values()]:
            future.result()


def _merge_in_order(console: Console, entries: list[tuple[str, PullRequest, str]]) -> None:
    for repo_name, pr, checked_sha in entries:
        approve_and_merge(console, repo_name, pr, checked_sha)


def approve_and_merge(console: Console, repo_name: str, pr: PullRequest, checked_sha: str) -> None:
    pr_link: Final = f"[link={pr.html_url}]{repo_name}#{pr.number}[/link]"
    try:
        console.print(f"[green]✓ Approving {pr_link}...[/green]")
        pr.create_review(body="LGTM", event="APPROVE")
        console.print(f"[green]✓ Merging {pr_link}...[/green]")
        merge_result = pr.merge(sha=checked_sha, merge_method="squash")
    except GithubException as exc:
        console.print(f"[red]❌ Failed to approve/merge {pr_link}: {exc}[/red]")
        return
    if merge_result.merged:
        console.print(f"[bold green]✅ Successfully merged {pr_link}![/bold green]")
    else:
        console.print(f"[yellow]⚠ Could not merge {pr_link}: {merge_result.message}[/yellow]")


def display_failed_prs(console: Console, failed_prs: list[tuple[str, PullRequest, str, str | None]]) -> None:
    console.print("[bold yellow]⚠️  PRs requiring manual review:[/bold yellow]")
    table: Final = Table(show_header=True)
    table.add_column("Repository", style="cyan")
    table.add_column("PR #", style="magenta")
    table.add_column("Title", style="yellow")
    table.add_column("Reason", style="red")
    for repo_name, pr, reason, reason_url in failed_prs:
        table.add_row(
            repo_name,
            Text(f"#{pr.number}", style=f"link {pr.html_url}"),
            pr.title,
            Text(reason, style=f"link {reason_url or f'{pr.html_url}/checks'}"),
        )
    console.print(table)
    console.print()


def open_failed_prs(console: Console, failed_prs: list[tuple[str, PullRequest, str, str | None]]) -> None:
    console.print("[bold]Opening failed PRs in browser...[/bold]")
    for repo_name, pr, _, _ in failed_prs:
        console.print(f"[dim]Opening {repo_name}#{pr.number}...[/dim]")
        webbrowser.open(pr.html_url)


if __name__ == "__main__":
    main()

__all__ = [
    "Options",
    "check_pr_status",
    "display_failed_prs",
    "display_mergeable_prs",
    "find_bot_prs",
    "process_mergeable_prs",
]
