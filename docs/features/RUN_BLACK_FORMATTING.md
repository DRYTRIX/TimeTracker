# Run Black Code Formatting

## Quick Fix

Run ONE of these commands to fix all 44 files:

```bash
# Option 1: Direct command
black app/

# Option 2: Via Python module
python -m black app/

# Option 3: Via Python launcher (Windows)
py -m black app/
```

## Install Black (If Not Installed)

```bash
# Using pip
pip install black

# Or add to requirements
pip install black
```

## What Will Be Fixed

Black will reformat these 44 files:
- All files in `app/models/` (22 files)
- All files in `app/routes/` (12 files)
- All files in `app/utils/` (10 files)
- `app/__init__.py`
- `app/config.py`

## Verify Formatting

```bash
# Check what would be changed (without changing)
black --check app/

# See diff of changes
black --diff app/

# Actually apply formatting
black app/
```

## Expected Output

```
reformatted app/models/__init__.py
reformatted app/models/client.py
... (42 more files) ...
All done! ✨ 🍰 ✨
44 files reformatted.
```

## Alternative: Format on Commit

If you prefer, you can set up pre-commit hooks:

```bash
# Install pre-commit
pip install pre-commit

# Create .pre-commit-config.yaml
cat > .pre-commit-config.yaml << EOF
repos:
  - repo: https://github.com/psf/black
    rev: 24.1.1
    hooks:
      - id: black
        language_version: python3.11
EOF

# Install hooks
pre-commit install

# Now Black will run automatically on git commit
```

## One-Line Fix

```bash
pip install black && black app/
```

That's it! 🎉
