#!/usr/bin/env python3
"""
Audit script to find untranslated strings in templates and Python files.

This script scans through templates and routes to identify:
1. Hardcoded English strings in templates
2. Flash messages without translation markers
3. Form labels without translation
4. Validation messages without translation
"""

import os
import re
from pathlib import Path


def find_untranslated_in_templates(base_dir='app/templates'):
    """Find potential untranslated strings in templates"""
    issues = []
    template_files = Path(base_dir).rglob('*.html')
    
    # Patterns that suggest untranslated content
    patterns = [
        # Buttons and links with hardcoded text
        (r'<button[^>]*>([A-Z][a-z]+ [A-Z][a-z]+.*?)</button>', 'button text'),
        (r'<a[^>]*>([A-Z][a-z]{3,}.*?)</a>', 'link text'),
        
        # Headers with English text
        (r'<h[1-6][^>]*>([A-Z][a-z]{3,}.*?)</h[1-6]>', 'header text'),
        
        # Labels
        (r'<label[^>]*>([A-Z][a-z]{3,}.*?):</label>', 'label text'),
        
        # Placeholders
        (r'placeholder="([A-Z][^"]{3,})"', 'placeholder'),
        
        # Title attributes
        (r'title="([A-Z][^"]{3,})"', 'title attribute'),
        
        # Alt text
        (r'alt="([A-Z][^"]{3,})"', 'alt text'),
    ]
    
    for template_file in template_files:
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Skip if file already uses translations heavily
                if content.count('{{') > 10 and content.count('_(') / max(len(content), 1) * 1000 > 1:
                    continue
                
                for pattern, desc in patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        text = match.group(1).strip()
                        # Skip if already translated
                        if '{{' in text or '{%' in text or '_(' in text:
                            continue
                        # Skip if it's a variable
                        if text.startswith('{{') or text.startswith('{%'):
                            continue
                        # Skip short strings or single words
                        if len(text) < 4 or len(text.split()) < 2:
                            continue
                            
                        issues.append({
                            'file': str(template_file),
                            'type': desc,
                            'text': text,
                            'line': content[:match.start()].count('\n') + 1
                        })
        except Exception as e:
            print(f"Error processing {template_file}: {e}")
    
    return issues


def find_untranslated_flash_messages(base_dir='app/routes'):
    """Find flash messages without translation markers"""
    issues = []
    route_files = Path(base_dir).rglob('*.py')
    
    # Pattern for flash messages
    flash_pattern = r'flash\(["\']([^"\']+)["\']\s*(?:,\s*["\'][^"\']+["\'])?\)'
    
    for route_file in route_files:
        try:
            with open(route_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                matches = re.finditer(flash_pattern, content)
                for match in matches:
                    message = match.group(1)
                    # Check if it's already wrapped with _()
                    start_pos = match.start()
                    preceding = content[max(0, start_pos-20):start_pos]
                    if '_(' not in preceding:
                        issues.append({
                            'file': str(route_file),
                            'type': 'flash message',
                            'text': message,
                            'line': content[:match.start()].count('\n') + 1
                        })
        except Exception as e:
            print(f"Error processing {route_file}: {e}")
    
    return issues


def generate_report(issues, output_file='i18n_audit_report.md'):
    """Generate a markdown report of i18n issues"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Internationalization Audit Report\n\n")
        f.write(f"Total issues found: {len(issues)}\n\n")
        
        # Group by file
        by_file = {}
        for issue in issues:
            file = issue['file']
            if file not in by_file:
                by_file[file] = []
            by_file[file].append(issue)
        
        f.write(f"## Files with Issues: {len(by_file)}\n\n")
        
        for file, file_issues in sorted(by_file.items()):
            f.write(f"### {file}\n\n")
            f.write(f"Issues: {len(file_issues)}\n\n")
            
            for issue in file_issues:
                f.write(f"- **Line {issue['line']}** ({issue['type']}): `{issue['text']}`\n")
            
            f.write("\n")
        
        # Summary by type
        f.write("## Summary by Type\n\n")
        by_type = {}
        for issue in issues:
            issue_type = issue['type']
            if issue_type not in by_type:
                by_type[issue_type] = 0
            by_type[issue_type] += 1
        
        for issue_type, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
            f.write(f"- {issue_type}: {count}\n")


def main():
    print("Starting i18n audit...")
    
    print("\n1. Scanning templates for untranslated strings...")
    template_issues = find_untranslated_in_templates()
    print(f"   Found {len(template_issues)} potential issues in templates")
    
    print("\n2. Scanning routes for untranslated flash messages...")
    flash_issues = find_untranslated_flash_messages()
    print(f"   Found {len(flash_issues)} untranslated flash messages")
    
    all_issues = template_issues + flash_issues
    
    print(f"\n3. Generating report...")
    generate_report(all_issues)
    print(f"   Report saved to: i18n_audit_report.md")
    
    print(f"\n✅ Audit complete! Total issues: {len(all_issues)}")
    
    # Print top 10 most common issues
    if all_issues:
        print("\nTop issues to address:")
        for i, issue in enumerate(all_issues[:10], 1):
            print(f"{i}. {issue['file']}:{issue['line']} - {issue['text'][:50]}...")


if __name__ == '__main__':
    main()

