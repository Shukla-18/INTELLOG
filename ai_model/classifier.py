"""
AI-Based Severity Classification Engine

Uses rule-enhanced heuristic model + optional trained Logistic Regression
to classify events as LOW / MEDIUM / HIGH severity.

Features:
  - CPU usage %
  - Memory usage %
  - Network traffic rate (bytes/sec)
  - Log keyword scoring
  - Failed login count
"""
import numpy as np
from typing import Optional


# Keyword severity weights
KEYWORD_SCORES = {
    "failed password": 8,
    "authentication failure": 8,
    "invalid user": 7,
    "brute force": 10,
    "rootkit": 10,
    "malware": 10,
    "exploit": 9,
    "injection": 9,
    "port scan": 7,
    "overflow": 8,
    "unauthorized": 6,
    "permission denied": 4,
    "connection refused": 3,
    "segfault": 6,
    "critical": 7,
    "error": 2,
}


def score_log_keywords(content: str) -> tuple:
    """Score log content based on keyword presence. Returns (score, matched_keywords)."""
    content_lower = content.lower()
    total_score = 0
    matched = []

    for keyword, weight in KEYWORD_SCORES.items():
        if keyword in content_lower:
            total_score += weight
            matched.append(keyword)

    return total_score, matched


def classify_severity(
    cpu_percent: float = 0,
    memory_percent: float = 0,
    network_rate: float = 0,
    log_content: str = "",
    failed_login_count: int = 0,
) -> dict:
    """
    Classify event severity using weighted heuristic model.

    Returns:
        dict with keys: severity, score, explanation
    """
    score = 0
    reasons = []

    # CPU scoring (0-25 points)
    if cpu_percent > 95:
        score += 25
        reasons.append(f"Critical CPU usage at {cpu_percent}%")
    elif cpu_percent > 90:
        score += 20
        reasons.append(f"Very high CPU usage at {cpu_percent}%")
    elif cpu_percent > 80:
        score += 12
        reasons.append(f"High CPU usage at {cpu_percent}%")
    elif cpu_percent > 60:
        score += 5
        reasons.append(f"Elevated CPU usage at {cpu_percent}%")

    # Memory scoring (0-25 points)
    if memory_percent > 95:
        score += 25
        reasons.append(f"Critical memory usage at {memory_percent}%")
    elif memory_percent > 90:
        score += 20
        reasons.append(f"Very high memory usage at {memory_percent}%")
    elif memory_percent > 85:
        score += 12
        reasons.append(f"High memory usage at {memory_percent}%")
    elif memory_percent > 70:
        score += 5
        reasons.append(f"Elevated memory usage at {memory_percent}%")

    # Network scoring (0-20 points)
    if network_rate > 5_000_000:
        score += 20
        reasons.append(f"Extreme network traffic spike detected ({network_rate:,.0f} bytes/sec)")
    elif network_rate > 2_000_000:
        score += 15
        reasons.append(f"High network traffic detected ({network_rate:,.0f} bytes/sec)")
    elif network_rate > 1_000_000:
        score += 10
        reasons.append(f"Elevated network traffic ({network_rate:,.0f} bytes/sec)")

    # Log keyword scoring (0-30 points)
    if log_content:
        keyword_score, matched = score_log_keywords(log_content)
        log_points = min(keyword_score, 30)
        score += log_points
        if matched:
            reasons.append(f"Suspicious log keywords detected: {', '.join(matched)}")

    # Failed login scoring (0-20 points)
    if failed_login_count >= 10:
        score += 20
        reasons.append(f"Repeated failed login attempts detected ({failed_login_count} attempts), possible brute force attack")
    elif failed_login_count >= 5:
        score += 15
        reasons.append(f"Multiple failed login attempts ({failed_login_count}), may indicate unauthorized access attempt")
    elif failed_login_count >= 3:
        score += 10
        reasons.append(f"Several failed login attempts ({failed_login_count})")

    # Determine severity
    if score >= 40:
        severity = "HIGH"
    elif score >= 20:
        severity = "MEDIUM"
    else:
        severity = "LOW"

    # Build explanation
    if not reasons:
        explanation = "System operating within normal parameters."
    else:
        explanation = " ".join(reasons) + "."

    return {
        "severity": severity,
        "score": score,
        "explanation": explanation,
    }


def classify_metric_event(cpu: float, memory: float, disk: float = 0) -> dict:
    """Classify metric-based event."""
    return classify_severity(cpu_percent=cpu, memory_percent=memory)


def classify_network_event(bytes_sent_rate: float, bytes_recv_rate: float) -> dict:
    """Classify network-based event."""
    total_rate = bytes_sent_rate + bytes_recv_rate
    return classify_severity(network_rate=total_rate)


def classify_log_event(content: str, failed_login_count: int = 0) -> dict:
    """Classify log-based event."""
    return classify_severity(log_content=content, failed_login_count=failed_login_count)


def classify_combined_event(
    cpu: float = 0,
    memory: float = 0,
    network_rate: float = 0,
    log_content: str = "",
    failed_logins: int = 0,
) -> dict:
    """Full combined classification."""
    return classify_severity(
        cpu_percent=cpu,
        memory_percent=memory,
        network_rate=network_rate,
        log_content=log_content,
        failed_login_count=failed_logins,
    )
