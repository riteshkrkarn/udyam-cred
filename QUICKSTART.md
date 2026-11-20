# UdyamCred — Quick Start (Stage 1)

Run the full stack locally in two terminals.

---

## Terminal 1: Backend (FastAPI)

```bash
cd be

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

```bash
cd fe

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
