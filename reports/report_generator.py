"""HTML Report Generator for Intellog"""
from datetime import datetime
from pathlib import Path
from backend.config import REPORTS_DIR


REPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Intellog Security Report</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',system-ui,sans-serif;background:#0a0e17;color:#c8d6e5;padding:40px;line-height:1.6}
.report{max-width:900px;margin:0 auto;background:#111827;border-radius:16px;padding:40px;border:1px solid #1e3a5f}
h1{color:#00f5d4;font-size:28px;margin-bottom:8px;text-shadow:0 0 20px rgba(0,245,212,0.3)}
.subtitle{color:#8892b0;margin-bottom:30px;font-size:14px}
h2{color:#64ffda;font-size:20px;margin:24px 0 12px;border-bottom:1px solid #1e3a5f;padding-bottom:8px}
.stat-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin:20px 0}
.stat{background:#0d1b2a;padding:20px;border-radius:12px;text-align:center;border:1px solid #1e3a5f}
.stat .value{font-size:32px;font-weight:700;color:#00f5d4}
.stat .label{font-size:12px;color:#8892b0;margin-top:4px}
table{width:100%;border-collapse:collapse;margin:12px 0}
th{background:#0d1b2a;color:#64ffda;padding:10px;text-align:left;font-size:13px}
td{padding:10px;border-bottom:1px solid #1a2332;font-size:13px}
.sev-high{color:#ff6b6b;font-weight:700}
.sev-medium{color:#ffd93d;font-weight:700}
.sev-low{color:#6bff6b;font-weight:700}
.explanation{background:#0d1b2a;padding:16px;border-radius:8px;margin:8px 0;border-left:3px solid #64ffda;font-size:14px}
.footer{text-align:center;color:#4a5568;font-size:12px;margin-top:30px;padding-top:20px;border-top:1px solid #1e3a5f}
</style>
</head>
<body>
<div class="report">
<h1>🛡️ Intellog Security Report</h1>
<p class="subtitle">Generated: {timestamp} | Report ID: {report_id}</p>

<h2>📊 System Overview</h2>
<div class="stat-grid">
<div class="stat"><div class="value">{total_vms}</div><div class="label">VMs Monitored</div></div>
<div class="stat"><div class="value">{total_logs}</div><div class="label">Logs Collected</div></div>
<div class="stat"><div class="value">{total_alerts}</div><div class="label">Total Alerts</div></div>
<div class="stat"><div class="value">{high_alerts}</div><div class="label">High Severity</div></div>
</div>

<h2>⚠️ Active Alerts</h2>
{alerts_table}

<h2>📝 Summary & Recommendations</h2>
{summary_section}

<div class="footer">
Intellog Cybersecurity Monitoring System v1.0 | Confidential Report
</div>
</div>
</body>
</html>"""


def generate_report(dashboard_data: dict) -> str:
    """Generate HTML report from dashboard data. Returns filepath."""
    now = datetime.now()
    report_id = f"RPT-{now.strftime('%Y%m%d%H%M%S')}"

    alerts = dashboard_data.get("recent_alerts", [])
    high_count = sum(1 for a in alerts if getattr(a, 'severity', '') == 'HIGH' or (isinstance(a, dict) and a.get('severity') == 'HIGH'))

    # Alerts table
    if alerts:
        rows = ""
        for a in alerts[:20]:
            if isinstance(a, dict):
                sev = a.get("severity", "LOW")
                vm = a.get("vm_name", "")
                atype = a.get("alert_type", "")
                msg = a.get("message", "")
                expl = a.get("explanation", "")
                ts = a.get("timestamp", "")
            else:
                sev = a.severity
                vm = a.vm_name
                atype = a.alert_type
                msg = a.message
                expl = a.explanation or ""
                ts = str(a.timestamp)
            sev_class = f"sev-{sev.lower()}"
            rows += f'<tr><td>{vm}</td><td>{atype}</td><td class="{sev_class}">{sev}</td><td>{msg}</td><td>{ts}</td></tr>\n'
            if expl:
                rows += f'<tr><td colspan="5"><div class="explanation">💡 {expl}</div></td></tr>\n'
        alerts_table = f'<table><tr><th>VM</th><th>Type</th><th>Severity</th><th>Message</th><th>Time</th></tr>{rows}</table>'
    else:
        alerts_table = '<p style="color:#6bff6b">✅ No active alerts. Systems operating normally.</p>'

    # Summary
    summaries = []
    if high_count > 0:
        summaries.append(f'<div class="explanation">🔴 <strong>{high_count} high-severity alerts</strong> detected. Immediate attention recommended. These may indicate unauthorized access attempts or critical system failures.</div>')
    
    total_alerts = dashboard_data.get("total_alerts", 0)
    if total_alerts == 0:
        summaries.append('<div class="explanation">✅ All systems operating within normal parameters. No security threats detected.</div>')
    elif high_count == 0:
        summaries.append('<div class="explanation">🟡 Some alerts detected but none are high severity. Continue monitoring.</div>')

    summaries.append('<div class="explanation">📋 <strong>Recommendations:</strong> Review all flagged alerts, verify legitimate access patterns, ensure all VMs have latest security patches.</div>')
    summary_section = "\n".join(summaries)

    html = REPORT_TEMPLATE.format(
        timestamp=now.strftime("%Y-%m-%d %H:%M:%S"),
        report_id=report_id,
        total_vms=dashboard_data.get("total_vms", 0),
        total_logs=dashboard_data.get("total_logs", 0),
        total_alerts=total_alerts,
        high_alerts=high_count,
        alerts_table=alerts_table,
        summary_section=summary_section,
    )

    filepath = REPORTS_DIR / f"report_{now.strftime('%Y%m%d_%H%M%S')}.html"
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    return str(filepath)
