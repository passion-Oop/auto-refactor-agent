#!/usr/bin/env python3
"""
AutoRefactor Agent - 一个可运行的多 Agent 框架示例（单文件实现）

功能：
- 扫描仓库代码质量（通过 flake8/ruff/pylint 输出）
- 自动格式化/重构（通过 black/isort/ruff --fix）
- 运行测试（pytest）
- 在通过验证后自动创建分支、提交并通过 GitHub API 创建 PR

注意：
- 该脚本旨在作为起点与参考实现；生产环境请补充更完善的安全、并发控制与回滚逻辑。
- 需要在运行环境中安装以下工具（pip install -r requirements.txt）：
    - gitpython
    - requests
    - black, isort, ruff, flake8, pytest 等 CLI 工具（可通过 pip 安装）
示例：
    export GITHUB_TOKEN="ghp_xxx"
    python3 auto_refactor_agent.py --repo-path /path/to/repo --github-owner myorg --github-repo myrepo
"""

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import requests
from git import Repo, GitCommandError

# -----------------------
# Configuration / Globals
# -----------------------
GITHUB_API = "https://api.github.com"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


# -----------------------
# Utility functions
# -----------------------
def run_cmd(cmd: List[str], cwd: Optional[Path] = None, capture_output: bool = False):
    logging.debug("Running command: %s (cwd=%s)", " ".join(cmd), cwd)
    try:
        res = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            check=True,
            stdout=subprocess.PIPE if capture_output else None,
            stderr=subprocess.PIPE if capture_output else None,
            text=True,
        )
        if capture_output:
            return res.stdout.strip()
        return ""
    except subprocess.CalledProcessError as e:
        logging.error("Command failed: %s", " ".join(cmd))
        if capture_output:
            logging.error("stdout: %s", e.stdout)
            logging.error("stderr: %s", e.stderr)
            return e.stdout + "\n" + e.stderr
        raise


# -----------------------
# Agents Implementation
# -----------------------
@dataclass
class ScanResult:
    file_path: Path
    issues: str


class RepoScannerAgent:
    """
    扫描仓库代码风格/静态问题（示例使用 flake8/ruff）
    """

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path

    def scan_with_flake8(self) -> List[ScanResult]:
        logging.info("Running flake8 scan...")
        try:
            output = run_cmd(["flake8", "--format=%(path)s:%(row)d:%(col)d:%(code)s:%(text)s"], cwd=self.repo_path, capture_output=True)
        except Exception as e:
            logging.warning("flake8 run failed or not installed: %s", e)
            output = ""
        results = []
        if output:
            for line in output.splitlines():
                # path:row:col:CODE:message
                parts = line.split(":", 4)
                if len(parts) >= 5:
                    path = self.repo_path.joinpath(parts[0]).resolve()
                    results.append(ScanResult(file_path=path, issues=line))
        logging.info("flake8 found %d issues", len(results))
        return results

    def scan_repo(self) -> List[ScanResult]:
        # 可以扩展多种扫描策略（ruff, pylint, safety etc.）
        results = self.scan_with_flake8()
        return results


class RefactorAgent:
    """
    对代码进行自动格式化与简单重构（调用 black/isort/ruff --fix）
    """

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path

    def apply_black(self):
        logging.info("Running black...")
        try:
            run_cmd(["black", "."], cwd=self.repo_path)
        except Exception as e:
            logging.warning("black failed or not installed: %s", e)

    def apply_isort(self):
        logging.info("Running isort...")
        try:
            run_cmd(["isort", "."], cwd=self.repo_path)
        except Exception as e:
            logging.warning("isort failed or not installed: %s", e)

    def apply_ruff_fix(self):
        logging.info("Running ruff --fix...")
        try:
            run_cmd(["ruff", "check", ".", "--fix"], cwd=self.repo_path)
        except Exception as e:
            logging.warning("ruff fix failed or not installed: %s", e)

    def run_refactors(self):
        # 执行一系列自动修复工具
        self.apply_isort()
        self.apply_black()
        self.apply_ruff_fix()
        # 这里可以接入更复杂的 AST 级别重构（rope / lib2to3 / jedi）
        logging.info("Refactor steps completed.")


class TestAgent:
    """
    运行测试套件（pytest）并报告结果
    """

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path

    def run_pytest(self) -> bool:
        logging.info("Running pytest...")
        try:
            run_cmd(["pytest", "-q"], cwd=self.repo_path)
            logging.info("Tests passed.")
            return True
        except Exception as e:
            logging.error("Tests failed or pytest not installed: %s", e)
            return False


class GitAgent:
    """
    处理 git 操作：创建分支、提交、推送
    使用 GitPython 进行示例实现
    """

    def __init__(self, repo_path: Path, remote_name: str = "origin"):
        self.repo_path = repo_path
        self.remote_name = remote_name
        self.repo = Repo(repo_path)

    def create_branch_and_checkout(self, branch_name: str):
        logging.info("Creating and checking out branch %s", branch_name)
        try:
            new_branch = self.repo.create_head(branch_name)
            new_branch.checkout()
        except GitCommandError as e:
            logging.warning("Branch create/checkout failed (maybe exists). Trying to checkout: %s", e)
            self.repo.git.checkout(branch_name)

    def commit_all(self, message: str):
        logging.info("Staging all changes and committing: %s", message)
        self.repo.git.add(A=True)
        if self.repo.index.diff("HEAD") or self.repo.untracked_files:
            self.repo.index.commit(message)
            logging.info("Commit created.")
            return True
        logging.info("No changes to commit.")
        return False

    def push_branch(self, branch_name: str):
        logging.info("Pushing branch %s to remote %s", branch_name, self.remote_name)
        origin = self.repo.remote(name=self.remote_name)
        origin.push(refspec=f"{branch_name}:{branch_name}")


class PRAgent:
    """
    使用 GitHub API 创建 PR（简单实现）
    """

    def __init__(self, github_token: str, owner: str, repo: str):
        self.token = github_token
        self.owner = owner
        self.repo = repo

    def create_pr(self, head_branch: str, base_branch: str, title: str, body: str) -> Optional[str]:
        url = f"{GITHUB_API}/repos/{self.owner}/{self.repo}/pulls"
        headers = {"Authorization": f"token {self.token}", "Accept": "application/vnd.github.v3+json"}
        payload = {"title": title, "head": head_branch, "base": base_branch, "body": body}
        logging.info("Creating PR via GitHub API: %s", url)
        resp = requests.post(url, headers=headers, json=payload)
        if resp.status_code in (200, 201):
            pr = resp.json()
            pr_url = pr.get("html_url")
            logging.info("PR created: %s", pr_url)
            return pr_url
        else:
            logging.error("Failed to create PR: %s %s", resp.status_code, resp.text)
            return None


# -----------------------
# Orchestrator
# -----------------------
class Orchestrator:
    """
    将上面的 Agents 串联起来，实现一个简单的工作流程：
    1. 扫描（发现问题）
    2. 创建本地临时分支
    3. 应用自动修复
    4. 运行测试
    5. 若测试通过则提交、推送并创建 PR
    """

    def __init__(
        self,
        repo_path: Path,
        github_owner: str,
        github_repo: str,
        github_token: str,
        base_branch: str = "main",
        work_branch_prefix: str = "auto/refactor/",
    ):
        self.repo_path = repo_path.resolve()
        self.github_owner = github_owner
        self.github_repo = github_repo
        self.github_token = github_token
        self.base_branch = base_branch
        self.work_branch_prefix = work_branch_prefix

        self.scanner = RepoScannerAgent(self.repo_path)
        self.refactor = RefactorAgent(self.repo_path)
        self.tester = TestAgent(self.repo_path)
        self.git = GitAgent(self.repo_path)
        self.pr_agent = PRAgent(self.github_token, self.github_owner, self.github_repo)

    def generate_branch_name(self) -> str:
        timestamp = int(time.time())
        return f"{self.work_branch_prefix}{timestamp}"

    def run_once(self, dry_run: bool = False):
        logging.info("Starting orchestration run in repo: %s", self.repo_path)
        scan_results = self.scanner.scan_repo()
        if not scan_results:
            logging.info("No issues found by scanner. Exiting.")
            return

        branch_name = self.generate_branch_name()
        self.git.create_branch_and_checkout(branch_name)

        # Save a safety copy of repo (optional)
        # shutil.copytree(self.repo_path, self.repo_path.parent / f"{self.repo_path.name}_backup_{branch_name}")

        # Run automated refactors
        self.refactor.run_refactors()

        # Run tests
        tests_ok = self.tester.run_pytest()
        if not tests_ok:
            logging.error("Automated refactors caused test failures. Aborting PR creation and rolling back.")
            # rollback to base branch
            try:
                self.git.repo.git.checkout(self.base_branch)
                self.git.repo.git.branch("-D", branch_name)
                logging.info("Rolled back to %s", self.base_branch)
            except Exception as e:
                logging.warning("Rollback failed: %s", e)
            return

        # Commit & push
        commit_message = "chore(auto-refactor): apply automated formatting and fixes"
        committed = self.git.commit_all(commit_message)
        if not committed:
            logging.info("No changes after refactor; nothing to push.")
            # cleanup branch
            try:
                self.git.repo.git.checkout(self.base_branch)
                self.git.repo.git.branch("-D", branch_name)
            except Exception:
                pass
            return

        if dry_run:
            logging.info("Dry run enabled - not pushing or creating PR.")
            return

        # Push branch
        self.git.push_branch(branch_name)

        # Create PR
        pr_title = "Automated refactor: formatting & lint fixes"
        pr_body = (
            "This PR was created by the AutoRefactor Agent. It applies automated formatting and common linter fixes.\n\n"
            "Tools applied: isort, black, ruff (fixes). Please review and squash-merge if acceptable."
        )
        pr_url = self.pr_agent.create_pr(head_branch=branch_name, base_branch=self.base_branch, title=pr_title, body=pr_body)
        if pr_url:
            logging.info("Created PR: %s", pr_url)
        else:
            logging.error("PR creation failed.")


# -----------------------
# CLI
# -----------------------
def parse_args():
    p = argparse.ArgumentParser(description="AutoRefactor Agent - 自动化代码重构与规范化")
    p.add_argument("--repo-path", required=True, help="本地 git 仓库路径")
    p.add_argument("--github-owner", required=True, help="GitHub 仓库所有者（组织或用户名）")
    p.add_argument("--github-repo", required=True, help="GitHub 仓库名")
    p.add_argument("--github-token", default=os.environ.get("GITHUB_TOKEN"), help="GitHub token (或 使用 GITHUB_TOKEN 环境变量)")
    p.add_argument("--base-branch", default="main", help="目标合并分支（默认 main）")
    p.add_argument("--dry-run", action="store_true", help="只运行到本地改动，不推送或创建 PR")
    p.add_argument("--log-level", default="INFO", help="日志级别")
    return p.parse_args()


def main():
    args = parse_args()
    logging.getLogger().setLevel(args.log_level.upper())

    if not args.github_token:
        logging.error("GitHub token 未提供。请通过 --github-token 或设置 GITHUB_TOKEN 环境变量。")
        sys.exit(1)

    repo_path = Path(args.repo_path)
    if not repo_path.exists():
        logging.error("repo-path 不存在: %s", repo_path)
        sys.exit(1)

    orch = Orchestrator(
        repo_path=repo_path,
        github_owner=args.github_owner,
        github_repo=args.github_repo,
        github_token=args.github_token,
        base_branch=args.base_branch,
    )
    orch.run_once(dry_run=args.dry_run)


if __name__ == "__main__":
    main()