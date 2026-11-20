# UdyamCred Backend

Credit assessment system for Indian MSME shops.

## Quick Start

```bash
# Navigate to backend folder
cd d:\Hackathon\udyam-cred\be

# Create virtual environment (optional but recommended)
python -m venv .venv
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Initialize database and load synthetic test data
python scripts/seed.py --seed 42 --shops 10

# Run the server
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`

## API Documentation

Once running, visit:
- **Swagger UI:** `http://127.0.0.1:8000/docs`
- **ReDoc:** `http://127.0.0.1:8000/redoc`

## Running Tests

```bash
# Run all tests with coverage
python -m pytest tests/ -v --cov=app --cov=synth --cov=scripts

# Run specific test file
python -m pytest tests/test_gstin.py -v
python -m pytest tests/test_reconciliation.py -v
python -m pytest tests/test_golden.py -v
```

## Project Structure

```
be/
├── app/
│   ├── config.py       # Environment variable loading
│   ├── database.py     # SQLAlchemy setup
│   ├── models.py       # ORM models
│   ├── gstin.py        # GSTIN validator
│   ├── policy.py       # Policy config loader
│   ├── reconciliation.py  # Stock verification logic
│   └── auth.py         # JWT authentication
├── config/
│   └── policy.yaml     # Margin rates, bands, caps
├── scripts/
│   └── seed.py         # Database initialization
├── synth/
│   └── generator.py    # Synthetic test data
├── tests/
│   ├── test_gstin.py
│   ├── test_generator.py
│   ├── test_reconciliation.py
│   ├── test_golden.py
│   ├── test_seed.py
│   └── conftest.py     # Shared fixtures
├── data/synthetic/     # Generated test data (CSV)
├── main.py             # FastAPI application entry
├── requirements.txt
└── .env.example
```

## Configuration

Copy `.env.example` to `.env` and adjust:

```env
DATABASE_URL=sqlite:///udyam.db
JWT_SECRET=your-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30
REMEMBER_ME_DAYS=1
```

## Test Users

After running `seed.py`:

| Role | Phone | Password |
|------|-------|----------|
| Owner | 98765XXXXX | test123 |
| Officer | 98765XXXXX | test123 |
| Approver | 98765XXXXX | test123 |
| Auditor | 98765XXXXX | test123 |

## Stage 1 Checkpoint

The core reconciliation function verifies whether a shop's UPI inflows are consistent with its stock movements:

- **Pass:** UPI inflow within 80-120% of stock-supported sales
- **Flag:** UPI inflow outside this band

The pair case test validates that two shops with identical UPI inflows can receive different verdicts based on their stock data.

## Stack

- Python 3.11
- FastAPI
- SQLAlchemy (SQLite)
- Pandas, NumPy
- Pytest