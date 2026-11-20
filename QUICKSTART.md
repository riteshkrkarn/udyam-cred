<<<<<<< HEAD
# UdyamCred — Quick Start (Stage 1)

Run the full stack locally in two terminals.

---

## Terminal 1: Backend (FastAPI)
=======
# UdyamCred - Quick Start Guide

Get the entire system running locally in 10 minutes.

## Prerequisites

- Python 3.8+
- Node.js 16+
- Git

## Installation & Startup

### 1️⃣ Terminal 1: ML (Model Training)

```bash
cd ml

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install pandas numpy scikit-learn scipy python-dotenv

# Generate data and train models
python run_generator.py --gen all --with-features
python train_models.py

# Expected output:
# ✓ Scorecard AUC: 0.75-0.85
# ✓ Capacity MAE: Rs 2,000-5,000
# ✓ Models saved to ml/models/
```

### 2️⃣ Terminal 2: Backend (API Server)
>>>>>>> de69834c8ed46eccb822f01b7efdfdc8f68a3f69

```bash
cd be

<<<<<<< HEAD
# First time only: create virtual environment
python -m venv .venv
.venv\Scripts\activate

# First time only: install dependencies
pip install -r requirements.txt

# First time only: initialize database
python scripts/seed.py --seed 42 --shops 10

# Run the server (every time)
uvicorn main:app --reload
```

**Expected output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

API docs at: `http://localhost:8000/docs`

---

## Terminal 2: Frontend (React + Vite)
=======
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies (when available)
pip install fastapi uvicorn sqlalchemy pydantic python-jose

# Run API server
python -m uvicorn api.main:app --reload --port 8000

# Expected output:
# INFO:     Uvicorn running on http://127.0.0.1:8000
# ✓ API ready for requests
```

### 3️⃣ Terminal 3: Frontend (Web UI)
>>>>>>> de69834c8ed46eccb822f01b7efdfdc8f68a3f69

```bash
cd fe

<<<<<<< HEAD
# First time only: install dependencies
npm install

# First time only: copy environment file
copy .env.example .env.local

# Run the dev server (every time)
npm run dev
```

**Expected output:**
```
  VITE v8.3.8  ready in 741 ms

  ➜  Local:   http://localhost:5174/
```

App at: `http://localhost:5174`

---

## Test It

### Demo Mode (no backend required)
1. Go to `http://localhost:5174`
2. Click "Sign in"
3. Choose **Demo** → pick a role
4. Explore the landing page and stock check

### Real Auth (backend required)
1. Both servers must be running (see above)
2. Click "Sign in"
3. Choose **Real auth** → register/login
4. Try the stock check or apply form

---

## Frontend-only (no backend)

The frontend works standalone in **demo mode**. Just run the frontend:

```bash
cd fe
npm run dev
```

All features work locally:
- ✓ Landing page
- ✓ Stock check (local reconciliation engine)
- ✓ Apply form
- ✓ Demo role picker
- ✓ GSTIN validator

To enable real auth later, start the backend and switch to **Real auth** tab in the sign-in dialog.

---

## Stopping

- **Backend:** Press `Ctrl+C` in the backend terminal
- **Frontend:** Press `Ctrl+C` in the frontend terminal

Both save state to databases/local storage so you can stop and restart without losing data.

---

## Troubleshooting

**Backend won't start:**
```bash
# Check if port 8000 is in use
netstat -ano | findstr :8000

# Kill the process if needed (use PID from above)
taskkill /PID <PID> /F

# Try again
uvicorn main:app --reload
```

**Frontend won't start:**
```bash
# Check if port 5174 is in use (try 5173, 5175, etc.)
# Or kill existing node processes:
taskkill /F /IM node.exe
npm run dev
```

**Backend connection refused:**
- Is the backend running? (`http://localhost:8000/docs` should load)
- Check `.env.local` in the frontend: `VITE_API_URL=http://localhost:8000`
- Check browser console for network errors (DevTools → Network tab)

**Tokens not persisting:**
- Check `localStorage` in DevTools → Application
- Keys: `udyam_access_token`, `udyam_refresh_token`
- If empty, try logging in again

---

## What's Connected

| Feature | Status |
|---|---|
| Landing page | ✓ Working |
| Demo auth | ✓ Working |
| Real auth (login/register) | ✓ Ready (backend required) |
| Health check | ✓ Working |
| Stock reconciliation (local) | ✓ Working |
| Stock reconciliation (backend) | ⏳ Ready in Stage 2 |
| Apply form | ✓ Working |
| Result page | ⏳ Placeholder (full logic in Stage 2) |

---

## Next Steps (Stage 2)

- Full apply wizard with stepper
- Bank decision screens
- Override and audit workflows
- Real reconciliation via backend API
- Document upload
- Scoring engine integration
=======
# Install dependencies
npm install

# Create environment file
echo 'NEXT_PUBLIC_API_URL=http://localhost:8000/api' > .env.local

# Run dev server
npm run dev

# Expected output:
# ▲ Next.js ready on http://localhost:3000
# ✓ UI ready for browsing
```

## Testing the Integration

### 1. Check Backend Health

```bash
curl http://localhost:8000/health
# Expected: {"status": "ok"}
```

### 2. Test ML Models

```bash
python -c "
import pickle
scorecard = pickle.load(open('ml/models/scorecard.pkl', 'rb'))
print('✓ Scorecard loaded')
print(f'  Coefficients: {scorecard.coef_[0][:5]}...')
"
```

### 3. Open Web UI

```
http://localhost:3000
```

Expected screens:
- Landing page
- Application form
- Scoring results

## Common Tasks

### Generate New Data

```bash
cd ml
python run_generator.py --gen all --with-features
# Creates: ml/data/features_gen*.csv, labels_gen*.csv
```

### Retrain Models

```bash
cd ml
python train_models.py
# Creates: ml/models/scorecard.pkl, capacity_model.pkl
```

### API Request Example

```bash
curl -X POST http://localhost:8000/api/scoring/score \
  -H "Content-Type: application/json" \
  -d '{
    "shop_id": "test_001",
    "upi_inflow": 50000,
    "gst_turnover": 80000,
    "stock_value": 25000,
    "family_size": 4
  }'
```

### View API Documentation

```
http://localhost:8000/docs
```

Auto-generated Swagger UI with all endpoints.

## File Structure

```
.
├── ml/                    ← ML models & data
│   ├── data/             ← Generated datasets
│   ├── models/           ← Trained models (after training)
│   └── MODEL_TRAINING.md ← Full training guide
├── be/                    ← Backend (Python/FastAPI)
│   └── api/
│       └── main.py       ← API entry point
├── fe/                    ← Frontend (React/Next.js)
│   └── pages/
│       └── index.tsx     ← Landing page
└── README.md             ← Full documentation
```

## Troubleshooting

### ML: `ModuleNotFoundError: No module named 'pandas'`

```bash
cd ml
source .venv/bin/activate
pip install -r requirements.txt
```

### Backend: `Port 8000 already in use`

```bash
# Use a different port
python -m uvicorn api.main:app --port 8001
# Update frontend: NEXT_PUBLIC_API_URL=http://localhost:8001/api
```

### Frontend: `Cannot reach API`

```bash
# Check backend is running
curl http://localhost:8000/health

# Check environment
cat fe/.env.local
# Should have: NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

## Stop Everything

```bash
# Terminal 1: Ctrl+C
# Terminal 2: Ctrl+C
# Terminal 3: Ctrl+C
```

## Next Steps

1. **Explore the UI**: http://localhost:3000
2. **Read the docs**: See `README.md` for full architecture
3. **Train models**: Follow `ml/MODEL_TRAINING.md`
4. **Build features**: Modify `ml/feature_builder.py`
5. **Deploy**: See `README.md` Deployment section

## Support

- **ML Issues**: See `ml/MODEL_TRAINING.md`
- **API Issues**: See `be/README.md`
- **UI Issues**: See `fe/README.md`
- **Architecture**: See `README.md`

---

**Status**: ✅ All components ready to run

**Time**: ~10 minutes to get everything up and running locally
>>>>>>> de69834c8ed46eccb822f01b7efdfdc8f68a3f69
