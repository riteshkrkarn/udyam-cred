# 🚀 Quick Start - Run Everything

## Step 1: Open 3 PowerShell Windows

### Window 1: Backend API
```powershell
cd d:\Hackathon\udyam-cred\be
.\.venv\Scripts\Activate.ps1
uvicorn main:app --reload
```
✅ Backend ready at `http://localhost:8000`

### Window 2: ML Module (Optional)
```powershell
cd d:\Hackathon\udyam-cred\ml
.\venv\Scripts\Activate.ps1
python demo.py
```
✅ View generated synthetic data for testing

### Window 3: Postman/Browser
1. Download Postman: https://www.postman.com/downloads/
2. Import collection: `UdyamCred.postman_collection.json`
3. Set environment variables:
   - `base_url` = `http://localhost:8000`
   - `token` = (auto-filled after login)

---

## Testing Sequence (Use Postman)

### 1. Health Check
```
GET http://localhost:8000/health
```
Should return: `{"status": "ok", "version": "0.1.0"}`

### 2. Register User
```
POST http://localhost:8000/auth/register
{
  "email": "merchant@example.com",
  "password": "SecurePass123!",
  "role": "borrower"
}
```

### 3. Login
```
POST http://localhost:8000/auth/login
{
  "email": "merchant@example.com",
  "password": "SecurePass123!",
  "remember_me": false
}
```
**Save the `access_token`** from response

### 4. Test Reconciliation
Use any of these test cases with your token:

#### ✅ Approved Shop
```json
{
  "shop_id": "shop_1",
  "gstin": "29AABCR0102R1Z5",
  "shop_category": "pharmacy",
  "purchases": 200000,
  "gst_turnover": 250000,
  "upi_turnover": 150000
}
```

#### ⚠️ Flagged Shop
```json
{
  "shop_id": "shop_2",
  "gstin": "29AABCR0102R1Z5",
  "shop_category": "general_store",
  "purchases": 500000,
  "gst_turnover": 350000,
  "upi_turnover": 200000
}
```

#### ❌ Rejected Shop
```json
{
  "shop_id": "shop_3",
  "gstin": "INVALID",
  "shop_category": "hardware",
  "purchases": 300000,
  "gst_turnover": 400000,
  "upi_turnover": 250000
}
```

---

## Backend-ML Integration

### Current Architecture
- **Backend (FastAPI)**: Handles auth, reconciliation rules, database
- **ML (Python)**: Generates synthetic data for testing

### How to Connect
1. ML generates shop data → 2. Backend validates using reconciliation → 3. Returns verdict

### Example Usage
```python
# From Postman, send generated ML data to /reconcile endpoint
# Backend will validate and return verdict (approved/flagged/rejected)
```

---

## Troubleshooting

### Backend won't start
```powershell
# Check if port 8000 is in use
netstat -ano | findstr :8000

# Use different port
uvicorn main:app --reload --port 8001
```

### ML import errors
```powershell
# Make sure venv is activated
cd ml
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 401 Unauthorized in Postman
- Make sure you logged in and got `access_token`
- Add header: `Authorization: Bearer {token}`

### Database errors
```powershell
# Reset database
cd be
python scripts/seed.py
```

---

## File Structure
```
udyam-cred/
├── be/                    # Backend (FastAPI)
│   ├── main.py           # Entry point
│   ├── app/              # Application code
│   ├── scripts/          # Database setup
│   └── requirements.txt
├── ml/                    # ML Module (Data generation)
│   ├── demo.py           # Test data generator
│   ├── generator.py      # Main generator
│   └── requirements.txt
├── fe/                    # Frontend (React/Vue)
├── SETUP_AND_TEST.md     # Full testing guide
├── RUN_ME.md             # This file
└── UdyamCred.postman_collection.json  # Postman collection
```

---

## API Endpoints Summary

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/health` | ❌ | Health check |
| POST | `/auth/register` | ❌ | Create account |
| POST | `/auth/login` | ❌ | Get tokens |
| POST | `/auth/refresh` | ❌ | Refresh access token |
| POST | `/auth/logout` | ❌ | Revoke refresh token |
| GET | `/shops/me` | ✅ | Get current user |
| POST | `/reconcile` | ✅ | Verify shop (Main feature) |

---

## Database Pre-loaded Data

When you run `python scripts/seed.py`, it creates:
- 4 test users (roles: borrower, officer, approver, auditor)
- 10 test shops with reconciliation results
- Database: `udyamcred.db` (SQLite)

---

## Next Steps

1. ✅ Run backend & test endpoints
2. ✅ Verify all reconciliation scenarios (approved/flagged/rejected)
3. ✅ Generate ML data with `python demo.py`
4. ✅ Integrate ML scoring into backend
5. ✅ Build frontend UI

Enjoy! 🎉
