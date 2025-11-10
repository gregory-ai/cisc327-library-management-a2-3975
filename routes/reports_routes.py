from flask import Blueprint, render_template, request
from services.library_service import get_patron_status_report

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/reports')
def show_patron_status_report():
    patron_id = request.args.get('patron_id', '').strip()
    report = None
    status_message = None

    if patron_id:
        report = get_patron_status_report(patron_id)
        status_message = report.get('status')

    return render_template(
        'reports.html',
        patron_id=patron_id,
        report=report,
        status_message=status_message
    )