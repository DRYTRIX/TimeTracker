# Legacy renderer (deprecated)

The Electron app loads the Vite-built React UI from `dist-renderer/` (`src/renderer-react/`).

This folder keeps **only** the pre-React JavaScript modules under `js/` so existing Node unit tests in `desktop/test/` can import them. The old HTML shell (`index.html`, `app.js`, bundled assets) has been removed.

Do not add new features here. Splash screen assets live in `src/main/splash/`.

Packaged desktop builds exclude `src/renderer/**` via `electron-builder` `files` in `package.json`.
