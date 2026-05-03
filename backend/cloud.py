"""
Intellog Cloud VM Discovery & Agent Deployment Module
Supports OpenStack API (real) and mock mode (demo).
"""
import os
import uuid
import random
import logging
import subprocess
import threading
from datetime import datetime
from typing import List, Optional, Dict

logger = logging.getLogger("intellog-cloud")

# ==================== MOCK CLOUD DATA ====================

MOCK_IMAGES = [
    "Ubuntu 22.04 LTS", "Ubuntu 20.04 LTS", "CentOS 9 Stream",
    "Debian 12", "Rocky Linux 9", "AlmaLinux 9",
]

MOCK_FLAVORS = [
    "m1.small (1 vCPU, 2GB RAM)", "m1.medium (2 vCPU, 4GB RAM)",
    "m1.large (4 vCPU, 8GB RAM)", "m1.xlarge (8 vCPU, 16GB RAM)",
    "c1.compute (4 vCPU, 4GB RAM)", "r1.memory (2 vCPU, 16GB RAM)",
]

MOCK_VMS = [
    {
        "vm_id": "i-" + uuid.uuid4().hex[:12],
        "vm_name": "web-server-prod",
        "private_ip": "10.0.1.10",
        "status": "ACTIVE",
        "image": "Ubuntu 22.04 LTS",
        "flavor": "m1.medium (2 vCPU, 4GB RAM)",
        "created_at": "2026-04-15T08:30:00Z",
    },
    {
        "vm_id": "i-" + uuid.uuid4().hex[:12],
        "vm_name": "db-server-01",
        "private_ip": "10.0.1.20",
        "status": "ACTIVE",
        "image": "CentOS 9 Stream",
        "flavor": "r1.memory (2 vCPU, 16GB RAM)",
        "created_at": "2026-04-15T09:00:00Z",
    },
    {
        "vm_id": "i-" + uuid.uuid4().hex[:12],
        "vm_name": "api-gateway",
        "private_ip": "10.0.1.30",
        "status": "ACTIVE",
        "image": "Ubuntu 22.04 LTS",
        "flavor": "m1.large (4 vCPU, 8GB RAM)",
        "created_at": "2026-04-16T10:15:00Z",
    },
    {
        "vm_id": "i-" + uuid.uuid4().hex[:12],
        "vm_name": "cache-node",
        "private_ip": "10.0.1.40",
        "status": "ACTIVE",
        "image": "Debian 12",
        "flavor": "m1.small (1 vCPU, 2GB RAM)",
        "created_at": "2026-04-17T14:20:00Z",
    },
    {
        "vm_id": "i-" + uuid.uuid4().hex[:12],
        "vm_name": "worker-batch-01",
        "private_ip": "10.0.2.10",
        "status": "ACTIVE",
        "image": "Rocky Linux 9",
        "flavor": "c1.compute (4 vCPU, 4GB RAM)",
        "created_at": "2026-04-18T07:45:00Z",
    },
    {
        "vm_id": "i-" + uuid.uuid4().hex[:12],
        "vm_name": "staging-server",
        "private_ip": "10.0.2.20",
        "status": "STOPPED",
        "image": "Ubuntu 20.04 LTS",
        "flavor": "m1.medium (2 vCPU, 4GB RAM)",
        "created_at": "2026-04-19T16:00:00Z",
    },
    {
        "vm_id": "i-" + uuid.uuid4().hex[:12],
        "vm_name": "log-aggregator",
        "private_ip": "10.0.1.50",
        "status": "ACTIVE",
        "image": "Ubuntu 22.04 LTS",
        "flavor": "m1.xlarge (8 vCPU, 16GB RAM)",
        "created_at": "2026-04-20T11:30:00Z",
    },
    {
        "vm_id": "i-" + uuid.uuid4().hex[:12],
        "vm_name": "dev-sandbox",
        "private_ip": "10.0.3.10",
        "status": "STOPPED",
        "image": "AlmaLinux 9",
        "flavor": "m1.small (1 vCPU, 2GB RAM)",
        "created_at": "2026-04-21T09:10:00Z",
    },
]


class CloudConnector:
    """Connects to OpenStack or returns mock VM list."""

    def __init__(self, mode="mock", openstack_url=None, credentials=None):
        self.mode = mode
        self.openstack_url = openstack_url
        self.credentials = credentials or {}

    def discover_vms(self) -> List[Dict]:
        """Fetch list of VMs from cloud provider."""
        if self.mode == "openstack":
            return self._openstack_discover()
        return self._mock_discover()

    def _mock_discover(self) -> List[Dict]:
        """Return mock VM list simulating OpenStack response."""
        logger.info("Cloud scan (mock mode): returning %d VMs", len(MOCK_VMS))
        return MOCK_VMS

    def _openstack_discover(self) -> List[Dict]:
        """Connect to real OpenStack Nova API to list servers."""
        try:
            import openstack
            conn = openstack.connect(
                auth_url=self.credentials.get("auth_url"),
                project_name=self.credentials.get("project_name"),
                username=self.credentials.get("username"),
                password=self.credentials.get("password"),
                user_domain_name=self.credentials.get("user_domain", "Default"),
                project_domain_name=self.credentials.get("project_domain", "Default"),
            )
            servers = conn.compute.servers(details=True)
            vms = []
            for s in servers:
                # Extract first private IP
                private_ip = ""
                for net_name, addrs in (s.addresses or {}).items():
                    for addr in addrs:
                        if addr.get("OS-EXT-IPS:type") == "fixed":
                            private_ip = addr["addr"]
                            break
                    if private_ip:
                        break

                vms.append({
                    "vm_id": s.id,
                    "vm_name": s.name,
                    "private_ip": private_ip,
                    "status": s.status,
                    "image": s.image.get("id", "unknown") if s.image else "unknown",
                    "flavor": s.flavor.get("original_name", "unknown") if s.flavor else "unknown",
                    "created_at": s.created_at,
                })
            logger.info("OpenStack scan: found %d servers", len(vms))
            return vms
        except ImportError:
            logger.warning("openstacksdk not installed, falling back to mock")
            return self._mock_discover()
        except Exception as e:
            logger.error("OpenStack connection failed: %s", e)
            return self._mock_discover()


class AgentDeployer:
    """Handles agent deployment to VMs (real SSH or simulated)."""

    def __init__(self, server_url="https://intellog.dev"):
        self.server_url = server_url

    def deploy(self, vm_id: str, ip: str, username: str = "",
               password: str = "", ssh_key: str = "", mode: str = "demo") -> Dict:
        """Deploy monitoring agent to a VM."""
        if mode == "real":
            return self._deploy_ssh(ip, username, password, ssh_key)
        return self._deploy_demo(vm_id, ip)

    def _deploy_demo(self, vm_id: str, ip: str) -> Dict:
        """Simulate agent deployment."""
        logger.info("Demo deploy agent to %s (%s)", vm_id, ip)
        import time
        time.sleep(1)  # Simulate deployment time
        return {
            "status": "success",
            "message": f"Agent deployed and started on {ip}",
            "vm_id": vm_id,
            "agent_pid": random.randint(1000, 9999),
            "deployed_at": datetime.utcnow().isoformat() + "Z",
        }

    def _deploy_ssh(self, ip: str, username: str, password: str, ssh_key: str) -> Dict:
        """Deploy agent via SSH to real VM."""
        try:
            import paramiko
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            if ssh_key:
                from io import StringIO
                key = paramiko.RSAKey.from_private_key(StringIO(ssh_key))
                ssh.connect(ip, username=username, pkey=key, timeout=15)
            else:
                ssh.connect(ip, username=username, password=password, timeout=15)

            # Install dependencies
            commands = [
                "pip3 install psutil requests 2>/dev/null || pip install psutil requests",
                f"git clone https://github.com/Shukla-18/INTELLOG.git /tmp/intellog 2>/dev/null || (cd /tmp/intellog && git pull)",
                f"nohup python3 -m agent.monitor --server {self.server_url} --vm-name $(hostname) --interval 60 > /tmp/intellog-agent.log 2>&1 &",
            ]

            for cmd in commands:
                stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
                stdout.channel.recv_exit_status()

            ssh.close()
            return {
                "status": "success",
                "message": f"Agent deployed and started on {ip}",
                "deployed_at": datetime.utcnow().isoformat() + "Z",
            }
        except ImportError:
            logger.error("paramiko not installed for SSH deployment")
            return {"status": "error", "message": "paramiko not installed. Run: pip install paramiko"}
        except Exception as e:
            logger.error("SSH deployment failed: %s", e)
            return {"status": "error", "message": str(e)}


# Global instances
cloud_connector = CloudConnector(mode=os.getenv("CLOUD_MODE", "mock"))
agent_deployer = AgentDeployer(server_url=os.getenv("INTELLOG_SERVER", "https://intellog.dev"))
