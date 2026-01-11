# Desktop App Icons

This directory should contain the icon files for the TimeTracker desktop application.

## Required Icon Files

The following icon files are required for building the desktop app:

- `icon.ico` - Windows icon (256x256 or 512x512 pixels, multi-resolution)
- `icon.icns` - macOS icon (512x512 pixels, multi-resolution)
- `icon.png` - Linux icon (512x512 pixels)

## Generating Icons from Logo

The main project logo is located at `app/static/images/timetracker-logo.svg`.

### Option 1: Online Tools

1. **For Windows (.ico)**:
   - Use [CloudConvert](https://cloudconvert.com/svg-to-ico) or [ConvertICO](https://convertio.co/svg-ico/)
   - Upload `app/static/images/timetracker-logo.svg`
   - Set size to 256x256 or 512x512
   - Download and save as `icon.ico`

2. **For macOS (.icns)**:
   - Use [CloudConvert](https://cloudconvert.com/svg-to-icns) or [iConvert Icons](https://iconverticons.com/)
   - Upload `app/static/images/timetracker-logo.svg`
   - Set size to 512x512
   - Download and save as `icon.icns`

3. **For Linux (.png)**:
   - Use [CloudConvert](https://cloudconvert.com/svg-to-png) or any image converter
   - Upload `app/static/images/timetracker-logo.svg`
   - Set size to 512x512
   - Download and save as `icon.png`

### Option 2: Command Line (if ImageMagick is installed)

```bash
# Convert SVG to PNG (for Linux)
convert app/static/images/timetracker-logo.svg -resize 512x512 desktop/assets/icon.png

# Convert SVG to ICO (for Windows) - requires additional tools
# On macOS: brew install imagemagick
# On Linux: apt-get install imagemagick
convert app/static/images/timetracker-logo.svg -resize 256x256 desktop/assets/icon.ico

# For .icns on macOS, use iconutil or online converter
```

### Option 3: Using Electron Icon Generator

If you have Node.js installed:

```bash
cd desktop
npm install -g electron-icon-maker
electron-icon-maker --input=../app/static/images/timetracker-logo.svg --output=./assets
```

## Current Status

- ⚠️ Icon files need to be generated from the SVG logo
- ✅ Configuration in `package.json` is set up correctly
- ✅ Favicon is configured in `index.html`

## Notes

- The icons will be used as the application icon in the taskbar/dock
- The favicon in the HTML will be used in the browser window title bar
- Make sure icons are high quality (at least 256x256 for Windows, 512x512 for macOS/Linux)
