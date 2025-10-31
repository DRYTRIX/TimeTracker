# Internationalization Audit Report

Total issues found: 384

## Files with Issues: 57

### app\routes\admin.py

Issues: 35

- **Line 161** (flash message): `Username is required`
- **Line 166** (flash message): `User already exists`
- **Line 173** (flash message): `Could not create user due to a database error. Please check server logs.`
- **Line 194** (flash message): `Username is required`
- **Line 200** (flash message): `Username already exists`
- **Line 208** (flash message): `Could not update user due to a database error. Please check server logs.`
- **Line 227** (flash message): `Cannot delete the last administrator`
- **Line 232** (flash message): `Cannot delete user with existing time entries`
- **Line 238** (flash message): `Could not delete user due to a database error. Please check server logs.`
- **Line 301** (flash message): `Telemetry has been enabled. Thank you for helping us improve!`
- **Line 303** (flash message): `Telemetry has been disabled.`
- **Line 380** (flash message): `Could not update settings due to a database error. Please check server logs.`
- **Line 382** (flash message): `Settings updated successfully`
- **Line 650** (flash message): `No logo file selected`
- **Line 655** (flash message): `No logo file selected`
- **Line 671** (flash message): `Invalid image file.`
- **Line 698** (flash message): `Could not save logo due to a database error. Please check server logs.`
- **Line 703** (flash message): `Invalid file type. Allowed types: PNG, JPG, JPEG, GIF, SVG, WEBP`
- **Line 726** (flash message): `Could not remove logo due to a database error. Please check server logs.`
- **Line 728** (flash message): `Company logo removed successfully. Upload a new logo in the section below if needed.`
- **Line 730** (flash message): `No logo to remove`
- **Line 789** (flash message): `Backup failed: archive not created`
- **Line 806** (flash message): `Invalid file type`
- **Line 813** (flash message): `Backup file not found`
- **Line 827** (flash message): `Invalid file type`
- **Line 838** (flash message): `Backup file not found`
- **Line 858** (flash message): `Invalid file type. Please select a .zip backup archive.`
- **Line 862** (flash message): `Backup file not found.`
- **Line 873** (flash message): `Invalid file type. Please upload a .zip backup archive.`
- **Line 880** (flash message): `No backup file provided`
- **Line 914** (flash message): `Restore started. You can monitor progress on this page.`
- **Line 1038** (flash message): `OIDC_ISSUER is not configured`
- **Line 1067** (flash message): `✓ OAuth client is registered in application`
- **Line 1070** (flash message): `✗ OAuth client is not registered`
- **Line 1112** (flash message): `OIDC configuration test completed`

### app\routes\budget_alerts.py

Issues: 2

- **Line 338** (flash message): `You do not have access to this project.`
- **Line 345** (flash message): `This project does not have a budget set.`

### app\routes\clients.py

Issues: 25

- **Line 101** (flash message): `Client name is required`
- **Line 112** (flash message): `A client with this name already exists`
- **Line 125** (flash message): `Invalid hourly rate format`
- **Line 147** (flash message): `Could not create client due to a database error. Please check server logs.`
- **Line 185** (flash message): `You do not have permission to edit clients`
- **Line 199** (flash message): `Client name is required`
- **Line 205** (flash message): `A client with this name already exists`
- **Line 212** (flash message): `Invalid hourly rate format`
- **Line 226** (flash message): `Could not update client due to a database error. Please check server logs.`
- **Line 246** (flash message): `You do not have permission to archive clients`
- **Line 250** (flash message): `Client is already inactive`
- **Line 267** (flash message): `You do not have permission to activate clients`
- **Line 271** (flash message): `Client is already active`
- **Line 286** (flash message): `You do not have permission to delete clients`
- **Line 291** (flash message): `Cannot delete client with existing projects`
- **Line 298** (flash message): `Could not delete client due to a database error. Please check server logs.`
- **Line 314** (flash message): `You do not have permission to delete clients`
- **Line 320** (flash message): `No clients selected for deletion`
- **Line 359** (flash message): `Could not delete clients due to a database error. Please check server logs.`
- **Line 370** (flash message): `No clients were deleted`
- **Line 380** (flash message): `You do not have permission to change client status`
- **Line 387** (flash message): `No clients selected`
- **Line 391** (flash message): `Invalid status`
- **Line 420** (flash message): `Could not update client status due to a database error. Please check server logs.`
- **Line 432** (flash message): `No clients were updated`

### app\routes\invoices.py

Issues: 19

- **Line 74** (flash message): `Project, client name, and due date are required`
- **Line 80** (flash message): `Invalid due date format`
- **Line 86** (flash message): `Invalid tax rate format`
- **Line 92** (flash message): `Selected project not found`
- **Line 127** (flash message): `Could not create invoice due to a database error. Please check server logs.`
- **Line 161** (flash message): `You do not have permission to view this invoice`
- **Line 180** (flash message): `You do not have permission to edit this invoice`
- **Line 276** (flash message): `Could not update invoice due to a database error. Please check server logs.`
- **Line 279** (flash message): `Invoice updated successfully`
- **Line 323** (flash message): `You do not have permission to delete this invoice`
- **Line 329** (flash message): `Could not delete invoice due to a database error. Please check server logs.`
- **Line 343** (flash message): `You do not have permission to edit this invoice`
- **Line 354** (flash message): `No time entries, costs, expenses, or extra goods selected`
- **Line 449** (flash message): `Could not generate items due to a database error. Please check server logs.`
- **Line 452** (flash message): `Invoice items generated successfully from time entries and costs`
- **Line 523** (flash message): `You do not have permission to export this invoice`
- **Line 628** (flash message): `You do not have permission to duplicate this invoice`
- **Line 652** (flash message): `Could not duplicate invoice due to a database error. Please check server logs.`
- **Line 683** (flash message): `Could not finalize duplicated invoice due to a database error. Please check server logs.`

### app\routes\kanban.py

Issues: 7

- **Line 65** (flash message): `Key and label are required`
- **Line 102** (flash message): `Could not create column due to a database error. Please check server logs.`
- **Line 137** (flash message): `Label is required`
- **Line 158** (flash message): `Could not update column due to a database error. Please check server logs.`
- **Line 186** (flash message): `System columns cannot be deleted`
- **Line 209** (flash message): `Could not delete column due to a database error. Please check server logs.`
- **Line 246** (flash message): `Could not toggle column due to a database error. Please check server logs.`

### app\routes\payments.py

Issues: 23

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
- **Line 226** (flash message): `Could not create payment due to a database error. Please check server logs.`
- **Line 270** (flash message): `You do not have permission to edit this payment`
- **Line 293** (flash message): `Payment amount must be greater than zero`
- **Line 296** (flash message): `Invalid payment amount`
- **Line 303** (flash message): `Invalid payment date format`
- **Line 312** (flash message): `Gateway fee cannot be negative`
- **Line 315** (flash message): `Invalid gateway fee amount`
- **Line 352** (flash message): `Could not update payment due to a database error. Please check server logs.`
- **Line 362** (flash message): `Payment updated successfully`
- **Line 376** (flash message): `You do not have permission to delete this payment`
- **Line 396** (flash message): `Could not delete payment due to a database error. Please check server logs.`
- **Line 405** (flash message): `Payment deleted successfully`

### app\routes\projects.py

Issues: 33

- **Line 220** (flash message): `Project name and client are required`
- **Line 230** (flash message): `Selected client not found`
- **Line 241** (flash message): `Invalid hourly rate format`
- **Line 251** (flash message): `Invalid budget amount`
- **Line 259** (flash message): `Invalid budget threshold percent (0-100)`
- **Line 264** (flash message): `A project with this name already exists`
- **Line 296** (flash message): `Could not create project due to a database error. Please check server logs.`
- **Line 627** (flash message): `Project name and client are required`
- **Line 633** (flash message): `Selected client not found`
- **Line 640** (flash message): `Invalid hourly rate format`
- **Line 651** (flash message): `Invalid budget amount`
- **Line 660** (flash message): `Invalid budget threshold percent (0-100)`
- **Line 666** (flash message): `A project with this name already exists`
- **Line 690** (flash message): `Could not update project due to a database error. Please check server logs.`
- **Line 718** (flash message): `You do not have permission to archive projects`
- **Line 726** (flash message): `Project is already archived`
- **Line 765** (flash message): `You do not have permission to unarchive projects`
- **Line 769** (flash message): `Project is already active`
- **Line 801** (flash message): `You do not have permission to deactivate projects`
- **Line 805** (flash message): `Project is already inactive`
- **Line 823** (flash message): `You do not have permission to activate projects`
- **Line 827** (flash message): `Project is already active`
- **Line 846** (flash message): `Cannot delete project with existing time entries`
- **Line 866** (flash message): `Could not delete project due to a database error. Please check server logs.`
- **Line 878** (flash message): `You do not have permission to delete projects`
- **Line 884** (flash message): `No projects selected for deletion`
- **Line 923** (flash message): `Could not delete projects due to a database error. Please check server logs.`
- **Line 934** (flash message): `No projects were deleted`
- **Line 944** (flash message): `You do not have permission to change project status`
- **Line 952** (flash message): `No projects selected`
- **Line 956** (flash message): `Invalid status`
- **Line 1014** (flash message): `Could not update project status due to a database error. Please check server logs.`
- **Line 1026** (flash message): `No projects were updated`

### app\routes\reports.py

Issues: 6

- **Line 101** (flash message): `Invalid date format`
- **Line 246** (flash message): `Invalid date format`
- **Line 380** (flash message): `Invalid date format`
- **Line 576** (flash message): `Invalid date format`
- **Line 660** (flash message): `Invalid date format`
- **Line 720** (flash message): `Invalid date format`

### app\routes\saved_filters.py

Issues: 1

- **Line 282** (flash message): `Could not delete filter due to a database error`

### app\routes\setup.py

Issues: 2

- **Line 36** (flash message): `Setup complete! Thank you for helping us improve TimeTracker.`
- **Line 38** (flash message): `Setup complete! Telemetry is disabled.`

### app\routes\tasks.py

Issues: 43

- **Line 119** (flash message): `Project and task name are required`
- **Line 125** (flash message): `Selected project does not exist`
- **Line 132** (flash message): `Invalid estimated hours format`
- **Line 141** (flash message): `Invalid due date format`
- **Line 158** (flash message): `Could not create task due to a database error. Please check server logs.`
- **Line 203** (flash message): `You do not have access to this task`
- **Line 225** (flash message): `You can only edit tasks you created`
- **Line 242** (flash message): `Task name is required`
- **Line 247** (flash message): `Project is required`
- **Line 251** (flash message): `Selected project does not exist or is inactive`
- **Line 258** (flash message): `Invalid estimated hours format`
- **Line 267** (flash message): `Invalid due date format`
- **Line 306** (flash message): `Could not update status due to a database error. Please check server logs.`
- **Line 330** (flash message): `Could not update status due to a database error. Please check server logs.`
- **Line 340** (flash message): `Could not update task due to a database error. Please check server logs.`
- **Line 383** (flash message): `You do not have permission to update this task`
- **Line 389** (flash message): `Invalid status`
- **Line 405** (flash message): `Could not update status due to a database error. Please check server logs.`
- **Line 438** (flash message): `Could not update status due to a database error. Please check server logs.`
- **Line 468** (flash message): `You can only update tasks you created`
- **Line 488** (flash message): `You can only assign tasks you created`
- **Line 494** (flash message): `Selected user does not exist`
- **Line 501** (flash message): `Task unassigned`
- **Line 513** (flash message): `You can only delete tasks you created`
- **Line 518** (flash message): `Cannot delete task with existing time entries`
- **Line 539** (flash message): `Could not delete task due to a database error. Please check server logs.`
- **Line 556** (flash message): `No tasks selected for deletion`
- **Line 602** (flash message): `Could not delete tasks due to a database error. Please check server logs.`
- **Line 623** (flash message): `No tasks selected`
- **Line 629** (flash message): `Invalid status value`
- **Line 660** (flash message): `Could not update tasks due to a database error`
- **Line 679** (flash message): `No tasks selected`
- **Line 683** (flash message): `Invalid priority value`
- **Line 710** (flash message): `Could not update tasks due to a database error`
- **Line 729** (flash message): `No tasks selected`
- **Line 733** (flash message): `No user selected for assignment`
- **Line 739** (flash message): `Invalid user selected`
- **Line 766** (flash message): `Could not assign tasks due to a database error`
- **Line 785** (flash message): `No tasks selected`
- **Line 789** (flash message): `No project selected`
- **Line 795** (flash message): `Invalid project selected`
- **Line 837** (flash message): `Could not move tasks due to a database error`
- **Line 1044** (flash message): `Only administrators can view all overdue tasks`

### app\routes\time_entry_templates.py

Issues: 5

- **Line 51** (flash message): `Template name is required`
- **Line 90** (flash message): `Could not create template due to a database error`
- **Line 167** (flash message): `Template name is required`
- **Line 205** (flash message): `Could not update template due to a database error`
- **Line 259** (flash message): `Could not delete template due to a database error`

### app\routes\timer.py

Issues: 41

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
- **Line 866** (flash message): `Invalid project selected`
- **Line 883** (flash message): `You can only duplicate your own timers`

### app\templates\admin\api_tokens.html

Issues: 3

- **Line 129** (header text): `Create API Token`
- **Line 255** (header text): `Usage Examples:`
- **Line 243** (label text): `Your API Token`

### app\templates\admin\backups.html

Issues: 5

- **Line 28** (header text): `Create Backup`
- **Line 47** (header text): `Restore Backup`
- **Line 61** (header text): `Existing Backups`
- **Line 124** (header text): `Important Information`
- **Line 178** (header text): `Confirm Deletion`

### app\templates\admin\clear_cache.html

Issues: 5

- **Line 6** (header text): `Clear Cache`
- **Line 15** (header text): `ServiceWorker Status`
- **Line 23** (header text): `Clear All Caches`
- **Line 35** (header text): `ServiceWorker Actions`
- **Line 49** (header text): `Manual Hard Refresh`

### app\templates\admin\dashboard.html

Issues: 2

- **Line 26** (header text): `Admin Sections`
- **Line 58** (header text): `Recent Activity`

### app\templates\admin\restore.html

Issues: 1

- **Line 11** (header text): `Restore Backup`

### app\templates\admin\settings.html

Issues: 11

- **Line 183** (button text): `Save Settings`
- **Line 60** (header text): `User Management`
- **Line 74** (header text): `Company Branding`
- **Line 109** (header text): `Invoice Defaults`
- **Line 132** (header text): `Backup Settings`
- **Line 147** (header text): `Export Settings`
- **Line 162** (header text): `Privacy & Analytics`
- **Line 190** (header text): `Company Logo`
- **Line 228** (header text): `Upload New Logo`
- **Line 211** (alt text): `Company Logo`
- **Line 242** (alt text): `Logo Preview`

### app\templates\admin\telemetry.html

Issues: 2

- **Line 47** (link text): `Admin → Settings`
- **Line 8** (header text): `Telemetry & Analytics Dashboard`

### app\templates\admin\user_form.html

Issues: 1

- **Line 35** (header text): `Advanced Permissions`

### app\templates\auth\edit_profile.html

Issues: 3

- **Line 74** (button text): `Save Changes`
- **Line 6** (header text): `Edit Profile`
- **Line 65** (placeholder): `Leave blank to keep current password`

### app\templates\auth\profile.html

Issues: 3

- **Line 9** (link text): `Edit Profile`
- **Line 47** (header text): `Member Since`
- **Line 52** (header text): `Last Login`

### app\templates\base.html

Issues: 3

- **Line 106** (link text): `Skip to content`
- **Line 711** (placeholder): `Type a command or search...`
- **Line 123** (title attribute): `Toggle sidebar`

### app\templates\clients\list.html

Issues: 2

- **Line 18** (header text): `Filter Clients`
- **Line 44** (title attribute): `Export to CSV`

### app\templates\components\save_filter_widget.html

Issues: 4

- **Line 18** (header text): `Save Current Filter`
- **Line 34** (placeholder): `e.g., Last 30 days - Billable`
- **Line 7** (title attribute): `Save current filters`
- **Line 66** (title attribute): `Load saved filter`

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

Issues: 3

- **Line 64** (header text): `Filter Expenses`
- **Line 69** (placeholder): `Title, vendor, notes...`
- **Line 154** (title attribute): `Export to CSV`

### app\templates\expenses\view.html

Issues: 3

- **Line 250** (header text): `Associated With`
- **Line 346** (header text): `Reject Expense`
- **Line 355** (placeholder): `Explain why this expense is being rejected...`

### app\templates\invoices\view.html

Issues: 5

- **Line 8** (link text): `Export PDF`
- **Line 9** (link text): `Record Payment`
- **Line 88** (header text): `Extra Goods`
- **Line 145** (header text): `Payment History`
- **Line 205** (header text): `Payment History`

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

Issues: 2

- **Line 58** (header text): `Filter Mileage`
- **Line 63** (placeholder): `Purpose, location...`

### app\templates\mileage\view.html

Issues: 2

- **Line 247** (placeholder): `Optional approval notes...`
- **Line 256** (placeholder): `Rejection reason (required)`

### app\templates\payments\create.html

Issues: 2

- **Line 7** (header text): `Record New Payment`
- **Line 44** (header text): `Invoice Details`

### app\templates\payments\list.html

Issues: 4

- **Line 153** (link text): `Record your first payment`
- **Line 24** (header text): `Total Payments`
- **Line 28** (header text): `Total Amount`
- **Line 37** (header text): `Gateway Fees`

### app\templates\payments\view.html

Issues: 2

- **Line 21** (header text): `Payment Details`
- **Line 151** (header text): `Related Invoice`

### app\templates\per_diem\form.html

Issues: 4

- **Line 34** (placeholder): `e.g., Business trip to Berlin`
- **Line 62** (placeholder): `e.g., DE, US, GB`
- **Line 73** (placeholder): `e.g., Berlin`
- **Line 197** (placeholder): `Additional notes...`

### app\templates\per_diem\list.html

Issues: 1

- **Line 46** (header text): `Filter Claims`

### app\templates\per_diem\rate_form.html

Issues: 3

- **Line 35** (placeholder): `e.g., DE, US, GB`
- **Line 46** (placeholder): `e.g., Berlin`
- **Line 156** (placeholder): `Additional notes about this rate...`

### app\templates\per_diem\view.html

Issues: 1

- **Line 103** (placeholder): `Rejection reason (required)`

### app\templates\projects\list.html

Issues: 5

- **Line 271** (button text): `Contract Ended`
- **Line 18** (header text): `Filter Projects`
- **Line 262** (header text): `Archive ${count} Project${count !== 1 ? 's' : ''}?`
- **Line 267** (placeholder): `e.g., Projects completed, Contracts ended, etc.`
- **Line 61** (title attribute): `Export to CSV`

### app\templates\reports\export_form.html

Issues: 1

- **Line 171** (placeholder): `e.g., development, meeting, urgent`

### app\templates\reports\index.html

Issues: 6

- **Line 63** (link text): `Project Report`
- **Line 64** (link text): `User Report`
- **Line 65** (link text): `Summary Report`
- **Line 66** (link text): `Task Report`
- **Line 61** (header text): `Report Types`
- **Line 77** (header text): `Recent Entries`

### app\templates\reports\project_report.html

Issues: 1

- **Line 5** (header text): `Project Report`

### app\templates\reports\summary.html

Issues: 1

- **Line 6** (header text): `Summary Report`

### app\templates\reports\task_report.html

Issues: 1

- **Line 5** (header text): `Task Report`

### app\templates\reports\user_report.html

Issues: 2

- **Line 5** (header text): `User Report`
- **Line 108** (header text): `About Overtime Tracking`

### app\templates\saved_filters\list.html

Issues: 1

- **Line 46** (title attribute): `Apply filter`

### app\templates\settings\keyboard_shortcuts.html

Issues: 2

- **Line 227** (header text): `Customize Shortcuts`
- **Line 235** (placeholder): `Search shortcuts...`

### app\templates\setup\initial_setup.html

Issues: 1

- **Line 61** (header text): `Welcome to TimeTracker`

### app\templates\tasks\list.html

Issues: 9

- **Line 264** (button text): `Update Status`
- **Line 284** (button text): `Assign Tasks`
- **Line 304** (button text): `Move Tasks`
- **Line 32** (header text): `Filter Tasks`
- **Line 226** (header text): `Delete Selected Tasks`
- **Line 246** (header text): `Change Status for Selected Tasks`
- **Line 274** (header text): `Assign Selected Tasks`
- **Line 294** (header text): `Move Selected Tasks to Project`
- **Line 99** (title attribute): `Export to CSV`

### app\templates\time_entry_templates\create.html

Issues: 5

- **Line 13** (header text): `Create Time Entry Template`
- **Line 33** (placeholder): `e.g., Daily Standup, Client Meeting`
- **Line 82** (placeholder): `e.g., 1.0, 0.5`
- **Line 97** (placeholder): `Pre-fill notes for this type of time entry`
- **Line 110** (placeholder): `e.g., meeting, development, admin`

### app\templates\time_entry_templates\edit.html

Issues: 5

- **Line 13** (header text): `Edit Template`
- **Line 33** (placeholder): `e.g., Daily Standup, Client Meeting`
- **Line 86** (placeholder): `e.g., 1.0, 0.5`
- **Line 101** (placeholder): `Pre-fill notes for this type of time entry`
- **Line 114** (placeholder): `e.g., meeting, development, admin`

### app\templates\timer\manual_entry.html

Issues: 3

- **Line 99** (button text): `Log Time`
- **Line 82** (placeholder): `What did you work on?`
- **Line 87** (placeholder): `tag1, tag2`

## Summary by Type

- flash message: 242
- header text: 65
- placeholder: 49
- link text: 10
- title attribute: 8
- button text: 7
- alt text: 2
- label text: 1
