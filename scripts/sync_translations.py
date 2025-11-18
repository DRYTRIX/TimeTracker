#!/usr/bin/env python3
"""
Script to sync translation files by adding missing msgid entries from English
to all other language files. This ensures all languages have the same structure.

Uses Babel's library for reliable .po file parsing.
"""

import os
import sys
from pathlib import Path

try:
    from babel.messages.pofile import read_po, write_po
    from babel.messages.catalog import Message
except ImportError:
    print("Error: Babel library not found. Please install it with: pip install Babel")
    sys.exit(1)


def read_po_catalog(filepath):
    """Read a .po file and return the catalog."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return read_po(f)


def sync_translations():
    """Sync all translation files with English as the reference."""
    translations_dir = Path('translations')
    en_file = translations_dir / 'en' / 'LC_MESSAGES' / 'messages.po'
    
    if not en_file.exists():
        print(f"Error: English translation file not found at {en_file}")
        return
    
    print("Reading English translation file...")
    en_catalog = read_po_catalog(en_file)
    
    print(f"Found {len(en_catalog)} entries in English file")
    
    # Languages to update (excluding English)
    languages = ['de', 'nl', 'fr', 'it', 'fi', 'es', 'ar', 'he', 'nb', 'no']
    
    for lang in languages:
        lang_file = translations_dir / lang / 'LC_MESSAGES' / 'messages.po'
        
        if not lang_file.exists():
            print(f"Warning: {lang} translation file not found, skipping...")
            continue
        
        print(f"\nProcessing {lang}...")
        lang_catalog = read_po_catalog(lang_file)
        
        # Add missing entries from English
        added = 0
        for message in en_catalog:
            if message.id and message.id not in lang_catalog:
                # Create new message with empty translation
                new_msg = Message(message.id, '', context=message.context)
                lang_catalog[message.id] = new_msg
                added += 1
        
        if added > 0:
            print(f"  Added {added} missing entries")
            # Backup original
            backup_file = lang_file.with_suffix('.po.bak')
            if backup_file.exists():
                backup_file.unlink()
            lang_file.rename(backup_file)
            
            # Write updated file
            with open(lang_file, 'wb') as f:
                write_po(f, lang_catalog, width=79)
            print(f"  Updated {lang_file}")
            print(f"  Backup saved to {backup_file}")
        else:
            print(f"  No missing entries, already up to date")
    
    print("\nSync complete!")


if __name__ == '__main__':
    sync_translations()

