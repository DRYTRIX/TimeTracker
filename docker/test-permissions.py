#!/usr/bin/env python3
"""
Test script to check current permissions in Docker container
Run this to see what's wrong with the upload directories
"""

import grp
import os
import pwd
import stat


def get_user_info():
    """Get current user information"""
    try:
        uid = os.getuid()
        gid = os.getgid()
        user_info = pwd.getpwuid(uid)
        group_info = grp.getgrgid(gid)

        print(f"Current user: {user_info.pw_name}")
        print(f"Current UID: {uid}")
        print(f"Current GID: {gid}")
        print(f"Current group: {group_info.gr_name}")
        print(f"Current working directory: {os.getcwd()}")

        return uid, gid
    except Exception as e:
        print(f"Error getting user info: {e}")
        return 1000, 1000


def check_directory_permissions(path, description):
    """Check permissions for a specific directory"""
    print(f"\n=== {description} ===")
    print(f"Path: {path}")

    if not os.path.exists(path):
        print("✗ Directory does not exist")
        return False

    try:
        # Get directory info
        stat_info = os.stat(path)
        mode = stat.filemode(stat_info.st_mode)
        owner_uid = stat_info.st_uid
        owner_gid = stat_info.st_gid

        print(f"Permissions: {mode}")
        print(f"Owner UID: {owner_uid}")
        print(f"Owner GID: {owner_gid}")

        # Try to get owner names
        try:
            owner_name = pwd.getpwuid(owner_uid).pw_name
            print(f"Owner name: {owner_name}")
        except:
            print(f"Owner name: Unknown (UID {owner_uid})")

        try:
            group_name = grp.getgrgid(owner_gid).gr_name
            print(f"Group name: {group_name}")
        except:
            print(f"Group name: Unknown (GID {owner_gid})")

        # Check if current user can write
        current_uid, current_gid = get_user_info()
        can_write = False

        if owner_uid == current_uid:
            can_write = bool(stat_info.st_mode & stat.S_IWUSR)
            print(f"Current user owns directory: {can_write}")
        elif owner_gid == current_gid:
            can_write = bool(stat_info.st_mode & stat.S_IWGRP)
            print(f"Current user in owner group: {can_write}")
        else:
            can_write = bool(stat_info.st_mode & stat.S_IWOTH)
            print(f"Current user has other write permission: {can_write}")

        # Test write permission
        test_file = os.path.join(path, "test_permissions.tmp")
        try:
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            print("✓ Write permission test: PASSED")
            return True
        except Exception as e:
            print(f"✗ Write permission test: FAILED - {e}")
            return False

    except Exception as e:
        print(f"Error checking directory: {e}")
        return False


def main():
    """Main function"""
    print("=== Docker Container Permission Test ===")

    # Get current user info
    current_uid, current_gid = get_user_info()

    # Check upload directories
    upload_dirs = [
        ("/app/app/static/uploads", "Main upload directory"),
        ("/app/app/static/uploads/logos", "Logo upload directory"),
        ("/app/static/uploads", "Alternative upload directory"),
        ("/app/static/uploads/logos", "Alternative logo directory"),
    ]

    all_passed = True
    for path, description in upload_dirs:
        if not check_directory_permissions(path, description):
            all_passed = False

    # Summary
    print(f"\n=== Summary ===")
    if all_passed:
        print("✓ All permission tests passed!")
        print("Upload directories should work correctly.")
    else:
        print("✗ Some permission tests failed!")
        print("\nTo fix these issues:")
        print("1. Rebuild the Docker container with the fixed Dockerfile")
        print("2. Or run the permission fix script inside the container")
        print("3. Or restart the container with proper volume permissions")

    return all_passed


if __name__ == "__main__":
    main()
