const assert = require('assert');
const fs = require('fs');
const path = require('path');
const test = require('node:test');

const root = path.resolve(__dirname, '..');

test('desktop package builds the React renderer with Vite', () => {
  const pkg = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
  assert.strictEqual(pkg.scripts['build:renderer'], 'vite build');
  assert.ok(pkg.dependencies.react);
  assert.ok(pkg.dependencies['react-dom']);
  assert.ok(pkg.devDependencies.vite);
  assert.ok(pkg.devDependencies['@vitejs/plugin-react']);
  assert.ok(fs.existsSync(path.join(root, 'vite.config.mjs')));
  assert.ok(!fs.existsSync(path.join(root, 'vite.config.js')));
  assert.ok(pkg.build.files.includes('dist-renderer/**/*'));
});

test('Electron loads only the built React renderer', () => {
  const windowSource = fs.readFileSync(path.join(root, 'src/main/window.js'), 'utf8');
  assert.match(windowSource, /dist-renderer\/index\.html/);
  assert.match(windowSource, /build:renderer/);
  assert.doesNotMatch(windowSource, /legacyIndex/);
  assert.match(windowSource, /splash\/splash\.html/);
  const pkg = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
  assert.ok(pkg.build.files.some((f) => String(f).includes('!src/renderer')));
});

test('main process store IPC is limited to known desktop settings', () => {
  const mainSource = fs.readFileSync(path.join(root, 'src/main/main.js'), 'utf8');
  assert.match(mainSource, /ALLOWED_STORE_KEYS/);
  assert.match(mainSource, /api_token_server_url/);
  assert.match(mainSource, /theme_mode/);
  assert.match(mainSource, /auto_sync/);
});

test('desktop GitHub workflows use a Vite-compatible Node version', () => {
  const workflowRoot = path.resolve(root, '..', '.github', 'workflows');
  const buildDesktop = fs.readFileSync(path.join(workflowRoot, 'build-desktop.yml'), 'utf8');
  const release = fs.readFileSync(path.join(workflowRoot, 'cd-release.yml'), 'utf8');
  for (const source of [buildDesktop, release]) {
    assert.match(source, /NODE_VERSION:\s+'24'/);
    assert.doesNotMatch(source, /node-version:\s+'18'/);
  }
});
