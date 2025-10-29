#!/usr/bin/env python3
"""
Migration script to ensure uploads directory structure for persistence.

This migration:
1. Creates the uploads directory structure if it doesn't exist
2. Ensures proper permissions for the uploads directories
3. Verifies that logos and avatars subdirectories exist
4. Creates .gitkeep files to preserve directory structure in git

Run this script to prepare the application for persistent file uploads.
"""

import os
import sys
import stat

def ensure_uploads_directories():
    """Ensure uploads directory structure exists with proper permissions"""
    print("=== Ensuring Uploads Directory Structure ===")
    
    # Define the upload directories that need to exist
    # Support both /app/app/static/uploads (container) and app/static/uploads (local)
    possible_base_paths = [
        '/app/app/static/uploads',  # Docker container path
        'app/static/uploads',        # Local development path
    ]
    
    # Try to find the correct base path
    base_path = None
    for path in possible_base_paths:
        parent = os.path.dirname(path)
        if os.path.exists(parent) or path.startswith('/app'):
            base_path = path
            break
    
    if not base_path:
        print("⚠ Could not determine base path. Using default: app/static/uploads")
        base_path = 'app/static/uploads'
    
    print(f"Using base path: {base_path}")
    
    # Define subdirectories
    subdirectories = ['logos', 'avatars']
    
    try:
        # Create main uploads directory
        if not os.path.exists(base_path):
            os.makedirs(base_path, mode=0o755, exist_ok=True)
            print(f"✓ Created uploads directory: {base_path}")
        else:
            print(f"✓ Uploads directory exists: {base_path}")
        
        # Set permissions on uploads directory
        try:
            os.chmod(base_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
            print(f"✓ Set permissions (755) on: {base_path}")
        except Exception as e:
            print(f"⚠ Could not set permissions on {base_path}: {e}")
        
        # Create subdirectories
        for subdir in subdirectories:
            subdir_path = os.path.join(base_path, subdir)
            if not os.path.exists(subdir_path):
                os.makedirs(subdir_path, mode=0o755, exist_ok=True)
                print(f"✓ Created subdirectory: {subdir_path}")
            else:
                print(f"✓ Subdirectory exists: {subdir_path}")
            
            # Set permissions on subdirectory
            try:
                os.chmod(subdir_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                print(f"✓ Set permissions (755) on: {subdir_path}")
            except Exception as e:
                print(f"⚠ Could not set permissions on {subdir_path}: {e}")
            
            # Create .gitkeep file to preserve directory in git
            gitkeep_path = os.path.join(subdir_path, '.gitkeep')
            if not os.path.exists(gitkeep_path):
                try:
                    with open(gitkeep_path, 'w') as f:
                        f.write('# This file ensures the directory is tracked by git\n')
                    print(f"✓ Created .gitkeep in: {subdir_path}")
                except Exception as e:
                    print(f"⚠ Could not create .gitkeep in {subdir_path}: {e}")
        
        # Test write permissions
        print("\nTesting write permissions...")
        for subdir in subdirectories:
            subdir_path = os.path.join(base_path, subdir)
            test_file = os.path.join(subdir_path, '.test_write_permissions')
            try:
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                print(f"✓ Write permission test passed: {subdir_path}")
            except Exception as e:
                print(f"⚠ Write permission test failed for {subdir_path}: {e}")
        
        print("\n=== Uploads Directory Structure Ready ===")
        print("\nDirectory structure:")
        print(f"  {base_path}/")
        for subdir in subdirectories:
            print(f"    ├── {subdir}/")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error ensuring uploads directory structure: {e}")
        return False


def verify_docker_volume_config():
    """Verify that Docker volume configuration is present"""
    print("\n=== Verifying Docker Volume Configuration ===")
    
    compose_files = [
        'docker-compose.yml',
        'docker-compose.example.yml',
        'docker-compose.remote.yml',
        'docker-compose.local-test.yml',
        'docker-compose.remote-dev.yml',
    ]
    
    for compose_file in compose_files:
        if os.path.exists(compose_file):
            with open(compose_file, 'r') as f:
                content = f.read()
                if 'app_uploads' in content or 'uploads' in content:
                    print(f"✓ {compose_file} has uploads volume configured")
                else:
                    print(f"⚠ {compose_file} may be missing uploads volume configuration")
        else:
            print(f"  {compose_file} not found (optional)")
    
    print("\n=== Volume Configuration Verification Complete ===")


def main():
    """Main migration function"""
    print("\n" + "="*60)
    print("  Uploads Persistence Migration")
    print("="*60 + "\n")
    
    success = True
    
    # Ensure directory structure
    if not ensure_uploads_directories():
        success = False
    
    # Verify Docker configuration
    verify_docker_volume_config()
    
    if success:
        print("\n" + "="*60)
        print("  ✓ Migration completed successfully!")
        print("="*60)
        print("\nNext steps:")
        print("1. If using Docker, rebuild your containers:")
        print("   docker-compose down")
        print("   docker-compose up -d")
        print("\n2. Your uploaded logos and avatars will now persist")
        print("   between container rebuilds.")
        print("\n3. Existing uploaded files should remain intact.")
        print("="*60 + "\n")
        return 0
    else:
        print("\n" + "="*60)
        print("  ⚠ Migration completed with warnings")
        print("="*60)
        print("\nSome steps failed, but the application may still work.")
        print("Check the warnings above for details.")
        print("="*60 + "\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())

