#!/usr/bin/env python3
"""
Quick Wins Features - Validation Test Script

This script validates that all new features can be imported
and basic functionality works without errors.
"""

import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_imports():
    """Test that all new modules can be imported"""
    print("🔍 Testing imports...")

    try:
        # Test model imports
        from app.models import Activity, SavedFilter, TimeEntryTemplate, User

        print("✅ Models imported successfully")

        # Test route imports
        from app.routes.saved_filters import saved_filters_bp
        from app.routes.time_entry_templates import time_entry_templates_bp
        from app.routes.user import user_bp

        print("✅ Routes imported successfully")

        # Test utility imports
        from app.utils.email import init_mail, mail, send_email
        from app.utils.excel_export import create_project_report_excel, create_time_entries_excel
        from app.utils.scheduled_tasks import check_overdue_invoices, register_scheduled_tasks, scheduler

        print("✅ Utilities imported successfully")

        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_model_attributes():
    """Test that models have expected attributes"""
    print("\n🔍 Testing model attributes...")

    try:
        from app.models import Activity, SavedFilter, TimeEntryTemplate, User

        # Test TimeEntryTemplate attributes
        template_attrs = [
            "id",
            "user_id",
            "name",
            "project_id",
            "task_id",
            "default_duration_minutes",
            "default_notes",
            "tags",
            "usage_count",
            "last_used_at",
        ]
        for attr in template_attrs:
            assert hasattr(TimeEntryTemplate, attr), f"TimeEntryTemplate missing {attr}"
        print("✅ TimeEntryTemplate has all attributes")

        # Test Activity attributes
        activity_attrs = [
            "id",
            "user_id",
            "action",
            "entity_type",
            "entity_id",
            "description",
            "metadata",
            "created_at",
        ]
        for attr in activity_attrs:
            assert hasattr(Activity, attr), f"Activity missing {attr}"
        print("✅ Activity has all attributes")

        # Test SavedFilter attributes
        filter_attrs = ["id", "user_id", "name", "scope", "payload", "is_shared", "created_at", "updated_at"]
        for attr in filter_attrs:
            assert hasattr(SavedFilter, attr), f"SavedFilter missing {attr}"
        print("✅ SavedFilter has all attributes")

        # Test User new attributes
        user_new_attrs = [
            "email_notifications",
            "notification_overdue_invoices",
            "notification_task_assigned",
            "notification_task_comments",
            "notification_weekly_summary",
            "timezone",
            "date_format",
            "time_format",
            "week_start_day",
        ]
        for attr in user_new_attrs:
            assert hasattr(User, attr), f"User missing new attribute {attr}"
        print("✅ User has all new preference attributes")

        return True
    except AssertionError as e:
        print(f"❌ Attribute test failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_model_methods():
    """Test that models have expected methods"""
    print("\n🔍 Testing model methods...")

    try:
        from app.models import Activity, TimeEntryTemplate

        # Test TimeEntryTemplate methods
        template_methods = ["to_dict", "record_usage", "increment_usage"]
        for method in template_methods:
            assert hasattr(TimeEntryTemplate, method), f"TimeEntryTemplate missing {method}"
        print("✅ TimeEntryTemplate has all methods")

        # Test Activity methods
        activity_methods = ["log", "get_recent", "to_dict"]
        for method in activity_methods:
            assert hasattr(Activity, method), f"Activity missing {method}"
        print("✅ Activity has all methods")

        return True
    except AssertionError as e:
        print(f"❌ Method test failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_blueprint_registration():
    """Test that blueprints are properly configured"""
    print("\n🔍 Testing blueprint registration...")

    try:
        from app.routes.saved_filters import saved_filters_bp
        from app.routes.time_entry_templates import time_entry_templates_bp
        from app.routes.user import user_bp

        # Check blueprint names
        assert user_bp.name == "user", "user_bp has wrong name"
        assert time_entry_templates_bp.name == "time_entry_templates", "time_entry_templates_bp has wrong name"
        assert saved_filters_bp.name == "saved_filters", "saved_filters_bp has wrong name"
        print("✅ All blueprints properly configured")

        return True
    except AssertionError as e:
        print(f"❌ Blueprint test failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_utility_functions():
    """Test that utility functions exist"""
    print("\n🔍 Testing utility functions...")

    try:
        from app.utils.email import init_mail, send_email
        from app.utils.excel_export import create_project_report_excel, create_time_entries_excel
        from app.utils.scheduled_tasks import check_overdue_invoices, register_scheduled_tasks

        # Check that functions are callable
        assert callable(init_mail), "init_mail is not callable"
        assert callable(send_email), "send_email is not callable"
        assert callable(create_time_entries_excel), "create_time_entries_excel is not callable"
        assert callable(create_project_report_excel), "create_project_report_excel is not callable"
        assert callable(register_scheduled_tasks), "register_scheduled_tasks is not callable"
        assert callable(check_overdue_invoices), "check_overdue_invoices is not callable"
        print("✅ All utility functions are callable")

        return True
    except AssertionError as e:
        print(f"❌ Utility function test failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_template_files():
    """Test that template files exist"""
    print("\n🔍 Testing template files...")

    template_files = [
        "app/templates/user/settings.html",
        "app/templates/user/profile.html",
        "app/templates/email/overdue_invoice.html",
        "app/templates/email/task_assigned.html",
        "app/templates/email/weekly_summary.html",
        "app/templates/email/comment_mention.html",
        "app/templates/time_entry_templates/list.html",
        "app/templates/time_entry_templates/create.html",
        "app/templates/time_entry_templates/edit.html",
        "app/templates/saved_filters/list.html",
        "app/templates/components/save_filter_widget.html",
        "app/templates/components/bulk_actions_widget.html",
        "app/templates/components/keyboard_shortcuts_help.html",
    ]

    missing = []
    for template in template_files:
        if not os.path.exists(template):
            missing.append(template)

    if missing:
        print(f"❌ Missing templates: {', '.join(missing)}")
        return False
    else:
        print(f"✅ All {len(template_files)} template files exist")
        return True


def test_migration_file():
    """Test that migration file exists and has correct structure"""
    print("\n🔍 Testing migration file...")

    migration_file = "migrations/versions/add_quick_wins_features.py"

    if not os.path.exists(migration_file):
        print(f"❌ Migration file not found: {migration_file}")
        return False

    try:
        with open(migration_file, "r") as f:
            content = f.read()

        # Check for required elements
        required = [
            "revision = '022'",
            "down_revision = '021'",
            "def upgrade():",
            "def downgrade():",
            "time_entry_templates",
            "activities",
        ]

        for req in required:
            if req not in content:
                print(f"❌ Migration missing required element: {req}")
                return False

        print("✅ Migration file is valid")
        return True
    except Exception as e:
        print(f"❌ Error reading migration file: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("🚀 Quick Wins Features - Validation Test")
    print("=" * 60)

    tests = [
        ("Imports", test_imports),
        ("Model Attributes", test_model_attributes),
        ("Model Methods", test_model_methods),
        ("Blueprint Registration", test_blueprint_registration),
        ("Utility Functions", test_utility_functions),
        ("Template Files", test_template_files),
        ("Migration File", test_migration_file),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print("=" * 60)
    print(f"Results: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    print("=" * 60)

    if passed == total:
        print("\n🎉 All tests passed! Ready for deployment.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please fix before deployment.")
        return 1


if __name__ == "__main__":
    exit(main())
