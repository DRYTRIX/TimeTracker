#!/usr/bin/env python3
"""
Complete Dutch translations by translating all empty msgstr entries.
Uses Babel library for reliable .po file parsing.
"""

import sys
from pathlib import Path

try:
    from babel.messages.pofile import read_po, write_po
except ImportError:
    print("Error: Babel library not found. Please install it with: pip install Babel")
    sys.exit(1)


# Comprehensive translation dictionary
TRANSLATIONS = {
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
    "Comment deleted successfully": 
        "Reactie succesvol verwijderd",
    "Error deleting comment: %(error)s": 
        "Fout bij verwijderen reactie: %(error)s",
    
    # Expenses
    "Category name is required": 
        "Categorienaam is vereist",
    "Expense category created successfully": 
        "Uitgavencategorie succesvol aangemaakt",
    "Error creating expense category": 
        "Fout bij aanmaken uitgavencategorie",
    "Expense category updated successfully": 
        "Uitgavencategorie succesvol bijgewerkt",
    "Error updating expense category": 
        "Fout bij bijwerken uitgavencategorie",
    "Expense category deactivated successfully": 
        "Uitgavencategorie succesvol gedeactiveerd",
    "Error deactivating expense category": 
        "Fout bij deactiveren uitgavencategorie",
    "Title is required": 
        "Titel is vereist",
    "Category is required": 
        "Categorie is vereist",
    "Amount is required": 
        "Bedrag is vereist",
    "Expense date is required": 
        "Uitgavedatum is vereist",
    "Invalid date format": 
        "Ongeldig datumformaat",
    "Invalid amount format": 
        "Ongeldig bedragsformaat",
    "Expense created successfully": 
        "Uitgave succesvol aangemaakt",
    "Error creating expense": 
        "Fout bij aanmaken uitgave",
    "You do not have permission to view this expense": 
        "U heeft geen toestemming om deze uitgave te bekijken",
    "You do not have permission to edit this expense": 
        "U heeft geen toestemming om deze uitgave te bewerken",
    "Cannot edit approved or reimbursed expenses": 
        "Kan goedgekeurde of terugbetaalde uitgaven niet bewerken",
    "Please fill in all required fields": 
        "Vul alle verplichte velden in",
    "Expense updated successfully": 
        "Uitgave succesvol bijgewerkt",
    "Error updating expense": 
        "Fout bij bijwerken uitgave",
    "You do not have permission to delete this expense": 
        "U heeft geen toestemming om deze uitgave te verwijderen",
    "Cannot delete approved or invoiced expenses": 
        "Kan goedgekeurde of gefactureerde uitgaven niet verwijderen",
    "Expense deleted successfully": 
        "Uitgave succesvol verwijderd",
    "Error deleting expense": 
        "Fout bij verwijderen uitgave",
    "Only administrators can approve expenses": 
        "Alleen beheerders kunnen uitgaven goedkeuren",
    "Only pending expenses can be approved": 
        "Alleen openstaande uitgaven kunnen worden goedgekeurd",
    "Expense approved successfully": 
        "Uitgave succesvol goedgekeurd",
    "Error approving expense": 
        "Fout bij goedkeuren uitgave",
    "Only administrators can reject expenses": 
        "Alleen beheerders kunnen uitgaven afwijzen",
    "Only pending expenses can be rejected": 
        "Alleen openstaande uitgaven kunnen worden afgewezen",
    "Rejection reason is required": 
        "Afwijzingsreden is vereist",
    "Expense rejected": 
        "Uitgave afgewezen",
    "Error rejecting expense": 
        "Fout bij afwijzen uitgave",
    "Only administrators can mark expenses as reimbursed": 
        "Alleen beheerders kunnen uitgaven als terugbetaald markeren",
    "Only approved expenses can be marked as reimbursed": 
        "Alleen goedgekeurde uitgaven kunnen als terugbetaald worden gemarkeerd",
    "This expense is not marked as reimbursable": 
        "Deze uitgave is niet gemarkeerd als terugbetaalbaar",
    "Expense marked as reimbursed": 
        "Uitgave gemarkeerd als terugbetaald",
    "Error marking expense as reimbursed": 
        "Fout bij markeren uitgave als terugbetaald",
    "OCR is not available. Please contact your administrator.": 
        "OCR is niet beschikbaar. Neem contact op met uw beheerder.",
    "No file provided": 
        "Geen bestand opgegeven",
    "No file selected": 
        "Geen bestand geselecteerd",
    "Invalid file type. Allowed types: png, jpg, jpeg, gif, pdf": 
        "Ongeldig bestandstype. Toegestane typen: png, jpg, jpeg, gif, pdf",
    "Receipt scanned successfully! You can now create an expense with the extracted data.": 
        "Bon succesvol gescand! U kunt nu een uitgave aanmaken met de geëxtraheerde gegevens.",
    "Error scanning receipt. Please try again or enter the expense manually.": 
        "Fout bij scannen bon. Probeer het opnieuw of voer de uitgave handmatig in.",
    "No scanned receipt data found. Please scan a receipt first.": 
        "Geen gescande bongegevens gevonden. Scan eerst een bon.",
    "Expense created successfully from scanned receipt": 
        "Uitgave succesvol aangemaakt van gescande bon",
    "You do not have permission to export this invoice": 
        "U heeft geen toestemming om deze factuur te exporteren",
    "PDF generation failed: %(err)s. Fallback also failed: %(fb)s": 
        "PDF-generatie mislukt: %(err)s. Fallback ook mislukt: %(fb)s",
    
    # Mileage
    "Mileage entry created successfully": 
        "Kilometergeregistratie succesvol aangemaakt",
    "Error creating mileage entry": 
        "Fout bij aanmaken kilometergeregistratie",
    "You do not have permission to view this mileage entry": 
        "U heeft geen toestemming om deze kilometergeregistratie te bekijken",
    "You do not have permission to edit this mileage entry": 
        "U heeft geen toestemming om deze kilometergeregistratie te bewerken",
    "Cannot edit approved or reimbursed mileage entries": 
        "Kan goedgekeurde of terugbetaalde kilometergeregistraties niet bewerken",
    "Mileage entry updated successfully": 
        "Kilometergeregistratie succesvol bijgewerkt",
    "Error updating mileage entry": 
        "Fout bij bijwerken kilometergeregistratie",
    "You do not have permission to delete this mileage entry": 
        "U heeft geen toestemming om deze kilometergeregistratie te verwijderen",
    "Mileage entry deleted successfully": 
        "Kilometergeregistratie succesvol verwijderd",
    "Error deleting mileage entry": 
        "Fout bij verwijderen kilometergeregistratie",
    "Only administrators can approve mileage entries": 
        "Alleen beheerders kunnen kilometergeregistraties goedkeuren",
    "Only pending mileage entries can be approved": 
        "Alleen openstaande kilometergeregistraties kunnen worden goedgekeurd",
    "Mileage entry approved successfully": 
        "Kilometergeregistratie succesvol goedgekeurd",
    "Error approving mileage entry": 
        "Fout bij goedkeuren kilometergeregistratie",
    "Only administrators can reject mileage entries": 
        "Alleen beheerders kunnen kilometergeregistraties afwijzen",
    "Only pending mileage entries can be rejected": 
        "Alleen openstaande kilometergeregistraties kunnen worden afgewezen",
    "Mileage entry rejected": 
        "Kilometergeregistratie afgewezen",
    "Error rejecting mileage entry": 
        "Fout bij afwijzen kilometergeregistratie",
    "Only administrators can mark mileage entries as reimbursed": 
        "Alleen beheerders kunnen kilometergeregistraties als terugbetaald markeren",
    "Only approved mileage entries can be marked as reimbursed": 
        "Alleen goedgekeurde kilometergeregistraties kunnen als terugbetaald worden gemarkeerd",
    "Mileage entry marked as reimbursed": 
        "Kilometergeregistratie gemarkeerd als terugbetaald",
    "Error marking mileage entry as reimbursed": 
        "Fout bij markeren kilometergeregistratie als terugbetaald",
    
    # Per diem
    "Start date must be before end date": 
        "Startdatum moet voor einddatum liggen",
    "No per diem rate found for this location. Please configure rates first.": 
        "Geen per diem-tarief gevonden voor deze locatie. Configureer eerst de tarieven.",
    "Per diem claim created successfully": 
        "Per diem-claim succesvol aangemaakt",
    "Error creating per diem claim": 
        "Fout bij aanmaken per diem-claim",
    "You do not have permission to view this per diem claim": 
        "U heeft geen toestemming om deze per diem-claim te bekijken",
    "You do not have permission to edit this per diem claim": 
        "U heeft geen toestemming om deze per diem-claim te bewerken",
    "Cannot edit approved or reimbursed per diem claims": 
        "Kan goedgekeurde of terugbetaalde per diem-claims niet bewerken",
    "Per diem claim updated successfully": 
        "Per diem-claim succesvol bijgewerkt",
    "Error updating per diem claim": 
        "Fout bij bijwerken per diem-claim",
    "You do not have permission to delete this per diem claim": 
        "U heeft geen toestemming om deze per diem-claim te verwijderen",
    "Per diem claim deleted successfully": 
        "Per diem-claim succesvol verwijderd",
    "Error deleting per diem claim": 
        "Fout bij verwijderen per diem-claim",
    "Only administrators can approve per diem claims": 
        "Alleen beheerders kunnen per diem-claims goedkeuren",
    "Only pending per diem claims can be approved": 
        "Alleen openstaande per diem-claims kunnen worden goedgekeurd",
    "Per diem claim approved successfully": 
        "Per diem-claim succesvol goedgekeurd",
    "Error approving per diem claim": 
        "Fout bij goedkeuren per diem-claim",
    "Only administrators can reject per diem claims": 
        "Alleen beheerders kunnen per diem-claims afwijzen",
    "Only pending per diem claims can be rejected": 
        "Alleen openstaande per diem-claims kunnen worden afgewezen",
    "Per diem claim rejected": 
        "Per diem-claim afgewezen",
    "Error rejecting per diem claim": 
        "Fout bij afwijzen per diem-claim",
    "Per diem rate created successfully": 
        "Per diem-tarief succesvol aangemaakt",
    "Error creating per diem rate": 
        "Fout bij aanmaken per diem-tarief",
    
    # Roles
    "You do not have permission to access this page": 
        "U heeft geen toestemming om deze pagina te openen",
    "Role name is required": 
        "Rolnaam is vereist",
    "A role with this name already exists": 
        "Een rol met deze naam bestaat al",
    "Could not create role due to a database error": 
        "Kon rol niet aanmaken vanwege een databasefout",
    "Role created successfully": 
        "Rol succesvol aangemaakt",
    "System roles cannot be edited": 
        "Systeemrollen kunnen niet worden bewerkt",
    "Could not update role due to a database error": 
        "Kon rol niet bijwerken vanwege een databasefout",
    "Role updated successfully": 
        "Rol succesvol bijgewerkt",
    "You do not have permission to perform this action": 
        "U heeft geen toestemming om deze actie uit te voeren",
    "System roles cannot be deleted": 
        "Systeemrollen kunnen niet worden verwijderd",
    "Cannot delete role that is assigned to users. Please reassign users first.": 
        "Kan rol niet verwijderen die aan gebruikers is toegewezen. Wijs eerst gebruikers opnieuw toe.",
    "Could not delete role due to a database error": 
        "Kon rol niet verwijderen vanwege een databasefout",
    "Role \"%(name)s\" deleted successfully": 
        "Rol \"%(name)s\" succesvol verwijderd",
    "Could not update user roles due to a database error": 
        "Kon gebruikersrollen niet bijwerken vanwege een databasefout",
    "User roles updated successfully": 
        "Gebruikersrollen succesvol bijgewerkt",
    
    # Projects
    "Project code already in use": 
        "Projectcode is al in gebruik",
    "Project is already in favorites": 
        "Project staat al in favorieten",
    "Project added to favorites": 
        "Project toegevoegd aan favorieten",
    "Failed to add project to favorites": 
        "Kon project niet toevoegen aan favorieten",
    "Project is not in favorites": 
        "Project staat niet in favorieten",
    "Project removed from favorites": 
        "Project verwijderd uit favorieten",
    "Failed to remove project from favorites": 
        "Kon project niet verwijderen uit favorieten",
    
    # Costs
    "Description, category, amount, and date are required": 
        "Beschrijving, categorie, bedrag en datum zijn vereist",
    "Could not add cost due to a database error. Please check server logs.": 
        "Kon kosten niet toevoegen vanwege een databasefout. Controleer de serverlogs.",
    "Cost added successfully": 
        "Kosten succesvol toegevoegd",
    "Cost not found": 
        "Kosten niet gevonden",
    "You do not have permission to edit this cost": 
        "U heeft geen toestemming om deze kosten te bewerken",
    "Could not update cost due to a database error. Please check server logs.": 
        "Kon kosten niet bijwerken vanwege een databasefout. Controleer de serverlogs.",
    "Cost updated successfully": 
        "Kosten succesvol bijgewerkt",
    "You do not have permission to delete this cost": 
        "U heeft geen toestemming om deze kosten te verwijderen",
    "Cannot delete cost that has been invoiced": 
        "Kan kosten niet verwijderen die zijn gefactureerd",
    "Could not delete cost due to a database error. Please check server logs.": 
        "Kon kosten niet verwijderen vanwege een databasefout. Controleer de serverlogs.",
    
    # Invoice items
    "Name and unit price are required": 
        "Naam en eenheidsprijs zijn vereist",
    "Invalid quantity format": 
        "Ongeldig hoeveelheidsformaat",
    "Invalid unit price format": 
        "Ongeldig eenheidsprijsformaat",
}


def translate_message(msgid):
    """Get Dutch translation for a message ID."""
    return TRANSLATIONS.get(msgid, "")


def complete_translations():
    """Complete all missing Dutch translations."""
    po_file = Path('translations/nl/LC_MESSAGES/messages.po')
    
    if not po_file.exists():
        print(f"Error: File not found: {po_file}")
        return
    
    print(f"Reading {po_file}...")
    with open(po_file, 'r', encoding='utf-8') as f:
        catalog = read_po(f)
    
    print(f"Found {len(catalog)} entries in catalog")
    
    # Find untranslated entries
    untranslated = []
    for message in catalog:
        if message.id:
            is_empty = False
            if isinstance(message.string, tuple):
                is_empty = not message.string or all(not s for s in message.string)
            else:
                is_empty = not message.string or message.string == ""
            
            if is_empty:
                untranslated.append(message)
    
    print(f"Found {len(untranslated)} untranslated entries")
    
    if len(untranslated) == 0:
        print("All translations are complete!")
        return
    
    # Translate entries
    translated_count = 0
    for message in untranslated:
        translation = translate_message(message.id)
        if translation:
            if isinstance(message.string, tuple):
                # Plural form - set first form
                message.string = (translation, message.string[1] if len(message.string) > 1 else "")
            else:
                message.string = translation
            translated_count += 1
    
    print(f"Translated {translated_count} entries")
    
    if translated_count > 0:
        # Backup
        backup_file = po_file.with_suffix('.po.bak3')
        if backup_file.exists():
            backup_file.unlink()
        po_file.rename(backup_file)
        
        # Write updated file
        with open(po_file, 'wb') as f:
            write_po(f, catalog, width=79)
        
        print(f"Backup saved to {backup_file}")
        print(f"Updated {po_file}")
        print(f"\nRemaining untranslated entries: {len(untranslated) - translated_count}")
        if len(untranslated) - translated_count > 0:
            print("\nFirst 10 remaining untranslated entries:")
            for msg in untranslated[translated_count:translated_count+10]:
                print(f"  - {msg.id[:80]}...")
    else:
        print("No translations found in dictionary. Manual translation needed.")


if __name__ == '__main__':
    complete_translations()

