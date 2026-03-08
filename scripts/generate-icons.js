#!/usr/bin/env node

/**
 * Icon Generation Script for TimeTracker
 * 
 * This script generates all required icon formats from the SVG logo.
 * Requires: sharp, to-ico (npm install sharp to-ico)
 * 
 * Usage: node scripts/generate-icons.js
 * 
 * For macOS .icns: run scripts/generate-macos-icon.sh on macOS (uses iconutil)
 */

const fs = require('fs');
const path = require('path');

// Check if sharp is available
let sharp;
try {
  sharp = require('sharp');
} catch (e) {
  console.error('Error: sharp package is required. Install it with: npm install sharp');
  process.exit(1);
}

let toIco;
try {
  toIco = require('to-ico');
} catch (e) {
  console.error('Error: to-ico package is required. Install it with: npm install to-ico');
  process.exit(1);
}

const logoPath = path.join(__dirname, '../app/static/images/timetracker-logo.svg');
const outputDir = path.join(__dirname, '../app/static/images');
const desktopAssetsDir = path.join(__dirname, '../desktop/assets');

// Ensure output directories exist
[outputDir, desktopAssetsDir].forEach(dir => {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
});

async function generateIcons() {
  console.log('Generating icons from SVG logo...\n');

  if (!fs.existsSync(logoPath)) {
    console.error(`Error: Logo file not found at ${logoPath}`);
    process.exit(1);
  }

  try {
    // Read SVG
    const svgBuffer = fs.readFileSync(logoPath);

    // Generate favicon.ico (multi-size)
    console.log('Generating favicon.ico...');
    const faviconSizes = [16, 32, 48];
    const faviconImages = await Promise.all(
      faviconSizes.map(size =>
        sharp(svgBuffer)
          .resize(size, size)
          .png()
          .toBuffer()
      )
    );
    // Note: Creating a proper .ico file requires additional library
    // For now, we'll create a 32x32 PNG as favicon
    await sharp(svgBuffer)
      .resize(32, 32)
      .png()
      .toFile(path.join(outputDir, 'favicon-32x32.png'));
    console.log('  ✓ Created favicon-32x32.png');

    // Generate Apple Touch Icon (180x180)
    console.log('Generating Apple Touch Icon...');
    await sharp(svgBuffer)
      .resize(180, 180)
      .png()
      .toFile(path.join(outputDir, 'apple-touch-icon.png'));
    console.log('  ✓ Created apple-touch-icon.png (180x180)');

    // Generate Android Chrome Icons
    console.log('Generating Android Chrome Icons...');
    await sharp(svgBuffer)
      .resize(192, 192)
      .png()
      .toFile(path.join(outputDir, 'android-chrome-192x192.png'));
    console.log('  ✓ Created android-chrome-192x192.png');

    await sharp(svgBuffer)
      .resize(512, 512)
      .png()
      .toFile(path.join(outputDir, 'android-chrome-512x512.png'));
    console.log('  ✓ Created android-chrome-512x512.png');

    // Generate Desktop Icons
    console.log('\nGenerating Desktop Icons...');

    // Linux PNG (512x512)
    await sharp(svgBuffer)
      .resize(512, 512)
      .png()
      .toFile(path.join(desktopAssetsDir, 'icon.png'));
    console.log('  ✓ Created desktop/assets/icon.png (512x512)');

    // Windows ICO (multi-size: 16, 32, 48, 256)
    const icoSizes = [16, 32, 48, 256];
    const icoBuffers = await Promise.all(
      icoSizes.map(size =>
        sharp(svgBuffer)
          .resize(size, size)
          .png()
          .toBuffer()
      )
    );
    const icoBuffer = await toIco(icoBuffers);
    fs.writeFileSync(path.join(desktopAssetsDir, 'icon.ico'), icoBuffer);
    console.log('  ✓ Created desktop/assets/icon.ico (multi-size)');

    // macOS ICNS source: create icon.iconset for iconutil (macOS only)
    // The icon.icns must be created on macOS via: iconutil -c icns icon.iconset -o icon.icns
    const iconsetDir = path.join(desktopAssetsDir, 'icon.iconset');
    if (!fs.existsSync(iconsetDir)) {
      fs.mkdirSync(iconsetDir, { recursive: true });
    }
    const macSizes = [
      { size: 16, name: 'icon_16x16.png' },
      { size: 32, name: 'icon_16x16@2x.png' },
      { size: 32, name: 'icon_32x32.png' },
      { size: 64, name: 'icon_32x32@2x.png' },
      { size: 128, name: 'icon_128x128.png' },
      { size: 256, name: 'icon_128x128@2x.png' },
      { size: 256, name: 'icon_256x256.png' },
      { size: 512, name: 'icon_256x256@2x.png' },
      { size: 512, name: 'icon_512x512.png' },
      { size: 1024, name: 'icon_512x512@2x.png' },
    ];
    for (const { size, name } of macSizes) {
      await sharp(svgBuffer)
        .resize(size, size)
        .png()
        .toFile(path.join(iconsetDir, name));
    }
    console.log('  ✓ Created desktop/assets/icon.iconset/ (run iconutil on macOS to create icon.icns)');

    console.log('\n✓ Icon generation complete!');

  } catch (error) {
    console.error('Error generating icons:', error);
    process.exit(1);
  }
}

// Run the script
generateIcons();
