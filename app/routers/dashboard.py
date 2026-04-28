# app/routers/dashboard.py
"""
Quantum Nexus Dashboard Router
Maps FastAPI routes to lattice dependencies per Phase 2 blueprint hooks.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.quantum_nexus import QuantumNexus

router = APIRouter(tags=["dashboard"])

# Resolve templates directory relative to project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"
BLUEPRINT_PATH = PROJECT_ROOT / "data" / "quantum_nexus_blueprint.yaml"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Load blueprint once at import
QN = QuantumNexus.from_yaml(BLUEPRINT_PATH)


@router.get("/api/metrics", response_model=dict)
async def api_metrics() -> Dict[str, Any]:
    """
    Quantum Nexus metrics endpoint.
    
    dependency: dep_AllFiles_L2R_to_Z1
    domains: [memory_zones, cognitive_lenses, system_health]
    """
    dep = QN.dependency("dep_AllFiles_L2R_to_Z1")

    # Build metrics response with lattice context
    metrics = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dependency": {
            "id": dep["id"],
            "type": dep.get("type"),
            "from": dep.get("from"),
            "to": dep.get("to"),
            "terminus_label": dep.get("terminus_label"),
            "origin_label": dep.get("origin_label"),
        },
        "domains": {
            "memory_zones": {
                "active": 0.85,        # >0.7 entropy
                "emergent": 0.45,      # 0.3-0.7 entropy
                "archived": 0.15,      # <0.3 entropy
            },
            "cognitive_lenses": {
                "adhd": {"efficiency": 0.92, "queries": 45},
                "autism": {"efficiency": 0.88, "queries": 38},
                "dyslexia": {"efficiency": 0.95, "queries": 52},
                "neurotypical": {"efficiency": 0.78, "queries": 29},
            },
            "system_health": {
                "response_time_ms": 145,
                "error_rate": 0.02,
                "uptime_hours": 24,
            },
        },
        "great_greg": {
            "origin": QN.resolve("A1").__dict__,
            "terminus": QN.resolve("Z1").__dict__,
        },
        "path": dep.get("path"),  # row-major path A1 → ... → Z1
    }
    return metrics


@router.get("/api/resolve/{ref}")
async def api_resolve(ref: str) -> Dict[str, Any]:
    """
    Great Greg coordinate resolver endpoint.
    
    Accepts:
      - /api/resolve/P1
      - /api/resolve/Node_3:P1
      - /api/resolve/Node_3.R3C4
    """
    try:
        return QN.to_api_response(ref)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/api/dependency/{dep_id}")
async def api_dependency(dep_id: str) -> Dict[str, Any]:
    """
    Get dependency configuration and traced path.
    """
    try:
        dep = QN.dependency(dep_id)
        path = dep.get("path", [])
        traced = QN.trace_path(path)
        return {
            "dependency": dep,
            "traced_path": [coord.__dict__ for coord in traced],
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/api/lattice/diagonal")
async def api_diagonal_trace() -> Dict[str, Any]:
    """
    Return the diagonal dependency path (A1 → H1 → O1 → V1).
    """
    path = QN.diagonal_trace()
    return {
        "dependency_id": "dep_A1_to_V1",
        "path": [coord.__dict__ for coord in path],
        "description": "Prime Truth (A1) → Meta Research focal point (V1)"
    }


@router.get("/api/lattice/lateral")
async def api_lateral_trace() -> Dict[str, Any]:
    """
    Return the full lateral row-major path (A1 → Z1).
    """
    path = QN.lateral_trace()
    return {
        "dependency_id": "dep_AllFiles_L2R_to_Z1",
        "path": [coord.__dict__ for coord in path],
        "description": "Origin (A1) → Terminus (Z1) row-major traversal"
    }


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    """
    Quantum Nexus Dashboard HTML view.
    
    dependency: dep_A1_to_V1
    template: quantum_dashboard.html
    """
    dep = QN.dependency("dep_A1_to_V1")

    # Resolve the diagonal path cells into GreatGreg objects for display
    diagonal = [QN.resolve_cell(cell).__dict__ for cell in dep.get("path", [])]

    return templates.TemplateResponse(
        "quantum_dashboard.html",
        {
            "request": request,
            "dependency": dep,
            "diagonal_path": diagonal,   # A1 → H1 → O1 → V1
        },
    )
