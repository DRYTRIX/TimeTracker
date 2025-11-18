#!/usr/bin/env python3
"""
Script to complete all Dutch translations by translating empty msgstr entries.
This script reads the Dutch .po file and translates all missing entries.
"""

import re
from pathlib import Path


def translate_text(text):
    """
    Translate English text to Dutch.
    This function contains common translations and patterns.
    """
    # Common error messages and UI strings
    translations = {
        # Session and authentication
        "Your session expired or the page was open too long. Please try again.": 
            "Uw sessie is verlopen of de pagina was te lang open. Probeer het opnieuw.",
        "Administrator access required": 
            "Beheerdersrechten vereist",
        
        # PDF layout
        "Could not update PDF layout due to a database error.": 
            "Kon PDF-lay-out niet bijwerken vanwege een databasefout.",
        "PDF layout updated successfully": 
            "PDF-lay-out succesvol bijgewerkt",
        "Could not reset PDF layout due to a database error.": 
            "Kon PDF-lay-out niet resetten vanwege een databasefout.",
        "PDF layout reset to defaults": 
            "PDF-lay-out gereset naar standaardwaarden",
        
        # User account
        "Username is required": 
            "Gebruikersnaam is vereist",
        "Could not create your account due to a database error. Please try again later.": 
            "Kon uw account niet aanmaken vanwege een databasefout. Probeer het later opnieuw.",
        "Welcome! Your account has been created.": 
            "Welkom! Uw account is aangemaakt.",
        "User not found. Please contact an administrator.": 
            "Gebruiker niet gevonden. Neem contact op met een beheerder.",
        "Could not update your account role due to a database error.": 
            "Kon uw accountrol niet bijwerken vanwege een databasefout.",
        "Account is disabled. Please contact an administrator.": 
            "Account is uitgeschakeld. Neem contact op met een beheerder.",
        "Welcome back, %(username)s!": 
            "Welkom terug, %(username)s!",
        "Unexpected error during login. Please try again or check server logs.": 
            "Onverwachte fout tijdens aanmelden. Probeer het opnieuw of controleer de serverlogs.",
        "Goodbye, %(username)s!": 
            "Tot ziens, %(username)s!",
        
        # Avatar/Profile
        "Invalid avatar file type. Allowed: PNG, JPG, JPEG, GIF, WEBP": 
            "Ongeldig avatarbestandstype. Toegestaan: PNG, JPG, JPEG, GIF, WEBP",
        "Invalid image file.": 
            "Ongeldig afbeeldingsbestand.",
        "Failed to save avatar on server.": 
            "Kon avatar niet opslaan op server.",
        "Profile updated successfully": 
            "Profiel succesvol bijgewerkt",
        "Could not update your profile due to a database error.": 
            "Kon uw profiel niet bijwerken vanwege een databasefout.",
        "Avatar removed": 
            "Avatar verwijderd",
        "Failed to remove avatar.": 
            "Kon avatar niet verwijderen.",
        
        # SSO
        "Single Sign-On is not configured yet. Please contact an administrator.": 
            "Single Sign-On is nog niet geconfigureerd. Neem contact op met een beheerder.",
        "Single Sign-On is not configured.": 
            "Single Sign-On is niet geconfigureerd.",
        "Authentication failed: missing issuer or subject claim. Please check OIDC configuration.": 
            "Authenticatie mislukt: ontbrekende issuer of subject claim. Controleer de OIDC-configuratie.",
        "User account does not exist and self-registration is disabled.": 
            "Gebruikersaccount bestaat niet en zelfregistratie is uitgeschakeld.",
        "Could not create your account due to a database error.": 
            "Kon uw account niet aanmaken vanwege een databasefout.",
        "Unexpected error during SSO login. Please try again or contact support.": 
            "Onverwachte fout tijdens SSO-aanmelden. Probeer het opnieuw of neem contact op met ondersteuning.",
        
        # Events
        "Event created successfully": 
            "Gebeurtenis succesvol aangemaakt",
        "Event updated successfully": 
            "Gebeurtenis succesvol bijgewerkt",
        "You do not have permission to delete this event.": 
            "U heeft geen toestemming om deze gebeurtenis te verwijderen.",
        "Failed to delete event": 
            "Kon gebeurtenis niet verwijderen",
        "Event deleted successfully": 
            "Gebeurtenis succesvol verwijderd",
        "Error deleting event: %(error)s": 
            "Fout bij verwijderen gebeurtenis: %(error)s",
        "Event moved successfully": 
            "Gebeurtenis succesvol verplaatst",
        "Event resized successfully": 
            "Gebeurtenis succesvol van grootte gewijzigd",
        "You do not have permission to view this event.": 
            "U heeft geen toestemming om deze gebeurtenis te bekijken.",
        "You do not have permission to edit this event.": 
            "U heeft geen toestemming om deze gebeurtenis te bewerken.",
        
        # Notes
        "Note content cannot be empty": 
            "Notitie-inhoud kan niet leeg zijn",
        "Note added successfully": 
            "Notitie succesvol toegevoegd",
        "Error adding note": 
            "Fout bij toevoegen notitie",
        "Error adding note: %(error)s": 
            "Fout bij toevoegen notitie: %(error)s",
        "Note does not belong to this client": 
            "Notitie behoort niet bij deze klant",
        "You do not have permission to edit this note": 
            "U heeft geen toestemming om deze notitie te bewerken",
        "Error updating note": 
            "Fout bij bijwerken notitie",
        "Note updated successfully": 
            "Notitie succesvol bijgewerkt",
        "Error updating note: %(error)s": 
            "Fout bij bijwerken notitie: %(error)s",
        "You do not have permission to delete this note": 
            "U heeft geen toestemming om deze notitie te verwijderen",
        "Error deleting note": 
            "Fout bij verwijderen notitie",
        "Note deleted successfully": 
            "Notitie succesvol verwijderd",
        "Error deleting note: %(error)s": 
            "Fout bij verwijderen notitie: %(error)s",
        
        # Clients
        "You do not have permission to create clients": 
            "U heeft geen toestemming om klanten aan te maken",
        
        # Comments
        "Comment content cannot be empty": 
            "Reactie-inhoud kan niet leeg zijn",
        "Comment must be associated with a project or task": 
            "Reactie moet gekoppeld zijn aan een project of taak",
        "Comment cannot be associated with both a project and a task": 
            "Reactie kan niet tegelijk gekoppeld zijn aan een project en een taak",
        "Invalid parent comment": 
            "Ongeldige bovenliggende reactie",
        "Comment added successfully": 
            "Reactie succesvol toegevoegd",
        "Error adding comment": 
            "Fout bij toevoegen reactie",
        "Error adding comment: %(error)s": 
            "Fout bij toevoegen reactie: %(error)s",
        "You do not have permission to edit this comment": 
            "U heeft geen toestemming om deze reactie te bewerken",
        "Comment updated successfully": 
            "Reactie succesvol bijgewerkt",
        "Error updating comment: %(error)s": 
            "Fout bij bijwerken reactie: %(error)s",
        "You do not have permission to delete this comment": 
            "U heeft geen toestemming om deze reactie te verwijderen",
    }
    
    # Direct translation
    if text in translations:
        return translations[text]
    
    # Pattern-based translations for common phrases
    patterns = [
        (r"^(.+) created successfully$", r"\1 succesvol aangemaakt"),
        (r"^(.+) updated successfully$", r"\1 succesvol bijgewerkt"),
        (r"^(.+) deleted successfully$", r"\1 succesvol verwijderd"),
        (r"^Failed to (.+)$", r"Kon \1 niet"),
        (r"^Error (.+)$", r"Fout \1"),
        (r"^You do not have permission to (.+)$", r"U heeft geen toestemming om \1"),
        (r"^Could not (.+) due to a database error\.$", r"Kon \1 niet vanwege een databasefout."),
        (r"^(.+) cannot be empty$", r"\1 kan niet leeg zijn"),
        (r"^(.+) is required$", r"\1 is vereist"),
        (r"^(.+) is not configured\.$", r"\1 is niet geconfigureerd."),
        (r"^(.+) is not configured yet\. Please contact an administrator\.$", r"\1 is nog niet geconfigureerd. Neem contact op met een beheerder."),
    ]
    
    for pattern, replacement in patterns:
        match = re.match(pattern, text, re.IGNORECASE)
        if match:
            # Simple word-by-word translation for common words
            words = {
                "create": "aanmaken", "update": "bijwerken", "delete": "verwijderen",
                "save": "opslaan", "remove": "verwijderen", "add": "toevoegen",
                "edit": "bewerken", "view": "bekijken", "access": "toegang",
                "permission": "toestemming", "error": "fout", "failed": "mislukt",
            }
            translated = replacement
            for en, nl in words.items():
                translated = translated.replace(en, nl)
            return translated.capitalize() if text[0].isupper() else translated
    
    # Fallback: return empty string (needs manual translation)
    return ""


def translate_po_file():
    """Translate all empty msgstr entries in the Dutch .po file."""
    po_file = Path('translations/nl/LC_MESSAGES/messages.po')
    
    if not po_file.exists():
        print(f"Error: File not found: {po_file}")
        return
    
    print(f"Reading {po_file}...")
    content = po_file.read_text(encoding='utf-8')
    
    # Find all empty msgstr entries
    # Pattern 1: Simple msgstr ""
    pattern1 = r'(msgid "([^"]+)"\nmsgstr "")'
    # Pattern 2: Multi-line msgid with empty msgstr
    pattern2 = r'(msgid ""\n"([^"]+)"\nmsgstr "")'
    
    matches1 = list(re.finditer(pattern1, content, re.MULTILINE))
    matches2 = list(re.finditer(pattern2, content, re.MULTILINE))
    
    print(f"Found {len(matches1)} simple untranslated entries")
    print(f"Found {len(matches2)} multi-line untranslated entries")
    
    # Translate and replace
    translated_count = 0
    for match in matches1 + matches2:
        msgid = match.group(2) if match.group(2) else match.group(1)
        translation = translate_text(msgid)
        if translation:
            # Replace empty msgstr with translation
            old_str = match.group(0)
            new_str = old_str.replace('msgstr ""', f'msgstr "{translation}"')
            content = content.replace(old_str, new_str, 1)
            translated_count += 1
    
    if translated_count > 0:
        # Backup original
        backup_file = po_file.with_suffix('.po.bak2')
        if backup_file.exists():
            backup_file.unlink()
        po_file.rename(backup_file)
        
        # Write updated content
        po_file.write_text(content, encoding='utf-8')
        print(f"\nTranslated {translated_count} entries")
        print(f"Backup saved to {backup_file}")
    else:
        print("No translations applied (all entries already translated or no matches found)")


if __name__ == '__main__':
    translate_po_file()

