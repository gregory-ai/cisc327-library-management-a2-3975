import os
import pytest
from flask import Flask
from datetime import datetime, timedelta

from library_service import (
    add_book_to_catalog, 
    borrow_book_by_patron,
    return_book_by_patron,
    calculate_late_fee_for_book,
    search_books_in_catalog,
    get_patron_status_report,
)

from routes.catalog_routes import catalog_bp  # blueprint
from routes.borrowing_routes import borrowing_bp # blueprint
from routes.search_routes import search_bp # blueprint
from database import get_book_by_isbn, get_book_by_id, update_borrow_record_return_date, get_patron_borrowing_history, get_db_connection

def reset_database():
    """
    Reset the database by clearing all tables.
    """
    conn = get_db_connection()
    try:
        # Clear borrow records first 
        conn.execute("DELETE FROM borrow_records")
        # Clear books
        conn.execute("DELETE FROM books")
        conn.commit()
    finally:
        conn.close()

@pytest.fixture(autouse=True)
def clear_db():
    reset_database()  # Implement this to clear all books, patrons, borrows
    yield

# pytest fixture that builds a temporary Flask app for testing 
@pytest.fixture
def client():
    # Absolute path to templates/ directory 
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates"))
    
    # Create Flask app just for testing 
    app = Flask(__name__, template_folder=template_dir)
    app.config["TESTING"] = True

    # Register catalog blueprint
    app.register_blueprint(catalog_bp)
    app.register_blueprint(borrowing_bp) 
    app.register_blueprint(search_bp)

    # Makes client available to any test with client argument 
    with app.test_client() as client:
        with app.app_context():
            yield client


''' Tests for Functional Requirements '''

# R1: Add Book To Catalog
def test_add_book_valid_input():
    # Test1 adding a book with valid input.
    success, message = add_book_to_catalog("Harry Potter", "JK Rowling", "1000000000001", 5)
    
    assert success == True
    assert "successfully added" in message.lower()


def test_add_book_long_title():
    # Test2 adding a book with a title over 200 chars.
    success, message = add_book_to_catalog("bookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbookbook ", "Author With Long Book Name", "1000000000002", 5)
    
    assert success == False
    assert "Title must be less than 200 characters." in message


def test_add_book_long_author():
    # Test3 adding a book with a author over 100 chars.
    success, message = add_book_to_catalog("How to Deal with a Having Long Name", "NameNameNameNameNameNameNameNameNameNameNameNameNameNameNameNameNameNameNameNameNameNameNameNameNameNameNameNameNameNameNameNameNameNameNameName", "1000000000003", 5)
    
    assert success == False
    assert "Author must be less than 100 characters." in message


def test_add_book_long_isbn():
    # Test4 adding a book with a isbn over 13 digits.
    success, message = add_book_to_catalog("Best Book Ever", "Best Author Ever", "10000000000044444", 5)
    
    assert success == False
    assert "ISBN must be exactly 13 digits." in message


def test_add_book_negative_copies():
    # Test5 adding a book with a total_copies with negative number.
    success, message = add_book_to_catalog("Really Cool Book", "Really Cool Author", "1000000000005", -12)
    
    assert success == False
    assert "Total copies must be a positive integer." in message


def test_add_book_duplicate_isbn():
    # Test6 adding a book with a duplicate isbn.
    add_book_to_catalog("The way I used to be", "Allan Shirt", "1000000000006", 5) 
    success, message = add_book_to_catalog("The way I am", "Allan Shirt", "1000000000006", 5)
    
    assert success == False
    assert "A book with this ISBN already exists." in message


def test_add_book_empty_title():
    # Test7 adding a book with an empty title.
    success, message = add_book_to_catalog("", "Some Author", "1000000000007", 5)
    
    assert success == False
    assert "Title is required." in message


def test_add_book_empty_author():  
    # Test8 adding a book with an empty author.
    success, message = add_book_to_catalog("Some Book", "", "1000000000008", 5)
    
    assert success == False
    assert "Author is required." in message

def test_add_book_whitespace_title():
    # Test9 adding a book with an empty author.
    success, message = add_book_to_catalog("   ", "Author Name", "1000000000010", 1)
    assert success == False
    assert "Title is required." in message


def test_add_book_whitespace_author():
    # Test10 adding a book with an empty author.
    success, message = add_book_to_catalog("Whitespace Author Test", "   ", "1000000000011", 1)
    assert success == False
    assert "Author is required." in message

def test_add_book_zero_copies():
    # Test11 adding a book with a total_copies of zero.
    success, message = add_book_to_catalog("Empty Library", "Zero Author", "1000000000012", 0)
    assert success == False
    assert "Total copies must be a positive integer." in message


#-----------------------------------------------------------------------------------------------------------------------

# R2: Book Catalog Display
def test_catalog_valid_input(client):
    # Test1 retrieving catalog with valid input after adding books.
    add_book_to_catalog("New Book", "New Author", "2000000000001", 5)
    response = client.get("/catalog")
    
    # Check that the response is successful
    assert response.status_code == 200
    # Check that the added book title appears in the HTML
    assert b"New Book" in response.data


def test_catalog_book_fields_present(client):
    # Test2 each book in catalog contains required fields.
    add_book_to_catalog("Field Test Book", "Field Author", "2000000000003", 3)
    response = client.get("/catalog")
    
    # Check that required fields are present in the rendered HTML
    html = response.data.decode()
    assert "Field Test Book" in html
    assert "Field Author" in html
    assert "2000000000003" in html


def test_catalog_available_copies_match(client):
    # Test3 borrowing a book should reduce available copies in catalog.
    add_book_to_catalog("Borrowable Book", "Borrow Author", "2000000000004", 2)
    book = get_book_by_isbn("2000000000004")
    borrow_book_by_patron("123456", book["id"])
    response = client.get("/catalog")
    
    html = response.data.decode()
    # Ensure the borrowed book is listed
    assert "Borrowable Book" in html
    # Available copies should be reduced (1 left out of 2)
    assert "1" in html  # available copies
    assert "2" in html  # total copies


def test_catalog_duplicate_books_displayed_once(client):
    # Test4 catalog should not list duplicate ISBN entries.
    add_book_to_catalog("Unique Book", "Unique Author", "2000000000005", 1)
    add_book_to_catalog("Unique Book 2", "Unique Author 2", "2000000000005", 1)
    
    response = client.get("/catalog")
    html = response.data.decode()
    
    # ISBN should appear only once
    assert html.count("2000000000005") == 1

#-----------------------------------------------------------------------------------------------------------------------
    
# R3: Book Borrowing Interface

def test_borrow_book_by_patron_valid():
    # Test1 borrowing a book with valid input.
    add_book_to_catalog("Borrowable Book", "Some Author", "3000000000001", 1)
    book = get_book_by_isbn("3000000000001")
    success, message = borrow_book_by_patron("300001", book["id"])
    
    assert success == True
    assert "successfully borrowed" in message.lower()


def test_borrow_book_by_patron_invalid_patron_id():
    # Test2 borrowing a book with an invalid patron ID (not 6 digits)
    add_book_to_catalog("Some Book", "Some Author", "3000000000002", 1)
    book = get_book_by_isbn("3000000000002")
    success, message = borrow_book_by_patron("3002", book["id"])
    
    assert success == False
    assert "Invalid patron ID. Must be exactly 6 digits." in message


def test_borrow_book_by_patron_invalid_book_id():
    # Test3 borrowing a book with an invalid book ID.
    success, message = borrow_book_by_patron("300003", 999999)
    
    assert success == False
    assert "Book not found." in message


def test_borrow_book_by_patron_unavailable_book():
    # Test4 borrowing a book that is unavailable.
    add_book_to_catalog("Unavailable Book", "No Author", "3000000000004", 1)
    book = get_book_by_isbn("3000000000004")
    borrow_book_by_patron("300004", book["id"])

    success, message = borrow_book_by_patron("310004", book["id"])
    
    assert success == False
    assert "This book is currently not available." in message


def test_borrow_book_by_patron_exceed_limit():
    # Test5 borrowing a book when patron has already borrowed 5 books.
    patron_id = "300005"
    
    # Borrow 5 books for the patron
    for i in range(5):
        isbn = f"350000000000{i+1}"
        add_book_to_catalog(f"Book {i+1}", f"Author {i+1}", isbn, 1)
        book = get_book_by_isbn(isbn)
        borrow_book_by_patron(patron_id, book["id"])
    
    # Borrow a 6th book
    add_book_to_catalog("Extra Book", "Extra Author", "3000000000006", 1)
    book = get_book_by_isbn("3000000000006")
    success, message = borrow_book_by_patron(patron_id, book["id"])
    
    assert success == False
    assert "You have reached the maximum borrowing limit of 5 books." in message

def test_borrow_book_by_patron_whitespace_in_id():
    # Test6 patron ID with leading/trailing spaces should be invalid.
    success, message = borrow_book_by_patron(" 600011 ", 1)
    assert success == False
    assert "Invalid patron ID" in message


def test_borrow_book_by_patron_nondigit_id():
    # Test7 patron ID with non-digit characters should be invalid.
    success, message = borrow_book_by_patron("ABC123", 1)
    assert success == False
    assert "Invalid patron ID" in message

#-----------------------------------------------------------------------------------------------------------------------

# R4: Book Return Processing

def test_return_book_by_patron_valid():
    # Test1 returning a book with valid input.
    add_book_to_catalog("Book about Giraffes", "Giraffe", "4000000000001", 1)
    book = get_book_by_isbn("4000000000001")
    borrow_book_by_patron("400001", book["id"])

    success, message = return_book_by_patron("400001", book["id"])
    assert success == True
    assert "successfully returned" in message.lower()

def test_return_book_by_patron_invalid_patron_id():
    # Test2 returning a book with an invalid patron ID.
    add_book_to_catalog("Book about Monkeys", "Monkey", "4000000000002", 1)
    book = get_book_by_isbn("4000000000002")
    success, message = return_book_by_patron("Patron ID", book["id"])
    
    assert success == False
    assert "Invalid patron ID. Must be exactly 6 digits." in message

def test_return_book_by_patron_invalid_book_id():
    # Test3 returning a book with an invalid book ID.
    success, message = return_book_by_patron("400002", "book_id")
    assert success == False
    assert "Book not found." in message

def test_return_book_by_patron_not_borrowed():
    # Test4 returning a book that was not borrowed by the patron.
    add_book_to_catalog("Book about Horses", "Horse", "4000000000003", 1)
    book = get_book_by_isbn("4000000000003")

    success, message = return_book_by_patron("400003", book["id"])
    assert success == False
    assert "Book not borrowed by patron." in message

def test_return_book_multiple_patrons_same_book():
    # Test5 ensure each patron can only return books they borrowed
    add_book_to_catalog("Shared Book", "Author", "4000000000008", 2)
    book = get_book_by_isbn("4000000000008")
    
    borrow_book_by_patron("400008", book["id"])
    
    success, message = return_book_by_patron("410008", book["id"])
    assert success is False
    assert "Book not borrowed by patron." in message

def test_return_book_increases_availability():
    # Test6 returning should increase available copies
    add_book_to_catalog("Availability Check", "Author", "4000000000009", 1)
    book = get_book_by_isbn("4000000000009")
    borrow_book_by_patron("400009", book["id"])

    borrowed_book = get_book_by_isbn("4000000000009")
    assert borrowed_book["available_copies"] == 0

    return_book_by_patron("400009", book["id"])

    returned_book = get_book_by_isbn("4000000000009")
    assert returned_book["available_copies"] == 1

#-----------------------------------------------------------------------------------------------------------------------

# R5: Late Fee Calculation API
# ASSUMPTIONS: calculate_late_fee_for_book returns a dict with keys:
# 'fee_amount' (float), 'days_overdue' (int), 'status' (str for errors)

def test_calculate_late_fee_for_book_valid():
    # Test1 valid patron and book IDs should return a dict with expected keys.
    add_book_to_catalog("Late Fee Book", "Late Author", "5000000000001", 1)
    book = get_book_by_isbn("5000000000001")
    borrow_book_by_patron("500001", book["id"])
    return_book_by_patron("500001", book["id"])
    
    result = calculate_late_fee_for_book("500001", book["id"])
    
    assert isinstance(result, dict)
    assert "fee_amount" in result # checks that the key exists
    assert "days_overdue" in result # checks that the key exists
    assert "status" in result # checks that the key exists
    assert result['status'] == "Book is not overdue."

def test_calculate_late_fee_for_book_invalid_patron_id():
    # Test2 invalid patron ID should return an error status.
    add_book_to_catalog("Late Fee Book", "Late Author", "5000000000002", 1)
    book = get_book_by_isbn("5000000000002")
    result = calculate_late_fee_for_book("invalid_patron", book["id"])
    
    assert isinstance(result, dict)
    assert "status" in result # checks that the key exists
    assert result['status'] == "Invalid patron ID. Must be exactly 6 digits."

def test_calculate_late_fee_for_book_invalid_book_id():
    # Test3 invalid book ID should return an error status.
    result = calculate_late_fee_for_book("500003", "invalid_book_id")
    
    assert isinstance(result, dict) 
    assert "status" in result # checks that the key exists
    assert result['status'] == "Book not found." 

def test_calculate_late_fee_for_book_not_borrowed():
    # Test4 book not borrowed by the patron should return an error status.
    add_book_to_catalog("Late Fee Book", "Late Author", "5000000000004", 1)
    book = get_book_by_isbn("5000000000004")
    result = calculate_late_fee_for_book("500004", book["id"])
    
    assert isinstance(result, dict)
    assert "status" in result # checks that the key exists
    assert result['status'] == "Book not borrowed by patron."

def test_calculate_late_fee_accurate_fee_calculation():
    # Test5 book overdue 10 days should be 3.50 + (10-7)*1 = 6.50
    add_book_to_catalog("Important book", "Mr.Important", "5000000000005", 1)
    book = get_book_by_isbn("5000000000005")
    borrow_book_by_patron("500005", book["id"])
    update_borrow_record_return_date("500005", book["id"], (datetime.now()+timedelta(days=24)))

    result = calculate_late_fee_for_book("500005", book["id"])
    assert isinstance(result, dict)
    assert round(result["fee_amount"], 2) == 6.50
    assert result["days_overdue"] == 10
    assert result['status'] == "Fee amount successfully calculated." 

def test_calculate_late_fee_not_returned_book():
    # Test6 book fee will not calculate and return error status
    add_book_to_catalog("Book not returned", "Adam Bob", "5000000000006", 1)
    book = get_book_by_isbn("5000000000006")
    borrow_book_by_patron("500006", book["id"])

    result = calculate_late_fee_for_book("500006", book["id"])
    assert isinstance(result, dict)
    assert round(result["fee_amount"], 2) == 0.00
    assert result["days_overdue"] == 0
    assert result['status'] == "Book not returned."


def test_calculate_late_fee_zero_overdue():
    # Test7 book returned exactly on due date should have zero fee
    add_book_to_catalog("On Time Book", "Author", "5000000000010", 1)
    book = get_book_by_isbn("5000000000010")
    borrow_book_by_patron("500010", book["id"])
    # Set return_date exactly on due_date
    record = get_patron_borrowing_history("500010")[0]
    update_borrow_record_return_date("500010", book["id"], record["due_date"])
    
    result = calculate_late_fee_for_book("500010", book["id"])
    assert result['fee_amount'] == 0.00
    assert result['days_overdue'] == 0
    assert result['status'] == "Book is not overdue."


def test_calculate_late_fee_max_fee_cap():
    # Test8 book overdue more than enough days to hit $15 max
    add_book_to_catalog("Max Fee Book", "Author", "5000000000011", 1)
    book = get_book_by_isbn("5000000000011")
    borrow_book_by_patron("500011", book["id"])
    
    record = get_patron_borrowing_history("500011")[0]
    update_borrow_record_return_date("500011", book["id"], record["due_date"] + timedelta(days=25))
    
    result = calculate_late_fee_for_book("500011", book["id"])
    assert round(result['fee_amount'], 2) == 15.00
    assert result['days_overdue'] == 25
    assert result['status'] == "Fee amount successfully calculated."


def test_calculate_late_fee_under_seven_days():
    # Test9 Book overdue 5 days (under 7) should be 5*0.5 = 2.5
    add_book_to_catalog("Short Overdue Book", "Author", "5000000000012", 1)
    book = get_book_by_isbn("5000000000012")
    borrow_book_by_patron("500012", book["id"])
    
    record = get_patron_borrowing_history("500012")[0]
    update_borrow_record_return_date("500012", book["id"], record["due_date"] + timedelta(days=5))
    
    result = calculate_late_fee_for_book("500012", book["id"])
    assert round(result['fee_amount'], 2) == 2.50
    assert result['days_overdue'] == 5
    assert result['status'] == "Fee amount successfully calculated."


def test_calculate_late_fee_exactly_seven_days():
    # Test10 Book overdue exactly 7 days should use $0.5 per day = 3.5
    add_book_to_catalog("Seven Day Book", "Author", "5000000000013", 1)
    book = get_book_by_isbn("5000000000013")
    borrow_book_by_patron("500013", book["id"])
    
    record = get_patron_borrowing_history("500013")[0]
    update_borrow_record_return_date("500013", book["id"], record["due_date"] + timedelta(days=7))
    
    result = calculate_late_fee_for_book("500013", book["id"])
    assert round(result['fee_amount'], 2) == 3.50
    assert result['days_overdue'] == 7
    assert result['status'] == "Fee amount successfully calculated."


def test_calculate_late_fee_over_seven_days():
    # Test11 book overdue 10 days should be 3.50 + (10-7)*1 = 6.50
    add_book_to_catalog("Over Seven Book", "Author", "5000000000014", 1)
    book = get_book_by_isbn("5000000000014")
    borrow_book_by_patron("500014", book["id"])
    
    record = get_patron_borrowing_history("500014")[0]
    update_borrow_record_return_date("500014", book["id"], record["due_date"] + timedelta(days=10))
    
    result = calculate_late_fee_for_book("500014", book["id"])
    assert round(result['fee_amount'], 2) == 6.50
    assert result['days_overdue'] == 10
    assert result['status'] == "Fee amount successfully calculated."

#-----------------------------------------------------------------------------------------------------------------------

# R6: Book Search Functionality
# ASSUMPTIONS: search_books_in_catalog returns a list of dictionaries (same structure as get_all_books())
    # keys: 'id', 'title', 'author', 'isbn', 'total_copies', 'available_copies'

def test_search_books_in_catalog_by_title_partial():
    # Test1 searching books by title (partial, case-insensitive).
    add_book_to_catalog("How to be Creative", "Alex Greg", "6000000000001", 3)
    add_book_to_catalog("Creativity", "John Apple", "6000000000002", 2)
    
    results = search_books_in_catalog("creativ", "title")
    
    assert isinstance(results, list)
    assert any("how to be creative" in book["title"].lower() for book in results)
    assert any("creativity" in book["title"].lower() for book in results)

def test_search_books_in_catalog_by_author_partial():
    # Test2 searching books by author (partial, case-insensitive).
    add_book_to_catalog("The Hunger Games", "Suzanne Collins", "6000000000003", 4)
    
    results = search_books_in_catalog("colli", "author")
    
    assert isinstance(results, list)
    assert any("suzanne collins" in book["author"].lower() for book in results)

def test_search_books_in_catalog_by_isbn_exact():
    # Test3 searching books by ISBN (exact match only).
    add_book_to_catalog("The Book Thief", "Markus Zusak", "6000000000004", 1)
    
    results = search_books_in_catalog("6000000000004", "isbn")
    
    assert isinstance(results, list)
    assert any(book["isbn"] == "6000000000004" for book in results)

def test_search_books_in_catalog_no_results():
    # Test4 searching books with no results found.
    results = search_books_in_catalog("Nonexistent", "title")
    
    assert results == []

def test_search_books_in_catalog_invalid_type():
    # Test5 searching books with an invalid search type.
    results = search_books_in_catalog("Harry Potter", "invalid_type")
    
    assert results == []


def test_search_books_in_catalog_multiple_matches_author():
    # Test6 multiple books by same author
    add_book_to_catalog("Book A", "Same Author", "6000000000011", 1)
    add_book_to_catalog("Book B", "Same Author", "6000000000012", 1)
    results = search_books_in_catalog("same author", "author")
    assert len(results) >= 2
    authors = [b["author"].lower() for b in results]
    assert all(a == "same author" for a in authors)


def test_search_books_in_catalog_whitespace_search_term():
    # Test7 search term with leading/trailing whitespace
    add_book_to_catalog("Whitespace Test", "Author", "6000000000013", 1)
    results = search_books_in_catalog("  whitespace test  ", "title")
    assert any("whitespace test" in book["title"].lower() for book in results)

#-----------------------------------------------------------------------------------------------------------------------

# R7: Patron Status Report
# ASSUMPTIONS: get_patron_status_report returns a dict with keys:
# 'current_borrowed_books' (list), 'total_fees_owed' (float), 'num_current_borrowed_books' (int), 'borrowing_history' (list), 'status' (str for errors)

def test_get_patron_status_report_valid():
    # Test1: getting patron status with valid input.
    report = get_patron_status_report("123456")
    
    assert isinstance(report, dict)
    assert "current_borrowed_books" in report # checks that the key exists
    assert "total_fees_owed" in report # checks that the key exists
    assert "num_current_borrowed_books" in report # checks that the key exists
    assert "borrowing_history" in report # checks that the key exists
    assert "status" in report # checks that the key exists

def test_get_patron_status_report_invalid_patron_id():
    # Test2: getting patron status with a non-integer patron ID.
    report = get_patron_status_report("Patron ID")
    
    assert isinstance(report, dict)
    assert "Invalid patron ID. Must be exactly 6 digits." in report.get('status')

def test_get_patron_status_report_no_borrowed_books():
    # Test3: getting patron status for a patron with no borrowed books.
    report = get_patron_status_report("638054")
    
    assert isinstance(report, dict)
    assert len(report["current_borrowed_books"]) == 0
    assert report["num_current_borrowed_books"] == 0
    assert round(report["total_fees_owed"], 2) == 0.00
    assert len(report["borrowing_history"]) == 0

def test_get_patron_status_report_borrow_count():
    # Test4: borrow_count should equal the number of currently borrowed books.
    add_book_to_catalog("History Book", "History Author", "7000000000001", 2)
    add_book_to_catalog("Another History Book", "Another Author", "7000000000002", 1)
    book1 = get_book_by_isbn("7000000000001")
    book2 = get_book_by_isbn("7000000000002")
    borrow_book_by_patron("820643", book1["id"])
    borrow_book_by_patron("820643", book2["id"])

    report = get_patron_status_report("820643")
    
    assert isinstance(report, dict)
    assert len(report["current_borrowed_books"]) == report["num_current_borrowed_books"]

def test_get_patron_status_report_borrowing_history():
    # Test5: borrowing_history should include 2 books, current books should not have any books.
    add_book_to_catalog("I love books", "Book Lover", "7000000000003", 2)
    add_book_to_catalog("I hate books", "Book Hater", "7000000000004", 1)
    book1 = get_book_by_isbn("7000000000003")
    book2 = get_book_by_isbn("7000000000004")
    borrow_book_by_patron("823649", book1["id"])
    borrow_book_by_patron("823649", book2["id"])
    return_book_by_patron("823649", book1["id"])
    return_book_by_patron("823649", book2["id"])

    report = get_patron_status_report("823649")
    
    assert isinstance(report, dict)
    assert "current_borrowed_books" in report
    assert "borrowing_history" in report
    assert "status" in report
    assert "Successfully retrieved patron's status report." in report.get('status')

    assert len(report["current_borrowed_books"]) == 0
    assert len(report["borrowing_history"]) == 2
    for record in report["borrowing_history"]:
        assert all(rec in record for rec in ["book_id", "title", "author", "borrow_date", "due_date", "return_date"])
    assert round(report["total_fees_owed"], 2) == 0.00
    assert report["num_current_borrowed_books"] == 0

def test_get_patron_status_report_overdue_books():
    # Test6: patron has overdue books, total_fees_owed > 0
    add_book_to_catalog("Overdue Book", "Author", "7000000000005", 1)
    book = get_book_by_isbn("7000000000005")
    borrow_book_by_patron("700001", book["id"])
    # Manipulate borrow record to be overdue
    record = get_patron_borrowing_history("700001")[0]
    update_borrow_record_return_date("700001", book["id"], record["due_date"] + timedelta(days=5))
    calculate_late_fee_for_book("700001", book["id"])

    report = get_patron_status_report("700001")
    assert len(report["current_borrowed_books"]) == 0
    assert len(report["borrowing_history"]) == 1
    assert round(report["total_fees_owed"], 2) > 0
    assert report["num_current_borrowed_books"] == 0


def test_get_patron_status_report_multiple_current_books():
    # Test7: patron currently borrowing multiple books
    add_book_to_catalog("Book A", "Author A", "7000000000006", 1)
    add_book_to_catalog("Book B", "Author B", "7000000000007", 1)
    book1 = get_book_by_isbn("7000000000006")
    book2 = get_book_by_isbn("7000000000007")
    borrow_book_by_patron("700002", book1["id"])
    borrow_book_by_patron("700002", book2["id"])

    report = get_patron_status_report("700002")
    assert report["num_current_borrowed_books"] == 2
    assert len(report["current_borrowed_books"]) == 2