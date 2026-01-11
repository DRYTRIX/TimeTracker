#!/usr/bin/env python3
"""
Sync version from setup.py to mobile app (Flutter pubspec.yaml and Android build.gradle)
This ensures the mobile app uses the same version as the main application.
"""

import os
import sys
import re

def get_version_from_setup():
    """Read version from setup.py"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    setup_path = os.path.join(project_root, 'setup.py')
    
    if not os.path.exists(setup_path):
        print(f"ERROR: setup.py not found at {setup_path}")
        sys.exit(1)
    
    try:
        with open(setup_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract version using regex
        # Matches: version='X.Y.Z' or version="X.Y.Z"
        version_match = re.search(r'version\s*=\s*[\'"]([^\'"]+)[\'"]', content)
        
        if version_match:
            return version_match.group(1)
        else:
            print("ERROR: Could not find version in setup.py")
            sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to read setup.py: {e}")
        sys.exit(1)

def update_pubspec_yaml(version):
    """Update version in mobile/pubspec.yaml"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    pubspec_path = os.path.join(project_root, 'mobile', 'pubspec.yaml')
    
    if not os.path.exists(pubspec_path):
        print(f"ERROR: pubspec.yaml not found at {pubspec_path}")
        sys.exit(1)
    
    try:
        # Read current pubspec.yaml
        with open(pubspec_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract current version
        version_match = re.search(r'^version:\s*([^\s+]+)', content, re.MULTILINE)
        old_version = version_match.group(1) if version_match else 'unknown'
        
        # Parse version to get build number (if present)
        # Format: X.Y.Z+build or X.Y.Z
        version_parts = old_version.split('+')
        build_number = version_parts[1] if len(version_parts) > 1 else '1'
        
        # Update version line
        new_version_line = f"version: {version}+{build_number}"
        content = re.sub(
            r'^version:\s*[^\s+]+(?:\+\d+)?',
            new_version_line,
            content,
            flags=re.MULTILINE
        )
        
        # Write back to file
        with open(pubspec_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Updated mobile/pubspec.yaml version: {old_version} -> {new_version_line}")
        return True
    except Exception as e:
        print(f"ERROR: Failed to update pubspec.yaml: {e}")
        sys.exit(1)

def update_android_build_gradle(version):
    """Update version in mobile/android/local.properties (Flutter will use this)"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    local_properties_path = os.path.join(project_root, 'mobile', 'android', 'local.properties')
    
    # Parse version to get version code
    # Convert X.Y.Z to version code: X*10000 + Y*100 + Z
    try:
        parts = version.split('.')
        if len(parts) >= 3:
            major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
            version_code = major * 10000 + minor * 100 + patch
        elif len(parts) == 2:
            major, minor = int(parts[0]), int(parts[1])
            version_code = major * 10000 + minor * 100
        else:
            version_code = int(parts[0]) * 10000
    except ValueError:
        print(f"WARNING: Could not parse version {version}, using default version code")
        version_code = 1
    
    try:
        # Read existing local.properties or create new
        properties = {}
        if os.path.exists(local_properties_path):
            with open(local_properties_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        properties[key.strip()] = value.strip()
        
        # Update version properties
        old_version_code = properties.get('flutter.versionCode', 'unknown')
        old_version_name = properties.get('flutter.versionName', 'unknown')
        
        properties['flutter.versionCode'] = str(version_code)
        properties['flutter.versionName'] = version
        
        # Write back to file
        with open(local_properties_path, 'w', encoding='utf-8') as f:
            for key, value in properties.items():
                f.write(f"{key}={value}\n")
        
        print(f"Updated mobile/android/local.properties:")
        print(f"  versionCode: {old_version_code} -> {version_code}")
        print(f"  versionName: {old_version_name} -> {version}")
        return True
    except Exception as e:
        print(f"WARNING: Failed to update local.properties: {e}")
        print("This is not critical - Flutter will use pubspec.yaml version")
        return False

def main():
    """Main function"""
    print("Syncing version from setup.py to mobile app...")
    
    # Get version from setup.py
    version = get_version_from_setup()
    print(f"Found version in setup.py: {version}")
    
    # Update pubspec.yaml
    update_pubspec_yaml(version)
    
    # Update Android build configuration
    update_android_build_gradle(version)
    
    print("Version sync complete!")

if __name__ == '__main__':
    main()
