# Email Configuration Guide

This guide explains how to configure and use the email functionality in TimeTracker.

## Overview

TimeTracker includes built-in email support for:
- Test emails to verify configuration
- Invoice notifications
- Task assignment notifications
- Weekly time summaries
- Comment mentions
- System alerts

## Configuration Methods

TimeTracker supports two ways to configure email:

### 1. **Database Configuration** (Recommended)
Configure email settings through the admin web interface. Settings are saved to the database and persist between sessions.

**Advantages:**
- No server restart required for changes
- Easy to update via web interface
- Settings persist in database
- Can be changed by admins without server access

**To Use:**
1. Navigate to Admin → Email Configuration
2. Check "Enable Database Email Configuration"
3. Fill in the form and save

### 2. **Environment Variables** (Fallback)
Configure email settings through environment variables. These serve as defaults when database configuration is disabled.

**Advantages:**
- More secure for sensitive credentials
- Standard configuration method
- Works without database access

**To Use:**
Add settings to your `.env` file or environment

---

## Configuration Hierarchy

Email settings are loaded in this order (highest priority first):

1. **Database Settings** (when `mail_enabled` is `True` in settings table)
2. **Environment Variables** (fallback)
3. **Default Values**

## Database Configuration

Email settings are configured through environment variables. Add these to your `.env` file or set them in your environment:

### Basic SMTP Configuration

```bash
# SMTP Server Settings
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USE_SSL=false

# Authentication
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# Sender Information
MAIL_DEFAULT_SENDER=noreply@yourdomain.com

# Optional: Maximum emails per connection
MAIL_MAX_EMAILS=100
```

### Configuration Options

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `MAIL_SERVER` | SMTP server hostname | `localhost` | Yes |
| `MAIL_PORT` | SMTP server port | `587` | Yes |
| `MAIL_USE_TLS` | Use TLS encryption | `true` | No |
| `MAIL_USE_SSL` | Use SSL encryption | `false` | No |
| `MAIL_USERNAME` | SMTP username for authentication | None | Yes (for most providers) |
| `MAIL_PASSWORD` | SMTP password | None | Yes (for most providers) |
| `MAIL_DEFAULT_SENDER` | Default "From" address | `noreply@timetracker.local` | Yes |
| `MAIL_MAX_EMAILS` | Max emails per SMTP connection | `100` | No |

## Common Email Providers

### Gmail

```bash
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com
```

**Important:** Gmail requires an [App Password](https://support.google.com/accounts/answer/185833) when 2-factor authentication is enabled.

### Outlook / Office 365

```bash
MAIL_SERVER=smtp.office365.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@outlook.com
MAIL_PASSWORD=your-password
MAIL_DEFAULT_SENDER=your-email@outlook.com
```

### SendGrid

```bash
MAIL_SERVER=smtp.sendgrid.net
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=apikey
MAIL_PASSWORD=your-sendgrid-api-key
MAIL_DEFAULT_SENDER=noreply@yourdomain.com
```

### Amazon SES

```bash
MAIL_SERVER=email-smtp.us-east-1.amazonaws.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-smtp-username
MAIL_PASSWORD=your-smtp-password
MAIL_DEFAULT_SENDER=noreply@yourdomain.com
```

Replace `us-east-1` with your AWS region.

### Mailgun

```bash
MAIL_SERVER=smtp.mailgun.org
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=postmaster@yourdomain.mailgun.org
MAIL_PASSWORD=your-mailgun-password
MAIL_DEFAULT_SENDER=noreply@yourdomain.com
```

## Testing Email Configuration

### Using the Admin Panel (Database Configuration)

1. Log in as an administrator
2. Navigate to **Admin** → **Email Configuration**
3. **Configure Settings**:
   - Check "Enable Database Email Configuration"
   - Fill in: Mail Server, Port, Username, Password, etc.
   - Click "Save Configuration"
4. **Test Configuration**:
   - Review the configuration status (should show "configured")
   - Enter your email address in the test form
   - Click "Send Test Email"
   - Check your inbox for the test email

### Using Environment Variables

1. Set environment variables in `.env`
2. Restart the application
3. Navigate to **Admin** → **Email Configuration**
4. Review the configuration status
5. Send a test email

### Using the Command Line

You can also test email configuration programmatically:

```python
from app import create_app
from app.utils.email import send_test_email

app = create_app()
with app.app_context():
    success, message = send_test_email('your-email@example.com', 'Test')
    print(f"Success: {success}")
    print(f"Message: {message}")
```

## Troubleshooting

### Email Not Sending

1. **Check Configuration Status**
   - Go to Admin → Email Configuration
   - Review any errors or warnings displayed

2. **Verify Credentials**
   - Ensure username and password are correct
   - For Gmail, use an App Password, not your regular password

3. **Check Firewall Rules**
   - Ensure outbound connections to SMTP port are allowed
   - Test connectivity: `telnet smtp.gmail.com 587`

4. **Review Logs**
   - Check application logs for email-related errors
   - Look for SMTP authentication or connection errors

5. **TLS/SSL Configuration**
   - Don't enable both `MAIL_USE_TLS` and `MAIL_USE_SSL`
   - Use TLS (port 587) for most modern SMTP servers
   - Use SSL (port 465) only if required by your provider

### Common Error Messages

#### "Mail server not configured"
- Set `MAIL_SERVER` environment variable
- Ensure it's not set to `localhost`

#### "Authentication failed"
- Verify `MAIL_USERNAME` and `MAIL_PASSWORD`
- For Gmail, generate an App Password
- Check if your account requires 2FA

#### "Connection refused"
- Check firewall rules
- Verify SMTP port is correct (587 for TLS, 465 for SSL, 25 for unencrypted)
- Ensure server can reach SMTP host

#### "TLS/SSL handshake failed"
- Check `MAIL_USE_TLS` and `MAIL_USE_SSL` settings
- Ensure only one is enabled
- Verify port matches TLS/SSL setting

## Security Best Practices

1. **Use App Passwords**
   - Never use your main account password
   - Generate app-specific passwords for Gmail, Outlook, etc.

2. **Use Environment Variables**
   - Never commit email credentials to version control
   - Use `.env` file (excluded from git)
   - Use secrets management in production

3. **Use Dedicated Email Service**
   - For production, use SendGrid, Amazon SES, or similar
   - These provide better deliverability and monitoring
   - Personal email accounts may have sending limits

4. **Configure SPF/DKIM/DMARC**
   - Set up proper DNS records for your sending domain
   - Improves email deliverability
   - Reduces likelihood of emails being marked as spam

5. **Limit Default Sender**
   - Use a proper noreply address
   - Don't use personal email as default sender

## Email Templates

Email templates are located in `app/templates/email/`. Available templates:

- `test_email.html` - Test email template
- `overdue_invoice.html` - Overdue invoice notification
- `task_assigned.html` - Task assignment notification
- `weekly_summary.html` - Weekly time summary
- `comment_mention.html` - Comment mention notification

### Customizing Templates

To customize email templates:

1. Navigate to `app/templates/email/`
2. Edit the HTML template files
3. Use Jinja2 syntax for dynamic content
4. Test your changes using the admin panel

Example:
```html
<!DOCTYPE html>
<html>
<body>
    <h1>Hello {{ user.display_name }}!</h1>
    <p>{{ message }}</p>
</body>
</html>
```

## API Reference

### `send_email(subject, recipients, text_body, html_body=None, sender=None, attachments=None)`

Send an email message.

**Parameters:**
- `subject` (str): Email subject line
- `recipients` (list): List of recipient email addresses
- `text_body` (str): Plain text email body
- `html_body` (str, optional): HTML email body
- `sender` (str, optional): Sender email address (defaults to `MAIL_DEFAULT_SENDER`)
- `attachments` (list, optional): List of (filename, content_type, data) tuples

**Example:**
```python
from app.utils.email import send_email

send_email(
    subject='Welcome to TimeTracker',
    recipients=['user@example.com'],
    text_body='Welcome to our application!',
    html_body='<p>Welcome to our application!</p>'
)
```

### `test_email_configuration()`

Test email configuration and return status.

**Returns:**
- `dict`: Configuration status with keys:
  - `configured` (bool): Whether email is properly configured
  - `settings` (dict): Current email settings
  - `errors` (list): Configuration errors
  - `warnings` (list): Configuration warnings

**Example:**
```python
from app.utils.email import test_email_configuration

status = test_email_configuration()
if status['configured']:
    print("Email is configured!")
else:
    print("Errors:", status['errors'])
```

### `send_test_email(recipient_email, sender_name='TimeTracker Admin')`

Send a test email to verify configuration.

**Parameters:**
- `recipient_email` (str): Email address to send test to
- `sender_name` (str, optional): Name of sender

**Returns:**
- `tuple`: (success: bool, message: str)

**Example:**
```python
from app.utils.email import send_test_email

success, message = send_test_email('test@example.com')
if success:
    print("Test email sent!")
else:
    print("Error:", message)
```

## Docker Configuration

### Option 1: Database Configuration (Recommended)

1. Start TimeTracker with Docker
2. Log in as administrator
3. Navigate to Admin → Email Configuration
4. Configure email through the web interface
5. No restart needed!

### Option 2: Environment Variables

When running TimeTracker in Docker, add email configuration to your `docker-compose.yml`:

```yaml
services:
  app:
    environment:
      - MAIL_SERVER=smtp.gmail.com
      - MAIL_PORT=587
      - MAIL_USE_TLS=true
      - MAIL_USERNAME=${MAIL_USERNAME}
      - MAIL_PASSWORD=${MAIL_PASSWORD}
      - MAIL_DEFAULT_SENDER=${MAIL_DEFAULT_SENDER}
```

Then set the values in your `.env` file:

```bash
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=noreply@yourdomain.com
```

**Note:** Database configuration (Option 1) takes precedence when enabled.

## Advanced Configuration

### Rate Limiting

The email test endpoint is rate-limited to 5 requests per minute to prevent abuse.

### Asynchronous Sending

Emails are sent asynchronously in background threads to avoid blocking the main application. This is handled automatically.

### Connection Pooling

Flask-Mail manages SMTP connection pooling automatically based on `MAIL_MAX_EMAILS` setting.

## Support

For issues with email configuration:

1. Check the [GitHub Issues](https://github.com/yourusername/timetracker/issues)
2. Review application logs
3. Test with a simple SMTP client to verify credentials
4. Check your email provider's documentation

## Related Documentation

- [Admin Panel Guide](ADMIN_GUIDE.md)
- [Configuration Guide](CONFIGURATION.md)
- [Deployment Guide](../DEPLOYMENT_GUIDE.md)

