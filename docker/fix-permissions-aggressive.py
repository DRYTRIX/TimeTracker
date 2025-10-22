#!/usr/bin/env python3
"""
Aggressive permission fix script for Docker containers
This script will fix file upload permissions by changing ownership and permissions
"""

import os
import sys
import stat
import subprocess

def run_command(cmd, description):
    """Run a shell command and return success status"""
    try:
        print(f"Running: {description}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ {description} - Success")
            return True
        else:
            print(f"⚠ {description} - Failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ {description} - Error: {e}")
        return False

def fix_permissions_aggressive():
    """Fix file upload permissions aggressively"""
    print("=== Aggressive Permission Fix for Docker Container ===")
    
    # Define the upload directories
    upload_dirs = [
        '/app/app/static/uploads',
        '/app/app/static/uploads/logos',
        '/app/app/static/uploads/avatars',
        '/app/static/uploads',
        '/app/static/uploads/logos',
        '/app/static/uploads/avatars'
    ]
    
    # Define the static directories
    static_dirs = ['/app/app/static', '/app/static']
    
    try:
        # Step 1: Create directories if they don't exist
        print("\n1. Creating upload directories...")
        for upload_dir in upload_dirs:
            if not os.path.exists(upload_dir):
                print(f"Creating directory: {upload_dir}")
                os.makedirs(upload_dir, mode=0o777, exist_ok=True)
            else:
                print(f"Directory exists: {upload_dir}")
        
        # Step 2: Set very permissive permissions (777 for testing)
        print("\n2. Setting permissive permissions...")
        for upload_dir in upload_dirs:
            if os.path.exists(upload_dir):
                print(f"Setting 777 permissions for: {upload_dir}")
                os.chmod(upload_dir, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)  # 777
                
                # Also try to change ownership to current user
                current_uid = os.getuid()
                current_gid = os.getgid()
                print(f"Current user: {current_uid}, group: {current_gid}")
        
        # Step 3: Try to change ownership using chown (if we have permission)
        print("\n3. Attempting to change ownership...")
        current_user = os.environ.get('USER', 'www-data')
        current_uid = os.environ.get('UID', '1000')
        
        for upload_dir in upload_dirs:
            if os.path.exists(upload_dir):
                # Try to change ownership to current user
                run_command(f"chown -R {current_user}:{current_user} {upload_dir}", 
                          f"Change ownership of {upload_dir}")
                
                # Also try to change ownership by UID
                run_command(f"chown -R {current_uid}:{current_uid} {upload_dir}", 
                          f"Change ownership of {upload_dir} by UID")
        
        # Step 4: Set permissions on parent directories
        print("\n4. Setting permissions on parent directories...")
        for static_dir in static_dirs:
            if os.path.exists(static_dir):
                print(f"Setting 755 permissions for: {static_dir}")
                os.chmod(static_dir, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
        
        # Step 5: Test write permissions
        print("\n5. Testing write permissions...")
        test_success = True
        for upload_dir in upload_dirs:
            if os.path.exists(upload_dir):
                test_file = os.path.join(upload_dir, 'test_permissions.tmp')
                try:
                    with open(test_file, 'w') as f:
                        f.write('test')
                    os.remove(test_file)
                    print(f"✓ Write permission test passed for: {upload_dir}")
                except Exception as e:
                    print(f"✗ Write permission test failed for: {upload_dir}: {e}")
                    test_success = False
        
        # Step 6: Show current permissions
        print("\n6. Current directory permissions:")
        for upload_dir in upload_dirs:
            if os.path.exists(upload_dir):
                try:
                    stat_info = os.stat(upload_dir)
                    mode = stat_info.st_mode
                    permissions = stat.filemode(mode)
                    print(f"{upload_dir}: {permissions}")
                except Exception as e:
                    print(f"{upload_dir}: Error getting permissions - {e}")
        
        if test_success:
            print("\n=== Permission fix completed successfully! ===")
            print("The application should now be able to upload logo files.")
        else:
            print("\n⚠ Some permission tests failed. You may need to run this as root or adjust Docker permissions.")
            
    except Exception as e:
        print(f"✗ Error during permission fix: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def main():
    """Main function"""
    print("=== Starting Aggressive Permission Fix ===")
    
    if fix_permissions_aggressive():
        print("\nPermission fix completed. Try uploading a logo file now.")
    else:
        print("\nPermission fix failed. You may need to:")
        print("1. Run this script as root (sudo)")
        print("2. Check Docker volume permissions")
        print("3. Restart the container with proper user mapping")
        sys.exit(1)

if __name__ == "__main__":
    main()
