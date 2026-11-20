# UdyamCred - Setup & Testing Guide

## Quick Start (3 Terminal Windows)

### Terminal 1: Backend
```powershell
cd d:\Hackathon\udyam-cred\be
.\.venv\Scripts\Activate.ps1
uvicorn main:app --reload
```
Backend runs on `http://localhost:8000`

### Terminal 2: ML (Optional - for data generation)
```powershell
cd d:\Hackathon\udyam-cred\ml
.\venv\Scripts\Activate.ps1
python demo.py
```

### Terminal 3: Postman or API Testing
Use any HTTP client to test the API endpoints below.

---

## API Endpoints & Testing

### 1. Health Check (No Auth)
```
GET http://localhost:8000/health
```
Expected response:
```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

### 2. Register a New User
```
POST http://localhost:8000/auth/register
Content-Type: application/json

{
  "email": "merchant@shop.com",
  "password": "SecurePass123!",
  "role": "borrower"
}
```
Available roles: `borrower`, `officer`, `approver`, `auditor`

Response:
```json
{
  "id": 1,
  "email": "merchant@shop.com",
  "role": "borrower"
}
```

### 3. Login
```
POST http://localhost:8000/auth/login
Content-Type: application/json

{
  "email": "merchant@shop.com",
  "password": "SecurePass123!",
  "remember_me": false
}
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "random_string_here",
  "expires_in": 3600
}
```

**Copy the `access_token` for protected endpoints.**

### 4. Get Current User Info
```
GET http://localhost:8000/shops/me
Authorization: Bearer {access_token}
```

Response:
```json
{
  "id": 1,
  "email": "merchant@shop.com",
  "role": "borrower"
}
```

### 5. Reconcile a Shop (Protected - Main Feature)
```
POST http://localhost:8000/reconcile
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "shop_id": "S001",
  "gstin": "29AABCR0102R1Z5",
  "shop_category": "general_store",
  "purchases": 500000,
  "gst_turnover": 600000,
  "upi_turnover": 450000
}
```

**Available shop categories:**
- general_store
- pharmacy
- electronics
- apparel
- hardware
- furniture
- printing
- textiles

Response:
```json
{
  "shop_id": "S001",
  "gstin_valid": true,
  "shop_category": "general_store",
  "margin_low": 0.15,
  "margin_high": 0.30,
  "goods_sold": 500000.0,
  "expected_sales_low": 384615.38,
  "expected_sales_high": 434782.61,
  "reported_sales": 600000.0,
  "upi_turnover": 450000.0,
  "gst_turnover": 600000.0,
  "verdict": "flagged",
  "reason": "declared sales above expected margin band"
}
```

### 6. Refresh Token
```
POST http://localhost:8000/auth/refresh
Content-Type: application/json

{
  "refresh_token": "{refresh_token_from_login}"
}
```

### 7. Logout
```
POST http://localhost:8000/auth/logout
Content-Type: application/json

{
  "refresh_token": "{refresh_token_from_login}"
}
```

---

## Backend-ML Integration

### Current State
- **Backend**: Validates shops using reconciliation logic (margin bands, GSTIN, UPI checks)
- **ML**: Generates synthetic shop data for testing

### How They Connect

1. **Data Generation** (ML → Backend)
   - Run `python demo.py` in ML folder to generate test data
   - Use generated data to test `/reconcile` endpoint

2. **ML Model Integration** (Future)
   - Import ML models in `be/app/reconciliation.py`
   - Add ML scoring alongside rule-based validation
   - Example:
     ```python
     from ml.generator import SyntheticDataGenerator
     
     # In reconcile function:
     ml_risk_score = model.predict(features)
     ```

### Test Data Examples

#### Approved Shop
```json
{
  "shop_id": "approved_001",
  "gstin": "29AABCR0102R1Z5",
  "shop_category": "pharmacy",
  "purchases": 200000,
  "gst_turnover": 250000,
  "upi_turnover": 150000
}
```
*Expected: `approved` - sales within margin band (25-40% for pharmacy)*

#### Flagged Shop (Sales Suppression)
```json
{
  "shop_id": "flagged_001",
  "gstin": "29AABCR0102R1Z5",
  "shop_category": "general_store",
  "purchases": 500000,
  "gst_turnover": 350000,
  "upi_turnover": 400000
}
```
*Expected: `flagged` - reported sales below expected band*

#### Flagged Shop (UPI Anomaly)
```json
{
  "shop_id": "flagged_002",
  "gstin": "29AABCR0102R1Z5",
  "shop_category": "electronics",
  "purchases": 1000000,
  "gst_turnover": 1100000,
  "upi_turnover": 1500000
}
```
*Expected: `flagged` - UPI turnover exceeds declared GST sales*

#### Invalid GSTIN
```json
{
  "shop_id": "rejected_001",
  "gstin": "INVALID123",
  "shop_category": "hardware",
  "purchases": 300000,
  "gst_turnover": 400000,
  "upi_turnover": 250000
}
```
*Expected: `rejected` - GSTIN format/checksum failed*

---

## Postman Collection (Copy & Paste)

Create a Postman Collection with these requests:

### Setup
1. Create a new collection: "UdyamCred"
2. Set a collection variable: `token` (leave empty initially)
3. Set a base URL variable: `base_url` = `http://localhost:8000`

### Requests

#### 1. Health Check
```
GET {{base_url}}/health
```

#### 2. Register
```
POST {{base_url}}/auth/register
Content-Type: application/json

{
  "email": "test@shop.com",
  "password": "TestPass123!",
  "role": "borrower"
}
```

#### 3. Login
```
POST {{base_url}}/auth/login
Content-Type: application/json

{
  "email": "test@shop.com",
  "password": "TestPass123!",
  "remember_me": false
}
```
**Post-test script:**
```javascript
var jsonData = pm.response.json();
pm.collectionVariables.set("token", jsonData.access_token);
pm.collectionVariables.set("refresh_token", jsonData.refresh_token);
```

#### 4. Me
```
GET {{base_url}}/shops/me
Authorization: Bearer {{token}}
```

#### 5. Reconcile - Approved
```
POST {{base_url}}/reconcile
Authorization: Bearer {{token}}
Content-Type: application/json

{
  "shop_id": "shop_approved_1",
  "gstin": "29AABCR0102R1Z5",
  "shop_category": "pharmacy",
  "purchases": 200000,
  "gst_turnover": 250000,
  "upi_turnover": 150000
}
```

#### 6. Reconcile - Flagged
```
POST {{base_url}}/reconcile
Authorization: Bearer {{token}}
Content-Type: application/json

{
  "shop_id": "shop_flagged_1",
  "gstin": "29AABCR0102R1Z5",
  "shop_category": "general_store",
  "purchases": 500000,
  "gst_turnover": 350000,
  "upi_turnover": 400000
}
```

#### 7. Reconcile - Rejected
```
POST {{base_url}}/reconcile
Authorization: Bearer {{token}}
Content-Type: application/json

{
  "shop_id": "shop_rejected_1",
  "gstin": "INVALID123",
  "shop_category": "hardware",
  "purchases": 300000,
  "gst_turnover": 400000,
  "upi_turnover": 250000
}
```

---

## Common Issues & Fixes

### ML Module Not Found
```powershell
# Make sure you're in the right venv
cd d:\Hackathon\udyam-cred\ml
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Backend Port Already in Use
```powershell
# Run on a different port
uvicorn main:app --reload --port 8001
```

### Database Error
```powershell
# Reseed the database
python scripts/seed.py
```

### 401 Unauthorized
- Make sure you're sending the `Authorization: Bearer {token}` header
- Token may have expired (use refresh endpoint)

### Invalid GSTIN
Test with a valid GSTIN format: `29AABCR0102R1Z5`
Invalid formats: `INVALID123`, `12345`

---

## Architecture Overview

```
┌─────────────────────────────────────────────┐
│           Frontend (React/Vue)              │
└─────────────┬───────────────────────────────┘
              │ HTTP/REST
┌─────────────▼───────────────────────────────┐
│        Backend (FastAPI)                    │
│  ┌──────────────────────────────────────┐   │
│  │ Auth (JWT + Refresh Tokens)          │   │
│  │ Reconciliation Logic (Rule-based)    │   │
│  │ Database (SQLAlchemy + SQLite)       │   │
│  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
              │ (Optional Integration)
┌─────────────▼───────────────────────────────┐
│        ML Module (Python)                   │
│  ┌──────────────────────────────────────┐   │
│  │ Synthetic Data Generator             │   │
│  │ Feature Builder                      │   │
│  │ ML Models (TBD)                      │   │
│  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

---

## Next Steps

1. **Test all endpoints** with Postman
2. **Review reconciliation logic** in `be/app/reconciliation.py`
3. **Check ML output** by running `python ml/demo.py`
4. **Integrate ML scoring** into backend when ready
5. **Add frontend** to consume the API

Enjoy testing!
