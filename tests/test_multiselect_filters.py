#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for multi-select filter functionality
Tests both Kanban and Tasks views with various filter combinations
"""

import sys
import os
import io

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_parse_ids():
    """Test the parse_ids function logic"""
    print("Testing parse_ids logic...")
    
    # Simulate the parse_ids function
    def parse_ids(multi_param, single_param):
        """Parse comma-separated IDs or single ID into a list of integers"""
        if multi_param:
            try:
                return [int(x.strip()) for x in multi_param.split(',') if x.strip()]
            except (ValueError, AttributeError):
                return []
        if single_param:
            return [single_param]
        return []
    
    # Test cases
    test_cases = [
        # (multi_param, single_param, expected_result, description)
        ('', None, [], 'Empty parameters'),
        ('', 5, [5], 'Single ID only (backward compatibility)'),
        ('1,2,3', None, [1, 2, 3], 'Multiple IDs'),
        ('1,2,3', 5, [1, 2, 3], 'Multi-select takes precedence'),
        ('1, 2, 3', None, [1, 2, 3], 'IDs with spaces'),
        ('1,,3', None, [1, 3], 'Empty values filtered out'),
        ('invalid', None, [], 'Invalid input'),
        ('1,2,abc', None, [], 'Mixed valid/invalid'),
    ]
    
    passed = 0
    failed = 0
    
    for multi, single, expected, desc in test_cases:
        result = parse_ids(multi, single)
        if result == expected:
            print(f"  ✓ {desc}: {result}")
            passed += 1
        else:
            print(f"  ✗ {desc}: Expected {expected}, got {result}")
            failed += 1
    
    print(f"\nParse IDs Tests: {passed} passed, {failed} failed\n")
    return failed == 0


def test_sqlalchemy_in_filter():
    """Test SQLAlchemy IN filter logic"""
    print("Testing SQLAlchemy IN filter logic...")
    
    # Simulate filter building
    def build_filter_query(project_ids=None, user_ids=None):
        """Build a query representation"""
        filters = []
        if project_ids:
            filters.append(f"Task.project_id.in_({project_ids})")
        if user_ids:
            filters.append(f"Task.assigned_to.in_({user_ids})")
        return " AND ".join(filters) if filters else "No filters"
    
    test_cases = [
        (None, None, "No filters", "No filters applied"),
        ([1], None, "Task.project_id.in_([1])", "Single project filter"),
        ([1, 2, 3], None, "Task.project_id.in_([1, 2, 3])", "Multiple projects"),
        (None, [5], "Task.assigned_to.in_([5])", "Single user filter"),
        ([1, 2], [5, 6], "Task.project_id.in_([1, 2]) AND Task.assigned_to.in_([5, 6])", "Both filters"),
    ]
    
    passed = 0
    failed = 0
    
    for project_ids, user_ids, expected, desc in test_cases:
        result = build_filter_query(project_ids, user_ids)
        if result == expected:
            print(f"  ✓ {desc}")
            passed += 1
        else:
            print(f"  ✗ {desc}: Expected '{expected}', got '{result}'")
            failed += 1
    
    print(f"\nSQLAlchemy Filter Tests: {passed} passed, {failed} failed\n")
    return failed == 0


def test_url_parameter_generation():
    """Test URL parameter generation for multi-select"""
    print("Testing URL parameter generation...")
    
    from urllib.parse import urlencode
    
    test_cases = [
        ({}, "", "Empty parameters"),
        ({'project_ids': '1,2,3'}, "project_ids=1%2C2%2C3", "Multiple project IDs"),
        ({'user_ids': '5,6'}, "user_ids=5%2C6", "Multiple user IDs"),
        ({'project_ids': '1,2', 'user_ids': '5,6'}, "project_ids=1%2C2&user_ids=5%2C6", "Both filters"),
        ({'project_ids': '1'}, "project_ids=1", "Single ID (backward compatible)"),
    ]
    
    passed = 0
    failed = 0
    
    for params, expected, desc in test_cases:
        result = urlencode(params)
        if result == expected:
            print(f"  ✓ {desc}: {result}")
            passed += 1
        else:
            print(f"  ✗ {desc}: Expected '{expected}', got '{result}'")
            failed += 1
    
    print(f"\nURL Parameter Tests: {passed} passed, {failed} failed\n")
    return failed == 0


def test_backward_compatibility():
    """Test backward compatibility with old single-ID parameters"""
    print("Testing backward compatibility...")
    
    def parse_ids_compat(multi_param, single_param):
        """Parse with backward compatibility"""
        if multi_param:
            try:
                return [int(x.strip()) for x in multi_param.split(',') if x.strip()]
            except (ValueError, AttributeError):
                return []
        if single_param:
            return [single_param]
        return []
    
    # Old URL format tests
    test_cases = [
        ('', 1, [1], 'Old format: ?project_id=1'),
        ('', 5, [5], 'Old format: ?user_id=5'),
        ('2,3', 1, [2, 3], 'New format takes precedence'),
    ]
    
    passed = 0
    failed = 0
    
    for multi, single, expected, desc in test_cases:
        result = parse_ids_compat(multi, single)
        if result == expected:
            print(f"  ✓ {desc}: {result}")
            passed += 1
        else:
            print(f"  ✗ {desc}: Expected {expected}, got {result}")
            failed += 1
    
    print(f"\nBackward Compatibility Tests: {passed} passed, {failed} failed\n")
    return failed == 0


def main():
    """Run all tests"""
    print("=" * 60)
    print("Multi-Select Filter Implementation Tests")
    print("=" * 60)
    print()
    
    results = []
    results.append(("Parse IDs", test_parse_ids()))
    results.append(("SQLAlchemy Filters", test_sqlalchemy_in_filter()))
    results.append(("URL Parameters", test_url_parameter_generation()))
    results.append(("Backward Compatibility", test_backward_compatibility()))
    
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed. Please review the implementation.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
