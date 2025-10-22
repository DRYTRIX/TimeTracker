#!/usr/bin/env python3
"""
Migration Script: Move User Avatars to Persistent Storage

This script migrates user avatar files from the application directory
(app/static/uploads/avatars) to the persistent /data volume (/data/uploads/avatars).

This ensures profile pictures persist between Docker container updates and rebuilds.

Usage:
    python migrate-avatar-storage.py

The script will:
1. Check for avatars in the old location (app/static/uploads/avatars)
2. Create the new directory structure (/data/uploads/avatars)
3. Copy all avatar files to the new location
4. Verify successful migration
5. Optionally remove old files after confirmation

Note: This is safe to run multiple times - it will skip files that already exist
in the new location.
"""

import os
import shutil
from pathlib import Path


def get_old_avatar_dir():
    """Get the old avatar directory path"""
    # Try to find the app directory
    possible_paths = [
        'app/static/uploads/avatars',
        '../app/static/uploads/avatars',
        '/app/static/uploads/avatars',
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None


def get_new_avatar_dir():
    """Get the new avatar directory path"""
    return '/data/uploads/avatars'


def ensure_directory(path):
    """Ensure a directory exists"""
    os.makedirs(path, exist_ok=True)
    print(f"✓ Ensured directory exists: {path}")


def migrate_avatars():
    """Migrate avatar files from old to new location"""
    old_dir = get_old_avatar_dir()
    new_dir = get_new_avatar_dir()
    
    print("=" * 70)
    print("User Avatar Storage Migration")
    print("=" * 70)
    print()
    
    if not old_dir:
        print("⚠️  Old avatar directory not found. Possible reasons:")
        print("   - No avatars have been uploaded yet")
        print("   - Avatars are already in the new location")
        print("   - Script is being run from an unexpected directory")
        print()
        print("Creating new avatar directory structure...")
        ensure_directory(new_dir)
        print()
        print("✓ Migration complete (no files to migrate)")
        return
    
    print(f"Old location: {old_dir}")
    print(f"New location: {new_dir}")
    print()
    
    # Ensure new directory exists
    ensure_directory(new_dir)
    
    # Get list of avatar files
    try:
        avatar_files = [f for f in os.listdir(old_dir) if os.path.isfile(os.path.join(old_dir, f))]
    except Exception as e:
        print(f"❌ Error listing files in {old_dir}: {e}")
        return
    
    if not avatar_files:
        print("ℹ️  No avatar files found in old location")
        print("✓ Migration complete (nothing to migrate)")
        return
    
    print(f"Found {len(avatar_files)} avatar file(s) to migrate")
    print()
    
    # Migrate each file
    migrated = 0
    skipped = 0
    errors = 0
    
    for filename in avatar_files:
        old_path = os.path.join(old_dir, filename)
        new_path = os.path.join(new_dir, filename)
        
        # Skip if already exists in new location
        if os.path.exists(new_path):
            print(f"⊘ Skipped (already exists): {filename}")
            skipped += 1
            continue
        
        # Copy file
        try:
            shutil.copy2(old_path, new_path)
            print(f"✓ Migrated: {filename}")
            migrated += 1
        except Exception as e:
            print(f"❌ Error migrating {filename}: {e}")
            errors += 1
    
    print()
    print("=" * 70)
    print("Migration Summary")
    print("=" * 70)
    print(f"✓ Successfully migrated: {migrated}")
    print(f"⊘ Skipped (already exist): {skipped}")
    print(f"❌ Errors: {errors}")
    print()
    
    if migrated > 0:
        print("⚠️  IMPORTANT: Old avatar files are still in place.")
        print("   After verifying all avatars work correctly, you can safely")
        print(f"   remove the old directory: {old_dir}")
        print()
        print("   To remove old files, run:")
        print(f"   rm -rf {old_dir}")
    
    if errors > 0:
        print("⚠️  Some files could not be migrated. Please check the errors above.")
    elif migrated > 0 or skipped > 0:
        print("✓ Migration completed successfully!")
    
    print()


def verify_migration():
    """Verify that the new directory is accessible and writable"""
    new_dir = get_new_avatar_dir()
    test_file = os.path.join(new_dir, '.test_write')
    
    print("Verifying new directory permissions...")
    try:
        # Test write
        with open(test_file, 'w') as f:
            f.write('test')
        # Test read
        with open(test_file, 'r') as f:
            content = f.read()
        # Cleanup
        os.remove(test_file)
        print("✓ New directory is writable and readable")
        return True
    except Exception as e:
        print(f"❌ Error verifying new directory: {e}")
        print("   Please check directory permissions")
        return False


if __name__ == '__main__':
    print()
    migrate_avatars()
    print()
    verify_migration()
    print()

