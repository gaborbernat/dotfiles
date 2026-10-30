# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "pygithub>=2.10.0",
#     "rich>=15.0.0",
#     "rich-argparse>=1.8.0",
#     "truststore>=0.10.4",
# ]
# ///

import dataclasses
import os
import subprocess
from argparse import ArgumentParser, Namespace
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Final, Literal

from github import Github
from github.Auth import Token
from github.GithubException import GithubException
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm
from rich.table import Table
from rich_argparse import RichHelpFormatter
from truststore import inject_into_ssl

if TYPE_CHECKING:
    from github.Repository import Repository

type Category = Literal["gone", "merged", "remote-only", "stale"]


def main() -> None:
    opts: Final = parse_cli()
    console: Final = Console()
    try:
        run(console, opts)
    except KeyboardInterrupt:
        console.print("[red]Interrupted by user (Ctrl+C)[/red]")
    except subprocess.CalledProcessError as error:
        console.print(f"[red]Git command failed: {error}[/red]")
        raise SystemExit(1) from error


def parse_cli() -> Options:
    parser: Final = ArgumentParser(
        description="Clean up Git repository: delete merged branches, sync with upstream, remove stale branches.",
        formatter_class=RichHelpFormatter,
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--stale-days",
        type=int,
        default=14,
        help="Days of inactivity before a branch is considered stale (default: 14)",
    )
    return parser.parse_args(namespace=Options())


class Options(Namespace):
    dry_run: bool
    verbose: bool
    stale_days: int


def run(console: Console, opts: Options) -> None:
    if not run_git(["git", "rev-parse", "--git-dir"], opts, capture=True, check=False).strip():
        console.print("[red]Error: Not a git repository[/red]")
        raise SystemExit(1)
    console.print("[bold cyan]Git Repository Housekeeping[/bold cyan]\n")
    github_repo: Final = get_github_repo(console, opts)
    default_branch: Final = get_default_branch(console, opts)
    console.print(f"[dim]Default branch: {default_branch}[/dim]\n")
    # Load everything up front so the prompts that follow do not stall on Git or the GitHub API
    candidates: Final = load_all_data(console, opts, default_branch, github_repo)
    console.print()
    show_branches_to_review(console, candidates)
    deletions: Final = [
        *collect_gone_branches(opts, default_branch, candidates.gone),
        *collect_merged_branches(opts, candidates.merged),
        *collect_remote_only_branches(candidates.remote_only),
        *collect_stale_branches(console, opts, candidates.stale),
    ]
    if not deletions:
        console.print("\n[bold green]No branches to delete. Housekeeping complete![/bold green]")
        show_remaining_branches_summary(console, opts, default_branch, deletions)
        return
    show_deletion_summary(console, deletions)
    console.print()
    show_remaining_branches_summary(console, opts, default_branch, deletions)
    if opts.dry_run:
        console.print("\n[dim][DRY RUN] No changes made[/dim]")
        console.print("\n[bold green]Housekeeping complete![/bold green]")
        return
    if not Confirm.ask("\nProceed with deletion?", default=True):
        console.print("[dim]Cancelled[/dim]")
        console.print("\n[bold green]Housekeeping complete![/bold green]")
        return
    console.print()
    sync_default_branch(console, opts, default_branch)
    console.print()
    execute_all_deletions(console, opts, default_branch, deletions)
    console.print("\n[bold green]Housekeeping complete![/bold green]")


def run_git(cmd: list[str], opts: Options, *, capture: bool = False, check: bool = True) -> str:
    if opts.dry_run and not capture and not is_readonly_git(cmd):
        return ""
    result: Final = subprocess.run(cmd, capture_output=True, text=True, check=check)
    return result.stdout if capture else ""


def is_readonly_git(cmd: list[str]) -> bool:
    if cmd[1] in {"rev-parse", "symbolic-ref", "remote", "for-each-ref", "ls-remote", "log", "merge-base"}:
        return True
    # `git branch` only lists unless a mutating flag is present
    mutating_flags: Final = {"-d", "-D", "--delete", "-m", "-M", "--move", "-c", "-C", "--copy"}
    return cmd[1] == "branch" and mutating_flags.isdisjoint(cmd[2:])


def get_github_repo(console: Console, opts: Options) -> Repository | None:
    try:
        # Forks track the canonical repository as upstream, which is where their PRs merge
        remote_url = run_git(["git", "remote", "get-url", "upstream"], opts, capture=True, check=False).strip()
        if not remote_url:
            remote_url = run_git(["git", "remote", "get-url", "origin"], opts, capture=True).strip()
        enterprise_host: Final = os.environ.get("GITHUB_ENTERPRISE_HOST", "")
        on_enterprise: Final = bool(enterprise_host) and enterprise_host in remote_url
        if "github.com" not in remote_url and not on_enterprise:
            console.print("[yellow]Warning: Not a GitHub repository, skipping PR merge check[/yellow]")
            return None
        # git@github.com:owner/repo.git or https://github.com/owner/repo.git
        if remote_url.startswith("git@"):
            repo_path = remote_url.split(":")[-1].removesuffix(".git")
        else:
            repo_path = "/".join(remote_url.split("/")[-2:]).removesuffix(".git")
        if on_enterprise:
            if not (token := os.environ.get("GITHUB_ENTERPRISE_TOKEN")):
                console.print("[yellow]Warning: GITHUB_ENTERPRISE_TOKEN not set, skipping PR merge check[/yellow]")
                return None
            github = Github(base_url=f"https://{enterprise_host}/api/v3", auth=Token(token))
        else:
            if not (token := os.environ.get("GITHUB_TOKEN")):
                console.print("[yellow]Warning: GITHUB_TOKEN not set, skipping PR merge check[/yellow]")
                return None
            inject_into_ssl()
            github = Github(auth=Token(token))
        if opts.verbose:
            console.print(f"[dim]Using GitHub repository: {repo_path}[/dim]")
        return github.get_repo(repo_path)
    except (subprocess.CalledProcessError, GithubException) as error:
        if opts.verbose:
            console.print(f"[yellow]Warning: Could not access GitHub repository: {error}[/yellow]")
        return None


def get_default_branch(console: Console, opts: Options) -> str:
    for remote in ("origin", "upstream"):
        symref = run_git(["git", "ls-remote", "--symref", remote, "HEAD"], opts, capture=True, check=False)
        for line in symref.splitlines():
            if line.startswith("ref: refs/heads/") and line.endswith("\tHEAD"):
                return line.removeprefix("ref: refs/heads/").removesuffix("\tHEAD")
    console.print("[red]Could not determine the default branch from origin or upstream[/red]")
    raise SystemExit(2)


def load_all_data(console: Console, opts: Options, default_branch: str, github_repo: Repository | None) -> Candidates:
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task("Fetching remotes...", total=None)
        run_git(["git", "fetch", "--all", "--prune"], opts)
        progress.update(task, description="Loading branch information...")
        # Tab-delimited so any branch name parses
        tracking: Final = run_git(
            ["git", "for-each-ref", "--format=%(refname:short)%09%(upstream:track)", "refs/heads/"],
            opts,
            capture=True,
        )
        gone: Final = [
            name
            for name, _, track in (line.partition("\t") for line in tracking.splitlines())
            if name and "[gone]" in track
        ]
        merged_pr_refs: Final = find_merged_pr_refs(github_repo, opts, console) if github_repo else {}
        merged: list[str] = []
        if github_repo:
            progress.update(task, description="Checking for merged PRs...")
            merged = [
                branch
                for branch in run_git(["git", "branch", "--format=%(refname:short)"], opts, capture=True).splitlines()
                if branch and branch != default_branch and is_ref_merged(branch, merged_pr_refs, branch, opts)
            ]
        progress.update(task, description="Analyzing stale branches...")
        stale_branches: Final = sorted(
            get_stale_branches({default_branch, *gone, *merged}, opts), key=lambda item: item[1]
        )
        stale: Final[list[StaleBranch]] = []
        for index, (branch, days_ago) in enumerate(stale_branches, 1):
            progress.update(task, description=f"Analyzing {branch} ({index}/{len(stale_branches)})...")
            stale.append(
                StaleBranch(
                    name=branch,
                    days_ago=days_ago,
                    commits=get_branch_commits(branch, default_branch, opts),
                    remotes=remotes_with_branch(branch, opts),
                )
            )
        remote_only: Final[dict[str, list[str]]] = {"origin": [], "upstream": []}
        if github_repo:
            progress.update(task, description="Checking remote-only branches...")
            for remote, branches in get_remote_only_branches(default_branch, opts).items():
                remote_only[remote] = [
                    branch for branch in branches if is_ref_merged(f"{remote}/{branch}", merged_pr_refs, branch, opts)
                ]
    return Candidates(gone=gone, merged=merged, stale=stale, remote_only=remote_only)


def find_merged_pr_refs(github_repo: Repository, opts: Options, console: Console) -> dict[str, set[str]]:
    try:
        if opts.verbose:
            console.print(f"[dim]Fetching closed PRs from {github_repo.full_name}...[/dim]")
        refs: Final[dict[str, set[str]]] = {}
        count = 0
        for pr in github_repo.get_pulls(state="closed", sort="created", direction="desc"):
            count += 1
            if pr.merged and pr.head and pr.head.ref and pr.head.sha:
                refs.setdefault(pr.head.ref, set()).add(pr.head.sha)
        if opts.verbose:
            console.print(f"[dim]Checked {count} closed PRs; {len(refs)} merged head refs[/dim]")
    except GithubException as error:
        if opts.verbose:
            console.print(f"[yellow]GitHub API error: {error}[/yellow]")
        return {}
    return refs


def is_ref_merged(ref: str, merged_pr_refs: dict[str, set[str]], name: str, opts: Options) -> bool:
    # Match the tip SHA too, so a branch that reuses the name of a merged PR is kept
    if not (shas := merged_pr_refs.get(name)):
        return False
    tip: Final = run_git(["git", "rev-parse", "--verify", ref], opts, capture=True, check=False).strip()
    return bool(tip) and tip in shas


def get_stale_branches(excluded: set[str], opts: Options) -> list[tuple[str, int]]:
    output: Final = run_git(
        ["git", "for-each-ref", "--format=%(refname:short)%09%(committerdate:iso8601)", "refs/heads/"],
        opts,
        capture=True,
    )
    cutoff_date: Final = datetime.now(UTC) - timedelta(days=opts.stale_days)
    stale_branches: Final[list[tuple[str, int]]] = []
    for line in output.splitlines():
        branch, tab, date_str = line.partition("\t")
        if not tab or branch in excluded:
            continue
        if (commit_date := datetime.fromisoformat(date_str.replace(" ", "T"))) < cutoff_date:
            stale_branches.append((branch, (datetime.now(UTC) - commit_date).days))
    return stale_branches


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class StaleBranch:
    name: str
    days_ago: int
    commits: str
    remotes: tuple[str, ...]


def get_branch_commits(branch: str, default_branch: str, opts: Options) -> str:
    if not (
        merge_base := run_git(["git", "merge-base", default_branch, branch], opts, capture=True, check=False).strip()
    ):
        return ""
    return run_git(
        ["git", "log", "--oneline", "--no-decorate", f"{merge_base}..{branch}", "-15"],
        opts,
        capture=True,
        check=False,
    ).strip()


def remotes_with_branch(branch: str, opts: Options) -> tuple[str, ...]:
    return tuple(
        remote
        for remote in ("origin", "upstream")
        if run_git(["git", "ls-remote", "--heads", remote, branch], opts, capture=True, check=False).strip()
    )


def get_remote_only_branches(default_branch: str, opts: Options) -> dict[str, list[str]]:
    # %(refname:short) yields bare names, without the * and + worktree markers
    local_branches: Final = {
        branch
        for branch in run_git(["git", "branch", "--format=%(refname:short)"], opts, capture=True).splitlines()
        if branch
    }
    remote_only: Final[dict[str, list[str]]] = {"origin": [], "upstream": []}
    for raw_line in run_git(["git", "branch", "-r"], opts, capture=True).strip().split("\n"):
        line = raw_line.strip()
        if not line or "HEAD ->" in line or "/" not in line:
            continue
        remote, branch = line.split("/", 1)
        if branch not in {default_branch, "HEAD"} and branch not in local_branches and remote in remote_only:
            remote_only[remote].append(branch)
    return remote_only


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Candidates:
    gone: list[str]
    merged: list[str]
    stale: list[StaleBranch]
    remote_only: dict[str, list[str]]


def show_branches_to_review(console: Console, candidates: Candidates) -> None:
    if not (candidates.gone or candidates.merged or candidates.stale or any(candidates.remote_only.values())):
        return
    console.print("[bold cyan]Branches to review:[/bold cyan]\n")
    table: Final = Table(show_header=True)
    table.add_column("Branch", style="yellow")
    table.add_column("Category", style="cyan")
    table.add_column("Details", style="dim")
    for branch in candidates.gone:
        table.add_row(branch, "Gone", "Tracking deleted remote")
    for branch in candidates.merged:
        table.add_row(branch, "Merged", "PR has been merged")
    for remote, branches in candidates.remote_only.items():
        for branch in branches:
            table.add_row(f"{remote}/{branch}", "Remote-only", f"Merged on {remote}, not local")
    for stale in candidates.stale:
        table.add_row(stale.name, "Stale", f"Inactive for {stale.days_ago} days")
    console.print(table)
    console.print()


def collect_gone_branches(opts: Options, default_branch: str, gone: list[str]) -> list[Deletion]:
    upstream_ref: Final = f"upstream/{default_branch}"
    base_ref: Final = (
        upstream_ref if run_git_ok(["git", "rev-parse", "--verify", upstream_ref], opts) else default_branch
    )
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {
            executor.submit(run_git_ok, ["git", "merge-base", "--is-ancestor", branch, base_ref], opts): branch
            for branch in gone
        }
        return [
            Deletion(name=futures[future], category="gone", remotes=remotes_with_branch(futures[future], opts))
            for future in as_completed(futures)
            if future.result()
        ]


def run_git_ok(cmd: list[str], opts: Options) -> bool:
    if opts.dry_run and not is_readonly_git(cmd):
        return True
    return subprocess.run(cmd, capture_output=True, text=True, check=False).returncode == 0


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Deletion:
    name: str
    category: Category
    remotes: tuple[str, ...]


def collect_merged_branches(opts: Options, merged: list[str]) -> list[Deletion]:
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(remotes_with_branch, branch, opts): branch for branch in merged}
        return [
            Deletion(name=futures[future], category="merged", remotes=future.result())
            for future in as_completed(futures)
        ]


def collect_remote_only_branches(remote_only: dict[str, list[str]]) -> list[Deletion]:
    return [
        Deletion(name=branch, category="remote-only", remotes=(remote,))
        for remote, branches in remote_only.items()
        for branch in branches
    ]


def collect_stale_branches(console: Console, opts: Options, stale_branches: list[StaleBranch]) -> list[Deletion]:
    if not stale_branches:
        return []
    console.print(
        f"\n[bold yellow]Found {len(stale_branches)} stale branches "
        f"(inactive for {opts.stale_days}+ days):[/bold yellow]"
    )
    console.print("[dim]Review each branch:[/dim]\n")
    deletions: Final[list[Deletion]] = []
    for stale in stale_branches:
        if stale.commits:
            console.print(f"[dim]Recent commits on {stale.name}:[/dim]")
            for line in stale.commits.split("\n"):
                console.print(f"[dim]  {line}[/dim]")
            console.print()
        if Confirm.ask(f"Delete {stale.name} (inactive for {stale.days_ago} days)?", default=True):
            deletions.append(Deletion(name=stale.name, category="stale", remotes=stale.remotes))
    return deletions


def show_remaining_branches_summary(
    console: Console, opts: Options, default_branch: str, deletions: list[Deletion]
) -> None:
    console.print("\n[bold]Remaining branches:[/bold]")
    excluded: Final = {default_branch, "dependyfriend-updates", *(deletion.name for deletion in deletions)}
    table: Final = Table(show_header=True)
    table.add_column("Branch", style="cyan")
    table.add_column("Last Commit", style="yellow")
    table.add_column("Message", style="dim")
    current_branch: Final = run_git(["git", "rev-parse", "--abbrev-ref", "HEAD"], opts, capture=True).strip()
    output: Final = run_git(
        [
            "git",
            "for-each-ref",
            "--format=%(refname:short)%09%(committerdate:relative)%09%(subject)",
            "--sort=-committerdate",
            "refs/heads/",
        ],
        opts,
        capture=True,
    )
    for line in output.splitlines():
        if len(parts := line.split("\t", 2)) != 3 or parts[0] in excluded:
            continue
        branch, when, message = parts
        table.add_row(f"* {branch}" if branch == current_branch else f"  {branch}", when, message)
    console.print(table)


def show_deletion_summary(console: Console, deletions: list[Deletion]) -> None:
    console.print(f"\n[bold yellow]Will delete {len(deletions)} branches:[/bold yellow]")
    by_category: Final[dict[Category, list[Deletion]]] = {"gone": [], "merged": [], "remote-only": [], "stale": []}
    for deletion in deletions:
        by_category[deletion.category].append(deletion)
    for category, members in by_category.items():
        if not members:
            continue
        console.print(f"\n[cyan]{category.title()} branches ({len(members)}):[/cyan]")
        for deletion in members:
            console.print(f"  • {deletion.name}{f' + {", ".join(deletion.remotes)}' if deletion.remotes else ''}")


def sync_default_branch(console: Console, opts: Options, default_branch: str) -> None:
    console.print(f"[bold]Syncing {default_branch} with upstream...[/bold]")
    current_branch: Final = run_git(["git", "rev-parse", "--abbrev-ref", "HEAD"], opts, capture=True).strip()
    # A detached HEAD reports "HEAD"; remember the commit so we can return to it.
    original_ref: Final = (
        current_branch
        if current_branch != "HEAD"
        else run_git(["git", "rev-parse", "HEAD"], opts, capture=True).strip()
    )
    on_default: Final = current_branch == default_branch
    has_upstream: Final = "upstream" in run_git(["git", "remote"], opts, capture=True).split()
    upstream_ref: Final = f"upstream/{default_branch}" if has_upstream else f"origin/{default_branch}"
    if stashed := bool(run_git(["git", "status", "--porcelain"], opts, capture=True).strip()):
        console.print("[yellow]Working directory has uncommitted changes, stashing...[/yellow]")
        run_git(["git", "stash", "push", "-u", "-m", "git-tidy auto-stash"], opts)
    try:
        if not on_default:
            console.print(f"[dim]Switching to {default_branch}[/dim]")
            run_git(["git", "checkout", default_branch], opts)
        update_default_branch(console, opts, default_branch, upstream_ref)
    finally:
        if not on_default:
            console.print(f"[dim]Switching back to {original_ref}[/dim]")
            run_git(["git", "checkout", original_ref], opts)
        if stashed:
            console.print("[yellow]Restoring stashed changes...[/yellow]")
            if not run_git_ok(["git", "stash", "pop"], opts):
                console.print("[yellow]⚠ Could not pop stash automatically; run 'git stash pop' by hand[/yellow]")
    console.print()


def update_default_branch(console: Console, opts: Options, default_branch: str, upstream_ref: str) -> None:
    local_commit: Final = run_git(["git", "rev-parse", default_branch], opts, capture=True).strip()
    if local_commit == run_git(["git", "rev-parse", upstream_ref], opts, capture=True).strip():
        console.print(f"[green]✓ {default_branch} is up to date with {upstream_ref}[/green]")
        return
    if (
        run_git(["git", "merge-base", default_branch, upstream_ref], opts, capture=True).strip() == local_commit
        or not run_git(["git", "log", f"{upstream_ref}..{default_branch}", "--oneline"], opts, capture=True).strip()
    ):
        console.print(f"[yellow]Fast-forwarding {default_branch} to {upstream_ref}[/yellow]")
        run_git(["git", "merge", "--ff-only", upstream_ref], opts)
        console.print(f"[green]✓ {default_branch} fast-forwarded[/green]")
        return
    console.print(f"[yellow]Local {default_branch} has diverged from {upstream_ref}[/yellow]")
    if opts.dry_run:
        console.print(f"[dim][DRY RUN] Would rebase {default_branch} onto {upstream_ref}[/dim]")
    elif Confirm.ask(f"Rebase {default_branch} onto {upstream_ref}?"):
        # On a rebase conflict, abort so we never leave a half-finished rebase for the finally block.
        if run_git_ok(["git", "rebase", upstream_ref], opts):
            console.print(f"[green]✓ {default_branch} rebased onto {upstream_ref}[/green]")
        else:
            run_git(["git", "rebase", "--abort"], opts, check=False)
            console.print(f"[red]✗ Rebase hit conflicts; aborted, {default_branch} left unchanged[/red]")


def execute_all_deletions(console: Console, opts: Options, default_branch: str, deletions: list[Deletion]) -> None:
    console.print("\n[bold]Deleting branches...[/bold]")
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task("Deleting branches...", total=len(deletions))
        for deletion in deletions:
            progress.update(task, description=f"Deleting {deletion.name}...")
            if deletion.category == "remote-only":
                delete_remote_only_branch(deletion, opts, console)
            else:
                delete_branch_and_remotes(deletion, default_branch, opts, console)
            progress.advance(task)


def delete_remote_only_branch(deletion: Deletion, opts: Options, console: Console) -> None:
    branch: Final = deletion.name
    for remote in deletion.remotes:
        expected_tip = run_git(["git", "rev-parse", f"{remote}/{branch}"], opts, capture=True, check=False).strip()
        if not expected_tip or remote_branch_tip(remote, branch) != expected_tip:
            console.print(f"[yellow]⚠ Kept {remote}/{branch}: remote tip changed or could not be verified[/yellow]")
        else:
            push_delete(remote, branch, expected_tip, opts, console)


def remote_branch_tip(remote: str, branch: str) -> str | None:
    result: Final = subprocess.run(
        ["git", "ls-remote", "--heads", remote, f"refs/heads/{branch}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.partition("\t")[0] if result.returncode == 0 else None


def push_delete(remote: str, branch: str, remote_tip: str, opts: Options, console: Console) -> None:
    if run_git_ok(
        ["git", "push", f"--force-with-lease=refs/heads/{branch}:{remote_tip}", remote, "--delete", branch], opts
    ):
        console.print(f"[green]✓ Deleted remote branch {remote}/{branch}[/green]")
    else:
        console.print(f"[yellow]⚠ Could not delete remote branch {remote}/{branch}[/yellow]")


def delete_branch_and_remotes(deletion: Deletion, default_branch: str, opts: Options, console: Console) -> None:
    branch: Final = deletion.name
    if branch == run_git(["git", "rev-parse", "--abbrev-ref", "HEAD"], opts, capture=True).strip():
        console.print(f"[yellow]Switching to {default_branch} (current branch will be deleted)[/yellow]")
        run_git(["git", "checkout", default_branch], opts)
    local_tip: Final = run_git(["git", "rev-parse", branch], opts, capture=True).strip()
    run_git(["git", "branch", "-D", branch], opts)
    console.print(f"[green]✓ Deleted local branch {branch}[/green]")
    for remote in deletion.remotes:
        if remote_branch_tip(remote, branch) != local_tip:
            console.print(f"[yellow]⚠ Kept {remote}/{branch}: remote tip differs or could not be verified[/yellow]")
        else:
            push_delete(remote, branch, local_tip, opts, console)


if __name__ == "__main__":
    main()
