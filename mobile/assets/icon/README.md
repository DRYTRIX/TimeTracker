# App icon source

The launcher icon is generated at build time from `app_icon.png` (1024×1024) by `flutter_launcher_icons`.

## Creating or updating `app_icon.png`

Export the TimeTracker icon from the web app assets:

- **Source:** `app/static/images/timetracker-logo-icon.svg` (project root)
- **Size:** 1024×1024 pixels, PNG

You can export once using:

- **ImageMagick:** `magick ../../app/static/images/timetracker-logo-icon.svg -resize 1024x1024 app_icon.png`
- **Inkscape:** Export as PNG at 1024×1024 from the SVG.
- **Browser:** Open the SVG, use dev tools or a screenshot tool at 1024×1024.

Alternatively, run the project script from the repo root:

- Windows: `scripts\generate-mobile-icon.bat`
- Linux/macOS: `./scripts/generate-mobile-icon.sh`

(Requires ImageMagick or Inkscape to be installed.)
