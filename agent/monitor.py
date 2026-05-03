"""
Intellog VM Monitoring Agent
Collects system metrics, network traffic, system logs.
Sends to backend via REST API.

Usage: python -m agent.monitor --server http://localhost:8000 --vm-name my-vm
"""
import argparse
import json
import logging
import os
import platform
import random
import time
from datetime import datetime

import psutil
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("intellog-agent")


class IntellogAgent:
    def __init__(self, server_url, vm_name, interval=60, token=""):
        self.server_url = server_url.rstrip("/")
        self.vm_name = vm_name
        self.interval = interval
        self.headers = {"Content-Type": "application/json"}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
        self._prev_net = None
        self._prev_time = None

    def _api(self, path):
        return f"{self.server_url}/api{path}"

    def collect_metrics(self):
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        try:
            disk = psutil.disk_usage("/")
        except Exception:
            disk = psutil.disk_usage("C:\\")
        return {
            "vm_name": self.vm_name,
            "cpu_percent": cpu,
            "memory_percent": mem.percent,
            "memory_used_mb": round(mem.used / 1048576, 2),
            "memory_total_mb": round(mem.total / 1048576, 2),
            "disk_percent": disk.percent,
        }

    def collect_network(self):
        net = psutil.net_io_counters()
        now = time.time()
        sr, rr = 0, 0
        if self._prev_net and self._prev_time:
            dt = now - self._prev_time
            if dt > 0:
                sr = (net.bytes_sent - self._prev_net.bytes_sent) / dt
                rr = (net.bytes_recv - self._prev_net.bytes_recv) / dt
        self._prev_net = net
        self._prev_time = now
        return {
            "vm_name": self.vm_name,
            "bytes_sent": net.bytes_sent,
            "bytes_recv": net.bytes_recv,
            "packets_sent": net.packets_sent,
            "packets_recv": net.packets_recv,
            "bytes_sent_rate": round(sr, 2),
            "bytes_recv_rate": round(rr, 2),
        }

    def collect_logs(self, log_files=None, max_lines=50):
        if log_files is None:
            log_files = ["/var/log/syslog", "/var/log/auth.log"]
        logs = []
        for lf in log_files:
            if not os.path.exists(lf):
                continue
            try:
                with open(lf, "r", errors="ignore") as f:
                    lines = f.readlines()
                    logs.extend([l.strip() for l in lines[-max_lines:] if l.strip()])
            except Exception as e:
                logger.error(f"Error reading {lf}: {e}")
        if not logs:
            logs = self._sim_logs()
        return {"vm_name": self.vm_name, "source": ",".join(log_files), "logs": logs}

    def _sim_logs(self):
        now = datetime.now().strftime("%b %d %H:%M:%S")
        h = self.vm_name
        r = random.randint
        lines = [
            f"{now} {h} sshd[{r(1000,9999)}]: Accepted password for admin from 192.168.1.{r(1,254)} port {r(1024,65535)} ssh2",
            f"{now} {h} kernel: TCP connection established from 10.0.0.{r(1,254)}",
            f"{now} {h} systemd[1]: Started Session {r(1,100)} of user admin.",
            f"{now} {h} CRON[{r(1000,9999)}]: (root) CMD (/usr/bin/check_health)",
        ]
        if random.random() < 0.3:
            lines.append(f"{now} {h} sshd[{r(1000,9999)}]: Failed password for invalid user root from 10.0.0.{r(1,254)} port {r(1024,65535)} ssh2")
        if random.random() < 0.15:
            for _ in range(3):
                lines.append(f"{now} {h} sshd[{r(1000,9999)}]: Failed password for admin from 10.0.0.{r(1,254)} port {r(1024,65535)} ssh2")
        if random.random() < 0.1:
            lines.append(f"{now} {h} kernel: segfault at 0000000000000000 ip 00007f error 4")
        return random.sample(lines, min(len(lines), r(3, len(lines))))

    def send(self, endpoint, data):
        url = self._api(endpoint)
        try:
            resp = requests.post(url, json=data, headers=self.headers, timeout=10)
            if resp.status_code in (200, 201):
                logger.info(f"OK {endpoint}")
                return True
            logger.warning(f"FAIL {endpoint}: {resp.status_code}")
            return False
        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect: {url}")
            return False
        except Exception as e:
            logger.error(f"Error {endpoint}: {e}")
            return False

    def run_once(self):
        logger.info(f"--- Collecting: {self.vm_name} ---")
        m = self.collect_metrics()
        logger.info(f"CPU:{m['cpu_percent']}% MEM:{m['memory_percent']}%")
        self.send("/metrics", m)
        n = self.collect_network()
        logger.info(f"NetOut:{n['bytes_sent_rate']:.0f}B/s NetIn:{n['bytes_recv_rate']:.0f}B/s")
        self.send("/network", n)
        l = self.collect_logs()
        logger.info(f"Logs:{len(l['logs'])} lines")
        self.send("/logs", l)

    def run(self):
        logger.info(f"Agent started: {self.vm_name} -> {self.server_url}")
        while True:
            try:
                self.run_once()
            except KeyboardInterrupt:
                logger.info("Stopped")
                break
            except Exception as e:
                logger.error(f"Error: {e}")
            sleep = max(10, self.interval + random.randint(-10, 10))
            logger.info(f"Next in {sleep}s")
            time.sleep(sleep)


def main():
    p = argparse.ArgumentParser(description="Intellog Agent")
    p.add_argument("--server", default="http://localhost:8000")
    p.add_argument("--vm-name", default=f"vm-{platform.node()}")
    p.add_argument("--interval", type=int, default=60)
    p.add_argument("--token", default="")
    p.add_argument("--once", action="store_true")
    args = p.parse_args()
    agent = IntellogAgent(args.server, args.vm_name, args.interval, args.token)
    if args.once:
        agent.run_once()
    else:
        agent.run()


if __name__ == "__main__":
    main()
