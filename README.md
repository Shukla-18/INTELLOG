# 🛡️ INTELLOG — Cybersecurity Monitoring System

Real-time cybersecurity monitoring platform for cloud virtual machines. Collects system metrics, network traffic, and logs from VMs via lightweight agents, analyzes threats using rule-based filtering and AI severity classification, and displays everything on a premium live dashboard.

![Dashboard](https://img.shields.io/badge/Dashboard-Live-00f5d4?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)

## 🏗️ Architecture

```
┌──────────────────┐     REST API      ┌──────────────────────────────┐
│   VM Agent       │──────────────────▶│   FastAPI Backend            │
│   (psutil)       │                    │   ├── Rule-Based Filtering   │
│   Collects:      │                    │   ├── AI Severity Classifier │
│   • CPU/Memory   │                    │   ├── SQLite Database        │
│   • Network I/O  │                    │   └── JWT Authentication     │
│   • System Logs  │                    └──────────┬───────────────────┘
└──────────────────┘                               │
                                                   ▼
                                        ┌──────────────────────┐
                                        │   Web Dashboard      │
                                        │   • Live Charts      │
                                        │   • Alert Management │
                                        │   • Report Generator │
                                        └──────────────────────┘
```

## ✨ Features

- **Agent-Based Collection** — Lightweight Python agent using `psutil` for CPU, memory, disk, network metrics + system log ingestion
- **Rule-Based Threat Detection** — 6 detection rules:
  - SSH brute-force (failed login threshold ≥ 5)
  - Suspicious C2/backdoor ports (4444, 1337, 31337...)
  - Lateral movement (private IP + high port)
  - High traffic volume + data exfiltration detection
  - Privilege escalation (sudo failures, useradd/userdel)
  - Resource abuse (CPU > 90%, RAM > 90%, Disk > 85%)
- **AI Severity Classification** — Weighted heuristic scoring (LOW/MEDIUM/HIGH)
- **JWT Authentication** — Secure login with user registration
- **Live Dashboard** — Auto-refreshing charts, alert badges, VM filtering
- **Report Generation** — HTML security reports
- **CSV Export** — Export metrics and alerts data

## 📁 Project Structure

```
intellog/
├── agent/
│   ├── monitor.py          # VM monitoring agent
│   ├── simulator.py        # Multi-VM test simulator
│   └── __main__.py         # CLI entry point
├── backend/
│   ├── main.py             # FastAPI application
│   ├── config.py           # Configuration & thresholds
│   ├── database.py         # SQLAlchemy + SQLite
│   ├── models.py           # ORM models
│   ├── schemas.py          # Pydantic validation
│   ├── routes.py           # API endpoints
│   ├── auth.py             # JWT + bcrypt authentication
│   ├── filtering.py        # Rule-based detection engine
│   └── csv_export.py       # Data export
├── frontend/
│   ├── index.html          # Dashboard UI
│   ├── styles.css          # Cyber-themed styling
│   └── app.js              # Charts & real-time updates
├── ai_model/
│   └── classifier.py       # Severity classification
├── reports/
│   └── report_generator.py # HTML report builder
├── data/                   # SQLite DB (auto-created)
└── requirements.txt
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start Backend (serves dashboard too)
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### 3. Open Dashboard
Navigate to `http://localhost:8000` — Login: `admin` / `intellog2024`

### 4. Connect VM Agent
```bash
# On target VM (or locally for testing)
python -m agent.monitor --server http://YOUR_SERVER:8000 --vm-name my-vm --interval 60
```

### 5. (Optional) Run Simulator for Testing
```bash
python -m agent.simulator --vms 3 --interval 15
```

## 🌐 Remote Access

Expose dashboard publicly using Cloudflare Tunnel:
```bash
cloudflared tunnel --url http://localhost:8000
```
Gives public HTTPS URL accessible from anywhere.

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Login → JWT token |
| POST | `/api/auth/register` | Create new account |
| POST | `/api/metrics` | Ingest system metrics |
| POST | `/api/network` | Ingest network data |
| POST | `/api/logs` | Ingest log batch |
| GET | `/api/dashboard-data` | Aggregated dashboard data |
| GET | `/api/alerts` | List alerts |
| PATCH | `/api/alerts/{id}/resolve` | Resolve alert |
| GET | `/api/export/metrics` | Export CSV |
| GET | `/api/report/generate` | Generate HTML report |

## 🔧 Configuration

Edit `backend/config.py` for thresholds:
- `CPU_THRESHOLD`: 80% (alert trigger)
- `MEMORY_THRESHOLD`: 85%
- `NETWORK_SPIKE_THRESHOLD`: 1MB/s
- `FAILED_LOGIN_THRESHOLD`: 5 attempts

## 📜 License

MIT License
