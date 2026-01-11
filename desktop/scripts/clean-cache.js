#!/usr/bin/env node
/**
 * Clean electron-builder cache
 * Helps resolve permission/symlink issues on Windows
 */

const { execSync } = require('child_process');
const os = require('os');
const path = require('path');
const fs = require('fs');

const platform = os.platform();
const cacheDir = path.join(os.homedir(), 
  platform === 'win32' 
    ? 'AppData/Local/electron-builder/Cache'
    : platform === 'darwin'
    ? 'Library/Caches/electron-builder'
    : '.cache/electron-builder'
);

console.log(`\n🧹 Cleaning electron-builder cache...\n`);
console.log(`📁 Cache directory: ${cacheDir}\n`);

try {
  if (fs.existsSync(cacheDir)) {
    if (platform === 'win32') {
      // Windows: use rmdir command
      try {
        execSync(`rmdir /s /q "${cacheDir}"`, { stdio: 'inherit' });
        console.log('✅ Cache cleaned successfully!');
      } catch (error) {
        console.error('❌ Failed to clean cache. Try running as Administrator.');
        console.error('   Or manually delete:', cacheDir);
        process.exit(1);
      }
    } else {
      // Unix: use rm command
      execSync(`rm -rf "${cacheDir}"`, { stdio: 'inherit' });
      console.log('✅ Cache cleaned successfully!');
    }
  } else {
    console.log('ℹ️  Cache directory does not exist (already clean)');
  }
} catch (error) {
  console.error('❌ Error cleaning cache:', error.message);
  console.error('   Try running as Administrator (Windows) or with sudo (Unix)');
  process.exit(1);
}
