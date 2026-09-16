"""REST API v1 endpoints for geofences."""

from flask import g

from app.models.geofence import Geofence
from app.routes.api_v1 import api_v1_bp
from app.utils.api_auth import require_api_token
from app.utils.api_responses import success_response


@api_v1_bp.route("/geofences", methods=["GET"])
@require_api_token("read:time_entries")
def api_list_geofences():
    geofences = Geofence.query.filter_by(is_active=True).order_by(Geofence.name.asc()).all()
    return success_response(data={"geofences": [fence.to_dict() for fence in geofences]})
