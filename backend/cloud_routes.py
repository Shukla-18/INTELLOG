"""Cloud VM Discovery & Agent Deployment API Routes"""
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import MonitoredVM
from backend.schemas import (
    CloudVM, DeployAgentRequest, DeployAgentResponse,
    StartMonitoringRequest, MonitoredVMResponse,
)
from backend.cloud import cloud_connector, agent_deployer

cloud_router = APIRouter(prefix="/cloud", tags=["Cloud"])


@cloud_router.get("/vms", response_model=List[CloudVM])
def scan_cloud_vms():
    """Scan cloud environment and return list of VMs."""
    vms = cloud_connector.discover_vms()
    return vms


@cloud_router.post("/deploy-agent", response_model=DeployAgentResponse)
def deploy_agent(req: DeployAgentRequest, db: Session = Depends(get_db)):
    """Deploy monitoring agent to a VM."""
    result = agent_deployer.deploy(
        vm_id=req.vm_id,
        ip=req.ip,
        username=req.username,
        password=req.password,
        ssh_key=req.ssh_key,
        mode=req.mode,
    )

    if result["status"] == "success":
        # Update or create MonitoredVM record
        vm = db.query(MonitoredVM).filter(MonitoredVM.vm_id == req.vm_id).first()
        if vm:
            vm.agent_status = "running"
            vm.agent_pid = result.get("agent_pid")
            vm.deployed_at = datetime.now(timezone.utc)
        else:
            vm = MonitoredVM(
                vm_id=req.vm_id,
                vm_name=req.vm_id,
                private_ip=req.ip,
                agent_status="running",
                agent_pid=result.get("agent_pid"),
                monitoring=True,
                deployed_at=datetime.now(timezone.utc),
            )
            db.add(vm)
        db.commit()

    return result


@cloud_router.post("/start-monitoring")
def start_monitoring(req: StartMonitoringRequest, db: Session = Depends(get_db)):
    """Start monitoring selected VMs — store in DB and deploy agents."""
    # Fetch cloud VMs to get details
    all_vms = {v["vm_id"]: v for v in cloud_connector.discover_vms()}
    results = []

    for vm_id in req.vm_ids:
        cloud_vm = all_vms.get(vm_id)
        if not cloud_vm:
            results.append({"vm_id": vm_id, "status": "error", "message": "VM not found"})
            continue

        # Upsert MonitoredVM
        existing = db.query(MonitoredVM).filter(MonitoredVM.vm_id == vm_id).first()
        if existing:
            existing.monitoring = True
            existing.status = cloud_vm["status"]
            existing.vm_name = cloud_vm["vm_name"]
        else:
            new_vm = MonitoredVM(
                vm_id=vm_id,
                vm_name=cloud_vm["vm_name"],
                private_ip=cloud_vm["private_ip"],
                status=cloud_vm["status"],
                image=cloud_vm.get("image", ""),
                flavor=cloud_vm.get("flavor", ""),
                monitoring=True,
            )
            db.add(new_vm)

        # Auto-deploy agent (demo mode)
        deploy_result = agent_deployer.deploy(
            vm_id=vm_id,
            ip=cloud_vm["private_ip"],
            mode="demo",
        )
        results.append({
            "vm_id": vm_id,
            "vm_name": cloud_vm["vm_name"],
            **deploy_result,
        })

    db.commit()

    # Update agent status for deployed VMs
    for r in results:
        if r.get("status") == "success":
            vm = db.query(MonitoredVM).filter(MonitoredVM.vm_id == r["vm_id"]).first()
            if vm:
                vm.agent_status = "running"
                vm.deployed_at = datetime.now(timezone.utc)
    db.commit()

    running = db.query(MonitoredVM).filter(MonitoredVM.monitoring == True).count()
    return {
        "message": f"Monitoring started for {len(req.vm_ids)} VM(s)",
        "total_monitored": running,
        "results": results,
    }


@cloud_router.get("/monitored", response_model=List[MonitoredVMResponse])
def get_monitored_vms(db: Session = Depends(get_db)):
    """Get list of all monitored VMs."""
    return db.query(MonitoredVM).all()


@cloud_router.get("/status")
def cloud_status(db: Session = Depends(get_db)):
    """Get cloud monitoring summary."""
    total = db.query(MonitoredVM).count()
    active = db.query(MonitoredVM).filter(MonitoredVM.monitoring == True).count()
    agents_running = db.query(MonitoredVM).filter(MonitoredVM.agent_status == "running").count()
    return {
        "total_vms": total,
        "active_monitoring": active,
        "agents_running": agents_running,
    }


@cloud_router.delete("/monitored/{vm_id}")
def stop_monitoring(vm_id: str, db: Session = Depends(get_db)):
    """Stop monitoring a specific VM."""
    vm = db.query(MonitoredVM).filter(MonitoredVM.vm_id == vm_id).first()
    if not vm:
        raise HTTPException(status_code=404, detail="VM not found")
    vm.monitoring = False
    vm.agent_status = "stopped"
    db.commit()
    return {"message": f"Stopped monitoring {vm.vm_name}"}
