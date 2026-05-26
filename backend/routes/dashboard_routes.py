from __future__ import annotations
from flask import Blueprint, jsonify
from ..services.dashboard_service import merged_dashboard

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")

@dashboard_bp.get("/today")
def today():
    return jsonify(merged_dashboard())
