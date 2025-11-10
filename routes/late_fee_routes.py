"""
Late Fee Routes - API endpoint for calculating late fees
"""

from flask import Blueprint, jsonify
from services.library_service import calculate_late_fee_for_book 

late_fee_bp = Blueprint("late_fee", __name__)

@late_fee_bp.route("/late_fee/<patron_id>/<int:book_id>", methods=["GET"])
def get_late_fee(patron_id, book_id):
    """
    API endpoint: Calculate late fees for a book borrowed by a patron.
    """
    result = calculate_late_fee_for_book(patron_id, book_id)
    return jsonify(result)