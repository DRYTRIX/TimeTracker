#!/usr/bin/env python3
"""
TimeTracker CI/CD Setup Validation Script
Validates that all CI/CD components are properly configured
"""

import os
import sys
import subprocess
from pathlib import Path


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.ENDC}\n")


def print_success(text):
    """Print success message"""
    print(f"{Colors.GREEN}✓{Colors.ENDC} {text}")


def print_error(text):
    """Print error message"""
    print(f"{Colors.RED}✗{Colors.ENDC} {text}")


def print_warning(text):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠{Colors.ENDC} {text}")


def print_info(text):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ{Colors.ENDC} {text}")


def check_file_exists(filepath, required=True):
    """Check if a file exists"""
    path = Path(filepath)
    if path.exists():
        print_success(f"Found: {filepath}")
        return True
    else:
        if required:
            print_error(f"Missing required file: {filepath}")
        else:
            print_warning(f"Optional file not found: {filepath}")
        return False


def check_python_package(package_name):
    """Check if a Python package is installed"""
    try:
        __import__(package_name)
        print_success(f"Python package '{package_name}' is installed")
        return True
    except ImportError:
        print_error(f"Python package '{package_name}' is NOT installed")
        return False


def run_command(command, description):
    """Run a command and check if it succeeds
    
    Args:
        command: Command string or list of command arguments
        description: Human-readable description
    """
    import shlex
    try:
        # If command is a string, split it safely
        if isinstance(command, str):
            try:
                cmd_list = shlex.split(command)
            except ValueError:
                # Fallback to simple split
                cmd_list = command.split()
        else:
            cmd_list = command
        
        result = subprocess.run(
            cmd_list,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            print_success(f"{description}: OK")
            return True
        else:
            print_error(f"{description}: FAILED")
            if result.stderr:
                print(f"  Error: {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        print_error(f"{description}: TIMEOUT")
        return False
    except Exception as e:
        print_error(f"{description}: ERROR ({str(e)})")
        return False


def main():
    """Main validation function"""
    print_header("TimeTracker CI/CD Setup Validation")
    
    # Track results
    checks = {
        'workflows': [],
        'tests': [],
        'config': [],
        'docs': [],
        'python': []
    }
    
    # 1. Check GitHub Actions workflows
    print_header("1. GitHub Actions Workflows")
    workflows = [
        '.github/workflows/ci-comprehensive.yml',
        '.github/workflows/cd-development.yml',
        '.github/workflows/cd-release.yml',
        '.github/workflows/docker-publish.yml',
        '.github/workflows/migration-check.yml',
    ]
    
    for workflow in workflows:
        checks['workflows'].append(check_file_exists(workflow))
    
    # 2. Check test files
    print_header("2. Test Files")
    test_files = [
        'tests/conftest.py',
        'tests/test_basic.py',
        'tests/test_routes.py',
        'tests/test_models_comprehensive.py',
        'tests/test_security.py',
        'tests/test_analytics.py',
        'tests/test_invoices.py',
    ]
    
    for test_file in test_files:
        checks['tests'].append(check_file_exists(test_file))
    
    # 3. Check configuration files
    print_header("3. Configuration Files")
    config_files = [
        ('pytest.ini', True),
        ('requirements-test.txt', True),
        ('.pre-commit-config.yaml', False),
        ('Makefile', False),
        ('.gitignore', True),
    ]
    
    for config_file, required in config_files:
        checks['config'].append(check_file_exists(config_file, required))
    
    # 4. Check documentation
    print_header("4. Documentation")
    docs = [
        'CI_CD_DOCUMENTATION.md',
        'CI_CD_QUICK_START.md',
        'CI_CD_IMPLEMENTATION_SUMMARY.md',
    ]
    
    for doc in docs:
        checks['docs'].append(check_file_exists(doc))
    
    # 5. Check Python dependencies
    print_header("5. Python Dependencies")
    packages = [
        'pytest',
        'flask',
        'sqlalchemy',
    ]
    
    for package in packages:
        checks['python'].append(check_python_package(package))
    
    # 6. Check Python test dependencies
    print_header("6. Test Dependencies")
    test_packages = [
        'pytest',
        'pytest_cov',
        'pytest_flask',
        'black',
        'flake8',
        'bandit',
    ]
    
    test_deps_ok = True
    for package in test_packages:
        if not check_python_package(package.replace('_', '-')):
            test_deps_ok = False
    
    if not test_deps_ok:
        print_info("Install test dependencies: pip install -r requirements-test.txt")
    
    # 7. Run quick tests
    print_header("7. Quick Test Validation")
    
    # Check if pytest can discover tests
    if run_command(['pytest', '--collect-only', '-q'], 'Test discovery'):
        print_info("Tests can be discovered successfully")
    
    # Try to run smoke tests (if they exist)
    if run_command(['pytest', '-m', 'smoke', '--co', '-q'], 'Smoke test discovery'):
        print_info("Smoke tests are properly marked")
    
    # 8. Check Docker setup
    print_header("8. Docker Configuration")
    docker_files = [
        ('Dockerfile', True),
        ('docker-compose.yml', True),
        ('.dockerignore', False),
    ]
    
    for docker_file, required in docker_files:
        check_file_exists(docker_file, required)
    
    # 9. Check helper scripts
    print_header("9. Helper Scripts")
    scripts = [
        'scripts/run-tests.sh',
        'scripts/run-tests.bat',
    ]
    
    for script in scripts:
        check_file_exists(script, required=False)
    
    # 10. Summary
    print_header("Validation Summary")
    
    total_checks = sum(len(v) for v in checks.values())
    passed_checks = sum(sum(v) for v in checks.values())
    
    print(f"\n{Colors.BOLD}Results:{Colors.ENDC}")
    print(f"  Workflows:      {sum(checks['workflows'])}/{len(checks['workflows'])}")
    print(f"  Tests:          {sum(checks['tests'])}/{len(checks['tests'])}")
    print(f"  Configuration:  {sum(checks['config'])}/{len(checks['config'])}")
    print(f"  Documentation:  {sum(checks['docs'])}/{len(checks['docs'])}")
    print(f"  Python deps:    {sum(checks['python'])}/{len(checks['python'])}")
    print(f"\n{Colors.BOLD}Total:          {passed_checks}/{total_checks}{Colors.ENDC}")
    
    if passed_checks == total_checks:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ All checks passed! CI/CD setup is complete.{Colors.ENDC}")
        print(f"\n{Colors.BOLD}Next steps:{Colors.ENDC}")
        print("  1. Run smoke tests: pytest -m smoke")
        print("  2. Create a test PR to verify CI works")
        print("  3. Review documentation: CI_CD_QUICK_START.md")
        return 0
    else:
        failed = total_checks - passed_checks
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠ Setup incomplete: {failed} checks failed{Colors.ENDC}")
        print(f"\n{Colors.BOLD}Action required:{Colors.ENDC}")
        print("  1. Review errors above")
        print("  2. Install missing dependencies: pip install -r requirements-test.txt")
        print("  3. Check documentation: CI_CD_DOCUMENTATION.md")
        return 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Validation interrupted by user{Colors.ENDC}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Colors.RED}Validation failed with error: {e}{Colors.ENDC}")
        sys.exit(1)

