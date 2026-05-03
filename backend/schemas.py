"""Pydantic schemas for request/response validation"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# --- Auth ---
class UserCreate(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


# --- Metrics ---
class MetricCreate(BaseModel):
    vm_name: str
    cpu_percent: float
    memory_percent: float
    memory_used_mb: Optional[float] = None
    memory_total_mb: Optional[float] = None
    disk_percent: Optional[float] = None


class MetricResponse(MetricCreate):
    id: int
    suspicious: bool
    severity: str
    timestamp: datetime

    class Config:
        from_attributes = True


# --- Network ---
class NetworkCreate(BaseModel):
    vm_name: str
    bytes_sent: float
    bytes_recv: float
    packets_sent: Optional[int] = None
    packets_recv: Optional[int] = None
    bytes_sent_rate: Optional[float] = 0
    bytes_recv_rate: Optional[float] = 0


class NetworkResponse(NetworkCreate):
    id: int
    suspicious: bool
    severity: str
    timestamp: datetime

    class Config:
        from_attributes = True


# --- Logs ---
class LogCreate(BaseModel):
    vm_name: str
    source: Optional[str] = ""
    content: str


class LogBatchCreate(BaseModel):
    vm_name: str
    source: Optional[str] = ""
    logs: List[str]


class LogResponse(BaseModel):
    id: int
    vm_name: str
    source: str
    content: str
    suspicious: bool
    severity: str
    tags: str
    timestamp: datetime

    class Config:
        from_attributes = True


# --- Alerts ---
class AlertResponse(BaseModel):
    id: int
    vm_name: str
    alert_type: str
    severity: str
    message: str
    explanation: Optional[str]
    resolved: bool
    timestamp: datetime

    class Config:
        from_attributes = True


# --- Dashboard ---
class DashboardData(BaseModel):
    total_vms: int
    total_logs: int
    total_alerts: int
    active_alerts: int
    recent_metrics: List[MetricResponse]
    recent_network: List[NetworkResponse]
    recent_logs: List[LogResponse]
    recent_alerts: List[AlertResponse]
    vm_list: List[str]


# --- Cloud VM Discovery ---
class CloudVM(BaseModel):
    vm_id: str
    vm_name: str
    private_ip: str
    status: str
    image: str
    flavor: str
    created_at: Optional[str] = None


class DeployAgentRequest(BaseModel):
    vm_id: str
    ip: str
    username: Optional[str] = ""
    password: Optional[str] = ""
    ssh_key: Optional[str] = ""
    mode: Optional[str] = "demo"  # demo or real


class DeployAgentResponse(BaseModel):
    status: str
    message: str
    vm_id: Optional[str] = None
    agent_pid: Optional[int] = None
    deployed_at: Optional[str] = None


class StartMonitoringRequest(BaseModel):
    vm_ids: List[str]


class MonitoredVMResponse(BaseModel):
    id: int
    vm_id: str
    vm_name: str
    private_ip: Optional[str]
    status: str
    image: Optional[str]
    flavor: Optional[str]
    agent_status: str
    monitoring: bool
    deployed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

