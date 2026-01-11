#!/usr/bin/env node

/**
 * Icon Generation Script for TimeTracker
 * 
 * This script generates all required icon formats from the SVG logo.
 * Requires: sharp (npm install sharp)
 * 
 * Usage: node scripts/generate-icons.js
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

    // Windows ICO (requires multi-size, creating PNG for now)
    // Note: Proper .ico generation requires additional tools
    await sharp(svgBuffer)
      .resize(256, 256)
      .png()
      .toFile(path.join(desktopAssetsDir, 'icon-256x256.png'));
    console.log('  ✓ Created desktop/assets/icon-256x256.png');
    console.log('  ⚠ Note: Convert to .ico using online tool or ImageMagick');

    // macOS ICNS (requires iconutil, creating PNG for now)
    await sharp(svgBuffer)
      .resize(512, 512)
      .png()
      .toFile(path.join(desktopAssetsDir, 'icon-512x512.png'));
    console.log('  ✓ Created desktop/assets/icon-512x512.png');
    console.log('  ⚠ Note: Convert to .icns using iconutil on macOS');

    console.log('\n✓ Icon generation complete!');
    console.log('\nNext steps:');
    console.log('1. Convert icon-256x256.png to icon.ico for Windows');
    console.log('2. Convert icon-512x512.png to icon.icns for macOS');
    console.log('3. Use online tools like cloudconvert.com or iconverticons.com');

  } catch (error) {
    console.error('Error generating icons:', error);
    process.exit(1);
  }
}

// Run the script
generateIcons();
