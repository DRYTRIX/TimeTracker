#!/usr/bin/env python3
"""
Complete Spanish translation script - translates all empty msgstr entries.
Reads the .po file and replaces all empty translations with Spanish translations.
"""

import re
from pathlib import Path

# Comprehensive Spanish translations dictionary
TRANSLATIONS = {
    # Session and authentication
    "Your session expired or the page was open too long. Please try again.": 
        "Su sesión expiró o la página estuvo abierta demasiado tiempo. Por favor, intente nuevamente.",
    "Administrator access required": 
        "Se requiere acceso de administrador",
    
    # PDF Layout
    "Could not update PDF layout due to a database error.": 
        "No se pudo actualizar el diseño del PDF debido a un error de base de datos.",
    "PDF layout updated successfully": 
        "Diseño del PDF actualizado correctamente",
    "Could not reset PDF layout due to a database error.": 
        "No se pudo restablecer el diseño del PDF debido a un error de base de datos.",
    "PDF layout reset to defaults": 
        "Diseño del PDF restablecido a los valores predeterminados",
    
    # User account
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
    
    # Avatar and profile
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
    
    # SSO
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
    
    # Events
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
    
    # Notes
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
    
    # Clients
    "You do not have permission to create clients": 
        "No tiene permiso para crear clientes",
    
    # Comments
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
    
    # Expense categories
    "Category name is required": 
        "Se requiere el nombre de la categoría",
    "Expense category created successfully": 
        "Categoría de gasto creada correctamente",
    "Error creating expense category": 
        "Error al crear la categoría de gasto",
    "Expense category updated successfully": 
        "Categoría de gasto actualizada correctamente",
    "Error updating expense category": 
        "Error al actualizar la categoría de gasto",
    "Expense category deactivated successfully": 
        "Categoría de gasto desactivada correctamente",
    "Error deactivating expense category": 
        "Error al desactivar la categoría de gasto",
    
    # Expenses
    "Title is required": 
        "Se requiere el título",
    "Category is required": 
        "Se requiere la categoría",
    "Amount is required": 
        "Se requiere el monto",
    "Expense date is required": 
        "Se requiere la fecha del gasto",
    "Invalid date format": 
        "Formato de fecha no válido",
    "Invalid amount format": 
        "Formato de monto no válido",
    "Expense created successfully": 
        "Gasto creado correctamente",
    "Error creating expense": 
        "Error al crear el gasto",
    "You do not have permission to view this expense": 
        "No tiene permiso para ver este gasto",
    "You do not have permission to edit this expense": 
        "No tiene permiso para editar este gasto",
    "Cannot edit approved or reimbursed expenses": 
        "No se pueden editar gastos aprobados o reembolsados",
    "Please fill in all required fields": 
        "Por favor, complete todos los campos requeridos",
    "Expense updated successfully": 
        "Gasto actualizado correctamente",
    "Error updating expense": 
        "Error al actualizar el gasto",
    "You do not have permission to delete this expense": 
        "No tiene permiso para eliminar este gasto",
    "Cannot delete approved or invoiced expenses": 
        "No se pueden eliminar gastos aprobados o facturados",
    "Expense deleted successfully": 
        "Gasto eliminado correctamente",
    "Error deleting expense": 
        "Error al eliminar el gasto",
    "Only administrators can approve expenses": 
        "Solo los administradores pueden aprobar gastos",
    "Only pending expenses can be approved": 
        "Solo se pueden aprobar gastos pendientes",
    "Expense approved successfully": 
        "Gasto aprobado correctamente",
    "Error approving expense": 
        "Error al aprobar el gasto",
    "Only administrators can reject expenses": 
        "Solo los administradores pueden rechazar gastos",
    "Only pending expenses can be rejected": 
        "Solo se pueden rechazar gastos pendientes",
    "Rejection reason is required": 
        "Se requiere la razón del rechazo",
    "Expense rejected": 
        "Gasto rechazado",
    "Error rejecting expense": 
        "Error al rechazar el gasto",
    "Only administrators can mark expenses as reimbursed": 
        "Solo los administradores pueden marcar gastos como reembolsados",
    "Only approved expenses can be marked as reimbursed": 
        "Solo los gastos aprobados pueden marcarse como reembolsados",
    "This expense is not marked as reimbursable": 
        "Este gasto no está marcado como reembolsable",
    "Expense marked as reimbursed": 
        "Gasto marcado como reembolsado",
    "Error marking expense as reimbursed": 
        "Error al marcar el gasto como reembolsado",
    
    # OCR and receipts
    "OCR is not available. Please contact your administrator.": 
        "OCR no está disponible. Por favor, contacte a su administrador.",
    "No file provided": 
        "No se proporcionó archivo",
    "No file selected": 
        "No se seleccionó archivo",
    "Invalid file type. Allowed types: png, jpg, jpeg, gif, pdf": 
        "Tipo de archivo no válido. Tipos permitidos: png, jpg, jpeg, gif, pdf",
    "Receipt scanned successfully! You can now create an expense with the extracted data.": 
        "¡Recibo escaneado correctamente! Ahora puede crear un gasto con los datos extraídos.",
    "Error scanning receipt. Please try again or enter the expense manually.": 
        "Error al escanear el recibo. Por favor, intente nuevamente o ingrese el gasto manualmente.",
    "No scanned receipt data found. Please scan a receipt first.": 
        "No se encontraron datos del recibo escaneado. Por favor, escanee un recibo primero.",
    "Expense created successfully from scanned receipt": 
        "Gasto creado correctamente desde el recibo escaneado",
    
    # Invoices
    "You do not have permission to export this invoice": 
        "No tiene permiso para exportar esta factura",
    "PDF generation failed: %(err)s. Fallback also failed: %(fb)s": 
        "Error en la generación del PDF: %(err)s. El respaldo también falló: %(fb)s",
    
    # Mileage
    "Mileage entry created successfully": 
        "Entrada de kilometraje creada correctamente",
    "Error creating mileage entry": 
        "Error al crear la entrada de kilometraje",
    "You do not have permission to view this mileage entry": 
        "No tiene permiso para ver esta entrada de kilometraje",
    "You do not have permission to edit this mileage entry": 
        "No tiene permiso para editar esta entrada de kilometraje",
    "Cannot edit approved or reimbursed mileage entries": 
        "No se pueden editar entradas de kilometraje aprobadas o reembolsadas",
    "Mileage entry updated successfully": 
        "Entrada de kilometraje actualizada correctamente",
    "Error updating mileage entry": 
        "Error al actualizar la entrada de kilometraje",
    "You do not have permission to delete this mileage entry": 
        "No tiene permiso para eliminar esta entrada de kilometraje",
    "Mileage entry deleted successfully": 
        "Entrada de kilometraje eliminada correctamente",
    "Error deleting mileage entry": 
        "Error al eliminar la entrada de kilometraje",
    "Only administrators can approve mileage entries": 
        "Solo los administradores pueden aprobar entradas de kilometraje",
    "Only pending mileage entries can be approved": 
        "Solo se pueden aprobar entradas de kilometraje pendientes",
    "Mileage entry approved successfully": 
        "Entrada de kilometraje aprobada correctamente",
    "Error approving mileage entry": 
        "Error al aprobar la entrada de kilometraje",
    "Only administrators can reject mileage entries": 
        "Solo los administradores pueden rechazar entradas de kilometraje",
    "Only pending mileage entries can be rejected": 
        "Solo se pueden rechazar entradas de kilometraje pendientes",
    "Mileage entry rejected": 
        "Entrada de kilometraje rechazada",
    "Error rejecting mileage entry": 
        "Error al rechazar la entrada de kilometraje",
    "Only administrators can mark mileage entries as reimbursed": 
        "Solo los administradores pueden marcar entradas de kilometraje como reembolsadas",
    "Only approved mileage entries can be marked as reimbursed": 
        "Solo las entradas de kilometraje aprobadas pueden marcarse como reembolsadas",
    "Mileage entry marked as reimbursed": 
        "Entrada de kilometraje marcada como reembolsada",
    "Error marking mileage entry as reimbursed": 
        "Error al marcar la entrada de kilometraje como reembolsada",
    
    # Per diem
    "Start date must be before end date": 
        "La fecha de inicio debe ser anterior a la fecha de fin",
    "No per diem rate found for this location. Please configure rates first.": 
        "No se encontró tarifa de viáticos para esta ubicación. Por favor, configure las tarifas primero.",
    "Per diem claim created successfully": 
        "Reclamación de viáticos creada correctamente",
    "Error creating per diem claim": 
        "Error al crear la reclamación de viáticos",
    "You do not have permission to view this per diem claim": 
        "No tiene permiso para ver esta reclamación de viáticos",
    "You do not have permission to edit this per diem claim": 
        "No tiene permiso para editar esta reclamación de viáticos",
    "Cannot edit approved or reimbursed per diem claims": 
        "No se pueden editar reclamaciones de viáticos aprobadas o reembolsadas",
    "Per diem claim updated successfully": 
        "Reclamación de viáticos actualizada correctamente",
    "Error updating per diem claim": 
        "Error al actualizar la reclamación de viáticos",
    "You do not have permission to delete this per diem claim": 
        "No tiene permiso para eliminar esta reclamación de viáticos",
    "Per diem claim deleted successfully": 
        "Reclamación de viáticos eliminada correctamente",
    "Error deleting per diem claim": 
        "Error al eliminar la reclamación de viáticos",
    "Only administrators can approve per diem claims": 
        "Solo los administradores pueden aprobar reclamaciones de viáticos",
    "Only pending per diem claims can be approved": 
        "Solo se pueden aprobar reclamaciones de viáticos pendientes",
    "Per diem claim approved successfully": 
        "Reclamación de viáticos aprobada correctamente",
    "Error approving per diem claim": 
        "Error al aprobar la reclamación de viáticos",
    "Only administrators can reject per diem claims": 
        "Solo los administradores pueden rechazar reclamaciones de viáticos",
    "Only pending per diem claims can be rejected": 
        "Solo se pueden rechazar reclamaciones de viáticos pendientes",
    "Per diem claim rejected": 
        "Reclamación de viáticos rechazada",
    "Error rejecting per diem claim": 
        "Error al rechazar la reclamación de viáticos",
    "Per diem rate created successfully": 
        "Tarifa de viáticos creada correctamente",
    "Error creating per diem rate": 
        "Error al crear la tarifa de viáticos",
    
    # Permissions
    "You do not have permission to access this page": 
        "No tiene permiso para acceder a esta página",
    "Role name is required": 
        "Se requiere el nombre del rol",
    "A role with this name already exists": 
        "Ya existe un rol con este nombre",
    "Could not create role due to a database error": 
        "No se pudo crear el rol debido a un error de base de datos",
    "Role created successfully": 
        "Rol creado correctamente",
    "System roles cannot be edited": 
        "Los roles del sistema no se pueden editar",
    "Could not update role due to a database error": 
        "No se pudo actualizar el rol debido a un error de base de datos",
    "Role updated successfully": 
        "Rol actualizado correctamente",
    "You do not have permission to perform this action": 
        "No tiene permiso para realizar esta acción",
    "System roles cannot be deleted": 
        "Los roles del sistema no se pueden eliminar",
    "Cannot delete role that is assigned to users. Please reassign users first.": 
        "No se puede eliminar un rol que está asignado a usuarios. Por favor, reasigne los usuarios primero.",
    "Could not delete role due to a database error": 
        "No se pudo eliminar el rol debido a un error de base de datos",
    'Role "%(name)s" deleted successfully': 
        'Rol "%(name)s" eliminado correctamente',
    "Could not update user roles due to a database error": 
        "No se pudo actualizar los roles de usuario debido a un error de base de datos",
    "User roles updated successfully": 
        "Roles de usuario actualizados correctamente",
    
    # Projects
    "Project code already in use": 
        "El código del proyecto ya está en uso",
    "Project is already in favorites": 
        "El proyecto ya está en favoritos",
    "Project added to favorites": 
        "Proyecto agregado a favoritos",
    "Failed to add project to favorites": 
        "Error al agregar el proyecto a favoritos",
    "Project is not in favorites": 
        "El proyecto no está en favoritos",
    "Project removed from favorites": 
        "Proyecto eliminado de favoritos",
    "Failed to remove project from favorites": 
        "Error al eliminar el proyecto de favoritos",
    
    # Project costs
    "Description, category, amount, and date are required": 
        "Se requieren descripción, categoría, monto y fecha",
    "Could not add cost due to a database error. Please check server logs.": 
        "No se pudo agregar el costo debido a un error de base de datos. Por favor, revise los registros del servidor.",
    "Cost added successfully": 
        "Costo agregado correctamente",
    "Cost not found": 
        "Costo no encontrado",
    "You do not have permission to edit this cost": 
        "No tiene permiso para editar este costo",
    "Could not update cost due to a database error. Please check server logs.": 
        "No se pudo actualizar el costo debido a un error de base de datos. Por favor, revise los registros del servidor.",
    "Cost updated successfully": 
        "Costo actualizado correctamente",
    "You do not have permission to delete this cost": 
        "No tiene permiso para eliminar este costo",
    "Cannot delete cost that has been invoiced": 
        "No se puede eliminar un costo que ha sido facturado",
    "Could not delete cost due to a database error. Please check server logs.": 
        "No se pudo eliminar el costo debido a un error de base de datos. Por favor, revise los registros del servidor.",
    
    # Extra goods
    "Name and unit price are required": 
        "Se requieren nombre y precio unitario",
    "Invalid quantity format": 
        "Formato de cantidad no válido",
    "Invalid unit price format": 
        "Formato de precio unitario no válido",
    "Could not add extra good due to a database error. Please check server logs.": 
        "No se pudo agregar el artículo extra debido a un error de base de datos. Por favor, revise los registros del servidor.",
    "Extra good added successfully": 
        "Artículo extra agregado correctamente",
    "Extra good not found": 
        "Artículo extra no encontrado",
    "You do not have permission to edit this extra good": 
        "No tiene permiso para editar este artículo extra",
    "Could not update extra good due to a database error. Please check server logs.": 
        "No se pudo actualizar el artículo extra debido a un error de base de datos. Por favor, revise los registros del servidor.",
    "Extra good updated successfully": 
        "Artículo extra actualizado correctamente",
    "You do not have permission to delete this extra good": 
        "No tiene permiso para eliminar este artículo extra",
    "Cannot delete extra good that has been added to an invoice": 
        "No se puede eliminar un artículo extra que ha sido agregado a una factura",
    "Could not delete extra good due to a database error. Please check server logs.": 
        "No se pudo eliminar el artículo extra debido a un error de base de datos. Por favor, revise los registros del servidor.",
    
    # Timer and projects
    "Invalid project selected": 
        "Proyecto seleccionado no válido",
    "Cannot start timer for an archived project. Please unarchive the project first.": 
        "No se puede iniciar el temporizador para un proyecto archivado. Por favor, desarchive el proyecto primero.",
    "Cannot start timer for an inactive project": 
        "No se puede iniciar el temporizador para un proyecto inactivo",
    "Cannot create time entries for an archived project. Please unarchive the project first.": 
        "No se pueden crear entradas de tiempo para un proyecto archivado. Por favor, desarchive el proyecto primero.",
    "Cannot create time entries for an inactive project": 
        "No se pueden crear entradas de tiempo para un proyecto inactivo",
    "Invalid timezone selected": 
        "Zona horaria seleccionada no válida",
    "Standard hours per day must be between 0.5 and 24": 
        "Las horas estándar por día deben estar entre 0.5 y 24",
    
    # Settings
    "Settings saved successfully": 
        "Configuración guardada correctamente",
    "Error saving settings": 
        "Error al guardar la configuración",
    "Error saving settings: %(error)s": 
        "Error al guardar la configuración: %(error)s",
    "Preferences updated": 
        "Preferencias actualizadas",
    "Language updated successfully": 
        "Idioma actualizado correctamente",
    "Invalid language": 
        "Idioma no válido",
    "Language updated to %(language)s": 
        "Idioma actualizado a %(language)s",
    
    # Weekly goals
    "Please enter a valid target hours (greater than 0)": 
        "Por favor, ingrese un objetivo de horas válido (mayor que 0)",
    "A goal already exists for this week. Please edit the existing goal instead.": 
        "Ya existe un objetivo para esta semana. Por favor, edite el objetivo existente.",
    "Weekly time goal created successfully!": 
        "¡Objetivo de tiempo semanal creado correctamente!",
    "Failed to create goal. Please try again.": 
        "Error al crear el objetivo. Por favor, intente nuevamente.",
    "You do not have permission to view this goal": 
        "No tiene permiso para ver este objetivo",
    "You do not have permission to edit this goal": 
        "No tiene permiso para editar este objetivo",
    "Weekly time goal updated successfully!": 
        "¡Objetivo de tiempo semanal actualizado correctamente!",
    "Failed to update goal. Please try again.": 
        "Error al actualizar el objetivo. Por favor, intente nuevamente.",
    "You do not have permission to delete this goal": 
        "No tiene permiso para eliminar este objetivo",
    "Weekly time goal deleted successfully": 
        "Objetivo de tiempo semanal eliminado correctamente",
    "Failed to delete goal. Please try again.": 
        "Error al eliminar el objetivo. Por favor, intente nuevamente.",
    
    # Common UI strings
    "remaining": 
        "restante",
    "Success": 
        "Éxito",
    "Error": 
        "Error",
    "Warning": 
        "Advertencia",
    "Information": 
        "Información",
    "Saving...": 
        "Guardando...",
    "Save": 
        "Guardar",
    "Edit": 
        "Editar",
    "Add": 
        "Agregar",
    "Remove": 
        "Eliminar",
    "Yes": 
        "Sí",
    "No": 
        "No",
    "OK": 
        "Aceptar",
    "Are you sure you want to delete this?": 
        "¿Está seguro de que desea eliminar esto?",
    "You have unsaved changes. Are you sure you want to leave?": 
        "Tiene cambios sin guardar. ¿Está seguro de que desea salir?",
    "Operation failed": 
        "Operación fallida",
    "Operation completed successfully": 
        "Operación completada correctamente",
    "No items selected": 
        "No hay elementos seleccionados",
    "Invalid input": 
        "Entrada no válida",
    "This field is required": 
        "Este campo es obligatorio",
    
    # Timer
    "No active timer": 
        "No hay temporizador activo",
    "Timer stopped": 
        "Temporizador detenido",
    "Failed to stop timer": 
        "Error al detener el temporizador",
    "Error stopping timer": 
        "Error al detener el temporizador",
    "No form to save": 
        "No hay formulario para guardar",
    "No timer found": 
        "No se encontró temporizador",
    "Timer stopped due to inactivity": 
        "Temporizador detenido por inactividad",
    
    # Navigation
    "Navigation": 
        "Navegación",
    "Time Tracking": 
        "Seguimiento de Tiempo",
    "Kanban Board": 
        "Tablero Kanban",
    "Weekly Goals": 
        "Objetivos Semanales",
    "Templates": 
        "Plantillas",
    "Finance & Expenses": 
        "Finanzas y Gastos",
    "Payments": 
        "Pagos",
    "Expenses": 
        "Gastos",
    "Mileage": 
        "Kilometraje",
    "Per Diem": 
        "Viáticos",
    "Budget Alerts": 
        "Alertas de Presupuesto",
    "Tools & Data": 
        "Herramientas y Datos",
    "Import / Export": 
        "Importar / Exportar",
    "Saved Filters": 
        "Filtros Guardados",
    "Admin Dashboard": 
        "Panel de Administración",
    "Users": 
        "Usuarios",
    "API Tokens": 
        "Tokens de API",
    "Roles & Permissions": 
        "Roles y Permisos",
    "System Settings": 
        "Configuración del Sistema",
    "PDF Layout": 
        "Diseño de PDF",
    "Expense Categories": 
        "Categorías de Gastos",
    "Per Diem Rates": 
        "Tarifas de Viáticos",
    "System Info": 
        "Información del Sistema",
    "Backups": 
        "Copias de Seguridad",
    "OIDC Settings": 
        "Configuración OIDC",
    
    # Support
    "Support TimeTracker": 
        "Apoyar TimeTracker",
    "Enjoying TimeTracker? Consider buying me a coffee to support continued development!": 
        "¿Disfrutando de TimeTracker? ¡Considere invitarme un café para apoyar el desarrollo continuo!",
    "Made with": 
        "Hecho con",
    "by": 
        "por",
    "Support TimeTracker development": 
        "Apoyar el desarrollo de TimeTracker",
    "Support": 
        "Soporte",
    "Enjoying TimeTracker?": 
        "¿Disfrutando de TimeTracker?",
    "Support continued development with a coffee": 
        "Apoye el desarrollo continuo con un café",
    "Dismiss": 
        "Descartar",
    
    # UI elements
    "Toggle dark mode": 
        "Alternar modo oscuro",
    "Change language": 
        "Cambiar idioma",
    "User menu": 
        "Menú de usuario",
    "Guest": 
        "Invitado",
    "My Profile": 
        "Mi Perfil",
    "My Settings": 
        "Mis Configuraciones",
    "Are you sure you want to": 
        "¿Está seguro de que desea",
    "deactivate": 
        "desactivar",
    "activate": 
        "activar",
    "this token?": 
        "este token?",
    "Deactivate Token": 
        "Desactivar Token",
    "Activate Token": 
        "Activar Token",
    "Deactivate": 
        "Desactivar",
    "Activate": 
        "Activar",
    "Are you sure you want to delete this token? This action cannot be undone.": 
        "¿Está seguro de que desea eliminar este token? Esta acción no se puede deshacer.",
    "Delete Token": 
        "Eliminar Token",
    
    # Email configuration
    "Email Configuration & Testing": 
        "Configuración y Prueba de Correo Electrónico",
    "Configure and test email delivery": 
        "Configurar y probar la entrega de correo electrónico",
    "Back to Admin": 
        "Volver a Administración",
    "Email Configuration": 
        "Configuración de Correo Electrónico",
    "Configure email settings here to save them in the database. Database settings take precedence over environment variables.": 
        "Configure la configuración de correo electrónico aquí para guardarla en la base de datos. La configuración de la base de datos tiene prioridad sobre las variables de entorno.",
    "Enable Database Email Configuration": 
        "Habilitar Configuración de Correo Electrónico en Base de Datos",
    "Mail Server": 
        "Servidor de Correo",
    "Mail Port": 
        "Puerto de Correo",
    "Use TLS": 
        "Usar TLS",
    "Use SSL": 
        "Usar SSL",
}

def translate_po_file():
    """Translate all empty msgstr entries in the Spanish .po file."""
    po_file = Path('translations/es/LC_MESSAGES/messages.po')
    
    if not po_file.exists():
        print(f"Error: File not found: {po_file}")
        return
    
    # Read the file
    with open(po_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to match msgid followed by empty msgstr (single line)
    # Handle both single-line and multi-line msgid
    patterns = [
        # Single line msgid with empty msgstr
        (r'(msgid\s+"([^"]+)"\s*\nmsgstr\s+"")', r'msgid "\2"\nmsgstr "{}"'),
        # Multi-line msgid (handled separately)
    ]
    
    translated_count = 0
    untranslated = []
    
    # Process each translation
    def replace_match(match):
        nonlocal translated_count
        msgid_text = match.group(2)
        translation = TRANSLATIONS.get(msgid_text, "")
        if translation:
            translated_count += 1
            return f'msgid "{msgid_text}"\nmsgstr "{translation}"'
        else:
            untranslated.append(msgid_text)
            return match.group(0)  # Keep original if no translation
    
    # Replace single-line msgid patterns
    new_content = re.sub(patterns[0][0], replace_match, content)
    
    # Handle multi-line msgid (msgid "" followed by continuation lines)
    # This is more complex - we'll need to handle it separately
    multiline_pattern = r'msgid\s+""\s*\n((?:"[^"]*"\s*\n)+)msgstr\s+""'
    
    def replace_multiline(match):
        nonlocal translated_count
        # Extract the full msgid text from continuation lines
        lines = match.group(1).strip().split('\n')
        msgid_text = ''.join(line.strip('"') for line in lines if line.strip().startswith('"'))
        
        translation = TRANSLATIONS.get(msgid_text, "")
        if translation:
            translated_count += 1
            # Format translation for multi-line if needed
            if len(translation) > 70:
                # Split into multiple lines
                lines = [f'"{translation[i:i+70]}"' for i in range(0, len(translation), 70)]
                translation_lines = '\\n"\n"'.join(lines)
                return f'msgid ""\n{match.group(1)}msgstr ""\n"{translation_lines}"'
            else:
                return f'msgid ""\n{match.group(1)}msgstr "{translation}"'
        else:
            untranslated.append(msgid_text)
            return match.group(0)
    
    new_content = re.sub(multiline_pattern, replace_multiline, new_content, flags=re.MULTILINE)
    
    # Write back if changes were made
    if new_content != content:
        # Backup
        backup_path = po_file.with_suffix('.po.bak3')
        if backup_path.exists():
            backup_path.unlink()
        po_file.rename(backup_path)
        print(f"Backup created: {backup_path}")
        
        # Write new content
        with open(po_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated: {po_file}")
        print(f"Translated: {translated_count} entries")
        if untranslated:
            print(f"Still untranslated: {len(untranslated)} entries")
            print("First 10 untranslated:")
            for msg in untranslated[:10]:
                print(f"  - {msg}")
    else:
        print("No changes made")

if __name__ == '__main__':
    translate_po_file()

