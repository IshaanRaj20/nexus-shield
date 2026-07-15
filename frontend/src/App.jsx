import { useEffect, useMemo, useState } from "react";

const API_BASE = "/api";

function ShieldMark() {
  return (
    <svg className="logo-mark" viewBox="0 0 34 34" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M17 2 L30 7 V16 C30 24 24.5 29.5 17 32 C9.5 29.5 4 24 4 16 V7 Z"
        stroke="#FFB454"
        strokeWidth="1.6"
      />
      <path d="M11 17 L15 21 L23 12" stroke="#4FD1C5" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function LockIcon() {
  return (
    <svg width="18" height="22" viewBox="0 0 18 22" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="1" y="9" width="16" height="12" rx="2" stroke="#4FD1C5" strokeWidth="2" />
      <path d="M5 9V6C5 3.79086 6.79086 2 9 2C11.2091 2 13 3.79086 13 6V9" stroke="#4FD1C5" strokeWidth="2" />
      <circle cx="9" cy="15" r="1" fill="#4FD1C5" />
    </svg>
  );
}

function Gauge({ score }) {
  const clamped = Math.max(0, Math.min(100, score));
  const angle = -90 + (clamped / 100) * 180;
  const color = clamped >= 90 ? "#4FD1C5" : clamped >= 75 ? "#4FD1C5" : clamped >= 50 ? "#FFB454" : "#FF6B6B";
  const ticks = [0, 25, 50, 75, 100];
  const cx = 110;
  const cy = 110;
  const r = 90;

  const tickPoints = ticks.map((t) => {
    const a = (-90 + (t / 100) * 180) * (Math.PI / 180);
    const x1 = cx + Math.sin(a) * (r - 8);
    const y1 = cy - Math.cos(a) * (r - 8);
    const x2 = cx + Math.sin(a) * r;
    const y2 = cy - Math.cos(a) * r;
    return { x1, y1, x2, y2 };
  });

  return (
    <div className="gauge-wrap">
      <svg viewBox="0 0 220 130" width="220" height="130">
        <path
          d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          stroke="#2a343a"
          strokeWidth="10"
          fill="none"
          strokeLinecap="round"
        />
        {tickPoints.map((p, i) => (
          <line key={i} x1={p.x1} y1={p.y1} x2={p.x2} y2={p.y2} stroke="#3a444b" strokeWidth="2" />
        ))}
        <g
          style={{ transformOrigin: `${cx}px ${cy}px`, transition: "transform 0.8s cubic-bezier(0.34,1.4,0.64,1)" }}
          transform={`rotate(${angle} ${cx} ${cy})`}
        >
          <line x1={cx} y1={cy} x2={cx} y2={cy - r + 14} stroke={color} strokeWidth="3" strokeLinecap="round" />
        </g>
        <circle cx={cx} cy={cy} r="5" fill={color} />
      </svg>
      <div className="gauge-readout">
        <span className="gauge-score" style={{ color }}>{clamped}</span>
        <span className="gauge-max"> /100</span>
      </div>
    </div>
  );
}

function statusClass(status) {
  return "status-" + status.toLowerCase().replace(/\s+/g, "-");
}

function IssueCard({ issue }) {
  return (
    <div className={`issue-card ${issue.severity}`}>
      <div className="issue-top">
        <strong>{issue.category}</strong>
        <span className="issue-severity">{issue.severity}</span>
      </div>
      <p className="issue-explanation">{issue.explanation}</p>
      <div className="issue-fix">
        <strong>Fix:</strong>
        <span>{issue.fix}</span>
      </div>
    </div>
  );
}

function HistoryItem({ scan, onSelect }) {
  return (
    <button type="button" className="history-card" onClick={() => onSelect(scan)}>
      <div className="history-meta">
        <span className="history-url">{scan.url}</span>
        <span className={`status-pill ${statusClass(scan.status)}`}>{scan.status}</span>
      </div>
      <div className="history-stats">
        <span>{scan.score}/100</span>
        <span>{scan.issue_count} issues</span>
      </div>
    </button>
  );
}

export default function App() {
  const [url, setUrl] = useState("");
  const [consent, setConsent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authMode, setAuthMode] = useState("signup");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");

  const isAuthenticated = Boolean(user && token);

  useEffect(() => {
    const savedToken = window.localStorage.getItem("nexus_shield_token");
    if (savedToken) {
      setToken(savedToken);
      fetch(`${API_BASE}/me`, {
        headers: { Authorization: `Bearer ${savedToken}` },
      })
        .then((res) => {
          if (!res.ok) throw new Error("Not authenticated");
          return res.json();
        })
        .then(setUser)
        .catch(() => {
          window.localStorage.removeItem("nexus_shield_token");
          setToken(null);
        });
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      fetch(`${API_BASE}/history`, {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((res) => res.json())
        .then(setHistory)
        .catch(() => setHistory([]));
    }
  }, [isAuthenticated, token]);

  const authHeaders = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  async function runScan(e) {
    e.preventDefault();
    setError(null);
    setResult(null);
    setAnswer("");

    if (!url.trim()) {
      setError("Enter a website URL first.");
      return;
    }
    if (!consent) {
      setError("Please confirm you own this site or have permission to scan it.");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/scan`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? authHeaders : {}),
        },
        body: JSON.stringify({ url, consent }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Scan failed.");
      }
      setResult(data);
      if (isAuthenticated) {
        setHistory((prev) => [data, ...prev.filter((item) => item.scan_id !== data.scan_id)].slice(0, 8));
      }
    } catch (err) {
      setError(err.message || "Something went wrong while scanning. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  async function downloadReport() {
    try {
      const res = await fetch(`${API_BASE}/report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, consent }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Could not generate report.");
      const blob = new Blob([data.report_text], { type: "text/plain" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `nexus-shield-report-${data.url.replace(/https?:\/\//, "").replace(/\W+/g, "-")}.txt`;
      link.click();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleAsk() {
    if (!question.trim()) {
      setError("Ask a question about your scan.");
      return;
    }
    if (!result?.scan_id) {
      setError("Save a scan first by signing in and running a scan.");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/ask`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...authHeaders,
        },
        body: JSON.stringify({ scan_id: result.scan_id, question }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Question failed.");
      }
      setAnswer(data.answer);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function authAction(path, payload) {
    setError(null);
    setLoading(true);
    try {
      if (!payload.email || !payload.password) {
        throw new Error("Email and password are required.");
      }
      const res = await fetch(`${API_BASE}/${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Authentication failed.");
      window.localStorage.setItem("nexus_shield_token", data.access_token);
      setToken(data.access_token);
      const userRes = await fetch(`${API_BASE}/me`, {
        headers: { Authorization: `Bearer ${data.access_token}` },
      });
      const userData = await userRes.json();
      setUser(userData);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function handleAuthSubmit(path) {
    authAction(path, { email: authEmail.trim(), password: authPassword });
  }

  function logout() {
    window.localStorage.removeItem("nexus_shield_token");
    setToken(null);
    setUser(null);
    setHistory([]);
  }

  function loadHistoryItem(scan) {
    setResult(scan);
    setUrl(scan.url);
  }

  return (
    <div className="app">
      <header className="hero-panel">
        <div className="hero-copy">
          <div className="hero-badge">
            <ShieldMark />
            <span>Nexus Shield</span>
          </div>
          <h1>Website security scoring for founders and small teams.</h1>
          <p className="hero-subtitle">
            Passive HTTPS, TLS, and header checks with friendly explanations and saved scan history.
          </p>
          <div className="hero-actions">
            <button className="scan-btn" onClick={() => document.getElementById("scan-form")?.scrollIntoView({ behavior: "smooth" })}>
              Scan your site now
            </button>
            <button className="secondary-btn" onClick={() => document.getElementById("dashboard")?.scrollIntoView({ behavior: "smooth" })}>
              View the dashboard
            </button>
          </div>
        </div>
        <div className="hero-panel-side">
          <div className="hero-stat">
            <span>Trusted checks</span>
            <strong>HTTPS, TLS, headers, uptime, score</strong>
          </div>
          <div className="hero-stat">
            <span>AI explanation</span>
            <strong>Why it matters and how to fix it</strong>
          </div>
          <div className="hero-stat">
            <span>Saved history</span>
            <strong>Track past scans with login</strong>
          </div>
        </div>
      </header>

      <section className="scan-panel" id="scan-form">
        <div className="scan-header">
          <div>
            <h2>Start a scan</h2>
            <p>Enter the site you want to check and confirm you own it or have permission to scan it.</p>
          </div>
          <div className="auth-chip">
            {isAuthenticated ? (
              <>
                <span>Signed in as {user.email}</span>
                <button className="link-btn" onClick={logout}>Sign out</button>
              </>
            ) : (
              <span>Sign up or log in to save scan history.</span>
            )}
          </div>
        </div>
        <form className="scan-form" onSubmit={runScan}>
          <input
            type="text"
            placeholder="example.com"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={loading}
          />
          <button className="scan-btn" type="submit" disabled={loading}>
            {loading ? "Scanning…" : "Scan Website"}
          </button>
        </form>
        <label className="consent-row">
          <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
          <span>I own this website, or have permission to scan it. Nexus Shield only reads publicly exposed web responses.</span>
        </label>
      </section>

      {error && <div className="error-banner">{error}</div>}

      {result && (
        <section className="results" id="dashboard">
          <div className="dashboard-grid">
            <div className="score-panel">
              <div className="score-topline">
                <div>
                  <div className="panel-label">Latest scan</div>
                  <div className="score-url">{result.url}</div>
                </div>
                <span className={`status-pill ${statusClass(result.status)}`}>{result.status}</span>
              </div>
              <Gauge score={result.score} />
              <div className="score-stats dashboard-stats">
                <div>
                  <strong>{result.issue_count}</strong>
                  Issues
                </div>
                <div>
                  <strong>{result.https_enabled ? "Yes" : "No"}</strong>
                  HTTPS
                </div>
                <div>
                  <strong>{result.response_time_ms ? `${result.response_time_ms}ms` : "—"}</strong>
                  Response
                </div>
              </div>
            </div>
            <div className="issue-column">
              <div className="section-label">Issues and recommendations</div>
              {result.issues.length === 0 ? (
                <div className="no-issues">No issues found — nice work keeping this site secure.</div>
              ) : (
                <div className="issue-list">
                  {result.issues.map((issue) => (
                    <IssueCard key={issue.id} issue={issue} />
                  ))}
                </div>
              )}
            </div>
          </div>

          {isAuthenticated && (
            <div className="ask-panel">
              <div className="section-label">Ask Nexus Shield</div>
              <div className="ask-form">
                <input
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder="Why is my score only 72?"
                />
                <button className="scan-btn" type="button" onClick={handleAsk} disabled={loading}>
                  Ask AI
                </button>
              </div>
              {answer && <div className="answer-box">{answer}</div>}
            </div>
          )}

          <div className="report-actions">
            <button className="secondary-btn" onClick={downloadReport}>Download report</button>
          </div>
        </section>
      )}

      {isAuthenticated && history.length > 0 && (
        <section className="history-panel">
          <div className="section-label">Saved scans</div>
          <div className="history-list">
            {history.map((scan) => (
              <HistoryItem key={scan.id} scan={scan} onSelect={loadHistoryItem} />
            ))}
          </div>
        </section>
      )}

      <section className="auth-panel">
        {!isAuthenticated ? (
          <div>
            <div className="auth-card">
              <h3>Sign up or log in</h3>
              <p>Save scans and ask follow-up questions after a scan completes.</p>
              <div className="auth-form">
                <label>
                  Email
                  <input
                    type="email"
                    value={authEmail}
                    onChange={(e) => setAuthEmail(e.target.value)}
                    placeholder="you@example.com"
                    disabled={loading}
                  />
                </label>
                <label>
                  Password
                  <input
                    type="password"
                    value={authPassword}
                    onChange={(e) => setAuthPassword(e.target.value)}
                    placeholder="At least 8 characters"
                    disabled={loading}
                  />
                </label>
                <div className="auth-grid">
                  <button className="scan-btn" type="button" onClick={() => handleAuthSubmit("signup")} disabled={loading}>
                    Create account
                  </button>
                  <button className="secondary-btn" type="button" onClick={() => handleAuthSubmit("login")} disabled={loading}>
                    Log in
                  </button>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="auth-card">
            <h3>Welcome back</h3>
            <p>Saved scans store your history securely in the browser-backed account.</p>
          </div>
        )}
      </section>

      <footer className="page-footer">
        <div>
          <strong>Nexus Shield AI</strong> · Passive website security scans · Not a substitute for a professional audit.
        </div>
      </footer>
    </div>
  );
}
