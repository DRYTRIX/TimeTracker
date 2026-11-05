#!/usr/bin/env node
/**
 * Platform-aware build script for electron-builder
 * Builds for all platforms supported on the current OS
 */

const { execSync } = require('child_process');
const os = require('os');

const platform = os.platform();
let buildCommand = 'electron-builder';

console.log(`\n🔨 Building for all supported platforms on ${platform}\n`);
console.log('📦 Building renderer bundle...');
execSync('npm run build:renderer', { stdio: 'inherit' });
console.log('');

// Determine which platforms can be built on the current OS
switch (platform) {
  case 'win32':
    // Windows can technically build Linux, but requires admin privileges for symlinks
    // For better UX, only build Windows on Windows by default
    // Use --linux flag explicitly if admin privileges are available
    const buildLinux = process.env.BUILD_LINUX_ON_WINDOWS === 'true';
    if (buildLinux) {
      console.log('📦 Building for Windows and Linux...');
      console.log('⚠️  Linux builds on Windows require administrator privileges for symlinks.');
      console.log('   If this fails, run as administrator or use: npm run build:win\n');
      buildCommand += ' --win --linux';
    } else {
      console.log('📦 Building for Windows only...');
      console.log('ℹ️  Linux builds on Windows require admin privileges (symlinks).');
      console.log('   To build Linux too, set BUILD_LINUX_ON_WINDOWS=true and run as admin.\n');
      buildCommand += ' --win';
    }
    break;

  case 'darwin':
    // macOS can build: Windows, macOS, Linux
    console.log('📦 Building for Windows, macOS, and Linux...');
    console.log('ℹ️  All platforms supported on macOS!\n');
    buildCommand += ' --win --mac --linux';
    break;

  case 'linux':
    // Linux can build: Windows, Linux
    console.log('📦 Building for Windows and Linux...');
    console.log('ℹ️  macOS builds require macOS. Skipping macOS build.\n');
    buildCommand += ' --win --linux';
    break;

  default:
    console.error(`❌ Unknown platform: ${platform}`);
    console.log('📦 Building for current platform only...\n');
    // Just build for current platform
    break;
}

// Disable code signing for Windows unless certificate is explicitly provided
if (platform === 'win32') {
  if (process.env.CSC_LINK || process.env.CSC_LINK_FILE) {
    console.log('ℹ️  Code signing will be enabled (certificate detected)\n');
  } else {
    console.log('ℹ️  No signing certificate configured; building unsigned Windows artifacts.\n');
  }
}

try {
  execSync(buildCommand, { stdio: 'inherit' });
  console.log('\n✅ Build completed successfully!');
} catch (error) {
  if (platform === 'win32') {
    console.error('\n❌ Build failed!');
    console.error('\n💡 Troubleshooting tips for Windows:');
    console.error('   1. Try running as Administrator');
    console.error('   2. Clear electron-builder cache: rmdir /s /q "%LOCALAPPDATA%\\electron-builder\\Cache"');
    console.error('   3. Build Windows only: npm run build:win');
    console.error('   4. Disable OneDrive sync for the desktop folder');
  } else {
    console.error('\n❌ Build failed!');
  }
  process.exit(1);
}
