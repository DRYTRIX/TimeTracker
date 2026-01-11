#!/usr/bin/env python3
"""
Sync version from setup.py to desktop/package.json
This ensures the Electron app uses the same version as the main application.
"""

import os
import sys
import json
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

def update_package_json(version):
    """Update version in desktop/package.json"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    package_json_path = os.path.join(project_root, 'desktop', 'package.json')
    
    if not os.path.exists(package_json_path):
        print(f"ERROR: package.json not found at {package_json_path}")
        sys.exit(1)
    
    try:
        # Read current package.json
        with open(package_json_path, 'r', encoding='utf-8') as f:
            package_data = json.load(f)
        
        old_version = package_data.get('version', 'unknown')
        
        # Update version
        package_data['version'] = version
        
        # Write back to file with proper formatting
        with open(package_json_path, 'w', encoding='utf-8') as f:
            json.dump(package_data, f, indent=2, ensure_ascii=False)
            f.write('\n')  # Add trailing newline
        
        print(f"Updated desktop/package.json version: {old_version} -> {version}")
        return True
    except Exception as e:
        print(f"ERROR: Failed to update package.json: {e}")
        sys.exit(1)

def main():
    """Main function"""
    print("Syncing version from setup.py to desktop/package.json...")
    
    # Get version from setup.py
    version = get_version_from_setup()
    print(f"Found version in setup.py: {version}")
    
    # Update package.json
    update_package_json(version)
    
    print("Version sync complete!")

if __name__ == '__main__':
    main()
