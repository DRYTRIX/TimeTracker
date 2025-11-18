#!/usr/bin/env python3
"""
Script to complete all Spanish translations by translating empty msgstr entries.
Uses Babel for proper .po file parsing and handles all translation cases.
"""

import sys
from pathlib import Path

try:
    from babel.messages.pofile import read_po, write_po
    from babel.messages.catalog import Message
except ImportError:
    print("Error: Babel library not found. Please install it with: pip install Babel")
    sys.exit(1)


def translate_string(english_text):
    """
    Translate English text to Spanish.
    Returns the Spanish translation or empty string if translation not available.
    """
    # Comprehensive translation dictionary
    translations = {
        "Your session expired or the page was open too long. Please try again.": 
            "Su sesión expiró o la página estuvo abierta demasiado tiempo. Por favor, intente nuevamente.",
        "Administrator access required": 
            "Se requiere acceso de administrador",
        "Could not update PDF layout due to a database error.": 
            "No se pudo actualizar el diseño del PDF debido a un error de base de datos.",
        "PDF layout updated successfully": 
            "Diseño del PDF actualizado correctamente",
        "Could not reset PDF layout due to a database error.": 
            "No se pudo restablecer el diseño del PDF debido a un error de base de datos.",
        "PDF layout reset to defaults": 
            "Diseño del PDF restablecido a los valores predeterminados",
        "Username is required": 
            "Se requiere nombre de usuario",
        "Could not create your account due to a database error. Please try again later.": 
            "No se pudo crear su cuenta debido a un error de base de datos. Por favor, intente nuevamente más tarde.",
        "Welcome! Your account has been created.": 
            "¡Bienvenido! Su cuenta ha sido creada.",
        "User not found. Please contact an administrator.": 
            "Usuario no encontrado. Por favor, contacte a un administrador.",
        "Could not update your account role due to a database error.": 
            "No se pudo actualizar el rol de su cuenta debido a un error de base de datos.",
        "Account is disabled. Please contact an administrator.": 
            "La cuenta está deshabilitada. Por favor, contacte a un administrador.",
        "Welcome back, %(username)s!": 
            "¡Bienvenido de nuevo, %(username)s!",
        "Unexpected error during login. Please try again or check server logs.": 
            "Error inesperado durante el inicio de sesión. Por favor, intente nuevamente o revise los registros del servidor.",
        "Goodbye, %(username)s!": 
            "¡Hasta luego, %(username)s!",
        "Invalid avatar file type. Allowed: PNG, JPG, JPEG, GIF, WEBP": 
            "Tipo de archivo de avatar no válido. Permitidos: PNG, JPG, JPEG, GIF, WEBP",
        "Invalid image file.": 
            "Archivo de imagen no válido.",
        "Failed to save avatar on server.": 
            "Error al guardar el avatar en el servidor.",
        "Profile updated successfully": 
            "Perfil actualizado correctamente",
        "Could not update your profile due to a database error.": 
            "No se pudo actualizar su perfil debido a un error de base de datos.",
        "Avatar removed": 
            "Avatar eliminado",
        "Failed to remove avatar.": 
            "Error al eliminar el avatar.",
        "Single Sign-On is not configured yet. Please contact an administrator.": 
            "El inicio de sesión único aún no está configurado. Por favor, contacte a un administrador.",
        "Single Sign-On is not configured.": 
            "El inicio de sesión único no está configurado.",
        "Authentication failed: missing issuer or subject claim. Please check OIDC configuration.": 
            "Error de autenticación: falta el emisor o la reclamación del sujeto. Por favor, verifique la configuración OIDC.",
        "User account does not exist and self-registration is disabled.": 
            "La cuenta de usuario no existe y el auto-registro está deshabilitado.",
        "Could not create your account due to a database error.": 
            "No se pudo crear su cuenta debido a un error de base de datos.",
        "Unexpected error during SSO login. Please try again or contact support.": 
            "Error inesperado durante el inicio de sesión SSO. Por favor, intente nuevamente o contacte al soporte.",
        "Event created successfully": 
            "Evento creado correctamente",
        "Event updated successfully": 
            "Evento actualizado correctamente",
        "You do not have permission to delete this event.": 
            "No tiene permiso para eliminar este evento.",
        "Failed to delete event": 
            "Error al eliminar el evento",
        "Event deleted successfully": 
            "Evento eliminado correctamente",
        "Error deleting event: %(error)s": 
            "Error al eliminar el evento: %(error)s",
        "Event moved successfully": 
            "Evento movido correctamente",
        "Event resized successfully": 
            "Evento redimensionado correctamente",
        "You do not have permission to view this event.": 
            "No tiene permiso para ver este evento.",
        "You do not have permission to edit this event.": 
            "No tiene permiso para editar este evento.",
        "Note content cannot be empty": 
            "El contenido de la nota no puede estar vacío",
        "Note added successfully": 
            "Nota agregada correctamente",
        "Error adding note": 
            "Error al agregar la nota",
        "Error adding note: %(error)s": 
            "Error al agregar la nota: %(error)s",
        "Note does not belong to this client": 
            "La nota no pertenece a este cliente",
        "You do not have permission to edit this note": 
            "No tiene permiso para editar esta nota",
        "Error updating note": 
            "Error al actualizar la nota",
        "Note updated successfully": 
            "Nota actualizada correctamente",
        "Error updating note: %(error)s": 
            "Error al actualizar la nota: %(error)s",
        "You do not have permission to delete this note": 
            "No tiene permiso para eliminar esta nota",
        "Error deleting note": 
            "Error al eliminar la nota",
        "Note deleted successfully": 
            "Nota eliminada correctamente",
        "Error deleting note: %(error)s": 
            "Error al eliminar la nota: %(error)s",
        "You do not have permission to create clients": 
            "No tiene permiso para crear clientes",
        "Comment content cannot be empty": 
            "El contenido del comentario no puede estar vacío",
        "Comment must be associated with a project or task": 
            "El comentario debe estar asociado con un proyecto o tarea",
        "Comment cannot be associated with both a project and a task": 
            "El comentario no puede estar asociado con un proyecto y una tarea",
        "Invalid parent comment": 
            "Comentario padre no válido",
        "Comment added successfully": 
            "Comentario agregado correctamente",
        "Error adding comment": 
            "Error al agregar el comentario",
        "Error adding comment: %(error)s": 
            "Error al agregar el comentario: %(error)s",
        "You do not have permission to edit this comment": 
            "No tiene permiso para editar este comentario",
        "Comment updated successfully": 
            "Comentario actualizado correctamente",
        "Error updating comment: %(error)s": 
            "Error al actualizar el comentario: %(error)s",
        "You do not have permission to delete this comment": 
            "No tiene permiso para eliminar este comentario",
        "Comment deleted successfully": 
            "Comentario eliminado correctamente",
        "Error deleting comment: %(error)s": 
            "Error al eliminar el comentario: %(error)s",
    }
    
    return translations.get(english_text, "")


def complete_spanish_translations():
    """Complete all Spanish translations in the messages.po file."""
    translations_dir = Path('translations')
    es_file = translations_dir / 'es' / 'LC_MESSAGES' / 'messages.po'
    
    if not es_file.exists():
        print(f"Error: Spanish translation file not found at {es_file}")
        return
    
    print("Reading Spanish translation file...")
    with open(es_file, 'r', encoding='utf-8') as f:
        catalog = read_po(f)
    
    print(f"Found {len(catalog)} entries in Spanish file")
    
    # Count and translate empty entries
    translated_count = 0
    untranslated_count = 0
    
    for message in catalog:
        if message.id and not message.string:
            # Empty translation found
            translation = translate_string(message.id)
            if translation:
                message.string = translation
                translated_count += 1
            else:
                untranslated_count += 1
    
    print(f"\nTranslated: {translated_count} entries")
    print(f"Still untranslated: {untranslated_count} entries")
    
    if translated_count > 0:
        # Backup original
        backup_file = es_file.with_suffix('.po.bak2')
        if backup_file.exists():
            backup_file.unlink()
        es_file.rename(backup_file)
        print(f"Backup created: {backup_file}")
        
        # Write updated file
        with open(es_file, 'wb') as f:
            write_po(f, catalog, width=79)
        print(f"Updated: {es_file}")
    else:
        print("No translations to update")
    
    if untranslated_count > 0:
        print(f"\nWarning: {untranslated_count} entries still need manual translation")
        print("These entries will need to be translated manually or added to the translation dictionary")


if __name__ == '__main__':
    complete_spanish_translations()

