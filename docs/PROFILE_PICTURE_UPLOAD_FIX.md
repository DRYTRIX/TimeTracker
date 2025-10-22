# Profile Picture Upload Fix

## Issues Addressed

This document describes the fixes applied to resolve two issues with profile picture uploads:

1. **Preview not updating** - The image preview didn't update when selecting a new profile picture
2. **413 Request Entity Too Large** - Nginx was rejecting uploads larger than 1MB (default limit)

## Changes Made

### 1. Nginx Configuration Update

**File**: `nginx/conf.d/https.conf`

Added `client_max_body_size` directive to allow uploads up to 10MB:

```nginx
# Allow larger file uploads (profile pictures, logos, etc.)
client_max_body_size 10M;
```

This change:
- Increases the upload limit from nginx's default 1MB to 10MB
- Applies to all file uploads (profile pictures, company logos, etc.)
- Provides a buffer above the application's 5MB limit for better error handling

### 2. Profile Picture Preview JavaScript

**File**: `app/templates/auth/edit_profile.html`

Added preview functionality with the following features:

#### Changes:
1. Added `id="avatar-preview"` to the profile image element
2. Added `onchange="previewAvatar(this)"` to the file input
3. Created `previewAvatar()` JavaScript function with:
   - File size validation (5MB limit)
   - File type validation (PNG, JPG, JPEG, GIF, WEBP)
   - Real-time image preview using FileReader API
   - User-friendly error messages

#### Code Added:
```javascript
function previewAvatar(input) {
    const preview = document.getElementById('avatar-preview');
    
    if (input.files && input.files[0]) {
        const file = input.files[0];
        
        // Validate file size (5MB limit)
        if (file.size > 5 * 1024 * 1024) {
            alert('File size must be less than 5MB');
            input.value = '';
            return;
        }
        
        // Validate file type
        const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp'];
        if (!allowedTypes.includes(file.type)) {
            alert('Invalid file type. Please select a valid image file (PNG, JPG, GIF, or WEBP).');
            input.value = '';
            return;
        }
        
        // Read and display the image
        const reader = new FileReader();
        reader.onload = function(e) {
            preview.src = e.target.result;
        };
        reader.readAsDataURL(file);
    }
}
```

## How to Apply These Changes

### If Using Docker

1. The nginx configuration change will be applied automatically when you restart the containers:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

2. The template change is also applied immediately since templates are mounted as volumes in development or baked into the image in production.

### If Running Locally

1. Restart your nginx server to apply the configuration change:
   ```bash
   sudo nginx -s reload
   # or
   sudo systemctl restart nginx
   ```

2. Clear your browser cache or do a hard refresh (Ctrl+F5) to ensure the updated JavaScript is loaded.

## Testing

### Manual Testing

1. **Test Preview Functionality**:
   - Navigate to Profile → Edit Profile
   - Click the file input to select an image
   - Verify the preview updates immediately to show your selected image
   - Try uploading files larger than 5MB - should show error message
   - Try uploading invalid file types - should show error message

2. **Test Upload**:
   - Select a valid image (< 5MB, PNG/JPG/GIF/WEBP)
   - Verify preview updates
   - Click "Save Changes"
   - Verify the upload succeeds without 413 error
   - Verify the profile picture displays correctly after save

### Automated Tests

Run the existing test suite which includes profile picture tests:

```bash
pytest tests/test_profile_avatar.py -v
```

The tests cover:
- Avatar upload functionality
- Avatar removal functionality
- File size validation (handled by backend)
- File type validation (handled by backend)

## Browser Compatibility

The FileReader API used for image preview is supported in:
- Chrome 7+
- Firefox 3.6+
- Safari 6+
- Edge (all versions)
- Opera 12+

This covers all modern browsers and provides graceful degradation for older browsers (preview won't work but upload will still function).

## Security Considerations

1. **File Size Limits**:
   - Client-side: 5MB (JavaScript validation)
   - Server-side: 5MB (Python validation in `app/routes/auth.py`)
   - Nginx: 10MB (allows buffer for proper error handling)

2. **File Type Restrictions**:
   - Client-side: PNG, JPG, JPEG, GIF, WEBP
   - Server-side: Same validation enforced
   - SVG is explicitly excluded to prevent XSS attacks

3. **File Storage**:
   - Avatars stored in `app/static/uploads/avatars/`
   - Unique filenames generated using UUID to prevent conflicts
   - Old avatars automatically deleted when new ones are uploaded

## Related Files

- `app/routes/auth.py` - Backend upload handling
- `app/models/user.py` - User model with avatar methods
- `app/templates/auth/profile.html` - Profile view page
- `tests/test_profile_avatar.py` - Automated tests
- `migrations/versions/020_add_user_avatar.py` - Database migration

## Additional Notes

- All docker-compose configurations use the same nginx config directory (`./nginx/conf.d`), so this fix applies to all deployment scenarios
- The 10MB nginx limit also benefits company logo uploads (which use the same 5MB limit)
- Preview validation matches server-side validation to provide immediate user feedback

