# Translation System Documentation

## Overview

TimeTracker includes a comprehensive internationalization (i18n) system powered by Flask-Babel. Enabled locales are defined in `app/config.py` (`LANGUAGES`), for example:

- **English** (en) - Default
- **Dutch** (nl - Nederlands)
- **German** (de - Deutsch)
- **French** (fr - Français)
- **Italian** (it - Italiano)
- **Finnish** (fi - Suomi)
- **Portuguese** (pt - Português)
- **Spanish** (es), **Norwegian** (no), **Arabic** (ar), **Hebrew** (he), and others as configured

Regional Portuguese tags (`pt-BR`, `pt-PT`, etc.) are normalized to **`pt`** so a single catalog under `translations/pt/` is used.

## User Experience

### Language Switcher

The language switcher is located in the top navigation bar, positioned between the command palette button and the user profile menu. It features:

- 🌐 Globe icon for easy recognition
- Current language label (on larger screens)
- Dropdown menu with all available languages
- Visual indicator (checkmark) for the currently selected language
- Smooth hover transitions and animations

### Language Selection

Users can change the interface language in two ways:

1. **Via Navigation Bar**: Click the globe icon and select a language from the dropdown
2. **Direct URL**: Visit `/i18n/set-language?lang=<code>` (e.g., `?lang=de` for German)

Language preference is persisted:
- **For authenticated users**: Saved to user profile in database
- **For guests**: Stored in session

## Technical Details

### Translation Files

Translation files are located in `translations/` directory (see `app/config.py` for the full list of enabled locales; additional `.po` files may exist for locales not yet wired in config).

```
translations/
├── en/LC_MESSAGES/messages.po   # English
├── nl/LC_MESSAGES/messages.po   # Dutch
├── de/LC_MESSAGES/messages.po   # German
├── fr/LC_MESSAGES/messages.po   # French
├── it/LC_MESSAGES/messages.po   # Italian
├── fi/LC_MESSAGES/messages.po   # Finnish
├── es/LC_MESSAGES/messages.po   # Spanish
├── pt/LC_MESSAGES/messages.po   # Portuguese
└── ...                          # Other locales as configured
```

### Configuration

Language configuration is defined in `app/config.py`:

```python
LANGUAGES = {
    'en': 'English',
    'nl': 'Nederlands',
    'de': 'Deutsch',
    'fr': 'Français',
    'it': 'Italiano',
    'fi': 'Suomi',
    'pt': 'Português',
    # ... es, no, ar, he, etc. — see app/config.py for the full map
}
BABEL_DEFAULT_LOCALE = 'en'
```

### Locale Selection Priority

The system determines the user's language in the following order:

1. **User preference from database** (for authenticated users)
2. **Session override** (via set-language route)
3. **Browser Accept-Language header** (best match)
4. **Default locale** (en)

The locale normalizer maps **`no` → `nb`** (Norwegian catalog folder) and folds **`pt-*`** (e.g. `pt-BR`, `pt-PT`) to **`pt`**.

See `app/__init__.py` for the locale selector implementation.

### In Templates

Use the `_()` function to mark strings for translation:

```html
<h1>{{ _('Welcome to TimeTracker') }}</h1>
<button>{{ _('Start Timer') }}</button>
```

For strings with variables, use named parameters:

```html
<p>{{ _('%(app)s is a web-based time tracking application', app='TimeTracker') }}</p>
```

### In Python Code

Import and use the translation function:

```python
from flask_babel import _

message = _('Timer started successfully')
flash(_('Project created'), 'success')
```

## Translation Compilation

Translation files (`.po`) are automatically compiled to binary files (`.mo`) when the application starts. The compilation is handled by `app/utils/i18n.py` which:

1. Checks if `.mo` files exist and are up-to-date
2. Compiles `.po` to `.mo` using Babel's message tools
3. Runs automatically during application initialization

## Adding a New Language

To add a new language:

1. **Add to configuration** in `app/config.py`:
   ```python
   LANGUAGES = {
       # ... existing languages ...
       'es': 'Español',  # Add Spanish
   }
   ```

2. **Create translation directory**:
   ```bash
   mkdir -p translations/es/LC_MESSAGES
   ```

3. **Initialize translation file**:
   ```bash
   pybabel init -i messages.pot -d translations -l es
   ```

4. **Translate the strings** in `translations/es/LC_MESSAGES/messages.po`

5. **Restart the application** - translations will compile automatically

## Updating Translations

When you add new translatable strings to the application:

1. Use a virtualenv with project dependencies (at least **Babel** and **Jinja2**) so `pybabel` can scan templates.

2. **Extract messages** (writes `messages.pot` at the repo root; it is gitignored):
   ```bash
   pybabel extract -F babel.cfg -o messages.pot .
   ```

   `babel.cfg` defines a `[extractors]` alias so the **jinja2** method resolves to `jinja2.ext:babel_extract` (needed on some Python/setuptools setups where the `babel.extractors` entry point is not visible).

3. **Update all translation files**:
   ```bash
   pybabel update -i messages.pot -d translations --no-wrap
   ```

   To drop obsolete entries after a large refactor:
   ```bash
   pybabel update -i messages.pot -d translations --ignore-obsolete --no-wrap
   ```

4. **Translate new strings** in each `.po` file (human review, [Crowdin](https://crowdin.com/project/drytrix-timetracker), or a local helper).

   For a **first-pass Portuguese fill** using offline Argos models (machine quality; always review):
   ```bash
   pip install polib argostranslate
   python -c "import argostranslate.package as p; p.update_package_index(); pkg=next(x for x in p.get_available_packages() if x.from_code=='en' and x.to_code=='pt'); p.install_from_path(pkg.download())"
   python scripts/fill_po_argos.py translations/pt/LC_MESSAGES/messages.po --from en --to pt
   ```

   Machine translators often break `%(name)s` / `{name}` placeholders. Run **`python scripts/sanitize_po_format_strings.py translations/pt/LC_MESSAGES/messages.po`** afterward, then **`msgfmt --check-format -o /dev/null …/messages.po`** to confirm the catalog is safe for Python’s `%` / `.format()` at runtime.

5. **Restart application** (or set `TT_COMPILE_TRANSLATIONS_ON_STARTUP=true`) so `.mo` files are compiled when needed

## Translation File Format

Translation files use the PO (Portable Object) format:

```po
# Comment
msgid "Original English text"
msgstr "Translated text"

# With context
msgid "Dashboard"
msgstr "Tableau de bord"  # French

# Plurals
msgid "1 hour"
msgid_plural "%d hours"
msgstr[0] "1 heure"
msgstr[1] "%d heures"
```

## Best Practices

1. **Keep strings short and contextual**
   - Good: `_('Save')`
   - Avoid: `_('Click this button to save your changes to the database')`

2. **Use sentence case**
   - Good: `_('Start timer')`
   - Avoid: `_('START TIMER')`

3. **Avoid concatenation**
   - Good: `_('Welcome back, %(name)s', name=user.name)`
   - Avoid: `_('Welcome back,') + ' ' + user.name`

4. **Provide context in comments**
   ```python
   # Translators: This is the button to start the time tracking timer
   _('Start Timer')
   ```

5. **Test in multiple languages** to ensure UI layout works correctly

## Troubleshooting

### Language not changing

1. Check browser console for JavaScript errors
2. Verify the language code exists in `LANGUAGES` config
3. Clear browser cache and cookies
4. Check that `.mo` files exist in `translations/<lang>/LC_MESSAGES/`

### Translations not showing

1. Ensure strings are wrapped in `_()` function
2. Check that `.mo` files are compiled (restart application)
3. Verify translation exists in the `.po` file
4. Check for syntax errors in `.po` file

### Compilation errors

If translations fail to compile:
1. Check `.po` file syntax (must be valid)
2. Ensure `msgid` and `msgstr` are properly quoted
3. Look for encoding issues (files must be UTF-8)

## Styling

Language switcher styling is defined in `app/static/base.css`:

- Smooth hover transitions
- Consistent with application design system
- Responsive design (icon-only on small screens)
- Follows light/dark theme

## Accessibility

The language switcher includes:

- Proper ARIA labels and attributes
- Keyboard navigation support
- Clear visual indication of current language
- Tooltip with current language name
- Semantic HTML structure

## Performance

- Translations are compiled at startup (one-time operation)
- Compiled `.mo` files are cached in memory
- No runtime performance impact
- Minimal bundle size increase per language (~50-100KB)

## Future Enhancements

Potential improvements:

1. Add more languages (Japanese, Chinese, etc.)
2. Right-to-left (RTL) language support (Arabic, Hebrew)
3. User-contributed translations via [CONTRIBUTING_TRANSLATIONS.md](CONTRIBUTING_TRANSLATIONS.md) (issues, spreadsheet, [Crowdin — Drytrix TimeTracker](https://crowdin.com/project/drytrix-timetracker), or Weblate)
4. Automatic language detection improvement
5. Translation coverage reporting

## Support

For questions or issues with translations:

1. Check this documentation
2. **Contributors without Git:** see [CONTRIBUTING_TRANSLATIONS.md](CONTRIBUTING_TRANSLATIONS.md) (issue template, spreadsheet option, maintainer workflow, and [Crowdin — Drytrix TimeTracker](https://crowdin.com/project/drytrix-timetracker) using root [`crowdin.yml`](../crowdin.yml) and the **Crowdin sync** GitHub Action)
3. Review `app/__init__.py` locale selector
4. Inspect browser network requests to `/i18n/set-language`
5. Check application logs for translation compilation errors

---

**Last Updated**: 2026-04-29 (catalog sync and `babel.cfg` extractors note)
**Flask-Babel Version**: 4.0.0
**Babel Version**: 2.14.0
