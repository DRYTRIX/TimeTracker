# TimeTracker Project Structure

This document provides an overview of the cleaned up TimeTracker project structure after removing unnecessary files and consolidating the codebase.

## 📁 Root Directory Structure

```
TimeTracker/
├── 📁 app/                    # Main Flask application
├── 📁 assets/                 # Static assets (images, screenshots)
├── 📁 docker/                 # Docker configuration files
├── 📁 templates/              # Additional template files
├── 📁 tests/                  # Test suite
├── 📁 .github/                # GitHub workflows and configurations
├── 📁 logs/                   # Application logs (with .gitkeep)
├── 🐳 Dockerfile              # Main Dockerfile
├── 🐳 Dockerfile              # Main Dockerfile
├── 📄 docker-compose.yml          # Local development compose
├── 📄 docker-compose.remote.yml   # Remote/production compose (ghcr.io)
├── 📄 docker-compose.remote-dev.yml # Remote dev/testing compose (ghcr.io)
├── 📄 requirements.txt         # Python dependencies
├── 📄 app.py                  # Application entry point
├── 📄 env.example             # Environment variables template
├── 📄 README.md               # Main project documentation
├── 📄 PROJECT_STRUCTURE.md    # This file
├── 📄 CONTRIBUTING.md         # Contribution guidelines
├── 📄 CODE_OF_CONDUCT.md      # Community code of conduct
├── 📄 LICENSE                 # GPL v3 license
├── 📄 GITHUB_WORKFLOW_IMAGES.md  # Docker image workflow docs
├── 📄 DOCKER_PUBLIC_SETUP.md     # Public container setup docs
├── 📄 REQUIREMENTS.md         # Detailed requirements documentation
├── 📄 deploy-public.bat       # Windows deployment script
└── 📄 deploy-public.sh        # Linux/Mac deployment script
```

## 🧹 Cleanup Summary

### Files Removed
- `DATABASE_INIT_FIX_FINAL_README.md` - Database fix documentation (resolved)
- `DATABASE_INIT_FIX_README.md` - Database fix documentation (resolved)
- `TIMEZONE_FIX_README.md` - Timezone fix documentation (resolved)
- `Dockerfile.test` - Test Dockerfile (not needed)
- `Dockerfile.combined` - Combined Dockerfile (consolidated)
- `docker-compose.yml` - Old compose file (replaced)
- `deploy.sh` - Old deployment script (replaced)
- `index.html` - Unused HTML file
- `_config.yml` - Unused config file
- `logs/timetracker.log` - Large log file (not in version control)
- `.pytest_cache/` - Python test cache directory

### Files Consolidated
- **Dockerfiles**: Now only `Dockerfile` and `Dockerfile.simple`
- **Docker Compose**: Now only `docker-compose.simple.yml` and `docker-compose.public.yml`
- **Deployment**: Now only `deploy-public.bat` and `deploy-public.sh`

## 🏗️ Core Components

### Application (`app/`)
- **Models**: Database models for users, projects, time entries, tasks, and settings
- **Routes**: API endpoints and web routes including task management
- **Templates**: Jinja2 HTML templates including task management views
- **Utils**: Utility functions including timezone management
- **Config**: Application configuration

### Docker Configuration (`docker/`)
- **Startup scripts**: Container initialization and database setup
- **Database scripts**: SQL-based database initialization
- **Configuration files**: Docker-specific configurations

### Templates (`templates/`)
- **Admin templates**: User management and system settings
- **Error templates**: Error page templates
- **Main templates**: Core application templates
- **Project templates**: Project management templates
- **Report templates**: Reporting and analytics templates
- **Timer templates**: Time tracking interface templates

### Assets (`assets/`)
- **Screenshots**: Application screenshots for documentation
- **Images**: Logo and other static images

## 🚀 Deployment Options

### 1. Local Development
- **File**: `docker-compose.yml`
- **Image**: Built from local source
- **Use case**: Developer workstation

### 2. Remote/Production
- **File**: `docker-compose.remote.yml`
- **Image**: `ghcr.io/drytrix/timetracker:latest` (or versioned tag)
- **Use case**: Production deployment

### 3. Remote Dev/Testing
- **File**: `docker-compose.remote-dev.yml`
- **Image**: `ghcr.io/drytrix/timetracker:development`
- **Use case**: Pre-release testing

## 📚 Documentation Files

- **README.md**: Main project documentation and quick start guide
- **PROJECT_STRUCTURE.md**: This file - project structure overview
- **TASK_MANAGEMENT_README.md**: Detailed Task Management feature documentation
- **CONTRIBUTING.md**: How to contribute to the project
- **CODE_OF_CONDUCT.md**: Community behavior guidelines

## ✅ Task Management Feature

The Task Management feature is fully integrated into the application with automatic database migration:

### Automatic Migration
- **No manual setup required**: Database tables are created automatically on first startup
- **Integrated migration**: Migration logic is built into the application initialization
- **Fallback support**: Manual migration script available if needed

### Components Added
- **Models**: `Task` model with full relationship support
- **Routes**: Complete CRUD operations for task management
- **Templates**: Responsive task management interface
- **Integration**: Tasks linked to projects and time tracking
- **GITHUB_WORKFLOW_IMAGES.md**: Docker image build workflow
- **DOCKER_PUBLIC_SETUP.md**: Public container setup guide
- **REQUIREMENTS.md**: Detailed system requirements

## 🔧 Development Files

- **requirements.txt**: Python package dependencies
- **app.py**: Flask application entry point
- **env.example**: Environment variables template
- **tests/**: Test suite and test files

## 📝 Key Improvements Made

1. **Removed Duplicate Files**: Eliminated redundant documentation and configuration files
2. **Consolidated Docker Setup**: Streamlined to two main container types
3. **Updated Documentation**: README now reflects current project state
4. **Timezone Support**: Added comprehensive timezone management (100+ options)
5. **Clean Structure**: Organized project for better maintainability

## 🎯 Getting Started

1. **Choose deployment type**: Local dev, remote, or remote-dev
2. **Follow README.md**: Complete setup instructions
3. **Use appropriate compose file**: `docker-compose.yml`, `docker-compose.remote.yml`, or `docker-compose.remote-dev.yml`
4. **Configure timezone**: Access admin settings to set your local timezone

## 🔍 File Purposes

- **`.gitkeep` files**: Ensure empty directories are tracked in Git
- **`.github/`**: GitHub Actions workflows for automated builds
- **`logs/`**: Application log storage (cleaned up, only `.gitkeep` remains)
- **`LICENSE`**: GPL v3 open source license
- **`.gitignore`**: Git ignore patterns for temporary files

This cleaned up structure provides a more maintainable and focused codebase while preserving all essential functionality and documentation.
