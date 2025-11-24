#!/usr/bin/env python3
"""
Script to fix placeholder names in translation files.
Preserves original English placeholder names (like %(error)s) in all translations.
"""

import sys
import re
from pathlib import Path

try:
    from babel.messages.pofile import read_po, write_po
except ImportError:
    print("Error: Babel library not found. Please install it with: pip install Babel")
    sys.exit(1)


def extract_placeholders_from_msgid(msgid):
    """Extract placeholder names from msgid (English text)."""
    if not msgid:
        return []
    # Find all %(name)s or %(name)d style placeholders
    pattern = r'%\(([^)]+)\)[sd]'
    return re.findall(pattern, msgid)


def fix_placeholders_in_msgstr(msgstr, original_placeholders):
    """Fix placeholder names in msgstr to match original English names."""
    if not msgstr or not original_placeholders:
        return msgstr
    
    # Find all placeholders in the translated string (including format specifiers like .2f)
    pattern = r'%\(([^)]+)\)([.0-9]*[sd]|[.0-9]*f)'
    matches = re.findall(pattern, msgstr)
    
    fixed_msgstr = msgstr
    
    # If we have the same number of placeholders, match by position
    if len(matches) == len(original_placeholders):
        for (translated_name, format_spec), original_name in zip(matches, original_placeholders):
            if translated_name != original_name:
                # Replace the translated placeholder name with the original
                fixed_msgstr = re.sub(
                    r'%\(' + re.escape(translated_name) + r'\)' + re.escape(format_spec),
                    r'%(' + original_name + r')' + format_spec,
                    fixed_msgstr
                )
    else:
        # If different counts, try to find and replace any translated placeholder
        # by searching for common translations and replacing with originals
        for original_name in original_placeholders:
            # Common translations that might have been used
            # This is a fallback - try to replace any placeholder that looks like it might be a translation
            # We'll be conservative and only replace if we find an exact match pattern
            pass
    
    return fixed_msgstr


def fix_translation_file(po_file):
    """Fix placeholder names in a single translation file."""
    print(f"Processing {po_file}...")
    
    with open(po_file, 'r', encoding='utf-8') as f:
        catalog = read_po(f)
    
    fixed_count = 0
    
    for message in catalog:
        if message.id and message.string:
            # Extract original placeholders from msgid
            original_placeholders = extract_placeholders_from_msgid(message.id)
            
            if original_placeholders:
                # Fix msgstr if it's a string
                if isinstance(message.string, str):
                    fixed = fix_placeholders_in_msgstr(message.string, original_placeholders)
                    if fixed != message.string:
                        message.string = fixed
                        fixed_count += 1
                # Fix msgstr if it's a tuple (plural forms)
                elif isinstance(message.string, tuple):
                    fixed_tuple = []
                    for msgstr_item in message.string:
                        fixed = fix_placeholders_in_msgstr(msgstr_item, original_placeholders)
                        fixed_tuple.append(fixed)
                    if fixed_tuple != list(message.string):
                        message.string = tuple(fixed_tuple)
                        fixed_count += 1
    
    if fixed_count > 0:
        # Backup original
        backup_file = po_file.with_suffix('.po.bak2')
        if backup_file.exists():
            backup_file.unlink()
        po_file.rename(backup_file)
        print(f"  Backup created: {backup_file}")
        
        # Write fixed file
        with open(po_file, 'wb') as f:
            write_po(f, catalog, width=79)
        print(f"  Fixed {fixed_count} entries in {po_file}")
        return True
    else:
        print(f"  No fixes needed in {po_file}")
        return False


def main():
    """Fix placeholder names in all translation files."""
    translations_dir = Path('translations')
    languages = ['nl', 'de', 'fr', 'it', 'fi', 'es', 'ar', 'he', 'nb', 'no']
    
    print("="*60)
    print("Fixing Placeholder Names in Translation Files")
    print("="*60)
    print("\nThis script will preserve original English placeholder names")
    print("(like %(error)s) in all translations.\n")
    
    fixed_files = []
    for lang in languages:
        po_file = translations_dir / lang / 'LC_MESSAGES' / 'messages.po'
        if po_file.exists():
            if fix_translation_file(po_file):
                fixed_files.append(lang)
        else:
            print(f"Warning: {po_file} not found, skipping...")
    
    if fixed_files:
        print(f"\n✓ Fixed placeholder names in {len(fixed_files)} files: {', '.join(fixed_files)}")
        print("\nNext step: Compile translations with: pybabel compile -d translations")
    else:
        print("\n✓ No placeholder fixes needed")


if __name__ == '__main__':
    main()

