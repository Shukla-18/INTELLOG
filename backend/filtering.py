"""Rule-based filtering engine for incoming data"""
import hashlib
import re
from backend.config import (
    CPU_THRESHOLD,
    MEMORY_THRESHOLD,
    NETWORK_SPIKE_THRESHOLD,
    FAILED_LOGIN_THRESHOLD,
)

# ==================== SUSPICIOUS LOG KEYWORDS ====================

SUSPICIOUS_KEYWORDS = [
    "failed password",
    "authentication failure",
    "invalid user",
    "connection refused",
    "permission denied",
    "segfault",
    "error",
    "critical",
    "unauthorized",
    "brute force",
    "port scan",
    "malware",
    "rootkit",
    "exploit",
    "injection",
    "overflow",
]

# ==================== KNOWN C2 / BACKDOOR PORTS ====================

SUSPICIOUS_PORTS = {
    4444,   # Metasploit default
    1337,   # Common backdoor
    31337,  # Back Orifice
    5555,   # Android ADB
    6666,   # IRC backdoor
    6667,   # IRC
    8888,   # Various backdoors
    1234,   # Common test/backdoor
    12345,  # NetBus
    27374,  # SubSeven
    31338,  # Back Orifice
    54321,  # Back Orifice 2000
    65535,  # Max port — often used by malware
    3127,   # MyDoom
    2745,   # Bagle
    1080,   # SOCKS proxy (suspicious if unexpected)
}

# Private IP ranges for lateral movement detection
PRIVATE_IP_PATTERNS = [
    re.compile(r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
    re.compile(r"172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"),
    re.compile(r"192\.168\.\d{1,3}\.\d{1,3}"),
]

# Privilege escalation keywords
PRIV_ESC_KEYWORDS = [
    "useradd",
    "userdel",
    "usermod",
    "sudo",
    "su ",
    "passwd",
    "visudo",
    "chmod 777",
    "chmod u+s",
    "setuid",
    "chown root",
]

SUDO_FAIL_KEYWORDS = [
    "sudo: pam_authenticate",
    "sudo:.*authentication failure",
    "sudo:.*incorrect password",
    "sudo:.*NOT in sudoers",
]


def is_private_ip(ip: str) -> bool:
    """Check if IP is in private range."""
    for pattern in PRIVATE_IP_PATTERNS:
        if pattern.match(ip):
            return True
    return False


def detect_suspicious_port(content: str) -> list:
    """Check log content for connections to known C2/backdoor ports."""
    tags = []
    # Match patterns like "port 4444", "dst_port=31337", ":4444"
    port_matches = re.findall(r"port\s+(\d+)|dst_port[=:](\d+)|:(\d{4,5})(?:\s|$)", content, re.IGNORECASE)
    for match_groups in port_matches:
        for port_str in match_groups:
            if port_str:
                port = int(port_str)
                if port in SUSPICIOUS_PORTS:
                    tags.append(f"SUSPICIOUS_PORT:{port}")
    return tags


def detect_lateral_movement(content: str) -> list:
    """Detect lateral movement: both IPs private + destination port > 49151."""
    tags = []
    # Find IP addresses in log line
    ips = re.findall(r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b", content)
    ports = re.findall(r"port\s+(\d+)|dst_port[=:](\d+)", content, re.IGNORECASE)

    if len(ips) >= 2:
        src_private = is_private_ip(ips[0])
        dst_private = is_private_ip(ips[1])

        if src_private and dst_private:
            # Check for high ephemeral port (> 49151)
            for match_groups in ports:
                for port_str in match_groups:
                    if port_str and int(port_str) > 49151:
                        tags.append(f"LATERAL_MOVEMENT:{ips[0]}->{ips[1]}:port{port_str}")
                        break

    return tags


def detect_privilege_escalation(content: str) -> list:
    """Detect privilege escalation attempts: sudo failures, useradd/userdel."""
    tags = []
    content_lower = content.lower()

    for keyword in PRIV_ESC_KEYWORDS:
        if keyword.lower() in content_lower:
            tags.append(f"PRIV_ESC:{keyword.strip()}")

    for pattern in SUDO_FAIL_KEYWORDS:
        if re.search(pattern, content, re.IGNORECASE):
            tags.append("SUDO_FAILURE")
            break

    return tags


# ==================== MAIN FILTER FUNCTIONS ====================

def filter_metrics(cpu_percent: float, memory_percent: float, disk_percent: float = 0) -> dict:
    """Check metrics against thresholds (resource abuse detection).

    Rules:
        CPU > 90% → resource abuse
        RAM > 90% → resource abuse
        Disk > 85% → resource abuse
        CPU > 80% → suspicious
        Memory > 85% → suspicious
    """
    suspicious = False
    tags = []

    # Resource abuse (stricter thresholds)
    if cpu_percent > 90:
        suspicious = True
        tags.append(f"RESOURCE_ABUSE_CPU:{cpu_percent}%")
    elif cpu_percent > CPU_THRESHOLD:
        suspicious = True
        tags.append(f"HIGH_CPU:{cpu_percent}%")

    if memory_percent > 90:
        suspicious = True
        tags.append(f"RESOURCE_ABUSE_RAM:{memory_percent}%")
    elif memory_percent > MEMORY_THRESHOLD:
        suspicious = True
        tags.append(f"HIGH_MEMORY:{memory_percent}%")

    if disk_percent and disk_percent > 85:
        suspicious = True
        tags.append(f"HIGH_DISK:{disk_percent}%")

    return {"suspicious": suspicious, "tags": tags}


def filter_network(bytes_sent_rate: float, bytes_recv_rate: float) -> dict:
    """Detect network spikes + high outbound traffic (resource abuse indicator)."""
    suspicious = False
    tags = []

    if bytes_sent_rate > NETWORK_SPIKE_THRESHOLD:
        suspicious = True
        tags.append(f"NETWORK_SPIKE_OUT:{bytes_sent_rate}")

    if bytes_recv_rate > NETWORK_SPIKE_THRESHOLD:
        suspicious = True
        tags.append(f"NETWORK_SPIKE_IN:{bytes_recv_rate}")

    total_rate = bytes_sent_rate + bytes_recv_rate
    if total_rate > NETWORK_SPIKE_THRESHOLD * 1.5:
        suspicious = True
        tags.append(f"TOTAL_TRAFFIC_SPIKE:{total_rate}")

    # High outbound = possible data exfiltration
    if bytes_sent_rate > bytes_recv_rate * 3 and bytes_sent_rate > 500000:
        suspicious = True
        tags.append(f"HIGH_OUTBOUND_RATIO:{bytes_sent_rate:.0f}vs{bytes_recv_rate:.0f}")

    return {"suspicious": suspicious, "tags": tags}


def filter_log(content: str) -> dict:
    """Full log filtering pipeline:
    1. Keyword matching
    2. Suspicious port detection
    3. Lateral movement detection
    4. Privilege escalation detection
    """
    suspicious = False
    tags = []
    content_lower = content.lower()

    # 1. Keyword matching
    for keyword in SUSPICIOUS_KEYWORDS:
        if keyword in content_lower:
            suspicious = True
            tags.append(f"KEYWORD:{keyword}")

    # 2. Suspicious ports (C2/backdoor)
    port_tags = detect_suspicious_port(content)
    if port_tags:
        suspicious = True
        tags.extend(port_tags)

    # 3. Lateral movement
    lateral_tags = detect_lateral_movement(content)
    if lateral_tags:
        suspicious = True
        tags.extend(lateral_tags)

    # 4. Privilege escalation
    priv_tags = detect_privilege_escalation(content)
    if priv_tags:
        suspicious = True
        tags.extend(priv_tags)

    return {"suspicious": suspicious, "tags": tags}


def count_failed_logins(logs: list) -> int:
    """Count failed login attempts in log batch (SSH brute-force detection)."""
    count = 0
    for log in logs:
        low = log.lower()
        if "failed password" in low or "authentication failure" in low or "invalid user" in low:
            count += 1
    return count


def is_failed_login_attack(logs: list) -> bool:
    """Check if failed login count exceeds threshold (default 5)."""
    return count_failed_logins(logs) >= FAILED_LOGIN_THRESHOLD


def deduplicate_log(content: str) -> str:
    """Generate hash for log dedup."""
    return hashlib.sha256(content.strip().encode()).hexdigest()
