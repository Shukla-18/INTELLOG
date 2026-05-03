"""
Multi-VM Simulator - Simulates multiple VMs sending data to backend.
Useful for testing without real VMs.

Usage: python -m agent.simulator --vms 3 --server http://localhost:8000
"""
import argparse
import random
import time
import threading
import logging
import requests
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("vm-simulator")

VM_PROFILES = [
    {"name": "web-server-01", "cpu_base": 35, "mem_base": 55, "net_base": 50000},
    {"name": "db-server-01", "cpu_base": 45, "mem_base": 70, "net_base": 80000},
    {"name": "app-server-01", "cpu_base": 30, "mem_base": 50, "net_base": 40000},
    {"name": "cache-server-01", "cpu_base": 20, "mem_base": 60, "net_base": 30000},
    {"name": "proxy-server-01", "cpu_base": 25, "mem_base": 40, "net_base": 120000},
]


def simulate_vm(profile, server_url, interval):
    """Simulate one VM sending data."""
    api = lambda p: f"{server_url}/api{p}"
    name = profile["name"]
    headers = {"Content-Type": "application/json"}
    prev_sent, prev_recv = random.randint(1000000, 9999999), random.randint(1000000, 9999999)

    while True:
        try:
            # Occasionally spike values
            spike = random.random() < 0.15
            cpu = min(100, profile["cpu_base"] + random.uniform(-10, 30 if not spike else 60))
            mem = min(100, profile["mem_base"] + random.uniform(-5, 20 if not spike else 40))

            requests.post(api("/metrics"), json={
                "vm_name": name, "cpu_percent": round(cpu, 1),
                "memory_percent": round(mem, 1),
                "memory_used_mb": round(mem * 160, 2),
                "memory_total_mb": 16384, "disk_percent": round(random.uniform(30, 80), 1),
            }, headers=headers, timeout=5)

            sent_delta = random.randint(1000, profile["net_base"] * (5 if spike else 1))
            recv_delta = random.randint(1000, profile["net_base"] * (5 if spike else 1))
            prev_sent += sent_delta
            prev_recv += recv_delta

            requests.post(api("/network"), json={
                "vm_name": name, "bytes_sent": prev_sent, "bytes_recv": prev_recv,
                "packets_sent": random.randint(100, 5000),
                "packets_recv": random.randint(100, 5000),
                "bytes_sent_rate": round(sent_delta / interval, 2),
                "bytes_recv_rate": round(recv_delta / interval, 2),
            }, headers=headers, timeout=5)

            # Logs
            now = datetime.now().strftime("%b %d %H:%M:%S")
            logs = [
                f"{now} {name} sshd[{random.randint(1000,9999)}]: Accepted password for admin from 192.168.1.{random.randint(1,254)} port {random.randint(1024,65535)}",
                f"{now} {name} systemd[1]: Started Session {random.randint(1,999)}",
                f"{now} {name} kernel: TCP established 10.0.0.{random.randint(1,254)}",
            ]
            if spike and random.random() < 0.5:
                for _ in range(random.randint(3, 6)):
                    logs.append(f"{now} {name} sshd[{random.randint(1000,9999)}]: Failed password for admin from 10.0.0.{random.randint(1,254)} port {random.randint(1024,65535)}")
            if random.random() < 0.1:
                logs.append(f"{now} {name} kernel: segfault at 0x0 error 4")

            requests.post(api("/logs"), json={
                "vm_name": name, "source": "/var/log/syslog", "logs": logs,
            }, headers=headers, timeout=5)

            logger.info(f"[{name}] CPU:{cpu:.1f}% MEM:{mem:.1f}% spike={spike}")

        except Exception as e:
            logger.error(f"[{name}] Error: {e}")

        time.sleep(interval + random.randint(-5, 5))


def main():
    p = argparse.ArgumentParser(description="Multi-VM Simulator")
    p.add_argument("--vms", type=int, default=3, help="Number of VMs")
    p.add_argument("--server", default="http://localhost:8000")
    p.add_argument("--interval", type=int, default=15, help="Seconds between sends")
    args = p.parse_args()

    profiles = VM_PROFILES[:args.vms]
    logger.info(f"Simulating {len(profiles)} VMs -> {args.server}")

    threads = []
    for prof in profiles:
        t = threading.Thread(target=simulate_vm, args=(prof, args.server, args.interval), daemon=True)
        t.start()
        threads.append(t)
        logger.info(f"Started VM: {prof['name']}")
        time.sleep(1)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Simulator stopped")


if __name__ == "__main__":
    main()
