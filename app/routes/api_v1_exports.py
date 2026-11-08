"""REST API v1 export endpoints (payroll and related downloads)."""

import csv
import io

from flask import Response, g, jsonify, request, send_file

from app.routes.api_v1 import api_v1_bp
from app.routes.api_v1_common import _parse_date
from app.utils.api_auth import require_api_token
from app.utils.api_responses import forbidden_response


@api_v1_bp.route("/exports/payroll", methods=["GET"])
@require_api_token("read:reports")
def export_payroll():
    """Template-aware payroll export (CSV default, XLSX via ?format=xlsx)."""
    from app.models.payroll_export_template import PayrollExportTemplate
    from app.services.workforce_governance_service import WorkforceGovernanceService

    start = _parse_date(request.args.get("start_date"))
    end = _parse_date(request.args.get("end_date"))
    if not start or not end:
        return jsonify({"error": "start_date and end_date are required (YYYY-MM-DD)"}), 400

    user_id = request.args.get("user_id", type=int)
    if not g.api_user.is_admin:
        user_id = g.api_user.id

    approved_only = request.args.get("approved_only", "false").lower() == "true"
    closed_only = request.args.get("closed_only", "false").lower() == "true"
    fmt = (request.args.get("format") or "csv").strip().lower()

    template_id = request.args.get("template_id", type=int)
    tmpl = PayrollExportTemplate.query.get(template_id) if template_id else None
    if not tmpl:
        tmpl = PayrollExportTemplate.query.filter_by(is_default=True).first()
    if not tmpl:
        tmpl = PayrollExportTemplate.ensure_builtin_defaults()

    columns = tmpl.columns or PayrollExportTemplate.DEFAULT_COLUMNS
    delimiter = tmpl.delimiter or ","
    grouping = tmpl.grouping or "week"

    rows = WorkforceGovernanceService().payroll_rows(
        start_date=start,
        end_date=end,
        user_id=user_id,
        approved_only=approved_only,
        closed_only=closed_only,
        grouping=grouping,
    )

    if fmt == "xlsx":
        try:
            from openpyxl import Workbook
        except ImportError:
            return jsonify({"error": "XLSX export requires openpyxl"}), 501

        wb = Workbook()
        ws = wb.active
        ws.title = "Payroll"
        ws.append(columns)
        for row in rows:
            ws.append([row.get(col, "") for col in columns])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        filename = f"payroll_export_{start.isoformat()}_{end.isoformat()}.xlsx"
        return send_file(
            buf,
            as_attachment=True,
            download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    output = io.StringIO()
    writer = csv.writer(output, delimiter=delimiter)
    writer.writerow(columns)
    for row in rows:
        writer.writerow([row.get(col, "") for col in columns])

    filename = f"payroll_export_{start.isoformat()}_{end.isoformat()}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@api_v1_bp.route("/reports/labor-compliance/<preset_id>", methods=["GET"])
@require_api_token("read:reports")
def labor_compliance_report_api(preset_id):
    """Labor-compliance preset export (JSON). Use ?format=csv for download."""
    from app.services.labor_compliance_service import LaborComplianceService

    start = _parse_date(request.args.get("start_date"))
    end = _parse_date(request.args.get("end_date"))
    if not start or not end:
        return jsonify({"error": "start_date and end_date are required (YYYY-MM-DD)"}), 400

    user_id = request.args.get("user_id", type=int)
    if not g.api_user.is_admin:
        if user_id is not None and user_id != g.api_user.id:
            return forbidden_response("Access denied")
        user_id = g.api_user.id

    weekly_threshold = request.args.get("weekly_threshold", type=float)
    overages_only = request.args.get("overages_only", "false").lower() == "true"
    fmt = (request.args.get("format") or "json").strip().lower()

    service = LaborComplianceService()
    try:
        rows, meta = service.export_rows(
            preset_id,
            start_date=start,
            end_date=end,
            user_id=user_id,
            weekly_threshold=weekly_threshold,
            overages_only=overages_only,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404

    if fmt == "csv":
        output = io.StringIO()
        if rows:
            writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        else:
            writer = csv.writer(output)
            writer.writerow(["message"])
            writer.writerow(["No records in range"])
        filename = f"{meta['preset_id']}_{start.isoformat()}_{end.isoformat()}.csv"
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    return jsonify({"meta": meta, "rows": rows, "count": len(rows)})


@api_v1_bp.route("/reports/labor-compliance", methods=["GET"])
@require_api_token("read:reports")
def labor_compliance_presets_api():
    from app.services.labor_compliance_service import LaborComplianceService

    return jsonify({"presets": LaborComplianceService().list_presets()})
