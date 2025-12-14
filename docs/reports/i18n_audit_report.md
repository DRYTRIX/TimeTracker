# Internationalization Audit Report

Total issues found: 387

## Files with Issues: 54

### app\routes\admin.py

Issues: 36

- **Line 162** (flash message): `Username is required`
- **Line 167** (flash message): `User already exists`
- **Line 174** (flash message): `Could not create user due to a database error. Please check server logs.`
- **Line 199** (flash message): `Username is required`
- **Line 205** (flash message): `Username already exists`
- **Line 210** (flash message): `Please select a client when enabling client portal access.`
- **Line 221** (flash message): `Could not update user due to a database error. Please check server logs.`
- **Line 240** (flash message): `Cannot delete the last administrator`
- **Line 245** (flash message): `Cannot delete user with existing time entries`
- **Line 251** (flash message): `Could not delete user due to a database error. Please check server logs.`
- **Line 314** (flash message): `Telemetry has been enabled. Thank you for helping us improve!`
- **Line 316** (flash message): `Telemetry has been disabled.`
- **Line 394** (flash message): `Could not update settings due to a database error. Please check server logs.`
- **Line 396** (flash message): `Settings updated successfully`
- **Line 1139** (flash message): `No logo file selected`
- **Line 1144** (flash message): `No logo file selected`
- **Line 1160** (flash message): `Invalid image file.`
- **Line 1187** (flash message): `Could not save logo due to a database error. Please check server logs.`
- **Line 1192** (flash message): `Invalid file type. Allowed types: PNG, JPG, JPEG, GIF, SVG, WEBP`
- **Line 1215** (flash message): `Could not remove logo due to a database error. Please check server logs.`
- **Line 1217** (flash message): `Company logo removed successfully. Upload a new logo in the section below if needed.`
- **Line 1219** (flash message): `No logo to remove`
- **Line 1278** (flash message): `Backup failed: archive not created`
- **Line 1295** (flash message): `Invalid file type`
- **Line 1302** (flash message): `Backup file not found`
- **Line 1316** (flash message): `Invalid file type`
- **Line 1327** (flash message): `Backup file not found`
- **Line 1347** (flash message): `Invalid file type. Please select a .zip backup archive.`
- **Line 1351** (flash message): `Backup file not found.`
- **Line 1362** (flash message): `Invalid file type. Please upload a .zip backup archive.`
- **Line 1369** (flash message): `No backup file provided`
- **Line 1403** (flash message): `Restore started. You can monitor progress on this page.`
- **Line 1527** (flash message): `OIDC_ISSUER is not configured`
- **Line 1556** (flash message): `✓ OAuth client is registered in application`
- **Line 1559** (flash message): `✗ OAuth client is not registered`
- **Line 1601** (flash message): `OIDC configuration test completed`

### app\routes\budget_alerts.py

Issues: 2

- **Line 342** (flash message): `You do not have access to this project.`
- **Line 349** (flash message): `This project does not have a budget set.`

### app\routes\clients.py

Issues: 25

- **Line 105** (flash message): `Client name is required`
- **Line 116** (flash message): `A client with this name already exists`
- **Line 129** (flash message): `Invalid hourly rate format`
- **Line 176** (flash message): `Could not create client due to a database error. Please check server logs.`
- **Line 248** (flash message): `You do not have permission to edit clients`
- **Line 264** (flash message): `Client name is required`
- **Line 270** (flash message): `A client with this name already exists`
- **Line 277** (flash message): `Invalid hourly rate format`
- **Line 339** (flash message): `Could not update client due to a database error. Please check server logs.`
- **Line 421** (flash message): `You do not have permission to archive clients`
- **Line 425** (flash message): `Client is already inactive`
- **Line 442** (flash message): `You do not have permission to activate clients`
- **Line 446** (flash message): `Client is already active`
- **Line 461** (flash message): `You do not have permission to delete clients`
- **Line 466** (flash message): `Cannot delete client with existing projects`
- **Line 473** (flash message): `Could not delete client due to a database error. Please check server logs.`
- **Line 489** (flash message): `You do not have permission to delete clients`
- **Line 495** (flash message): `No clients selected for deletion`
- **Line 534** (flash message): `Could not delete clients due to a database error. Please check server logs.`
- **Line 545** (flash message): `No clients were deleted`
- **Line 555** (flash message): `You do not have permission to change client status`
- **Line 562** (flash message): `No clients selected`
- **Line 566** (flash message): `Invalid status`
- **Line 595** (flash message): `Could not update client status due to a database error. Please check server logs.`
- **Line 607** (flash message): `No clients were updated`

### app\routes\invoices.py

Issues: 24

- **Line 117** (flash message): `Project, client name, and due date are required`
- **Line 123** (flash message): `Invalid due date format`
- **Line 129** (flash message): `Invalid tax rate format`
- **Line 135** (flash message): `Selected project not found`
- **Line 191** (flash message): `Could not create invoice due to a database error. Please check server logs.`
- **Line 226** (flash message): `You do not have permission to view this invoice`
- **Line 254** (flash message): `You do not have permission to edit this invoice`
- **Line 387** (flash message): `Could not update invoice due to a database error. Please check server logs.`
- **Line 390** (flash message): `Invoice updated successfully`
- **Line 496** (flash message): `You do not have permission to delete this invoice`
- **Line 502** (flash message): `Could not delete invoice due to a database error. Please check server logs.`
- **Line 515** (flash message): `No invoices selected for deletion`
- **Line 547** (flash message): `Could not delete invoices due to a database error. Please check server logs.`
- **Line 567** (flash message): `No invoices selected`
- **Line 573** (flash message): `Invalid status value`
- **Line 608** (flash message): `Could not update invoices due to a database error`
- **Line 626** (flash message): `You do not have permission to edit this invoice`
- **Line 637** (flash message): `No time entries, costs, expenses, or extra goods selected`
- **Line 741** (flash message): `Could not generate items due to a database error. Please check server logs.`
- **Line 744** (flash message): `Invoice items generated successfully from time entries and costs`
- **Line 842** (flash message): `You do not have permission to export this invoice`
- **Line 973** (flash message): `You do not have permission to duplicate this invoice`
- **Line 997** (flash message): `Could not duplicate invoice due to a database error. Please check server logs.`
- **Line 1028** (flash message): `Could not finalize duplicated invoice due to a database error. Please check server logs.`

### app\routes\invoices_refactored.py

Issues: 5

- **Line 131** (flash message): `Project, client name, and due date are required`
- **Line 137** (flash message): `Invalid due date format`
- **Line 143** (flash message): `Invalid tax rate format`
- **Line 150** (flash message): `Selected project not found`
- **Line 187** (flash message): `Could not create invoice due to a database error`

### app\routes\kanban.py

Issues: 7

- **Line 84** (flash message): `Key and label are required`
- **Line 134** (flash message): `Could not create column due to a database error. Please check server logs.`
- **Line 177** (flash message): `Label is required`
- **Line 198** (flash message): `Could not update column due to a database error. Please check server logs.`
- **Line 230** (flash message): `System columns cannot be deleted`
- **Line 266** (flash message): `Could not delete column due to a database error. Please check server logs.`
- **Line 310** (flash message): `Could not toggle column due to a database error. Please check server logs.`

### app\routes\payments.py

Issues: 28

- **Line 48** (flash message): `Invalid from date format`
- **Line 55** (flash message): `Invalid to date format`
- **Line 120** (flash message): `You do not have permission to view this payment`
- **Line 144** (flash message): `Invoice, amount, and payment date are required`
- **Line 151** (flash message): `Selected invoice not found`
- **Line 157** (flash message): `You do not have permission to add payments to this invoice`
- **Line 164** (flash message): `Payment amount must be greater than zero`
- **Line 168** (flash message): `Invalid payment amount`
- **Line 176** (flash message): `Invalid payment date format`
- **Line 186** (flash message): `Gateway fee cannot be negative`
- **Line 190** (flash message): `Invalid gateway fee amount`
- **Line 263** (flash message): `Could not create payment due to a database error. Please check server logs.`
- **Line 307** (flash message): `You do not have permission to edit this payment`
- **Line 330** (flash message): `Payment amount must be greater than zero`
- **Line 333** (flash message): `Invalid payment amount`
- **Line 340** (flash message): `Invalid payment date format`
- **Line 349** (flash message): `Gateway fee cannot be negative`
- **Line 352** (flash message): `Invalid gateway fee amount`
- **Line 389** (flash message): `Could not update payment due to a database error. Please check server logs.`
- **Line 399** (flash message): `Payment updated successfully`
- **Line 413** (flash message): `You do not have permission to delete this payment`
- **Line 433** (flash message): `Could not delete payment due to a database error. Please check server logs.`
- **Line 442** (flash message): `Payment deleted successfully`
- **Line 452** (flash message): `No payments selected for deletion`
- **Line 497** (flash message): `Could not delete payments due to a database error. Please check server logs.`
- **Line 517** (flash message): `No payments selected`
- **Line 523** (flash message): `Invalid status value`
- **Line 568** (flash message): `Could not update payments due to a database error`

### app\routes\projects.py

Issues: 33

- **Line 221** (flash message): `Project name and client are required`
- **Line 231** (flash message): `Selected client not found`
- **Line 242** (flash message): `Invalid hourly rate format`
- **Line 252** (flash message): `Invalid budget amount`
- **Line 260** (flash message): `Invalid budget threshold percent (0-100)`
- **Line 265** (flash message): `A project with this name already exists`
- **Line 297** (flash message): `Could not create project due to a database error. Please check server logs.`
- **Line 639** (flash message): `Project name and client are required`
- **Line 645** (flash message): `Selected client not found`
- **Line 652** (flash message): `Invalid hourly rate format`
- **Line 663** (flash message): `Invalid budget amount`
- **Line 672** (flash message): `Invalid budget threshold percent (0-100)`
- **Line 678** (flash message): `A project with this name already exists`
- **Line 702** (flash message): `Could not update project due to a database error. Please check server logs.`
- **Line 730** (flash message): `You do not have permission to archive projects`
- **Line 738** (flash message): `Project is already archived`
- **Line 777** (flash message): `You do not have permission to unarchive projects`
- **Line 781** (flash message): `Project is already active`
- **Line 813** (flash message): `You do not have permission to deactivate projects`
- **Line 817** (flash message): `Project is already inactive`
- **Line 835** (flash message): `You do not have permission to activate projects`
- **Line 839** (flash message): `Project is already active`
- **Line 858** (flash message): `Cannot delete project with existing time entries`
- **Line 878** (flash message): `Could not delete project due to a database error. Please check server logs.`
- **Line 890** (flash message): `You do not have permission to delete projects`
- **Line 896** (flash message): `No projects selected for deletion`
- **Line 935** (flash message): `Could not delete projects due to a database error. Please check server logs.`
- **Line 946** (flash message): `No projects were deleted`
- **Line 956** (flash message): `You do not have permission to change project status`
- **Line 964** (flash message): `No projects selected`
- **Line 968** (flash message): `Invalid status`
- **Line 1026** (flash message): `Could not update project status due to a database error. Please check server logs.`
- **Line 1038** (flash message): `No projects were updated`

### app\routes\recurring_invoices.py

Issues: 12

- **Line 65** (flash message): `Name, project, client, frequency, and next run date are required`
- **Line 71** (flash message): `Invalid next run date format`
- **Line 79** (flash message): `Invalid end date format`
- **Line 85** (flash message): `Invalid tax rate format`
- **Line 92** (flash message): `Selected project or client not found`
- **Line 129** (flash message): `Could not create recurring invoice due to a database error. Please check server logs.`
- **Line 158** (flash message): `You do not have permission to view this recurring invoice`
- **Line 175** (flash message): `You do not have permission to edit this recurring invoice`
- **Line 200** (flash message): `Could not update recurring invoice due to a database error. Please check server logs.`
- **Line 203** (flash message): `Recurring invoice updated successfully`
- **Line 220** (flash message): `You do not have permission to delete this recurring invoice`
- **Line 226** (flash message): `Could not delete recurring invoice due to a database error. Please check server logs.`

### app\routes\reports.py

Issues: 6

- **Line 181** (flash message): `Invalid date format`
- **Line 326** (flash message): `Invalid date format`
- **Line 460** (flash message): `Invalid date format`
- **Line 656** (flash message): `Invalid date format`
- **Line 740** (flash message): `Invalid date format`
- **Line 800** (flash message): `Invalid date format`

### app\routes\saved_filters.py

Issues: 1

- **Line 282** (flash message): `Could not delete filter due to a database error`

### app\routes\setup.py

Issues: 2

- **Line 36** (flash message): `Setup complete! Thank you for helping us improve TimeTracker.`
- **Line 38** (flash message): `Setup complete! Telemetry is disabled.`

### app\routes\tasks.py

Issues: 43

- **Line 129** (flash message): `Project and task name are required`
- **Line 135** (flash message): `Selected project does not exist`
- **Line 142** (flash message): `Invalid estimated hours format`
- **Line 151** (flash message): `Invalid due date format`
- **Line 168** (flash message): `Could not create task due to a database error. Please check server logs.`
- **Line 213** (flash message): `You do not have access to this task`
- **Line 235** (flash message): `You can only edit tasks you created`
- **Line 252** (flash message): `Task name is required`
- **Line 257** (flash message): `Project is required`
- **Line 261** (flash message): `Selected project does not exist or is inactive`
- **Line 268** (flash message): `Invalid estimated hours format`
- **Line 277** (flash message): `Invalid due date format`
- **Line 316** (flash message): `Could not update status due to a database error. Please check server logs.`
- **Line 340** (flash message): `Could not update status due to a database error. Please check server logs.`
- **Line 350** (flash message): `Could not update task due to a database error. Please check server logs.`
- **Line 393** (flash message): `You do not have permission to update this task`
- **Line 399** (flash message): `Invalid status`
- **Line 415** (flash message): `Could not update status due to a database error. Please check server logs.`
- **Line 448** (flash message): `Could not update status due to a database error. Please check server logs.`
- **Line 478** (flash message): `You can only update tasks you created`
- **Line 498** (flash message): `You can only assign tasks you created`
- **Line 504** (flash message): `Selected user does not exist`
- **Line 511** (flash message): `Task unassigned`
- **Line 523** (flash message): `You can only delete tasks you created`
- **Line 528** (flash message): `Cannot delete task with existing time entries`
- **Line 549** (flash message): `Could not delete task due to a database error. Please check server logs.`
- **Line 566** (flash message): `No tasks selected for deletion`
- **Line 612** (flash message): `Could not delete tasks due to a database error. Please check server logs.`
- **Line 633** (flash message): `No tasks selected`
- **Line 637** (flash message): `Invalid status value`
- **Line 674** (flash message): `Could not update tasks due to a database error`
- **Line 693** (flash message): `No tasks selected`
- **Line 697** (flash message): `Invalid priority value`
- **Line 724** (flash message): `Could not update tasks due to a database error`
- **Line 743** (flash message): `No tasks selected`
- **Line 747** (flash message): `No user selected for assignment`
- **Line 753** (flash message): `Invalid user selected`
- **Line 780** (flash message): `Could not assign tasks due to a database error`
- **Line 799** (flash message): `No tasks selected`
- **Line 803** (flash message): `No project selected`
- **Line 809** (flash message): `Invalid project selected`
- **Line 851** (flash message): `Could not move tasks due to a database error`
- **Line 1058** (flash message): `Only administrators can view all overdue tasks`

### app\routes\time_entry_templates.py

Issues: 5

- **Line 51** (flash message): `Template name is required`
- **Line 90** (flash message): `Could not create template due to a database error`
- **Line 167** (flash message): `Template name is required`
- **Line 205** (flash message): `Could not update template due to a database error`
- **Line 259** (flash message): `Could not delete template due to a database error`

### app\routes\timer.py

Issues: 44

- **Line 47** (flash message): `Project is required`
- **Line 72** (flash message): `Selected task is invalid for the chosen project`
- **Line 81** (flash message): `You already have an active timer. Stop it before starting a new one.`
- **Line 98** (flash message): `Could not start timer due to a database error. Please check server logs.`
- **Line 172** (flash message): `You already have an active timer. Stop it before starting a new one.`
- **Line 177** (flash message): `Template must have a project to start a timer`
- **Line 183** (flash message): `Cannot start timer for this project`
- **Line 205** (flash message): `Could not start timer due to a database error. Please check server logs.`
- **Line 250** (flash message): `You already have an active timer. Stop it before starting a new one.`
- **Line 266** (flash message): `Could not start timer due to a database error. Please check server logs.`
- **Line 299** (flash message): `No active timer to stop`
- **Line 397** (flash message): `You can only edit your own timers`
- **Line 415** (flash message): `Invalid project selected`
- **Line 428** (flash message): `Invalid task selected for the chosen project`
- **Line 451** (flash message): `Start time cannot be in the future`
- **Line 458** (flash message): `Invalid start date/time format`
- **Line 471** (flash message): `End time must be after start time`
- **Line 480** (flash message): `Invalid end date/time format`
- **Line 491** (flash message): `Could not update timer due to a database error. Please check server logs.`
- **Line 494** (flash message): `Timer updated successfully`
- **Line 515** (flash message): `You can only delete your own timers`
- **Line 520** (flash message): `Cannot delete an active timer`
- **Line 526** (flash message): `Could not delete timer due to a database error. Please check server logs.`
- **Line 579** (flash message): `All fields are required`
- **Line 604** (flash message): `Invalid task selected`
- **Line 613** (flash message): `Invalid date/time format`
- **Line 619** (flash message): `End time must be after start time`
- **Line 638** (flash message): `Could not create manual entry due to a database error. Please check server logs.`
- **Line 663** (flash message): `Invalid project selected`
- **Line 697** (flash message): `All fields are required`
- **Line 722** (flash message): `Invalid task selected`
- **Line 733** (flash message): `End date must be after or equal to start date`
- **Line 739** (flash message): `Date range cannot exceed 31 days`
- **Line 743** (flash message): `Invalid date format`
- **Line 753** (flash message): `End time must be after start time`
- **Line 757** (flash message): `Invalid time format`
- **Line 775** (flash message): `No valid dates found in the selected range`
- **Line 827** (flash message): `Could not create bulk entries due to a database error. Please check server logs.`
- **Line 842** (flash message): `An error occurred while creating bulk entries. Please try again.`
- **Line 926** (flash message): `Invalid project selected`
- **Line 943** (flash message): `You can only duplicate your own timers`
- **Line 982** (flash message): `You can only resume your own timers`
- **Line 988** (flash message): `You already have an active timer. Stop it before resuming another one.`
- **Line 1031** (flash message): `Could not resume timer due to a database error. Please check server logs.`

### app\templates\admin\email_templates\create.html

Issues: 3

- **Line 127** (header text): `Available Variables`
- **Line 134** (header text): `Invoice Variables`
- **Line 157** (header text): `Other Variables`

### app\templates\admin\email_templates\edit.html

Issues: 3

- **Line 125** (header text): `Available Variables`
- **Line 132** (header text): `Invoice Variables`
- **Line 155** (header text): `Other Variables`

### app\templates\admin\email_templates\view.html

Issues: 1

- **Line 21** (header text): `Template Information`

### app\templates\admin\quote_pdf_layout.html

Issues: 6

- **Line 3013** (title attribute): `Align Left`
- **Line 3016** (title attribute): `Center Horizontally`
- **Line 3019** (title attribute): `Align Right`
- **Line 3022** (title attribute): `Align Top`
- **Line 3025** (title attribute): `Center Vertically`
- **Line 3028** (title attribute): `Align Bottom`

### app\templates\admin\user_form.html

Issues: 1

- **Line 58** (header text): `Advanced Permissions`

### app\templates\audit_logs\view.html

Issues: 3

- **Line 22** (header text): `Change Information`
- **Line 80** (header text): `Change Details`
- **Line 104** (header text): `Request Information`

### app\templates\components\save_filter_widget.html

Issues: 4

- **Line 18** (header text): `Save Current Filter`
- **Line 34** (placeholder): `e.g., Last 30 days - Billable`
- **Line 7** (title attribute): `Save current filters`
- **Line 66** (title attribute): `Load saved filter`

### app\templates\email\quote_accepted.html

Issues: 1

- **Line 84** (link text): `View Quote`

### app\templates\email\quote_approval_rejected.html

Issues: 2

- **Line 98** (link text): `View Quote`
- **Line 74** (header text): `Quote Approval Rejected`

### app\templates\email\quote_approval_request.html

Issues: 1

- **Line 83** (link text): `Review Quote`

### app\templates\email\quote_approved.html

Issues: 1

- **Line 84** (link text): `View Quote`

### app\templates\email\quote_expired.html

Issues: 2

- **Line 83** (link text): `View Quote`
- **Line 67** (header text): `Quote Expired`

### app\templates\email\quote_expiring.html

Issues: 1

- **Line 93** (link text): `View Quote`

### app\templates\email\quote_rejected.html

Issues: 2

- **Line 81** (link text): `View Quote`
- **Line 67** (header text): `Quote Rejected`

### app\templates\email\quote_sent.html

Issues: 2

- **Line 81** (link text): `View Quote`
- **Line 67** (header text): `Quote Sent`

### app\templates\email\test_email.html

Issues: 1

- **Line 115** (header text): `Test Details`

### app\templates\email\weekly_summary.html

Issues: 1

- **Line 104** (header text): `Hours by Project`

### app\templates\expense_categories\form.html

Issues: 5

- **Line 34** (placeholder): `e.g., Travel, Meals, Office Supplies`
- **Line 44** (placeholder): `e.g., TRAVEL, MEALS`
- **Line 54** (placeholder): `Brief description of this category...`
- **Line 73** (placeholder): `e.g., fa-plane, fa-utensils`
- **Line 142** (placeholder): `e.g., 19.00`

### app\templates\expenses\form.html

Issues: 6

- **Line 34** (placeholder): `e.g., Flight to Berlin`
- **Line 43** (placeholder): `Additional details about the expense...`
- **Line 201** (placeholder): `e.g., Lufthansa`
- **Line 235** (placeholder): `e.g., INV-2024-001`
- **Line 246** (placeholder): `e.g., conference, client-meeting, urgent`
- **Line 255** (placeholder): `Additional notes...`

### app\templates\expenses\list.html

Issues: 4

- **Line 223** (button text): `Update Status`
- **Line 192** (header text): `Delete Selected Expenses`
- **Line 212** (header text): `Change Status for Selected Expenses`
- **Line 75** (placeholder): `Title, vendor, notes...`

### app\templates\invoices\list.html

Issues: 7

- **Line 293** (button text): `Update Status`
- **Line 32** (header text): `Filter Invoices`
- **Line 262** (header text): `Delete Selected Invoices`
- **Line 282** (header text): `Change Status for Selected Invoices`
- **Line 89** (title attribute): `Export to Excel`
- **Line 163** (title attribute): `Partially Paid`
- **Line 167** (title attribute): `Fully Paid`

### app\templates\invoices\view.html

Issues: 2

- **Line 366** (button text): `Send Email`
- **Line 344** (header text): `Send Invoice via Email`

### app\templates\mileage\form.html

Issues: 9

- **Line 55** (placeholder): `e.g., Client meeting, Site visit`
- **Line 64** (placeholder): `Additional details...`
- **Line 83** (placeholder): `e.g., Office, Home`
- **Line 93** (placeholder): `e.g., Client site, Airport`
- **Line 124** (placeholder): `e.g., 12345`
- **Line 134** (placeholder): `e.g., 12400`
- **Line 184** (placeholder): `e.g., VW Golf`
- **Line 194** (placeholder): `e.g., ABC-123`
- **Line 245** (placeholder): `Additional notes...`

### app\templates\mileage\list.html

Issues: 1

- **Line 69** (placeholder): `Purpose, location...`

### app\templates\mileage\view.html

Issues: 2

- **Line 247** (placeholder): `Optional approval notes...`
- **Line 256** (placeholder): `Rejection reason (required)`

### app\templates\payments\list.html

Issues: 5

- **Line 253** (button text): `Update Status`
- **Line 45** (header text): `Filter Payments`
- **Line 222** (header text): `Delete Selected Payments`
- **Line 242** (header text): `Change Status for Selected Payments`
- **Line 96** (title attribute): `Export to Excel`

### app\templates\per_diem\form.html

Issues: 4

- **Line 34** (placeholder): `e.g., Business trip to Berlin`
- **Line 62** (placeholder): `e.g., DE, US, GB`
- **Line 73** (placeholder): `e.g., Berlin`
- **Line 197** (placeholder): `Additional notes...`

### app\templates\per_diem\list.html

Issues: 3

- **Line 153** (button text): `Update Status`
- **Line 122** (header text): `Delete Selected Claims`
- **Line 142** (header text): `Change Status for Selected Claims`

### app\templates\per_diem\rate_form.html

Issues: 3

- **Line 41** (placeholder): `e.g., DE, US, GB`
- **Line 52** (placeholder): `e.g., Berlin`
- **Line 162** (placeholder): `Additional notes about this rate...`

### app\templates\per_diem\view.html

Issues: 1

- **Line 103** (placeholder): `Rejection reason (required)`

### app\templates\projects\list.html

Issues: 6

- **Line 540** (header text): `Archive ${count} Project${count !== 1 ? 's' : ''}?`
- **Line 545** (placeholder): `e.g., Projects completed, Contracts ended, etc.`
- **Line 70** (title attribute): `List View`
- **Line 73** (title attribute): `Grid View`
- **Line 208** (title attribute): `View Project`
- **Line 214** (title attribute): `Edit Project`

### app\templates\recurring_invoices\create.html

Issues: 1

- **Line 124** (button text): `Create Recurring Invoice`

### app\templates\recurring_invoices\edit.html

Issues: 1

- **Line 111** (button text): `Update Recurring Invoice`

### app\templates\recurring_invoices\view.html

Issues: 4

- **Line 17** (button text): `Generate Now`
- **Line 22** (header text): `Template Details`
- **Line 53** (header text): `Invoice Settings`
- **Line 92** (header text): `Recently Generated Invoices`

### app\templates\reports\export_form.html

Issues: 1

- **Line 171** (placeholder): `e.g., development, meeting, urgent`

### app\templates\reports\index.html

Issues: 9

- **Line 62** (header text): `Date Range & Comparison`
- **Line 66** (header text): `Quick Date Ranges`
- **Line 95** (header text): `Comparison View`
- **Line 121** (header text): `Comparison Results`
- **Line 130** (header text): `Export Reports`
- **Line 133** (header text): `Export Format`
- **Line 143** (header text): `Scheduled Reports`
- **Line 150** (header text): `Quick Actions`
- **Line 212** (header text): `Scheduled Reports`

### app\templates\reports\user_report.html

Issues: 1

- **Line 108** (header text): `About Overtime Tracking`

### app\templates\time_entry_templates\view.html

Issues: 2

- **Line 24** (header text): `Template Details`
- **Line 96** (header text): `Usage Statistics`

### app\templates\timer\timer_page.html

Issues: 2

- **Line 184** (header text): `Recent Projects`
- **Line 202** (header text): `Today's Stats`

## Summary by Type

- flash message: 273
- header text: 47
- placeholder: 35
- title attribute: 16
- link text: 8
- button text: 8
