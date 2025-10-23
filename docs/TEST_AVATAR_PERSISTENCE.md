# Testing Avatar Persistence

## Quick Test Checklist

Use this checklist to verify that profile pictures persist correctly across container updates.

### Prerequisites

- TimeTracker is running
- At least one user account exists
- You have admin access (if testing other users)

### Test Steps

#### 1. Upload a Profile Picture

1. Log in to TimeTracker
2. Navigate to Profile → Edit Profile
3. Upload a profile picture
4. Save and verify the picture displays

**Expected Result:** ✅ Avatar displays in header and profile page

---

#### 2. Verify Storage Location

```bash
# Check that the avatar was saved to /data volume
docker-compose exec app ls -la /data/uploads/avatars/

# You should see files like: avatar_1_a1b2c3d4.png
```

**Expected Result:** ✅ Avatar file exists in `/data/uploads/avatars/`

---

#### 3. Test Persistence Across Restart

```bash
# Restart the container
docker-compose restart app

# Wait for container to be healthy
docker-compose ps
```

1. Log back in to TimeTracker
2. Check if your profile picture still displays

**Expected Result:** ✅ Avatar still displays after restart

---

#### 4. Test Persistence Across Rebuild

```bash
# Stop and remove containers
docker-compose down

# Rebuild the image (simulates an update)
docker-compose build app

# Start containers
docker-compose up -d

# Wait for startup
sleep 10
```

1. Log in to TimeTracker
2. Check if your profile picture still displays

**Expected Result:** ✅ Avatar persists even after container rebuild

---

#### 5. Test New Avatar Upload

1. Go to Profile → Edit Profile
2. Upload a different profile picture
3. Verify the new picture displays

**Expected Result:** ✅ New avatar displays correctly

---

#### 6. Test Avatar Removal

1. Go to Profile → Edit Profile
2. Click "Remove current picture"
3. Verify the avatar is removed and initials are shown

**Expected Result:** ✅ Avatar removed, fallback to initials display

---

#### 7. Verify Old Location is Empty (After Migration)

```bash
# Check old location (should be empty after migration)
docker-compose exec app ls -la /app/static/uploads/avatars/ 2>&1
```

**Expected Result:** ✅ Directory doesn't exist or is empty

---

### Test Matrix

| Test Case | Expected Behavior | Status |
|-----------|-------------------|--------|
| Upload avatar | Saved to `/data/uploads/avatars/` | ⬜ |
| Display avatar | Shows in header & profile | ⬜ |
| Container restart | Avatar persists | ⬜ |
| Container rebuild | Avatar persists | ⬜ |
| Upload new avatar | Old file removed, new file saved | ⬜ |
| Remove avatar | File deleted, fallback to initials | ⬜ |
| Volume check | Files in `/data/uploads/avatars/` | ⬜ |

### Troubleshooting

#### Avatar doesn't display after upload

```bash
# Check file permissions
docker-compose exec app ls -la /data/uploads/avatars/

# Fix permissions if needed
docker-compose exec app chown -R app:app /data/uploads/avatars/
docker-compose exec app chmod -R 755 /data/uploads/avatars/
```

#### Avatar lost after rebuild

```bash
# Verify volume is mounted
docker inspect timetracker-app | grep -A 10 Mounts

# Check if app_data volume exists
docker volume ls | grep app_data

# Inspect volume
docker volume inspect timetracker_app_data
```

#### Migration didn't work

```bash
# Re-run migration script with verbose output
docker-compose run --rm app python /app/docker/migrate-avatar-storage.py

# Manually check both locations
docker-compose exec app ls -la /app/static/uploads/avatars/
docker-compose exec app ls -la /data/uploads/avatars/
```

### Automated Test Script

You can also run this automated test (save as `test_avatar_persistence.sh`):

```bash
#!/bin/bash

echo "Testing Avatar Persistence..."
echo ""

# Test 1: Check volume mount
echo "1. Checking volume mount..."
if docker inspect timetracker-app | grep -q "/data"; then
    echo "   ✅ Volume mounted"
else
    echo "   ❌ Volume NOT mounted"
    exit 1
fi

# Test 2: Check directory exists
echo "2. Checking avatar directory..."
if docker-compose exec -T app test -d /data/uploads/avatars; then
    echo "   ✅ Directory exists"
else
    echo "   ❌ Directory NOT found"
    exit 1
fi

# Test 3: Check write permissions
echo "3. Checking write permissions..."
if docker-compose exec -T app touch /data/uploads/avatars/.test 2>/dev/null; then
    docker-compose exec -T app rm /data/uploads/avatars/.test
    echo "   ✅ Directory is writable"
else
    echo "   ❌ Directory NOT writable"
    exit 1
fi

# Test 4: Count avatars
echo "4. Counting avatar files..."
count=$(docker-compose exec -T app sh -c 'ls -1 /data/uploads/avatars/ 2>/dev/null | wc -l')
echo "   ℹ️  Found $count avatar file(s)"

echo ""
echo "✅ All automated checks passed!"
echo "📝 Manual testing required: Upload, restart, rebuild tests"
```

Run with: `bash test_avatar_persistence.sh`

---

**Date:** October 2025  
**Purpose:** Verify profile picture persistence across updates

