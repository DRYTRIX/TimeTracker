#!/usr/bin/env python3
"""
Fix Docker container permission issues for file uploads
This script should be run INSIDE your Docker container
"""

import os
import sys
import stat
import subprocess
import shlex
import re

def run_command(cmd, description):
    """Run a shell command and return success status
    
    Args:
        cmd: Command string or list of command arguments
        description: Human-readable description
    """
    try:
        print(f"Running: {description}")
        # If cmd is a string, split it safely
        if isinstance(cmd, str):
            try:
                cmd_list = shlex.split(cmd)
            except ValueError:
                # Fallback to simple split
                cmd_list = cmd.split()
        else:
            cmd_list = cmd
        
        result = subprocess.run(cmd_list, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ {description} - Success")
            return True
        else:
            print(f"⚠ {description} - Failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ {description} - Error: {e}")
        return False

def get_user_info():
    """Get current user information"""
    try:
        user = os.environ.get('USER', 'unknown')
        uid = os.getuid()
        gid = os.getgid()
        cwd = os.getcwd()
        
        print(f"Current user: {user}")
        print(f"Current UID: {uid}")
        print(f"Current GID: {gid}")
        print(f"Current working directory: {cwd}")
        
        return user, uid, gid
    except Exception as e:
        print(f"Error getting user info: {e}")
        return 'unknown', 1000, 1000

def fix_docker_permissions():
    """Fix Docker container permission issues"""
    print("=== Fixing Docker Container Permissions ===")
    
    # Get user info
    user, uid, gid = get_user_info()
    
    # Define the upload directories
    upload_dirs = [
        "/app/app/static/uploads",
        "/app/app/static/uploads/logos",
        "/app/static/uploads",
        "/app/static/uploads/logos"
    ]
    
    # Step 1: Create directories with proper permissions
    print("\n1. Creating upload directories...")
    for upload_dir in upload_dirs:
        if not os.path.exists(upload_dir):
            print(f"Creating directory: {upload_dir}")
            try:
                os.makedirs(upload_dir, mode=0o777, exist_ok=True)
            except Exception as e:
                print(f"  - Failed to create {upload_dir}: {e}")
        else:
            print(f"Directory exists: {upload_dir}")
    
    # Step 2: Set very permissive permissions (777 for testing)
    print("\n2. Setting permissive permissions...")
    for upload_dir in upload_dirs:
        if os.path.exists(upload_dir):
            print(f"Setting 777 permissions for: {upload_dir}")
            try:
                os.chmod(upload_dir, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)  # 777
                # Also set permissions recursively
                for root, dirs, files in os.walk(upload_dir):
                    os.chmod(root, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
                    for file in files:
                        file_path = os.path.join(root, file)
                        os.chmod(file_path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
            except Exception as e:
                print(f"  - Failed to set permissions for {upload_dir}: {e}")
    
    # Step 3: Try to change ownership using chown
    print("\n3. Changing ownership to current user...")
    # Sanitize user to prevent command injection
    user = re.sub(r'[^a-zA-Z0-9_-]', '', str(user))
    uid = str(int(uid)) if str(uid).isdigit() else '1000'
    gid = str(int(gid)) if str(gid).isdigit() else '1000'
    
    for upload_dir in upload_dirs:
        if os.path.exists(upload_dir):
            print(f"Changing ownership of {upload_dir} to {user}:{user}")
            
            # Try chown with username (use list to avoid shell)
            if not run_command(['chown', '-R', f'{user}:{user}', upload_dir], 
                             f"Change ownership of {upload_dir}"):
                # If that fails, try with UID
                run_command(['chown', '-R', f'{uid}:{gid}', upload_dir], 
                           f"Change ownership of {upload_dir} by UID")
    
    # Step 4: Test write permissions
    print("\n4. Testing write permissions...")
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
    
    # Step 5: Show current permissions and ownership
    print("\n5. Current directory status:")
    for upload_dir in upload_dirs:
        if os.path.exists(upload_dir):
            print(f"\nDirectory: {upload_dir}")
            try:
                # List directory contents
                files = os.listdir(upload_dir)
                for file in files[:5]:  # Show first 5 files
                    file_path = os.path.join(upload_dir, file)
                    stat_info = os.stat(file_path)
                    mode = stat.filemode(stat_info.st_mode)
                    print(f"  {file}: {mode}")
                
                # Show directory permissions
                stat_info = os.stat(upload_dir)
                mode = stat.filemode(stat_info.st_mode)
                print(f"Directory permissions: {mode}")
                
            except Exception as e:
                print(f"  Error getting info: {e}")
    
    # Step 6: Fix parent directories
    print("\n6. Fixing parent directory permissions...")
    parent_dirs = ["/app/app/static", "/app/static"]
    for parent_dir in parent_dirs:
        if os.path.exists(parent_dir):
            print(f"Setting 755 permissions for parent: {parent_dir}")
            try:
                os.chmod(parent_dir, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                # Sanitize user before use
                safe_user = re.sub(r'[^a-zA-Z0-9_-]', '', str(user))
                run_command(['chown', safe_user + ':' + safe_user, parent_dir], f"Change ownership of {parent_dir}")
            except Exception as e:
                print(f"  - Failed to fix {parent_dir}: {e}")
    
    # Final test and recommendations
    print("\n7. Final permission test...")
    if test_success:
        print("=== Permission fix completed successfully! ===")
        print("The application should now be able to upload logo files.")
        print("\nTry uploading a logo file now. If it still fails, you may need to:")
        print("1. Restart the Docker container")
        print("2. Check Docker volume mount permissions")
        print("3. Run the container with proper user mapping")
    else:
        print("=== Some permission tests failed ===")
        print("\nTrying alternative approach...")
        
        # Try to run as root if possible
        if uid == 0:
            print("Running as root, setting permissions...")
            for upload_dir in upload_dirs:
                if os.path.exists(upload_dir):
                    try:
                        os.chmod(upload_dir, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
                        run_command(['chown', '-R', '1000:1000', upload_dir], f"Change ownership of {upload_dir} to 1000:1000")
                    except Exception as e:
                        print(f"  - Failed to fix {upload_dir}: {e}")
        else:
            print("Not running as root. You may need to:")
            print("1. Run this script as root (sudo)")
            print("2. Restart the container with proper user mapping")
            print("3. Check Docker volume permissions")
    
    return test_success

def main():
    """Main function"""
    print("=== Starting Docker Permission Fix ===")
    
    if fix_docker_permissions():
        print("\nPermission fix completed. Try uploading a logo file now.")
    else:
        print("\nPermission fix had some issues. Check the output above for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
