"""
Library Service Module - Business Logic Functions
Contains all the core business logic for the Library Management System
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from database import (
    get_book_by_id, get_book_by_isbn, get_patron_borrow_count,
    insert_book, insert_borrow_record, update_book_availability,
    update_borrow_record_return_date, get_all_books, get_patron_borrowed_books, get_patron_borrowing_history
)

def add_book_to_catalog(title: str, author: str, isbn: str, total_copies: int) -> Tuple[bool, str]:
    """
    Add a new book to the catalog.
    Implements R1: Book Catalog Management
    
    Args:
        title: Book title (max 200 chars)
        author: Book author (max 100 chars)
        isbn: 13-digit ISBN
        total_copies: Number of copies (positive integer)
        
    Returns:
        tuple: (success: bool, message: str)
    """
    # Input validation
    if not title or not title.strip():
        return False, "Title is required."
    
    if len(title.strip()) > 200:
        return False, "Title must be less than 200 characters."
    
    if not author or not author.strip():
        return False, "Author is required."
    
    if len(author.strip()) > 100:
        return False, "Author must be less than 100 characters."
    
    if len(isbn) != 13:
        return False, "ISBN must be exactly 13 digits."
    
    if not isinstance(total_copies, int) or total_copies <= 0:
        return False, "Total copies must be a positive integer."
    
    # Check for duplicate ISBN
    existing = get_book_by_isbn(isbn)
    if existing:
        return False, "A book with this ISBN already exists."
    
    # Insert new book
    success = insert_book(title.strip(), author.strip(), isbn, total_copies, total_copies)
    if success:
        return True, f'Book "{title.strip()}" has been successfully added to the catalog.'
    else:
        return False, "Database error occurred while adding the book."

def borrow_book_by_patron(patron_id: str, book_id: int) -> Tuple[bool, str]:
    """
    Allow a patron to borrow a book.
    Implements R3 as per requirements  
    
    Args:
        patron_id: 6-digit library card ID
        book_id: ID of the book to borrow
        
    Returns:
        tuple: (success: bool, message: str)
    """
    # Validate patron ID
    if not patron_id or not patron_id.isdigit() or len(patron_id) != 6:
        return False, "Invalid patron ID. Must be exactly 6 digits."
    
    # Check if book exists and is available
    book = get_book_by_id(book_id)
    if not book:
        return False, "Book not found."
    
    if book['available_copies'] <= 0:
        return False, "This book is currently not available."
    
    # Check patron's current borrowed books count
    current_borrowed = get_patron_borrow_count(patron_id)
    
    if current_borrowed > 5:
        return False, "You have reached the maximum borrowing limit of 5 books."
    
    # Create borrow record
    borrow_date = datetime.now()
    due_date = borrow_date + timedelta(days=14)
    
    # Insert borrow record and update availability
    borrow_success = insert_borrow_record(patron_id, book_id, borrow_date, due_date)
    if not borrow_success:
        return False, "Database error occurred while creating borrow record."
    
    availability_success = update_book_availability(book_id, -1)
    if not availability_success:
        return False, "Database error occurred while updating book availability."
    
    return True, f'Successfully borrowed "{book["title"]}". Due date: {due_date.strftime("%Y-%m-%d")}.'

def return_book_by_patron(patron_id: str, book_id: int) -> Tuple[bool, str]:
    """
    Process book return by a patron.
    Implements R4 as per requirements  
    
    Args:
        patron_id: 6-digit library card ID
        book_id: ID of the book to borrow
        
    Returns:
        tuple: (success: bool, message: str)
    """
    # Input validation
    # Validate patron ID
    if not patron_id or not patron_id.isdigit() or len(patron_id) != 6:
        return False, "Invalid patron ID. Must be exactly 6 digits."
    
    # Check if book exists and is available
    book = get_book_by_id(book_id)
    if not book:
        return False, "Book not found."

    # Check if patron actually borrowed this book
    borrowed_books = get_patron_borrowed_books(patron_id)
    if not any(b['book_id'] == book_id for b in borrowed_books):
        return False, "Book not borrowed by patron."

    # Update book availability
    availability_success = update_book_availability(book_id, +1)
    if not availability_success:
        return False, "Database error occurred while updating book availability."
    
    # Record return date
    return_date = datetime.now()
    return_success = update_borrow_record_return_date(patron_id, book_id, return_date)
    if not return_success:
            update_book_availability(book_id, -1)
            return False, "Database error occurred while recording return date."
    
    # Calculate late fees
    late_fees = calculate_late_fee_for_book(patron_id, book_id)

    if late_fees['status'] != "Fee amount sucessfully calculated." and late_fees['status'] != "Book is not overdue.":
        return True, "Late fees not updated. Error: "+late_fees['status']
    
    # Display late fees
    print("Late Fees:\n")
    print("Fee Amount: "+str(late_fees['fee_amount'])+'\nDays Overdue: '+str(late_fees['days_overdue'])+'\nStatus: '+str(late_fees['status'])+'\n')
    return True, "Book successfully returned."

def calculate_late_fee_for_book(patron_id: str, book_id: int) -> Dict:
    """
    Calculate late fee for book.
    Implements R5 as per requirements  
    
    Args:
        patron_id: 6-digit library card ID
        book_id: ID of the book to borrow
        
    Returns:
        Dictionary of late fees details including
            - Fee amount 
            - Days overdue 
            - Status of late fee calculation
    """
    late_fees = {'fee_amount':0.00, 'days_overdue': 0, 'status': ""}

    # Input validation
    # Validate patron ID
    if not patron_id or not patron_id.isdigit() or len(patron_id) != 6:
        late_fees['status'] = 'Invalid patron ID. Must be exactly 6 digits.'
        return late_fees
    
    # Check if book exists and is available
    book = get_book_by_id(book_id)
    if not book:
        late_fees['status'] = 'Book not found.'
        return late_fees

    # Check that book was borrowed by patron
    record = None
    borrowed_books = get_patron_borrowing_history(patron_id)
    for book in borrowed_books:
        if book['book_id'] == book_id:
            record = book
    if record is None:
        late_fees['status'] = 'Book not borrowed by patron.'
        return late_fees

    return_date = record["return_date"]
    if return_date is None:
        late_fees['status'] = 'Book not returned.'
        return late_fees
    
    due_date = record['due_date']
    if return_date <= due_date: 
        late_fees['status'] = 'Book is not overdue.'
        return late_fees
    
    overdue_days = (return_date - due_date).days
    late_fees['days_overdue'] = overdue_days

    if overdue_days <= 7: 
        late_fees['fee_amount'] = overdue_days*0.5
    else: 
        late_fees['fee_amount'] = min(3.50 + (overdue_days-7)*1.00, 15.00)

    late_fees['status'] = 'Fee amount successfully calculated.'
    return late_fees


def search_books_in_catalog(search_term: str, search_type: str) -> List[Dict]:
    """
    Search for books in the catalog.
    Implements R6 as per requirements  
    
    Args:
        search_term: string search term
        search_type: search type (title, author, isbn)
        
    Returns:
        List of books matching search term based on search type.
    """
    all_books = get_all_books()

    if not search_term: 
        return []
    
    results = []

    if search_type == "title":
        results = [book for book in all_books if search_term.lower() in book["title"].lower()]

    elif search_type == "author":
        results = [book for book in all_books if search_term.lower() in book["author"].lower()]
    
    elif search_type == "isbn": 
        results = [book for book in all_books if book["isbn"] == search_term]
    
    return results


def get_patron_status_report(patron_id: str) -> Dict:
    """
    Get status report for a patron.
    Implements R7 as per requirements  
    
    Args:
        patron_id: 6-digit library card ID
        
    Returns:
        Dictionary of patron's status including
            - Currently borrowed books with due dates
            - Total late fees owed  
            - Number of books currently borrowed
            - Borrowing history
            - Status of patron status report retrieval
    """
    status_report = {
        'current_borrowed_books': [],
        'total_fees_owed': 0.00,
        'num_current_borrowed_books': 0,
        'borrowing_history': [], 
        'status' : ""
    }

    # Validate patron ID
    if not patron_id or not patron_id.isdigit() or len(patron_id) != 6:
        status_report['status'] = "Invalid patron ID. Must be exactly 6 digits."
        return status_report

    # Current borrowed books
    borrowed_books = get_patron_borrowed_books(patron_id)
    total_late_fees = 0.0

    for book in borrowed_books:
        status_report['current_borrowed_books'].append({
            'book_id': book['book_id'],
            'title': book['title'],
            'author': book['author'],
            'due_date': book['due_date'],
            'is_overdue': book['is_overdue']
        })
        late_fees = calculate_late_fee_for_book(patron_id, book['book_id'])
        total_late_fees += late_fees.get('fee_amount', 0.0)

    status_report['num_current_borrowed_books'] = len(borrowed_books)
    status_report['total_fees_owed'] = round(total_late_fees, 2)

    # History borrowed books
    history_records = get_patron_borrowing_history(patron_id)

    for record in history_records:
        status_report['borrowing_history'].append({
            'book_id': record['book_id'],
            'title': record['title'],
            'author': record['author'],
            'borrow_date': record['borrow_date'],
            'due_date': record['due_date'],
            'return_date': record['return_date']
        })

    status_report['status'] = "Successfully retrieved patron's status report."
    return status_report