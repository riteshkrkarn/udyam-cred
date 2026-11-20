# 🔧 Postman Setup Guide - Token Management

## Problem
Token not persisting after login? Here's how to fix it.

---

## Step 1: Import the Fixed Collection

1. Open **Postman**
2. Click **Import** (top-left)
3. Select **UdyamCred-Fixed.postman_collection.json**
4. Click **Import**

---

## Step 2: Set Up Environment

### Option A: Use Collection Variables (Recommended - Easier)
1. After importing, open the collection
2. Go to **Variables** tab
3. You'll see three variables:
   - `base_url` = `http://localhost:8000`
   - `token` = (empty)
   - `refresh_token` = (empty)
4. These are already configured - **no changes needed**

### Option B: Create an Environment (Alternative)
1. Click **Environments** (left sidebar)
2. Click **Create**
3. Name it: `UdyamCred`
4. Add variables:
   ```
   base_url = http://localhost:8000
   token = (empty)
   refresh_token = (empty)
   ```
5. Click **Save**
6. In top-right, select this environment from dropdown

---

## Step 3: Test Login Flow

### 1. Register First
1. Open the **Register New User** request
2. Change the email to something unique (e.g., `merchant_001@example.com`)
3. Click **Send**
4. You should get a 201 response with user data

### 2. Login (THIS SAVES YOUR TOKEN)
1. Open the **Login (AUTO TOKEN SAVE)** request
2. **Make sure the email/password match** what you registered
3. Click **Send**
4. Look at the **Test Results** tab at the bottom (after sending)
5. You should see:
   ```
   Login Response: {"access_token": "...", "refresh_token": "...", ...}
   Token saved: eyJ0eXAiOiJKV1QiLC...
   ```

### 3. Verify Token Was Saved
1. In Postman, go to **Collection → Variables**
2. Scroll down and check the **Current Value** column
3. You should see your token is now filled in (long string starting with `eyJ`)

---

## Step 4: Use Token in Protected Endpoints

### Test 1: Check Your User Info
1. Open **Get Current User (Test Auth)**
2. Notice the header already has: `Authorization: Bearer {{token}}`
3. Click **Send**
4. Should get 200 response with your user info

### Test 2: Reconcile a Shop
1. Open any **Reconcile** request
2. The token is already in the Authorization header
3. Click **Send**
4. Should get a reconciliation verdict

---

## Troubleshooting

### ❌ "Could not validate credentials" or 401 error

**Cause 1: Token is empty**
- Go to **Collections → Variables**
- Check if `token` has a value
- If empty, re-run the **Login** request

**Cause 2: Token expired**
- Run the **Refresh Token** request
- This will update your token automatically

**Cause 3: Wrong Authorization header format**
- Check header is exactly: `Authorization: Bearer {{token}}`
- Not: `Bearer token={{token}}` or just `{{token}}`

### ❌ Test Results not showing after login

**Solution: Make sure Tests are enabled**
1. After sending Login request, look at bottom tabs
2. Click **Test Results** tab
3. If nothing shows, refresh the page or re-send

### ❌ "Invalid GSTIN" error in reconciliation

**This is correct!** Test with a valid GSTIN: `29AABCR0102R1Z5`

---

## Quick Testing Sequence

```
1. Register New User
   ↓
2. Login (AUTO TOKEN SAVE)
   ↓
3. Get Current User (verify token works)
   ↓
4. Try reconciliation endpoints
```

---

## Manual Token Management (If Auto Fails)

If the test script doesn't run automatically:

### After Login:
1. Copy the `access_token` from response
2. Go to **Collections → Variables**
3. Click the `token` row
4. Paste into **Current Value** field
5. Click **Save** (Ctrl+S)

### Repeat for Refresh Token:
1. Copy the `refresh_token` from response
2. Go to **Collections → Variables**
3. Click the `refresh_token` row
4. Paste into **Current Value** field
5. Click **Save**

---

## How Auto-Save Works

The **Login** request has a **Test** script:
```javascript
if (pm.response.code === 200) {
    var jsonData = pm.response.json();
    pm.environment.set('token', jsonData.access_token);
    pm.environment.set('refresh_token', jsonData.refresh_token);
}
```

This runs **after** you get a successful response and automatically updates the variables.

---

## Token Types

### Access Token
- Used for: Protected endpoints (`/reconcile`, `/shops/me`)
- Lifetime: 60 minutes (default)
- Goes in: `Authorization: Bearer {token}` header
- Expires? Use refresh token to get new one

### Refresh Token
- Used for: Getting new access token
- Lifetime: 7 days (or 30 if `remember_me: true`)
- Rotates: Each refresh gives you a new refresh token
- Revoked on: Logout

---

## Common Flow

```
Start
 ↓
Register / Login
 ↓
Get token (stored in {{token}})
 ↓
Use token for all protected endpoints
 ↓
Token expires after 1 hour?
 ↓
Call Refresh endpoint
 ↓
Get new token (auto-saved)
 ↓
Continue using protected endpoints
```

---

## Still Stuck?

Try this:

1. **Delete and re-import** the collection
2. **Restart Postman**
3. **Make sure backend is running**:
   ```powershell
   cd d:\Hackathon\udyam-cred\be
   .\.venv\Scripts\Activate.ps1
   uvicorn main:app --reload
   ```
4. **Check backend console** for errors

If backend is running and you see errors there, there might be a code issue. Let me know what error you see!
