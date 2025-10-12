"""
API Routes - JSON API endpoints
"""

from flask import Blueprint, jsonify, request
from library_service import calculate_late_fee_for_book, search_books_in_catalog, get_patron_status_report

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/late_fee/<patron_id>/<int:book_id>')
def get_late_fee(patron_id, book_id):
    """
    Calculate late fee for a specific book borrowed by a patron.
    API endpoint for R4: Late Fee Calculation
    """
    result = calculate_late_fee_for_book(patron_id, book_id)
    return jsonify(result), 501 if 'not implemented' in result.get('status', '') else 200

@api_bp.route('/search')
def search_books_api():
    """
    Search for books via API endpoint.
    Alternative API interface for R5: Book Search Functionality
    """
    search_term = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'title')
    
    if not search_term:
        return jsonify({'error': 'Search term is required'}), 400
    
    # Use business logic function
    books = search_books_in_catalog(search_term, search_type)
    
    return jsonify({
        'search_term': search_term,
        'search_type': search_type,
        'results': books,
        'count': len(books)
    })

@api_bp.route('/patron_status/<patron_id>')
def get_patron_status_api(patron_id):
    """
    Get patron status report.
    Implements R7: Patron Status Report
    """
    patron_id = patron_id.strip()

    if not patron_id.isdigit() or len(patron_id) != 6:
        return jsonify({
            'status': "Invalid patron ID. Must be exactly 6 digits.",
            'error': True
        }), 400

    report = get_patron_status_report(patron_id)
    status_message = report.get('status', '')

    if "Invalid" in status_message or "not found" in status_message.lower():
        return jsonify({
            'status': status_message,
            'error': True
        }), 404

    return jsonify({
        'patron_id': patron_id,
        'report': report,
        'status': status_message,
        'error': False
    }), 200