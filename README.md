# Nexus Shield AI — v1

Phase one: a website scanner that checks HTTPS, TLS, security headers, and
response time, scores the result out of 100, explains findings in plain
English via Claude, and generates a downloadable report.

This is intentionally scoped to **passive, read-only checks only** — no
port scanning, no exploit probing, no login attempts. It reads what a
server already sends back in a normal HTTP response.

## Structure

```
nexus-shield/
├── backend/          FastAPI app: scanning, scoring, AI explanations, reports
│   ├── main.py        API endpoints
│   ├── scanner.py      Core scan logic (HTTPS, TLS, headers, timing)
│   ├── scoring.py       0-100 scoring rubric
│   ├── ai_explainer.py  Claude-powered plain-English explanations
│   ├── report.py        Plain-text report builder
│   ├── requirements.txt
│   └── .env.example
└── frontend/         React (Vite) dashboard
    ├── src/App.jsx     Scan form, gauge, issue cards, report download
    ├── src/App.css
    └── index.html
```

## Running it

### 1. Backend

```bash
cd backend
python3 -m venv venv && source venv/bin/activate   # optional but recommended
pip install -r requirements.txt
cp .env.example .env
# edit .env and add your ANTHROPIC_API_KEY (get one at console.anthropic.com)
uvicorn main:app --reload --port 8000
```

The API is now live at `http://localhost:8000`. Without an API key set, the
app still works — it falls back to pre-written plain-English explanations
instead of AI-generated ones.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The dev server proxies `/api/*` to the
backend on port 8000 (see `vite.config.js`).

## How scoring works

Every scan starts at 100 points. Points are subtracted per issue found:

| Issue                                   | Points lost |
|------------------------------------------|-------------|
| No HTTPS enforced                         | 25          |
| Invalid/expired TLS certificate           | 20          |
| TLS certificate expiring within 14 days   | 10          |
| Missing Content-Security-Policy           | 15          |
| Missing Strict-Transport-Security (HSTS)  | 12          |
| Missing X-Content-Type-Options            | 8           |
| Missing X-Frame-Options                   | 8           |
| Missing Referrer-Policy                   | 5           |
| Missing Permissions-Policy                | 5           |
| Server version disclosed in headers       | 5           |
| Slow response time (>3s)                  | 5           |

90+ Excellent · 75-89 Good · 50-74 Needs Improvement · <50 Poor

This rubric is intentionally simple for v1 — tune the weights in
`scoring.py` / `scanner.py` as you learn what matters most to real users.

## What's deliberately NOT in v1

- No active vulnerability scanning or exploitation
- No user accounts / auth (add Firebase Auth in phase 2)
- No saved report history (add Firebase Firestore in phase 2)
- No scheduled/recurring scans
- No rate limiting or abuse protection (add before any public deploy —
  scanning arbitrary URLs on demand is an easy abuse vector)

## Next milestones (phase 2+)

1. Firebase Auth + Firestore: save scan history per user, shareable report links
2. Rate limiting + consent audit log (who scanned what, when)
3. Expand checks: cookie flags (Secure/HttpOnly/SameSite), mixed content,
   subresource integrity, open redirect basics
4. Score trend over time (re-scan and show improvement)
5. Email/webhook alert when a previously-good site's score drops
