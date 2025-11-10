import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from services.library_service import (
    add_book_to_catalog, 
    borrow_book_by_patron,
    return_book_by_patron,
    calculate_late_fee_for_book,
    search_books_in_catalog,
    get_patron_status_report,
    pay_late_fees, 
    refund_late_fee_payment
)
from services.payment_services import PaymentGateway
# -------------------------------------------------------------
# Statement Coverage Tests for add_book_to_catalog

def test_add_book_to_catalog_all_paths(mocker):
    # invalid title
    assert add_book_to_catalog("", "A", "1234567890123", 1)[0] is False
    # long title
    assert add_book_to_catalog("x"*201, "A", "1234567890123", 1)[0] is False
    # invalid author
    assert add_book_to_catalog("Book", "", "1234567890123", 1)[0] is False
    # long author
    assert add_book_to_catalog("Book", "x"*101, "1234567890123", 1)[0] is False
    # invalid isbn
    assert add_book_to_catalog("Book", "A", "123", 1)[0] is False
    # invalid copies
    assert add_book_to_catalog("Book", "A", "1234567890123", 0)[0] is False
    # duplicate ISBN
    mocker.patch("services.library_service.get_book_by_isbn", return_value={"id": 1})
    assert add_book_to_catalog("Book", "A", "1234567890123", 1)[0] is False
    
    # successful insert
    mocker.patch("services.library_service.get_book_by_isbn", return_value=None)
    mocker.patch("services.library_service.insert_book", return_value=True)
    assert add_book_to_catalog("Book", "A", "1234567890123", 1)[0] is True

    # failed insert
    mocker.patch("services.library_service.insert_book", return_value=False)
    assert add_book_to_catalog("Book", "A", "1234567890123", 1)[0] is False

# -------------------------------------------------------------
# Statement Coverage Tests for Catalog Routes (catalog_bp) 

def test_catalog_index_redirects_to_catalog(client):
    # covers redirect statement in index()
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert "/catalog" in response.headers["Location"]

def test_catalog_route_renders_books(client, mocker):
    # covers get_all_books(), render_template() path
    mocker.patch(
    "routes.catalog_routes.get_all_books",
    return_value=[{
        "title": "Book A",
        "author": "Author A",
        "isbn": "123",
        "total_copies": 5,
        "available_copies": 5
    }]
)
    response = client.get("/catalog")
    assert response.status_code == 200
    assert b"Book A" in response.data

def test_add_book_get_request_renders_form(client):
    # covers request.method == 'GET' path
    response = client.get("/add_book")
    assert response.status_code == 200
    assert b"<form" in response.data  

def test_add_book_post_invalid_total_copies_conversion(client):
    # covers error: invalid total_copies type
    response = client.post("/add_book", data={
        "title": "T",
        "author": "A",
        "isbn": "1234567890123",
        "total_copies": "abc"
    })
    assert response.status_code == 200
    assert b"Total copies must be a valid positive integer" in response.data

def test_add_book_post_business_logic_failure(client, mocker):
    # covers validation failure paths in add_book_to_catalog
    mocker.patch(
        "routes.catalog_routes.add_book_to_catalog",
        return_value=(False, "Some error occurred")
    )
    response = client.post("/add_book", data={
        "title": "Bad Book",
        "author": "A",
        "isbn": "1234567890123",
        "total_copies": "3"
    })
    assert response.status_code == 200
    assert b"Some error occurred" in response.data

def test_add_book_post_success_redirects(client, mocker):
    #covers success branch of add_book  
    mocker.patch(
        "routes.catalog_routes.add_book_to_catalog",
        return_value=(True, "Book added successfully!")
    )
    response = client.post("/add_book", data={
        "title": "Good Book",
        "author": "A",
        "isbn": "1234567890123",
        "total_copies": "5"
    }, follow_redirects=False)
    assert response.status_code == 302
    assert "/catalog" in response.headers["Location"]

# -------------------------------------------------------------
# Statement Coverage Tests for borrow_book_by_patron

def test_borrow_book_by_patron_all_paths(mocker):
    # invalid patron id
    assert borrow_book_by_patron("12", 1)[0] is False
    # book does not exist
    mocker.patch("services.library_service.get_book_by_id", return_value=None)
    assert borrow_book_by_patron("123456", 1)[0] is False
    # unavailable book
    mocker.patch("services.library_service.get_book_by_id",
                 return_value={"available_copies": 0})
    assert borrow_book_by_patron("123456", 1)[0] is False
    # borrow count >= 5
    mocker.patch("services.library_service.get_book_by_id",
                 return_value={"available_copies": 1, "title": "B"})
    mocker.patch("services.library_service.get_patron_borrow_count", return_value=5)
    assert borrow_book_by_patron("123456", 1)[0] is False
    # failed insert
    mocker.patch("services.library_service.get_patron_borrow_count", return_value=0)
    mocker.patch("services.library_service.insert_borrow_record", return_value=False)
    assert borrow_book_by_patron("123456", 1)[0] is False
    # availability update fails
    mocker.patch("services.library_service.insert_borrow_record", return_value=True)
    mocker.patch("services.library_service.update_book_availability", return_value=False)
    assert borrow_book_by_patron("123456", 1)[0] is False
    # success
    mocker.patch("services.library_service.update_book_availability", return_value=True)
    assert borrow_book_by_patron("123456", 1)[0] is True

# -------------------------------------------------------------
# Statement Coverage Tests for return_book_by_patron

def test_return_book_by_patron_all_paths(mocker):
    # invalid patron id
    assert return_book_by_patron("12", 1)[0] is False
    # book not found
    mocker.patch("services.library_service.get_book_by_id", return_value=None)
    assert return_book_by_patron("123456", 1)[0] is False
    # not borrowed
    mocker.patch("services.library_service.get_book_by_id", return_value={"id": 1})
    mocker.patch("services.library_service.get_patron_borrowed_books", return_value=[])
    assert return_book_by_patron("123456", 1)[0] is False

    # availability update fails
    mocker.patch("services.library_service.get_patron_borrowed_books",
                 return_value=[{"book_id": 1}])
    mocker.patch("services.library_service.update_book_availability", return_value=False)
    assert return_book_by_patron("123456", 1)[0] is False

    # return record update fails 
    mocker.patch("services.library_service.update_book_availability", return_value=True)
    mocker.patch("services.library_service.update_borrow_record_return_date", return_value=False)
    mocker.patch("services.library_service.update_book_availability", return_value=True)
    assert return_book_by_patron("123456", 1)[0] is False

    # late fee errors 
    mocker.patch("services.library_service.update_borrow_record_return_date", return_value=True)
    mocker.patch("services.library_service.calculate_late_fee_for_book",
                 return_value={"status": "Some Error"})
    assert return_book_by_patron("123456", 1)[0] is True

    # success
    mocker.patch("services.library_service.calculate_late_fee_for_book",
                 return_value={"status": "Book is not overdue.", "fee_amount": 0, "days_overdue": 0})
    
    assert return_book_by_patron("123456", 1)[0] is True

# -------------------------------------------------------------
# Statement Coverage Tests for calculate_late_fee_for_book
def test_calculate_late_fee_for_book_all_paths(mocker):
    # invalid patron id
    result = calculate_late_fee_for_book("12", 1)
    assert result["status"].startswith("Invalid")
    # book not found
    mocker.patch("services.library_service.get_book_by_id", return_value=None)
    result = calculate_late_fee_for_book("123456", 1)
    assert result["status"] == "Book not found."
    # record not found
    mocker.patch("services.library_service.get_book_by_id", return_value={"id": 1})
    mocker.patch("services.library_service.get_patron_borrowing_history", return_value=[])
    result = calculate_late_fee_for_book("123456", 1)
    assert result["status"] == "Book not borrowed by patron."
    # not returned
    mocker.patch("services.library_service.get_patron_borrowing_history",
                 return_value=[{"book_id": 1, "return_date": None}])
    result = calculate_late_fee_for_book("123456", 1)
    assert result["status"] == "Book not returned."
    # not overdue
    now = datetime.now()
    mocker.patch("services.library_service.get_patron_borrowing_history",
                 return_value=[{"book_id": 1, "return_date": now, "due_date": now}])
    result = calculate_late_fee_for_book("123456", 1)
    assert result["status"] == "Book is not overdue."
    # <= 7 days overdue
    mocker.patch("services.library_service.get_patron_borrowing_history",
                 return_value=[{"book_id": 1,
                                "return_date": now + timedelta(days=5),
                                "due_date": now}])
    result = calculate_late_fee_for_book("123456", 1)
    assert round(result["fee_amount"], 2) == 2.5
    # > 7 days overdue (cap)
    mocker.patch("services.library_service.get_patron_borrowing_history",
                 return_value=[{"book_id": 1,
                                "return_date": now + timedelta(days=20),
                                "due_date": now}])
    result = calculate_late_fee_for_book("123456", 1)
    assert round(result["fee_amount"], 2) == 15.00

# -------------------------------------------------------------
# Statement Coverage Tests for search_books_in_catalog
def test_search_books_in_catalog_all_paths(mocker):
    mocker.patch("services.library_service.get_all_books",
                 return_value=[
                     {"title": "Alpha", "author": "John", "isbn": "111"},
                     {"title": "Beta", "author": "Jane", "isbn": "222"}
                 ])
    assert search_books_in_catalog("   ", "title") == [] 
    assert len(search_books_in_catalog("alp", "title")) == 1
    assert len(search_books_in_catalog("jan", "author")) == 1 
    assert len(search_books_in_catalog("111", "isbn")) == 1
    assert search_books_in_catalog("alp", "bad") == []

# -------------------------------------------------------------
# Statement Coverage Tests for get_patron_status_report
def test_get_patron_status_report_all_paths(mocker):
    # invalid patron id
    r = get_patron_status_report("12")
    assert r["status"].startswith("Invalid")
    # no borrowed books, no history
    mocker.patch("services.library_service.get_patron_borrowed_books", return_value=[])
    mocker.patch("services.library_service.get_patron_borrowing_history", return_value=[])
    mocker.patch("services.library_service.calculate_late_fee_for_book",
                 return_value={"fee_amount": 0})

    r = get_patron_status_report("123456")
    assert r["num_current_borrowed_books"] == 0
    # with borrowed & history (including returned books)
    mocker.patch("services.library_service.get_patron_borrowed_books",
                 return_value=[{
                     "book_id": 1, "title": "A", "author": "B",
                     "due_date": datetime.now(), "is_overdue": False
                 }])
    mocker.patch("services.library_service.get_patron_borrowing_history",
                 return_value=[{
                     "book_id": 1, "title": "A", "author": "B",
                     "borrow_date": datetime.now(),
                     "due_date": datetime.now(),
                     "return_date": datetime.now()
                 }])
    mocker.patch("services.library_service.calculate_late_fee_for_book",
                 return_value={"fee_amount": 1.0})
    r = get_patron_status_report("123456")
    assert r["total_fees_owed"] >= 0

# -------------------------------------------------------------
# Statement Coverage Tests for pay_late_fees
def test_pay_late_fees_all_paths(mocker):
    # invalid patron ID
    assert pay_late_fees("12", 1, Mock(spec=PaymentGateway))[0] is False
    # unable to calculate fee
    mocker.patch("services.library_service.calculate_late_fee_for_book", return_value=None)
    assert pay_late_fees("123456", 1, Mock(spec=PaymentGateway))[0] is False
    # zero fee
    mocker.patch("services.library_service.calculate_late_fee_for_book",
                 return_value={"fee_amount": 0})
    assert pay_late_fees("123456", 1, Mock(spec=PaymentGateway))[0] is False
    # book not found
    mocker.patch("services.library_service.calculate_late_fee_for_book",
                 return_value={"fee_amount": 5})
    mocker.patch("services.library_service.get_book_by_id", return_value=None)
    assert pay_late_fees("123456", 1, Mock(spec=PaymentGateway))[0] is False
    # payment success
    mocker.patch("services.library_service.get_book_by_id",
                 return_value={"title": "Book"})
    pg = Mock(spec=PaymentGateway)
    pg.process_payment.return_value = (True, "txn1", "OK")
    assert pay_late_fees("123456", 1, pg)[0] is True
    # payment fail
    pg.process_payment.return_value = (False, None, "Nope")
    assert pay_late_fees("123456", 1, pg)[0] is False
    # exception path
    pg.process_payment.side_effect = Exception("Err")
    assert pay_late_fees("123456", 1, pg)[0] is False

# -------------------------------------------------------------
# Statement Coverage Tests for refund_late_fee_payment
def test_refund_late_fee_payment_all_paths():
    pg = Mock(spec=PaymentGateway)
    # invalid ID
    assert refund_late_fee_payment("bad", 5, pg)[0] is False
    # invalid amount 
    assert refund_late_fee_payment("txn_1", 0, pg)[0] is False
    # exceeds max
    assert refund_late_fee_payment("txn_1", 20, pg)[0] is False
    # success
    pg.refund_payment.return_value = (True, "OK")
    assert refund_late_fee_payment("txn_1", 5, pg)[0] is True
    # fail
    pg.refund_payment.return_value = (False, "Bad")
    assert refund_late_fee_payment("txn_1", 5, pg)[0] is False
    # exception
    pg.refund_payment.side_effect = Exception("Oops")
    assert refund_late_fee_payment("txn_1", 5, pg)[0] is False

def test_process_payment_invalid_amount_zero():
    gateway = PaymentGateway()
    success, txn, msg = gateway.process_payment("123456", 0, "test")
    assert success is False
    assert "Invalid amount" in msg

def test_process_payment_invalid_amount_negative():
    gateway = PaymentGateway()
    success, txn, msg = gateway.process_payment("123456", -10, "test")
    assert success is False
    assert "Invalid amount" in msg

def test_process_payment_amount_exceeds_limit():
    gateway = PaymentGateway()
    success, txn, msg = gateway.process_payment("123456", 2000, "test")
    assert success is False
    assert "exceeds limit" in msg

def test_process_payment_invalid_patron_id_format():
    gateway = PaymentGateway()
    success, txn, msg = gateway.process_payment("12345", 10, "test")
    assert success is False
    assert "Invalid patron ID" in msg

def test_process_payment_success():
    gateway = PaymentGateway()
    success, txn, msg = gateway.process_payment("123456", 25.5, "test")
    assert success is True
    assert txn.startswith("txn_")
    assert "processed successfully" in msg.lower()

# -------------------------------------------------------------
# Statement Coverage Tests for refund_payment

def test_refund_payment_invalid_transaction_id_empty():
    gateway = PaymentGateway()
    success, msg = gateway.refund_payment("", 5)
    assert success is False
    assert "Invalid transaction ID" in msg

def test_refund_payment_invalid_transaction_id_bad_format():
    gateway = PaymentGateway()
    success, msg = gateway.refund_payment("abc123", 5)
    assert success is False
    assert "Invalid transaction ID" in msg

def test_refund_payment_invalid_refund_amount_zero():
    gateway = PaymentGateway()
    success, msg = gateway.refund_payment("txn_123456_1", 0)
    assert success is False
    assert "Invalid refund amount" in msg

def test_refund_payment_invalid_refund_amount_negative():
    gateway = PaymentGateway()
    success, msg = gateway.refund_payment("txn_123456_1", -5)
    assert success is False
    assert "Invalid refund amount" in msg

def test_refund_payment_success():
    gateway = PaymentGateway()
    success, msg = gateway.refund_payment("txn_123456_1", 10.0)
    assert success is True
    assert "processed successfully" in msg

# -------------------------------------------------------------
# Statement Coverage Tests for verify_payment_status
def test_verify_payment_status_invalid_id():
    gateway = PaymentGateway()
    result = gateway.verify_payment_status("bad_id")
    assert result["status"] == "not_found"

def test_verify_payment_status_success():
    gateway = PaymentGateway()
    result = gateway.verify_payment_status("txn_123456_1")
    assert result["status"] == "completed"
    assert result["transaction_id"] == "txn_123456_1"