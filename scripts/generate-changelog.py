#!/usr/bin/env python3
"""
Automated Changelog Generator for TimeTracker
Generates changelogs from git commits and GitHub issues/PRs
"""

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests


class ChangelogGenerator:
    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.repo_url = self._get_repo_url()

    def _get_repo_url(self) -> Optional[str]:
        """Get GitHub repository URL from git remote"""
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"], cwd=self.repo_path, capture_output=True, text=True
            )
            if result.returncode == 0:
                url = result.stdout.strip()
                # Convert SSH URL to HTTPS if needed
                if url.startswith("git@github.com:"):
                    url = url.replace("git@github.com:", "https://github.com/")
                if url.endswith(".git"):
                    url = url[:-4]
                return url
        except Exception as e:
            print(f"Warning: Could not get repository URL: {e}")
        return None

    def _run_git_command(self, command: List[str]) -> str:
        """Run a git command and return output"""
        try:
            result = subprocess.run(["git"] + command, cwd=self.repo_path, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Git command failed: {e}")
            return ""

    def get_latest_tag(self) -> str:
        """Get the latest git tag"""
        output = self._run_git_command(["describe", "--tags", "--abbrev=0"])
        return output if output else "HEAD~50"  # Fallback to last 50 commits

    def get_commits_since_tag(self, since_tag: str) -> List[Dict[str, str]]:
        """Get commits since the specified tag"""
        if since_tag == "HEAD~50":
            command = ["log", "--pretty=format:%H|%s|%an|%ad|%b", "--date=short", "-50"]
        else:
            command = ["log", f"{since_tag}..HEAD", "--pretty=format:%H|%s|%an|%ad|%b", "--date=short"]

        output = self._run_git_command(command)
        commits = []

        if output:
            for line in output.split("\n"):
                if "|" in line:
                    parts = line.split("|", 4)
                    if len(parts) >= 4:
                        commits.append(
                            {
                                "hash": parts[0][:8],
                                "subject": parts[1],
                                "author": parts[2],
                                "date": parts[3],
                                "body": parts[4] if len(parts) > 4 else "",
                            }
                        )

        return commits

    def categorize_commits(self, commits: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
        """Categorize commits by type"""
        categories = {
            "Features": [],
            "Bug Fixes": [],
            "Improvements": [],
            "Documentation": [],
            "Refactoring": [],
            "Dependencies": [],
            "Database": [],
            "Docker": [],
            "CI/CD": [],
            "Other": [],
        }

        # Patterns for categorization
        patterns = {
            "Features": [r"^feat(\(.+\))?:", r"^add:", r"^implement:", r"^new:"],
            "Bug Fixes": [r"^fix(\(.+\))?:", r"^bug:", r"^hotfix:", r"^patch:"],
            "Improvements": [r"^improve:", r"^enhance:", r"^update:", r"^upgrade:"],
            "Documentation": [r"^docs?(\(.+\))?:", r"^readme:", r"^doc:"],
            "Refactoring": [r"^refactor(\(.+\))?:", r"^cleanup:", r"^reorganize:"],
            "Dependencies": [r"^deps?(\(.+\))?:", r"^bump:", r"^requirements:"],
            "Database": [r"^db:", r"^migration:", r"^schema:", r"^alembic:"],
            "Docker": [r"^docker:", r"^dockerfile:", r"^compose:"],
            "CI/CD": [r"^ci:", r"^cd:", r"^workflow:", r"^action:", r"^build:"],
        }

        for commit in commits:
            subject = commit["subject"].lower()
            categorized = False

            for category, category_patterns in patterns.items():
                for pattern in category_patterns:
                    if re.match(pattern, subject):
                        categories[category].append(commit)
                        categorized = True
                        break
                if categorized:
                    break

            if not categorized:
                categories["Other"].append(commit)

        return categories

    def extract_breaking_changes(self, commits: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Extract breaking changes from commits"""
        breaking_changes = []

        for commit in commits:
            # Look for BREAKING CHANGE in commit message
            full_message = f"{commit['subject']} {commit['body']}"
            if "BREAKING CHANGE" in full_message or "breaking:" in commit["subject"].lower():
                breaking_changes.append(commit)

        return breaking_changes

    def get_github_prs_and_issues(self, commits: List[Dict[str, str]]) -> Dict[str, List[Dict]]:
        """Get GitHub PRs and issues mentioned in commits"""
        prs = []
        issues = []

        if not self.github_token or not self.repo_url:
            return {"prs": prs, "issues": issues}

        # Extract PR/issue numbers from commit messages
        pr_pattern = r"#(\d+)"
        mentioned_numbers = set()

        for commit in commits:
            matches = re.findall(pr_pattern, f"{commit['subject']} {commit['body']}")
            mentioned_numbers.update(matches)

        # Fetch details from GitHub API
        repo_parts = self.repo_url.replace("https://github.com/", "").split("/")
        if len(repo_parts) >= 2:
            owner, repo = repo_parts[0], repo_parts[1]

            headers = {"Authorization": f"token {self.github_token}"}

            for number in mentioned_numbers:
                try:
                    # Try to fetch as PR first
                    pr_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{number}"
                    response = requests.get(pr_url, headers=headers)

                    if response.status_code == 200:
                        pr_data = response.json()
                        prs.append(
                            {
                                "number": number,
                                "title": pr_data["title"],
                                "url": pr_data["html_url"],
                                "author": pr_data["user"]["login"],
                            }
                        )
                    else:
                        # Try as issue
                        issue_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{number}"
                        response = requests.get(issue_url, headers=headers)

                        if response.status_code == 200:
                            issue_data = response.json()
                            issues.append(
                                {
                                    "number": number,
                                    "title": issue_data["title"],
                                    "url": issue_data["html_url"],
                                    "author": issue_data["user"]["login"],
                                }
                            )

                except Exception as e:
                    print(f"Warning: Could not fetch GitHub data for #{number}: {e}")

        return {"prs": prs, "issues": issues}

    def generate_changelog(self, version: str, since_tag: str = None) -> str:
        """Generate complete changelog"""
        if not since_tag:
            since_tag = self.get_latest_tag()

        print(f"Generating changelog for version {version} since {since_tag}...")

        # Get commits
        commits = self.get_commits_since_tag(since_tag)
        print(f"Found {len(commits)} commits")

        if not commits:
            return f"# {version}\n\n*No changes since {since_tag}*\n"

        # Categorize commits
        categorized = self.categorize_commits(commits)

        # Extract breaking changes
        breaking_changes = self.extract_breaking_changes(commits)

        # Get GitHub data
        github_data = self.get_github_prs_and_issues(commits)

        # Generate changelog content
        changelog = self._format_changelog(version, since_tag, categorized, breaking_changes, github_data)

        return changelog

    def _format_changelog(
        self,
        version: str,
        since_tag: str,
        categorized: Dict[str, List[Dict[str, str]]],
        breaking_changes: List[Dict[str, str]],
        github_data: Dict[str, List[Dict]],
    ) -> str:
        """Format the changelog content"""

        changelog = f"# {version}\n\n"
        changelog += f"*Released on {datetime.now().strftime('%Y-%m-%d')}*\n\n"

        # Summary
        total_commits = sum(len(commits) for commits in categorized.values())
        changelog += f"**{total_commits} changes** since {since_tag}\n\n"

        # Breaking changes (if any)
        if breaking_changes:
            changelog += "## ⚠️ Breaking Changes\n\n"
            for commit in breaking_changes:
                changelog += f"- {commit['subject']} ([{commit['hash']}]"
                if self.repo_url:
                    changelog += f"({self.repo_url}/commit/{commit['hash']}))\n"
                else:
                    changelog += ")\n"
            changelog += "\n"

        # Features and improvements
        feature_categories = ["Features", "Improvements", "Bug Fixes"]
        for category in feature_categories:
            if categorized[category]:
                icon = {"Features": "✨", "Improvements": "🚀", "Bug Fixes": "🐛"}[category]
                changelog += f"## {icon} {category}\n\n"

                for commit in categorized[category]:
                    # Clean up commit subject
                    subject = re.sub(
                        r"^(feat|fix|improve|enhance|update)(\(.+\))?:\s*", "", commit["subject"], flags=re.IGNORECASE
                    )
                    changelog += f"- {subject} ([{commit['hash']}]"
                    if self.repo_url:
                        changelog += f"({self.repo_url}/commit/{commit['hash']}))\n"
                    else:
                        changelog += ")\n"
                changelog += "\n"

        # Technical changes
        tech_categories = ["Database", "Docker", "CI/CD", "Refactoring", "Dependencies"]
        tech_changes = any(categorized[cat] for cat in tech_categories)

        if tech_changes:
            changelog += "## 🔧 Technical Changes\n\n"
            for category in tech_categories:
                if categorized[category]:
                    changelog += f"### {category}\n"
                    for commit in categorized[category]:
                        subject = re.sub(
                            r"^(db|docker|ci|cd|refactor|deps?)(\(.+\))?:\s*",
                            "",
                            commit["subject"],
                            flags=re.IGNORECASE,
                        )
                        changelog += f"- {subject} ([{commit['hash']}]"
                        if self.repo_url:
                            changelog += f"({self.repo_url}/commit/{commit['hash']}))\n"
                        else:
                            changelog += ")\n"
                    changelog += "\n"

        # Documentation
        if categorized["Documentation"]:
            changelog += "## 📚 Documentation\n\n"
            for commit in categorized["Documentation"]:
                subject = re.sub(r"^docs?(\(.+\))?:\s*", "", commit["subject"], flags=re.IGNORECASE)
                changelog += f"- {subject} ([{commit['hash']}]"
                if self.repo_url:
                    changelog += f"({self.repo_url}/commit/{commit['hash']}))\n"
                else:
                    changelog += ")\n"
            changelog += "\n"

        # Other changes
        if categorized["Other"]:
            changelog += "## 📋 Other Changes\n\n"
            for commit in categorized["Other"]:
                changelog += f"- {commit['subject']} ([{commit['hash']}]"
                if self.repo_url:
                    changelog += f"({self.repo_url}/commit/{commit['hash']}))\n"
                else:
                    changelog += ")\n"
            changelog += "\n"

        # GitHub PRs and Issues
        if github_data["prs"] or github_data["issues"]:
            changelog += "## 🔗 Related\n\n"

            if github_data["prs"]:
                changelog += "**Pull Requests:**\n"
                for pr in github_data["prs"]:
                    changelog += f"- [{pr['title']}]({pr['url']}) by @{pr['author']}\n"
                changelog += "\n"

            if github_data["issues"]:
                changelog += "**Issues:**\n"
                for issue in github_data["issues"]:
                    changelog += f"- [{issue['title']}]({issue['url']}) by @{issue['author']}\n"
                changelog += "\n"

        # Contributors
        contributors = set()
        for category_commits in categorized.values():
            for commit in category_commits:
                contributors.add(commit["author"])

        if contributors:
            changelog += "## 👥 Contributors\n\n"
            changelog += f"Thanks to all contributors: {', '.join(f'@{c}' for c in sorted(contributors))}\n\n"

        return changelog


def main():
    parser = argparse.ArgumentParser(description="Generate changelog for TimeTracker")
    parser.add_argument("version", help="Version for the changelog (e.g., v1.2.3)")
    parser.add_argument("--since", help="Generate changelog since this tag/commit")
    parser.add_argument("--output", "-o", help="Output file (default: CHANGELOG.md)")
    parser.add_argument("--append", action="store_true", help="Append to existing changelog")
    parser.add_argument("--repo-path", default=".", help="Repository path")

    args = parser.parse_args()

    generator = ChangelogGenerator(args.repo_path)
    changelog = generator.generate_changelog(args.version, args.since)

    if args.output:
        output_file = args.output
    else:
        output_file = os.path.join(args.repo_path, "CHANGELOG.md")

    # Write changelog
    mode = "a" if args.append else "w"
    with open(output_file, mode, encoding="utf-8") as f:
        if args.append and os.path.exists(output_file):
            f.write("\n\n---\n\n")
        f.write(changelog)

    print(f"Changelog written to {output_file}")

    # Also output to stdout for GitHub Actions
    print("\n" + "=" * 50)
    print("GENERATED CHANGELOG:")
    print("=" * 50)
    print(changelog)


if __name__ == "__main__":
    main()
