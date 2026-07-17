# 🛡️ Nexus Shield AI Backend

The backend service powering **Nexus Shield AI**.

It provides the API infrastructure for website security scanning, AI-powered explanations, user authentication, scan storage, and automated security reports.

🌐 **Frontend:** https://shield.zenithish.com
⚙️ **Backend API:** Hosted on Render

---

## Features

### 🔍 Website Security Scanning

* Runs website security checks
* Calculates security scores
* Detects missing security configurations
* Returns detailed scan results

### 🧠 AI Security Intelligence

* Explains security issues in simple terms
* Answers questions about scan results
* Provides security recommendations

### 👤 User System

* Token-based authentication
* Secure password hashing
* Protected user endpoints
* Personal user data management

### 💾 Data Storage

* SQLite persistence
* Stores users and scan history
* Tracks previous security scans

### 📧 Email Services

* Test security emails
* Scan alert notifications
* Weekly security summary reports
* Verified domain email sending through Resend

---

## Technology Stack

* **FastAPI** — Backend API framework
* **Python** — Core backend language
* **SQLite** — Database storage
* **Resend** — Email delivery
* **Render** — Backend hosting

---

## API Overview

Main endpoints include:

```
GET  /api/health              → Backend health check
POST /api/scan                → Run a security scan
POST /api/report              → Generate a security report
POST /api/signup              → Create an account
POST /api/login               → Authenticate a user
GET  /api/me                  → Get current user information
GET  /api/history             → View previous scans
POST /api/user/test-email     → Send a test email
POST /api/user/weekly-summary → Send weekly security summary
```

---

## Environment Variables

The backend uses environment variables for configuration, including:

* `ANTHROPIC_API_KEY` — AI explanation features
* `APP_SECRET_KEY` — Authentication token security
* Email service configuration variables

---

## Deployment

The backend is continuously deployed and hosted through Render.

The frontend communicates with this API to provide the full Nexus Shield AI experience at:

https://shield.zenithish.com

---

## Project Status

🚀 **Current Version: Nexus Shield AI V1.7**

Completed:

* Website security scanning
* AI explanations
* Authentication
* Scan history
* Email alerts
* Weekly security reports

Future development will expand Nexus Shield AI into a larger security intelligence platform.
