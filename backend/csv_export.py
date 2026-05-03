"""CSV export utilities"""
import csv
from datetime import datetime
from pathlib import Path
from backend.config import CSV_DIR


def export_metrics_csv(metrics: list):
    """Export metrics to CSV file."""
    filepath = CSV_DIR / f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    if not metrics:
        return str(filepath)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "id", "vm_name", "cpu_percent", "memory_percent",
            "memory_used_mb", "memory_total_mb", "disk_percent",
            "suspicious", "severity", "timestamp"
        ])
        for m in metrics:
            writer.writerow([
                m.id, m.vm_name, m.cpu_percent, m.memory_percent,
                m.memory_used_mb, m.memory_total_mb, m.disk_percent,
                m.suspicious, m.severity, m.timestamp
            ])
    return str(filepath)


def export_network_csv(network_data: list):
    """Export network data to CSV."""
    filepath = CSV_DIR / f"network_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    if not network_data:
        return str(filepath)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "id", "vm_name", "bytes_sent", "bytes_recv",
            "packets_sent", "packets_recv", "bytes_sent_rate",
            "bytes_recv_rate", "suspicious", "severity", "timestamp"
        ])
        for n in network_data:
            writer.writerow([
                n.id, n.vm_name, n.bytes_sent, n.bytes_recv,
                n.packets_sent, n.packets_recv, n.bytes_sent_rate,
                n.bytes_recv_rate, n.suspicious, n.severity, n.timestamp
            ])
    return str(filepath)


def export_logs_csv(logs: list):
    """Export logs to CSV."""
    filepath = CSV_DIR / f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    if not logs:
        return str(filepath)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "id", "vm_name", "source", "content",
            "suspicious", "severity", "tags", "timestamp"
        ])
        for l in logs:
            writer.writerow([
                l.id, l.vm_name, l.source, l.content,
                l.suspicious, l.severity, l.tags, l.timestamp
            ])
    return str(filepath)


def export_alerts_csv(alerts: list):
    """Export alerts to CSV."""
    filepath = CSV_DIR / f"alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    if not alerts:
        return str(filepath)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "id", "vm_name", "alert_type", "severity",
            "message", "explanation", "resolved", "timestamp"
        ])
        for a in alerts:
            writer.writerow([
                a.id, a.vm_name, a.alert_type, a.severity,
                a.message, a.explanation, a.resolved, a.timestamp
            ])
    return str(filepath)
