#!/usr/bin/env python3
"""
Simple Database Connection Test Script
This script tests database connectivity to help debug connection issues
"""

import os
import sys
import psycopg2
import sqlite3
from datetime import datetime


def test_postgresql_connection(db_url):
    """Test PostgreSQL connection"""
    print(f"Testing PostgreSQL connection: {db_url}")

    try:
        # Handle both postgresql:// and postgresql+psycopg2:// URLs
        clean_url = db_url.replace("+psycopg2://", "://")
        print(f"Cleaned URL: {clean_url}")

        # Test connection
        conn = psycopg2.connect(clean_url)
        cursor = conn.cursor()

        # Test basic query
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        print(f"✓ PostgreSQL connection successful")
        print(f"  Server version: {version}")

        # Test if we can access information_schema
        cursor.execute("SELECT current_database(), current_user")
        db_info = cursor.fetchone()
        print(f"  Database: {db_info[0]}")
        print(f"  User: {db_info[1]}")

        # Check if we can list tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        print(f"  Tables found: {len(tables)}")
        if tables:
            print(f"  Table names: {tables[:5]}{'...' if len(tables) > 5 else ''}")

        conn.close()
        return True

    except Exception as e:
        print(f"✗ PostgreSQL connection failed: {e}")
        return False


def test_sqlite_connection(db_url):
    """Test SQLite connection"""
    print(f"Testing SQLite connection: {db_url}")

    try:
        db_file = db_url.replace("sqlite:///", "")
        print(f"Database file: {db_file}")

        if not os.path.exists(db_file):
            print(f"  Database file does not exist, checking if directory is writable...")
            dir_path = os.path.dirname(db_file) if os.path.dirname(db_file) else "."
            if os.access(dir_path, os.W_OK):
                print(f"  ✓ Directory is writable: {dir_path}")
                return True
            else:
                print(f"  ✗ Directory is not writable: {dir_path}")
                return False

        # Test connection
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        # Test basic query
        cursor.execute("SELECT sqlite_version()")
        version = cursor.fetchone()[0]
        print(f"✓ SQLite connection successful")
        print(f"  SQLite version: {version}")

        # Check if we can list tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"  Tables found: {len(tables)}")
        if tables:
            print(f"  Table names: {tables[:5]}{'...' if len(tables) > 5 else ''}")

        conn.close()
        return True

    except Exception as e:
        print(f"✗ SQLite connection failed: {e}")
        return False


def main():
    """Main function"""
    print("=== Database Connection Test ===")
    print(f"Timestamp: {datetime.now()}")
    print()

    # Get database URL from environment
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("✗ DATABASE_URL environment variable not set")
        print("Please set DATABASE_URL to test database connection")
        sys.exit(1)

    print(f"Database URL: {db_url}")
    print()

    # Test connection based on database type
    success = False

    if db_url.startswith("postgresql"):
        success = test_postgresql_connection(db_url)
    elif db_url.startswith("sqlite"):
        success = test_sqlite_connection(db_url)
    else:
        print(f"✗ Unknown database type: {db_url}")
        print("Supported types: postgresql://, sqlite://")
        sys.exit(1)

    print()
    if success:
        print("🎉 Database connection test successful!")
        sys.exit(0)
    else:
        print("❌ Database connection test failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
