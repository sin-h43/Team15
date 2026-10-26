from flask import Blueprint, render_template, request

from crb.db import get_db
from crb.guards import role_required
from crb.reports import utilisation
from crb.validators import ValidationError

bp = Blueprint("reports", __name__)


@bp.route("/reports/utilisation")
@role_required("admin")
def utilisation_report():
    start = request.args.get("start", "")
    end = request.args.get("end", "")
    rows = None
    error = None
    if request.args:
        try:
            rows = utilisation(get_db(), start, end)
        except ValidationError as problem:
            error = str(problem)
    page = render_template("report.html", rows=rows, error=error, start=start, end=end)
    return page, 400 if error else 200
