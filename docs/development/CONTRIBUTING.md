# Contributing to TimeTracker

Thank you for your interest in contributing to TimeTracker! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Reporting Bugs](#reporting-bugs)
- [Feature Requests](#feature-requests)
- [Questions and Discussion](#questions-and-discussion)

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

- Use the GitHub issue tracker
- Include a clear and descriptive title
- Describe the exact steps to reproduce the bug
- Provide specific examples to demonstrate the steps
- Describe the behavior you observed after following the steps
- Explain which behavior you expected to see instead and why
- Include details about your configuration and environment

### Suggesting Enhancements

- Use the GitHub issue tracker
- Provide a clear and descriptive title
- Describe the suggested enhancement in detail
- Explain why this enhancement would be useful
- List any similar features and applications

### Pull Requests

- Fork the repository
- Create a feature branch (`git checkout -b feature/amazing-feature`)
- Make your changes
- Add tests for new functionality
- Ensure all tests pass
- Commit your changes (`git commit -m 'Add amazing feature'`)
- Push to the branch (`git push origin feature/amazing-feature`)
- Open a Pull Request

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Docker and Docker Compose (for containerized development)
- Git

### Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/drytrix/TimeTracker.git
   cd TimeTracker
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your development settings
   ```

5. Initialize the database:
   ```bash
   flask db upgrade
   ```

6. Run the development server:
   ```bash
   flask run
   ```

### Docker Development

1. Build and start the containers:
   ```bash
   docker-compose up --build
   ```

2. Access the application at `http://localhost:8080`

## Pull Request Process

1. **Fork and Clone**: Fork the repository and clone your fork locally
2. **Create Branch**: Create a feature branch from `main`
3. **Make Changes**: Implement your changes following the coding standards
4. **Test**: Ensure all tests pass and add new tests for new functionality
5. **Commit**: Write clear, descriptive commit messages
6. **Push**: Push your branch to your fork
7. **Submit PR**: Create a pull request with a clear description

### Commit Message Format

Use conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:
- `feat(timer): add automatic idle detection`
- `fix(auth): resolve session timeout issue`
- `docs(readme): update installation instructions`

## Coding Standards

### Python

- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Keep functions focused and single-purpose
- Write docstrings for all public functions and classes
- Maximum line length: 88 characters (use Black formatter)

### Flask

- Use blueprints for route organization
- Keep route handlers thin, move business logic to models or services
- Use proper HTTP status codes
- Implement proper error handling

### Database

- Use SQLAlchemy ORM for database operations
- Write migrations for schema changes
- Use proper indexing for performance
- Follow naming conventions for tables and columns

### Frontend

- Use semantic HTML
- Follow accessibility guidelines
- Keep CSS organized and maintainable
- Use HTMX for dynamic interactions

## Testing

### Running Tests

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=app

# Run specific test file
python -m pytest tests/test_timer.py
```

### Writing Tests

- Write tests for all new functionality
- Use descriptive test names
- Test both success and failure cases
- Mock external dependencies
- Use fixtures for common test data

### Test Structure

```
tests/
├── conftest.py          # Shared fixtures
├── test_models/         # Model tests
├── test_routes/         # Route tests
├── test_utils/          # Utility function tests
└── integration/         # Integration tests
```

## Reporting Bugs

When reporting bugs, please include:

- **Environment**: OS, Python version, browser (if applicable)
- **Steps to Reproduce**: Clear, numbered steps
- **Expected Behavior**: What you expected to happen
- **Actual Behavior**: What actually happened
- **Screenshots**: If applicable
- **Logs**: Any error messages or logs

## Feature Requests

For feature requests:

- Explain the problem you're trying to solve
- Describe the proposed solution
- Provide use cases and examples
- Consider implementation complexity
- Discuss alternatives you've considered

## Questions and Discussion

- Use GitHub Discussions for general questions
- Use GitHub Issues for bugs and feature requests
- Be respectful and constructive
- Search existing issues before creating new ones

## Getting Help

If you need help:

1. Check the [README.md](README.md) for basic information
2. Search existing issues and discussions
3. Create a new issue or discussion
4. Join our community channels (if available)

## License

By contributing to TimeTracker, you agree that your contributions will be licensed under the same license as the project (GNU General Public License v3.0).

## Recognition

Contributors will be recognized in:

- The project's README.md
- Release notes
- Contributor statistics on GitHub

Thank you for contributing to TimeTracker! 🚀
