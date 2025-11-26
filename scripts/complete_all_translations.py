#!/usr/bin/env python3
"""
Script to automatically complete all translations for all languages.
Uses deep-translator library for automatic translation of missing strings.
"""

import sys
from pathlib import Path

try:
    from babel.messages.pofile import read_po, write_po
    from babel.messages.catalog import Message
except ImportError:
    print("Error: Babel library not found. Please install it with: pip install Babel")
    sys.exit(1)

try:
    from deep_translator import GoogleTranslator
except ImportError:
    print("Error: deep-translator not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "deep-translator"])
    from deep_translator import GoogleTranslator


# Language mapping for deep-translator
LANGUAGE_MAP = {
    'nl': 'nl',  # Dutch
    'de': 'de',  # German
    'fr': 'fr',  # French
    'it': 'it',  # Italian
    'fi': 'fi',  # Finnish
    'es': 'es',  # Spanish
    'ar': 'ar',  # Arabic
    'he': 'iw',  # Hebrew (deep-translator uses 'iw')
    'nb': 'no',  # Norwegian Bokmål
    'no': 'no',  # Norwegian
}


def translate_text(text, target_lang):
    """Translate text to target language using Google Translator."""
    if not text or not text.strip():
        return ""
    
    try:
        translator = GoogleTranslator(source='en', target=target_lang)
        translated = translator.translate(text)
        return translated
    except Exception as e:
        print(f"  Warning: Translation failed for '{text[:50]}...': {e}")
        return ""


def complete_translations_for_language(lang_code):
    """Complete all missing translations for a specific language."""
    translations_dir = Path('translations')
    lang_file = translations_dir / lang_code / 'LC_MESSAGES' / 'messages.po'
    
    if not lang_file.exists():
        print(f"Error: Translation file not found: {lang_file}")
        return False
    
    if lang_code not in LANGUAGE_MAP:
        print(f"Warning: Language {lang_code} not in language map, skipping...")
        return False
    
    target_lang = LANGUAGE_MAP[lang_code]
    
    print(f"\n{'='*60}")
    print(f"Processing {lang_code.upper()} translations...")
    print(f"{'='*60}")
    
    # Read the PO file
    with open(lang_file, 'r', encoding='utf-8') as f:
        catalog = read_po(f)
    
    print(f"Found {len(catalog)} entries in catalog")
    
    # Find untranslated entries
    untranslated = []
    for message in catalog:
        if message.id:
            is_empty = False
            if isinstance(message.string, tuple):
                # Plural form
                is_empty = not message.string or all(not s for s in message.string)
            else:
                # Singular form
                is_empty = not message.string or message.string == ""
            
            if is_empty:
                untranslated.append(message)
    
    print(f"Found {len(untranslated)} untranslated entries")
    
    if len(untranslated) == 0:
        print(f"✓ All {lang_code.upper()} translations are complete!")
        return True
    
    # Translate entries
    translated_count = 0
    failed_count = 0
    
    print(f"\nTranslating {len(untranslated)} entries...")
    print("(This may take a while due to API rate limits)")
    
    for i, message in enumerate(untranslated, 1):
        if i % 50 == 0:
            print(f"  Progress: {i}/{len(untranslated)} entries processed...")
        
        translation = translate_text(message.id, target_lang)
        
        if translation:
            if isinstance(message.string, tuple):
                # Plural form - set first form, keep others empty for now
                message.string = (translation, message.string[1] if len(message.string) > 1 else "")
            else:
                message.string = translation
            translated_count += 1
        else:
            failed_count += 1
    
    print(f"\n✓ Translated: {translated_count} entries")
    if failed_count > 0:
        print(f"⚠ Failed: {failed_count} entries")
    
    if translated_count > 0:
        # Backup original
        backup_file = lang_file.with_suffix('.po.bak')
        if backup_file.exists():
            backup_file.unlink()
        lang_file.rename(backup_file)
        print(f"  Backup created: {backup_file}")
        
        # Write updated file
        with open(lang_file, 'wb') as f:
            write_po(f, catalog, width=79)
        print(f"  Updated: {lang_file}")
        
        return True
    else:
        print("  No translations applied")
        return False


def main():
    """Complete translations for all languages."""
    languages = ['nl', 'de', 'fr', 'it', 'fi', 'es', 'ar', 'he', 'nb', 'no']
    
    print("="*60)
    print("Automatic Translation Completion Script")
    print("="*60)
    print("\nThis script will translate all missing strings using Google Translate.")
    print("Note: This may take a while and is subject to API rate limits.")
    print("\nLanguages to process:", ", ".join(languages))
    
    response = input("\nDo you want to continue? (yes/no): ")
    if response.lower() != 'yes':
        print("Translation cancelled.")
        return
    
    results = {}
    for lang in languages:
        try:
            success = complete_translations_for_language(lang)
            results[lang] = success
        except Exception as e:
            print(f"\n✗ Error processing {lang}: {e}")
            results[lang] = False
    
    # Summary
    print("\n" + "="*60)
    print("Translation Summary")
    print("="*60)
    for lang, success in results.items():
        status = "✓ Complete" if success else "✗ Failed"
        print(f"{lang.upper():3s}: {status}")
    
    print("\nNext steps:")
    print("1. Review the translations (they are machine-translated)")
    print("2. Compile translations: pybabel compile -d translations")
    print("3. Test the application in different languages")


if __name__ == '__main__':
    main()

