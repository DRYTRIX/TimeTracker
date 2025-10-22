#!/usr/bin/env python3
"""
Fix script for upload directory permissions
This script will ensure the upload directories have proper permissions for file uploads
"""

import os
import sys
import stat

def main():
    """Fix upload directory permissions"""
    print("=== Fixing upload directory permissions ===")
    
    # Define the upload directories that need permissions fixed
    upload_dirs = [
        '/app/app/static/uploads',
        '/app/app/static/uploads/logos',
        '/app/app/static/uploads/avatars',
        '/app/static/uploads',
        '/app/static/uploads/logos',
        '/app/static/uploads/avatars'
    ]
    
    try:
        for upload_dir in upload_dirs:
            if os.path.exists(upload_dir):
                print(f"Fixing permissions for: {upload_dir}")
                
                # Set directory permissions to 755 (rwxr-xr-x)
                os.chmod(upload_dir, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                print(f"✓ Set directory permissions for: {upload_dir}")
                
                # Check if we can write to the directory
                test_file = os.path.join(upload_dir, 'test_permissions.tmp')
                try:
                    with open(test_file, 'w') as f:
                        f.write('test')
                    os.remove(test_file)
                    print(f"✓ Write permission test passed for: {upload_dir}")
                except Exception as e:
                    print(f"⚠ Write permission test failed for: {upload_dir}: {e}")
                    
            else:
                print(f"Creating directory: {upload_dir}")
                try:
                    os.makedirs(upload_dir, mode=0o755, exist_ok=True)
                    print(f"✓ Created directory: {upload_dir}")
                except Exception as e:
                    print(f"✗ Failed to create directory {upload_dir}: {e}")
        
        # Also check the parent static directory
        static_dirs = ['/app/app/static', '/app/static']
        for static_dir in static_dirs:
            if os.path.exists(static_dir):
                print(f"Fixing permissions for static directory: {static_dir}")
                os.chmod(static_dir, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                print(f"✓ Set static directory permissions for: {static_dir}")
        
        print("\n=== Permission fix completed ===")
        print("The application should now be able to upload logo files.")
        
    except Exception as e:
        print(f"✗ Error fixing permissions: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
