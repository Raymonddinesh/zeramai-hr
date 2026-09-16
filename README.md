# Zeramai HR — Phase 1 Slice

Built to a real spec but **not executed in this sandbox** (no network access
here to install packages/run Postgres). Every file was syntax-checked with
`py_compile`; run it for real in an environment with network access.

## What's implemented
- Auth: bcrypt password hashing, JWT in an httpOnly/SameSite=strict cookie
- RBAC: role-required dependency on every route (no implicit super-admin bypass)
- Person / Candidate / Engagement schema (unifies candidate→trainee→employee
  history without destroying records — see model docstrings in `models.py`)
- `POST /api/candidates/{id}/convert-to-trainee` — the core PRD workflow:
  validates status is SELECTED, computes engagement end date, preserves
  candidate history
- Document upload/download via **backend-proxied streaming** (no presigned
  URLs) — auth is re-checked on every download, not delegated to a token
- Append-only audit log, written on every sensitive action incl. denials

## What's intentionally NOT built yet
Everything else in the PRD (NDA/IP templates, PDF generation, evaluations,
stipend payment tracking, attendance, notifications, reports, frontend). This
is one vertical slice, chosen because it's the piece every later feature
depends on getting right: identity model, auth, RBAC, storage, audit.

## Run it (needs network)
```bash
cp backend/.env.example backend/.env
# edit JWT_SECRET to a real random value
docker compose up -d db
cd backend
pip install -r requirements.txt
python -m app.seed          # creates demo users, see app/seed.py
uvicorn app.main:app --reload
```
Demo login: `hr@zeramai.com` / `ChangeMe123!` (change before real use).

## Next slice (say the word)
Evaluation cycles + PDF generation (Jinja2 + WeasyPrint) are the next
highest-value pieces per the original architecture review.
