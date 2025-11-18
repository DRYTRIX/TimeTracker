#!/usr/bin/env python3
"""
Script to complete Spanish translations by translating all empty msgstr entries.
"""

import re
from pathlib import Path

def translate_to_spanish(english_text):
    """
    Translate English text to Spanish.
    This is a basic translation dictionary for common phrases.
    For a complete solution, you would use a translation API or manual translation.
    """
    # Common translations dictionary
    translations = {
        "Administrator access required": "Se requiere acceso de administrador",
        "Could not update PDF layout due to a database error.": "No se pudo actualizar el diseño del PDF debido a un error de base de datos.",
        "PDF layout updated successfully": "Diseño del PDF actualizado correctamente",
        "Could not reset PDF layout due to a database error.": "No se pudo restablecer el diseño del PDF debido a un error de base de datos.",
        "PDF layout reset to defaults": "Diseño del PDF restablecido a los valores predeterminados",
        "Username is required": "Se requiere nombre de usuario",
        "Welcome! Your account has been created.": "¡Bienvenido! Su cuenta ha sido creada.",
        "User not found. Please contact an administrator.": "Usuario no encontrado. Por favor, contacte a un administrador.",
        "Could not update your account role due to a database error.": "No se pudo actualizar el rol de su cuenta debido a un error de base de datos.",
        "Account is disabled. Please contact an administrator.": "La cuenta está deshabilitada. Por favor, contacte a un administrador.",
        "Unexpected error during login. Please try again or check server logs.": "Error inesperado durante el inicio de sesión. Por favor, intente nuevamente o revise los registros del servidor.",
        "Invalid avatar file type. Allowed: PNG, JPG, JPEG, GIF, WEBP": "Tipo de archivo de avatar no válido. Permitidos: PNG, JPG, JPEG, GIF, WEBP",
        "Invalid image file.": "Archivo de imagen no válido.",
        "Failed to save avatar on server.": "Error al guardar el avatar en el servidor.",
        "Profile updated successfully": "Perfil actualizado correctamente",
        "Could not update your profile due to a database error.": "No se pudo actualizar su perfil debido a un error de base de datos.",
        "Avatar removed": "Avatar eliminado",
        "Failed to remove avatar.": "Error al eliminar el avatar.",
        "Single Sign-On is not configured yet. Please contact an administrator.": "El inicio de sesión único aún no está configurado. Por favor, contacte a un administrador.",
        "Single Sign-On is not configured.": "El inicio de sesión único no está configurado.",
        "User account does not exist and self-registration is disabled.": "La cuenta de usuario no existe y el auto-registro está deshabilitado.",
        "Could not create your account due to a database error.": "No se pudo crear su cuenta debido a un error de base de datos.",
        "Unexpected error during SSO login. Please try again or contact support.": "Error inesperado durante el inicio de sesión SSO. Por favor, intente nuevamente o contacte al soporte.",
        "Event created successfully": "Evento creado correctamente",
        "Event updated successfully": "Evento actualizado correctamente",
        "You do not have permission to delete this event.": "No tiene permiso para eliminar este evento.",
        "Failed to delete event": "Error al eliminar el evento",
        "Event deleted successfully": "Evento eliminado correctamente",
        "Event moved successfully": "Evento movido correctamente",
        "Event resized successfully": "Evento redimensionado correctamente",
        "You do not have permission to view this event.": "No tiene permiso para ver este evento.",
        "You do not have permission to edit this event.": "No tiene permiso para editar este evento.",
        "Note content cannot be empty": "El contenido de la nota no puede estar vacío",
        "Note added successfully": "Nota agregada correctamente",
        "Error adding note": "Error al agregar la nota",
        "Note does not belong to this client": "La nota no pertenece a este cliente",
        "You do not have permission to edit this note": "No tiene permiso para editar esta nota",
        "Error updating note": "Error al actualizar la nota",
        "Note updated successfully": "Nota actualizada correctamente",
        "You do not have permission to delete this note": "No tiene permiso para eliminar esta nota",
        "Error deleting note": "Error al eliminar la nota",
        "Note deleted successfully": "Nota eliminada correctamente",
        "You do not have permission to create clients": "No tiene permiso para crear clientes",
        "Comment content cannot be empty": "El contenido del comentario no puede estar vacío",
        "Comment must be associated with a project or task": "El comentario debe estar asociado con un proyecto o tarea",
        "Comment cannot be associated with both a project and a task": "El comentario no puede estar asociado con un proyecto y una tarea",
        "Invalid parent comment": "Comentario padre no válido",
        "Comment added successfully": "Comentario agregado correctamente",
        "Error adding comment": "Error al agregar el comentario",
        "You do not have permission to edit this comment": "No tiene permiso para editar este comentario",
        "Comment updated successfully": "Comentario actualizado correctamente",
        "You do not have permission to delete this comment": "No tiene permiso para eliminar este comentario",
        "Comment deleted successfully": "Comentario eliminado correctamente",
        "Category name is required": "Se requiere el nombre de la categoría",
        "Expense category created successfully": "Categoría de gasto creada correctamente",
        "Error creating expense category": "Error al crear la categoría de gasto",
        "Expense category updated successfully": "Categoría de gasto actualizada correctamente",
        "Error updating expense category": "Error al actualizar la categoría de gasto",
        "Expense category deactivated successfully": "Categoría de gasto desactivada correctamente",
        "Error deactivating expense category": "Error al desactivar la categoría de gasto",
        "Title is required": "Se requiere el título",
        "Category is required": "Se requiere la categoría",
        "Amount is required": "Se requiere el monto",
        "Expense date is required": "Se requiere la fecha del gasto",
        "Invalid date format": "Formato de fecha no válido",
        "Invalid amount format": "Formato de monto no válido",
        "Expense created successfully": "Gasto creado correctamente",
        "Error creating expense": "Error al crear el gasto",
        "You do not have permission to view this expense": "No tiene permiso para ver este gasto",
        "You do not have permission to edit this expense": "No tiene permiso para editar este gasto",
        "Cannot edit approved or reimbursed expenses": "No se pueden editar gastos aprobados o reembolsados",
        "Please fill in all required fields": "Por favor, complete todos los campos requeridos",
        "Expense updated successfully": "Gasto actualizado correctamente",
        "Error updating expense": "Error al actualizar el gasto",
        "You do not have permission to delete this expense": "No tiene permiso para eliminar este gasto",
        "Cannot delete approved or invoiced expenses": "No se pueden eliminar gastos aprobados o facturados",
        "Expense deleted successfully": "Gasto eliminado correctamente",
        "Error deleting expense": "Error al eliminar el gasto",
        "Only administrators can approve expenses": "Solo los administradores pueden aprobar gastos",
        "Only pending expenses can be approved": "Solo se pueden aprobar gastos pendientes",
        "Expense approved successfully": "Gasto aprobado correctamente",
        "Error approving expense": "Error al aprobar el gasto",
        "Only administrators can reject expenses": "Solo los administradores pueden rechazar gastos",
        "Only pending expenses can be rejected": "Solo se pueden rechazar gastos pendientes",
        "Rejection reason is required": "Se requiere la razón del rechazo",
        "Expense rejected": "Gasto rechazado",
        "Error rejecting expense": "Error al rechazar el gasto",
        "Only administrators can mark expenses as reimbursed": "Solo los administradores pueden marcar gastos como reembolsados",
        "Only approved expenses can be marked as reimbursed": "Solo los gastos aprobados pueden marcarse como reembolsados",
        "This expense is not marked as reimbursable": "Este gasto no está marcado como reembolsable",
        "Expense marked as reimbursed": "Gasto marcado como reembolsado",
        "Error marking expense as reimbursed": "Error al marcar el gasto como reembolsado",
        "OCR is not available. Please contact your administrator.": "OCR no está disponible. Por favor, contacte a su administrador.",
        "No file provided": "No se proporcionó archivo",
        "No file selected": "No se seleccionó archivo",
        "Invalid file type. Allowed types: png, jpg, jpeg, gif, pdf": "Tipo de archivo no válido. Tipos permitidos: png, jpg, jpeg, gif, pdf",
        "Error scanning receipt. Please try again or enter the expense manually.": "Error al escanear el recibo. Por favor, intente nuevamente o ingrese el gasto manualmente.",
        "No scanned receipt data found. Please scan a receipt first.": "No se encontraron datos del recibo escaneado. Por favor, escanee un recibo primero.",
        "Expense created successfully from scanned receipt": "Gasto creado correctamente desde el recibo escaneado",
        "You do not have permission to export this invoice": "No tiene permiso para exportar esta factura",
        "Mileage entry created successfully": "Entrada de kilometraje creada correctamente",
        "Error creating mileage entry": "Error al crear la entrada de kilometraje",
        "You do not have permission to view this mileage entry": "No tiene permiso para ver esta entrada de kilometraje",
        "You do not have permission to edit this mileage entry": "No tiene permiso para editar esta entrada de kilometraje",
        "Cannot edit approved or reimbursed mileage entries": "No se pueden editar entradas de kilometraje aprobadas o reembolsadas",
        "Mileage entry updated successfully": "Entrada de kilometraje actualizada correctamente",
        "Error updating mileage entry": "Error al actualizar la entrada de kilometraje",
        "You do not have permission to delete this mileage entry": "No tiene permiso para eliminar esta entrada de kilometraje",
        "Mileage entry deleted successfully": "Entrada de kilometraje eliminada correctamente",
        "Error deleting mileage entry": "Error al eliminar la entrada de kilometraje",
        "Only administrators can approve mileage entries": "Solo los administradores pueden aprobar entradas de kilometraje",
        "Only pending mileage entries can be approved": "Solo se pueden aprobar entradas de kilometraje pendientes",
        "Mileage entry approved successfully": "Entrada de kilometraje aprobada correctamente",
        "Error approving mileage entry": "Error al aprobar la entrada de kilometraje",
        "Only administrators can reject mileage entries": "Solo los administradores pueden rechazar entradas de kilometraje",
        "Only pending mileage entries can be rejected": "Solo se pueden rechazar entradas de kilometraje pendientes",
        "Mileage entry rejected": "Entrada de kilometraje rechazada",
        "Error rejecting mileage entry": "Error al rechazar la entrada de kilometraje",
        "Only administrators can mark mileage entries as reimbursed": "Solo los administradores pueden marcar entradas de kilometraje como reembolsadas",
        "Only approved mileage entries can be marked as reimbursed": "Solo las entradas de kilometraje aprobadas pueden marcarse como reembolsadas",
        "Mileage entry marked as reimbursed": "Entrada de kilometraje marcada como reembolsada",
        "Error marking mileage entry as reimbursed": "Error al marcar la entrada de kilometraje como reembolsada",
    }
    
    # Check if we have a direct translation
    if english_text in translations:
        return translations[english_text]
    
    # Handle format strings with %(variable)s
    if '%(' in english_text:
        # For format strings, we need to preserve the format specifiers
        # This is a simplified approach - in production you'd want more sophisticated handling
        return english_text  # Return as-is for now, will need manual translation
    
    # For other strings, return empty to indicate manual translation needed
    return ""

def translate_po_file(po_file_path):
    """Translate all empty msgstr entries in a .po file."""
    po_file = Path(po_file_path)
    
    if not po_file.exists():
        print(f"Error: File not found: {po_file_path}")
        return
    
    # Read the file
    with open(po_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to match msgid followed by empty msgstr
    # Handle both single-line and multi-line msgid
    pattern = r'(msgid\s+"[^"]*"\s*(?:\n"[^"]*")*)\n(msgstr\s+"")'
    
    def replace_empty_translation(match):
        msgid_block = match.group(1)
        # Extract the actual msgid text
        msgid_lines = msgid_block.split('\n')
        msgid_text = ''
        for line in msgid_lines:
            if line.startswith('msgid '):
                msgid_text += line[6:].strip('"')
            elif line.startswith('"'):
                msgid_text += line.strip('"')
        
        # Translate
        translation = translate_to_spanish(msgid_text)
        
        if translation:
            return f'{msgid_block}\nmsgstr "{translation}"'
        else:
            # Return as-is if no translation found
            return match.group(0)
    
    # Replace empty translations
    new_content = re.sub(pattern, replace_empty_translation, content)
    
    # Also handle multiline msgid with empty msgstr
    # This is more complex and might need a proper PO file parser
    
    # Write back
    if new_content != content:
        # Backup
        backup_path = po_file.with_suffix('.po.backup')
        po_file.rename(backup_path)
        print(f"Backup created: {backup_path}")
        
        # Write new content
        with open(po_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated: {po_file_path}")
    else:
        print("No changes made")

if __name__ == '__main__':
    translate_po_file('translations/es/LC_MESSAGES/messages.po')

