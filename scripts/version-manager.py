#!/usr/bin/env python3
"""
Version Manager for TimeTracker
This script helps manage version tags for releases and builds
"""

import os
import sys
import subprocess
import argparse
from datetime import datetime
import re
import shlex

class VersionManager:
    def __init__(self):
        self.repo_path = os.getcwd()
        
    def run_command(self, command, capture_output=True):
        """Run a command and return the result
        
        Args:
            command: Command string or list of command arguments
            capture_output: Whether to capture output
        """
        try:
            # If command is a string, split it safely
            if isinstance(command, str):
                # For git commands with complex quoting, use shlex
                try:
                    cmd_list = shlex.split(command)
                except ValueError:
                    # Fallback to simple split
                    cmd_list = command.split()
            else:
                cmd_list = command
            
            result = subprocess.run(
                cmd_list, 
                capture_output=capture_output, 
                text=True, 
                cwd=self.repo_path
            )
            if result.returncode != 0:
                print(f"Error running command: {' '.join(cmd_list)}")
                if hasattr(result, 'stderr') and result.stderr:
                    print(f"Error: {result.stderr}")
                return None
            return result.stdout.strip() if capture_output and hasattr(result, 'stdout') else result
        except Exception as e:
            print(f"Exception running command: {e}")
            return None

    def get_current_branch(self):
        """Get the current git branch"""
        return self.run_command(['git', 'branch', '--show-current'])

    def get_latest_tag(self):
        """Get the latest git tag"""
        result = self.run_command(['git', 'describe', '--tags', '--abbrev=0'])
        if result:
            return result
        # If command fails (no tags), return 'none'
        return 'none'

    def get_commit_count(self):
        """Get the number of commits since the last tag"""
        latest_tag = self.get_latest_tag()
        if latest_tag == 'none':
            return self.run_command(['git', 'rev-list', '--count', 'HEAD'])
        else:
            # Sanitize tag name to prevent command injection
            safe_tag = re.sub(r'[^a-zA-Z0-9._/-]', '', latest_tag)
            return self.run_command(['git', 'rev-list', '--count', f'{safe_tag}..HEAD'])

    def get_commit_hash(self, short=True):
        """Get the current commit hash"""
        if short:
            return self.run_command(['git', 'rev-parse', '--short', 'HEAD'])
        else:
            return self.run_command(['git', 'rev-parse', 'HEAD'])

    def validate_version_format(self, version):
        """Validate version format"""
        # Allow various version formats
        patterns = [
            r'^v?\d+\.\d+\.\d+$',  # v1.2.3 or 1.2.3
            r'^v?\d+\.\d+$',       # v1.2 or 1.2
            r'^v?\d+$',             # v1 or 1
            r'^build-\d+$',         # build-123
            r'^rc\d+$',             # rc1
            r'^beta\d+$',           # beta1
            r'^alpha\d+$',          # alpha1
            r'^dev-\d+$',           # dev-123
        ]
        
        for pattern in patterns:
            if re.match(pattern, version):
                return True
        return False

    def suggest_next_version(self, current_version):
        """Suggest the next version based on current version"""
        if current_version == 'none':
            return 'v1.0.0'
        
        # Remove 'v' prefix if present
        clean_version = current_version.lstrip('v')
        
        try:
            parts = clean_version.split('.')
            if len(parts) >= 3:
                major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
                return f"v{major}.{minor}.{patch + 1}"
            elif len(parts) == 2:
                major, minor = int(parts[0]), int(parts[1])
                return f"v{major}.{minor + 1}.0"
            elif len(parts) == 1:
                major = int(parts[0])
                return f"v{major + 1}.0.0"
        except ValueError:
            pass
        
        return f"{current_version}-next"

    def create_tag(self, version, message=None, push=True):
        """Create a git tag"""
        if not self.validate_version_format(version):
            print(f"Error: Invalid version format '{version}'")
            print("Valid formats: v1.2.3, 1.2.3, build-123, rc1, beta1, etc.")
            return False
        
        # Ensure version starts with 'v' for semantic versions
        if re.match(r'^v?\d+\.\d+\.\d+$', version) and not version.startswith('v'):
            version = f"v{version}"
        
        # Generate message if not provided
        if not message:
            message = f"Release {version}"
        
        print(f"Creating tag: {version}")
        print(f"Message: {message}")
        
        # Create the tag using list to avoid shell injection
        # Version and message are already validated/sanitized
        tag_cmd = ['git', 'tag', '-a', version, '-m', message]
        if not self.run_command(tag_cmd, capture_output=False):
            print("Failed to create tag")
            return False
        
        print(f"✓ Tag '{version}' created successfully")
        
        # Push tag if requested
        if push:
            print("Pushing tag to remote...")
            push_cmd = ['git', 'push', 'origin', version]
            if not self.run_command(push_cmd, capture_output=False):
                print("Failed to push tag to remote")
                return False
            print(f"✓ Tag '{version}' pushed to remote")
        
        return True

    def create_build_tag(self, build_number=None):
        """Create a build tag with build number"""
        if not build_number:
            build_number = self.get_commit_count()
        
        branch = self.get_current_branch()
        version = f"{branch}-build-{build_number}"
        
        message = f"Build {build_number} from {branch} branch"
        
        return self.create_tag(version, message, push=False)

    def list_tags(self):
        """List all tags"""
        tags = self.run_command(['git', 'tag', '--sort=-version:refname'])
        if tags:
            print("Available tags:")
            for tag in tags.split('\n'):
                if tag.strip():
                    print(f"  {tag}")
        else:
            print("No tags found")

    def show_tag_info(self, tag):
        """Show information about a specific tag"""
        if not tag:
            tag = self.get_latest_tag()
        
        if tag == 'none':
            print("No tags found")
            return
        
        # Sanitize tag name to prevent command injection
        safe_tag = re.sub(r'[^a-zA-Z0-9._/-]', '', tag)
        
        print(f"Tag: {safe_tag}")
        print(f"Commit: {self.run_command(['git', 'rev-parse', safe_tag])}")
        print(f"Date: {self.run_command(['git', 'log', '-1', '--format=%cd', safe_tag])}")
        print(f"Message: {self.run_command(['git', 'log', '-1', '--format=%s', safe_tag])}")
        
        # Show commits since this tag
        commits_since = self.run_command(['git', 'log', '--oneline', f'{safe_tag}..HEAD'])
        if commits_since:
            print(f"\nCommits since {safe_tag}:")
            for commit in commits_since.split('\n')[:10]:  # Show last 10 commits
                if commit.strip():
                    print(f"  {commit}")
            commit_lines = commits_since.split('\n')
            if len(commit_lines) > 10:
                print(f"  ... and {len(commit_lines) - 10} more")

    def show_status(self):
        """Show current version status"""
        print("=== Version Status ===")
        print(f"Current branch: {self.get_current_branch()}")
        print(f"Latest tag: {self.get_latest_tag()}")
        print(f"Commits since last tag: {self.get_commit_count()}")
        print(f"Current commit: {self.get_commit_hash()}")
        
        current_tag = self.get_latest_tag()
        if current_tag != 'none':
            next_version = self.suggest_next_version(current_tag)
            print(f"Suggested next version: {next_version}")
        
        print("=====================")

def main():
    parser = argparse.ArgumentParser(description='Version Manager for TimeTracker')
    parser.add_argument('action', choices=['tag', 'build', 'list', 'info', 'status', 'suggest', 'release', 'changelog'], 
                       help='Action to perform')
    parser.add_argument('--version', '-v', help='Version string (e.g., v1.2.3, build-123)')
    parser.add_argument('--message', '-m', help='Tag message')
    parser.add_argument('--build-number', '-b', type=int, help='Build number for build tags')
    parser.add_argument('--no-push', action='store_true', help='Don\'t push tag to remote')
    parser.add_argument('--tag', '-t', help='Tag to show info for (for info action)')
    parser.add_argument('--pre-release', action='store_true', help='Mark as pre-release')
    parser.add_argument('--changelog', action='store_true', help='Generate changelog')
    parser.add_argument('--github-release', action='store_true', help='Create GitHub release')
    
    args = parser.parse_args()
    
    vm = VersionManager()
    
    if args.action == 'tag':
        if not args.version:
            print("Error: Version required for tag action")
            print("Use --version or -v to specify version")
            sys.exit(1)
        
        vm.create_tag(args.version, args.message, push=not args.no_push)
        
    elif args.action == 'build':
        vm.create_build_tag(args.build_number)
        
    elif args.action == 'list':
        vm.list_tags()
        
    elif args.action == 'info':
        vm.show_tag_info(args.tag)
        
    elif args.action == 'status':
        vm.show_status()
        
    elif args.action == 'suggest':
        current_tag = vm.get_latest_tag()
        if current_tag != 'none':
            next_version = vm.suggest_next_version(current_tag)
            print(f"Current version: {current_tag}")
            print(f"Suggested next version: {next_version}")
        else:
            print("No current version found")
            print("Suggested first version: v1.0.0")
    
    elif args.action == 'release':
        if not args.version:
            print("Error: Version required for release action")
            print("Use --version or -v to specify version")
            sys.exit(1)
        
        print(f"🚀 Creating release {args.version}...")
        
        # Create tag
        if vm.create_tag(args.version, args.message, push=not args.no_push):
            print(f"✅ Tag {args.version} created successfully")
            
            # Generate changelog if requested
            if args.changelog:
                print("📋 Generating changelog...")
                # Sanitize version before use
                safe_version = re.sub(r'[^a-zA-Z0-9._/-]', '', args.version)
                changelog_cmd = ['python', 'scripts/generate-changelog.py', safe_version]
                if vm.run_command(changelog_cmd, capture_output=False):
                    print("✅ Changelog generated successfully")
                else:
                    print("⚠️ Changelog generation failed")
            
            # Create GitHub release if requested
            if args.github_release:
                print("🐙 Creating GitHub release...")
                # Sanitize version before use
                safe_version = re.sub(r'[^a-zA-Z0-9._/-]', '', args.version)
                github_cmd = ['gh', 'release', 'create', safe_version]
                if args.pre_release:
                    github_cmd.append('--prerelease')
                if args.changelog and os.path.exists("CHANGELOG.md"):
                    github_cmd.extend(['--notes-file', 'CHANGELOG.md'])
                elif args.message:
                    # Sanitize message to prevent command injection
                    safe_message = args.message.replace("'", "'\"'\"'")
                    github_cmd.extend(['--notes', safe_message])
                
                if vm.run_command(github_cmd, capture_output=False):
                    print("✅ GitHub release created successfully")
                else:
                    print("⚠️ GitHub release creation failed (make sure 'gh' CLI is installed and authenticated)")
        else:
            print("❌ Failed to create tag")
            sys.exit(1)
    
    elif args.action == 'changelog':
        current_tag = vm.get_latest_tag()
        version = args.version or vm.suggest_next_version(current_tag)
        
        # Sanitize version before use
        safe_version = re.sub(r'[^a-zA-Z0-9._/-]', '', version)
        
        print(f"📋 Generating changelog for {safe_version}...")
        changelog_cmd = ['python', 'scripts/generate-changelog.py', safe_version]
        if vm.run_command(changelog_cmd, capture_output=False):
            print("✅ Changelog generated successfully")
        else:
            print("❌ Changelog generation failed")

if __name__ == '__main__':
    main()
