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

```bash
cd be

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

```bash
cd fe

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
