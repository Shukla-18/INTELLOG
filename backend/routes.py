"""API Routes for Intellog Backend"""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from backend.database import get_db
from backend.models import Metric, NetworkData, LogEntry, Alert, User
from backend.schemas import (
    MetricCreate, MetricResponse,
    NetworkCreate, NetworkResponse,
    LogCreate, LogBatchCreate, LogResponse,
    AlertResponse, DashboardData,
    UserCreate, Token,
)
from backend.filtering import (
    filter_metrics, filter_network, filter_log,
    deduplicate_log, count_failed_logins, is_failed_login_attack,
)
from backend.auth import (
    hash_password, verify_password, create_access_token, get_current_user,
)
from backend.csv_export import export_metrics_csv, export_alerts_csv
from ai_model.classifier import (
    classify_metric_event, classify_network_event, classify_log_event,
)

router = APIRouter()


# ==================== AUTH ====================

@router.post("/auth/login", response_model=Token)
def login(user_data: UserCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == user_data.username).first()
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(data={"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/auth/register", response_model=Token)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == user_data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    user = User(
        username=user_data.username,
        hashed_password=hash_password(user_data.password),
    )
    db.add(user)
    db.commit()
    token = create_access_token(data={"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}


# ==================== METRICS ====================

@router.post("/metrics", response_model=MetricResponse)
def ingest_metrics(data: MetricCreate, db: Session = Depends(get_db)):
    """Receive system metrics from agent, filter, classify, store."""
    # Filter
    result = filter_metrics(data.cpu_percent, data.memory_percent, data.disk_percent or 0)

    # AI classify
    classification = classify_metric_event(data.cpu_percent, data.memory_percent, data.disk_percent or 0)

    metric = Metric(
        vm_name=data.vm_name,
        cpu_percent=data.cpu_percent,
        memory_percent=data.memory_percent,
        memory_used_mb=data.memory_used_mb,
        memory_total_mb=data.memory_total_mb,
        disk_percent=data.disk_percent,
        suspicious=result["suspicious"],
        severity=classification["severity"],
    )
    db.add(metric)

    # Create alert if suspicious
    if result["suspicious"]:
        alert = Alert(
            vm_name=data.vm_name,
            alert_type="SYSTEM_METRIC",
            severity=classification["severity"],
            message=f"Suspicious metrics: {', '.join(result['tags'])}",
            explanation=classification["explanation"],
        )
        db.add(alert)

    db.commit()
    db.refresh(metric)
    return metric


# ==================== NETWORK ====================

@router.post("/network", response_model=NetworkResponse)
def ingest_network(data: NetworkCreate, db: Session = Depends(get_db)):
    """Receive network data from agent, filter, classify, store."""
    result = filter_network(data.bytes_sent_rate or 0, data.bytes_recv_rate or 0)
    classification = classify_network_event(data.bytes_sent_rate or 0, data.bytes_recv_rate or 0)

    net = NetworkData(
        vm_name=data.vm_name,
        bytes_sent=data.bytes_sent,
        bytes_recv=data.bytes_recv,
        packets_sent=data.packets_sent,
        packets_recv=data.packets_recv,
        bytes_sent_rate=data.bytes_sent_rate,
        bytes_recv_rate=data.bytes_recv_rate,
        suspicious=result["suspicious"],
        severity=classification["severity"],
    )
    db.add(net)

    if result["suspicious"]:
        alert = Alert(
            vm_name=data.vm_name,
            alert_type="NETWORK_SPIKE",
            severity=classification["severity"],
            message=f"Network anomaly: {', '.join(result['tags'])}",
            explanation=classification["explanation"],
        )
        db.add(alert)

    db.commit()
    db.refresh(net)
    return net


# ==================== LOGS ====================

@router.post("/logs", response_model=list[LogResponse])
def ingest_logs(data: LogBatchCreate, db: Session = Depends(get_db)):
    """Receive batch logs from agent, deduplicate, filter, classify, store."""
    stored_logs = []
    failed_login_count = count_failed_logins(data.logs)

    for line in data.logs:
        line = line.strip()
        if not line:
            continue

        # Deduplicate
        log_hash = deduplicate_log(line)
        existing = db.query(LogEntry).filter(LogEntry.log_hash == log_hash).first()
        if existing:
            continue

        # Filter
        result = filter_log(line)
        classification = classify_log_event(line, failed_login_count)

        log_entry = LogEntry(
            vm_name=data.vm_name,
            source=data.source or "",
            content=line,
            log_hash=log_hash,
            suspicious=result["suspicious"],
            severity=classification["severity"],
            tags=",".join(result["tags"]),
        )
        db.add(log_entry)
        stored_logs.append(log_entry)

    # Alert on failed login attack
    if is_failed_login_attack(data.logs):
        classification = classify_log_event("", failed_login_count)
        alert = Alert(
            vm_name=data.vm_name,
            alert_type="FAILED_LOGIN_ATTACK",
            severity="HIGH",
            message=f"Detected {failed_login_count} failed login attempts — possible brute force attack",
            explanation=classification["explanation"],
        )
        db.add(alert)

    db.commit()
    for log in stored_logs:
        db.refresh(log)
    return stored_logs


# ==================== DASHBOARD DATA ====================

@router.get("/dashboard-data", response_model=DashboardData)
def get_dashboard_data(
    vm_name: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    """Aggregate dashboard data."""
    # VM list
    vm_names = [r[0] for r in db.query(Metric.vm_name).distinct().all()]
    net_vms = [r[0] for r in db.query(NetworkData.vm_name).distinct().all()]
    log_vms = [r[0] for r in db.query(LogEntry.vm_name).distinct().all()]
    all_vms = sorted(set(vm_names + net_vms + log_vms))

    # Base queries
    metrics_q = db.query(Metric)
    network_q = db.query(NetworkData)
    logs_q = db.query(LogEntry)
    alerts_q = db.query(Alert)

    if vm_name:
        metrics_q = metrics_q.filter(Metric.vm_name == vm_name)
        network_q = network_q.filter(NetworkData.vm_name == vm_name)
        logs_q = logs_q.filter(LogEntry.vm_name == vm_name)
        alerts_q = alerts_q.filter(Alert.vm_name == vm_name)

    total_logs = logs_q.count()
    total_alerts = alerts_q.count()
    active_alerts = alerts_q.filter(Alert.resolved == False).count()

    recent_metrics = metrics_q.order_by(desc(Metric.timestamp)).limit(limit).all()
    recent_network = network_q.order_by(desc(NetworkData.timestamp)).limit(limit).all()
    recent_logs = logs_q.order_by(desc(LogEntry.timestamp)).limit(limit).all()
    recent_alerts = alerts_q.order_by(desc(Alert.timestamp)).limit(limit).all()

    return DashboardData(
        total_vms=len(all_vms),
        total_logs=total_logs,
        total_alerts=total_alerts,
        active_alerts=active_alerts,
        recent_metrics=recent_metrics,
        recent_network=recent_network,
        recent_logs=recent_logs,
        recent_alerts=recent_alerts,
        vm_list=all_vms,
    )


# ==================== ALERTS ====================

@router.get("/alerts", response_model=list[AlertResponse])
def get_alerts(
    severity: Optional[str] = Query(None),
    vm_name: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    """Get alerts, optionally filtered by severity or VM."""
    query = db.query(Alert)
    if severity:
        query = query.filter(Alert.severity == severity.upper())
    if vm_name:
        query = query.filter(Alert.vm_name == vm_name)
    return query.order_by(desc(Alert.timestamp)).limit(limit).all()


@router.patch("/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    """Mark alert as resolved."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.resolved = True
    db.commit()
    return {"status": "resolved", "id": alert_id}


# ==================== EXPORT ====================

@router.get("/export/metrics")
def export_metrics(db: Session = Depends(get_db)):
    metrics = db.query(Metric).all()
    path = export_metrics_csv(metrics)
    return {"status": "exported", "file": path}


@router.get("/export/alerts")
def export_alerts_route(db: Session = Depends(get_db)):
    alerts = db.query(Alert).all()
    path = export_alerts_csv(alerts)
    return {"status": "exported", "file": path}


# ==================== REPORT ====================

@router.get("/report/generate")
def generate_report_endpoint(db: Session = Depends(get_db)):
    """Generate HTML security report."""
    from reports.report_generator import generate_report

    # Gather dashboard data
    vm_names = [r[0] for r in db.query(Metric.vm_name).distinct().all()]
    net_vms = [r[0] for r in db.query(NetworkData.vm_name).distinct().all()]
    log_vms = [r[0] for r in db.query(LogEntry.vm_name).distinct().all()]
    all_vms = sorted(set(vm_names + net_vms + log_vms))

    data = {
        "total_vms": len(all_vms),
        "total_logs": db.query(LogEntry).count(),
        "total_alerts": db.query(Alert).count(),
        "recent_alerts": db.query(Alert).order_by(desc(Alert.timestamp)).limit(50).all(),
    }
    filepath = generate_report(data)
    return {"status": "generated", "file": filepath}
