# Nexus Shield AI Backend

This backend provides:

- FastAPI scan endpoints
- AI explanation and question answering
- SQLite persistence for users and scan history
- Basic token auth via bearer tokens

Setup:

1. Create and activate a Python virtual environment:

   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY` and optionally `APP_SECRET_KEY`.

4. Start the app:

   ```powershell
   uvicorn main:app --reload --port 8000
   ```
