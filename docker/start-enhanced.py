#!/usr/bin/env python3
"""
Enhanced Python startup script for TimeTracker
This script ensures proper database initialization with enhanced schema verification
"""

import os
import sys
import time
import subprocess
import traceback

def wait_for_database():
    """Wait for database to be ready"""
    print("Waiting for database to be ready...")
    time.sleep(5)  # Simple wait for now
    
def run_script(script_path, description):
    """Run a Python script with proper error handling"""
    print(f"Running {description}...")
    try:
        result = subprocess.run(
            [sys.executable, script_path], 
            check=True,
            capture_output=True,
            text=True
        )
        print(f"✓ {description} completed successfully")
        if result.stdout:
            print(f"Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed with exit code {e.returncode}")
        if e.stdout:
            print(f"stdout: {e.stdout}")
        if e.stderr:
            print(f"stderr: {e.stderr}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error running {description}: {e}")
        traceback.print_exc()
        return False

def display_network_info():
    """Display network information for debugging"""
    print("=== Network Information ===")
    print(f"Hostname: {os.uname().nodename}")
    # Use subprocess.run instead of os.popen to avoid command injection
    try:
        result = subprocess.run(['hostname', '-I'], capture_output=True, text=True, check=False)
        ip_address = result.stdout.strip() if result.returncode == 0 else "N/A"
    except Exception:
        ip_address = "N/A"
    print(f"IP Address: {ip_address}")
    print(f"Environment: {os.environ.get('FLASK_APP', 'N/A')}")
    print(f"Working Directory: {os.getcwd()}")
    print("==========================")

def main():
    print("=== Starting TimeTracker (Enhanced Mode) ===")
    
    # Display network information for debugging
    display_network_info()
    
    # Set environment
    os.environ['FLASK_APP'] = 'app'
    os.chdir('/app')
    
    # Wait for database
    wait_for_database()
    
    # Run enhanced database initialization (handles everything in one script)
    if not run_script('/app/docker/init-database-enhanced.py', 'Enhanced database initialization'):
        print("Enhanced database initialization failed, exiting...")
        sys.exit(1)
    
    print("✓ All database initialization completed successfully")
    
    print("Starting application...")
    # Start gunicorn
    os.execv('/usr/local/bin/gunicorn', [
        'gunicorn',
        '--bind', '0.0.0.0:8080',
        '--worker-class', 'eventlet',
        '--workers', '1',
        '--timeout', '120',
        'app:create_app()'
    ])

if __name__ == '__main__':
    main()
