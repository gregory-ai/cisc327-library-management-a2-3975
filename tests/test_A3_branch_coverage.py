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

# Branch Coverage Tests for add_book_to_catalog
def test_add_book_to_catalog_branch_coverage(mocker):
    # invalid title path
    assert add_book_to_catalog("", "A", "1234567890123", 1)[0] is False
    # too long title
    assert add_book_to_catalog("x"*201, "A", "1234567890123", 1)[0] is False
    # invalid author
    assert add_book_to_catalog("Book", "", "1234567890123", 1)[0] is False
    # long author
    assert add_book_to_catalog("Book", "x"*101, "1234567890123", 1)[0] is False
    # isbn wrong length
    assert add_book_to_catalog("Book", "A", "123", 1)[0] is False
    # copies <= 0
    assert add_book_to_catalog("Book", "A", "1234567890123", 0)[0] is False
    # duplicate ISBN branch
    mocker.patch("services.library_service.get_book_by_isbn",
                 return_value={"id": 10})
    assert add_book_to_catalog("Book", "A", "1234567890123", 2)[0] is False

    # success branch
    mocker.patch("services.library_service.get_book_by_isbn", return_value=None)
    mocker.patch("services.library_service.insert_book", return_value=True)
    assert add_book_to_catalog("Book", "A", "1234567890123", 2)[0] is True

    # failure branch
    mocker.patch("services.library_service.insert_book", return_value=False)
    assert add_book_to_catalog("Book", "A", "1234567890123", 2)[0] is False

# -------------------------------------------------------------
# Branch Coverage Tests for Catalog Routes (catalog_bp) 
def test_catalog_index_branch(client):
    # redirect branch
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 302

def test_catalog_route_branch(client, mocker):
    # data retrieval branch
    mocker.patch(
    "routes.catalog_routes.get_all_books",
    return_value=[{
        "title": "A",
        "author": "Auth",
        "isbn": "123",
        "total_copies": 5,
        "available_copies": 5
    }])
    r = client.get("/catalog")
    assert r.status_code == 200
    assert b"A" in r.data

def test_add_book_get_branch(client):
    # GET request branch
    r = client.get("/add_book")
    assert r.status_code == 200

def test_add_book_post_invalid_int_branch(client):
    # invalid total_copies branch
    r = client.post("/add_book", data={
        "title": "A",
        "author": "B",
        "isbn": "1234567890123",
        "total_copies": "BAD"
    })
    assert b"valid positive integer" in r.data

def test_add_book_post_fail_branch(client, mocker):
    # add_book_to_catalog failure branch
    mocker.patch("routes.catalog_routes.add_book_to_catalog",
                 return_value=(False, "ERR"))
    r = client.post("/add_book", data={
        "title": "A",
        "author": "B",
        "isbn": "1234567890123",
        "total_copies": "5"
    })
    assert b"ERR" in r.data

def test_add_book_post_success_branch(client, mocker):
    # success branch
    mocker.patch("routes.catalog_routes.add_book_to_catalog",
                 return_value=(True, "OK"))
    r = client.post("/add_book", data={
        "title": "A",
        "author": "B",
        "isbn": "1234567890123",
        "total_copies": "5"
    }, follow_redirects=False)
    assert r.status_code == 302

# -------------------------------------------------------------
# Branch Coverage Tests for borrow_book_by_patron
def test_borrow_book_by_patron_branch_coverage(mocker):
    # invalid patron ID
    assert borrow_book_by_patron("123", 1)[0] is False
    # book not found
    mocker.patch("services.library_service.get_book_by_id", return_value=None)
    assert borrow_book_by_patron("123456", 1)[0] is False
    # unavailable book
    mocker.patch("services.library_service.get_book_by_id",
                 return_value={"available_copies": 0})
    assert borrow_book_by_patron("123456", 1)[0] is False
    # borrow limit exceeded
    mocker.patch("services.library_service.get_book_by_id",
                 return_value={"available_copies": 1, "title": "B"})
    mocker.patch("services.library_service.get_patron_borrow_count",
                 return_value=5)
    assert borrow_book_by_patron("123456", 1)[0] is False
    # record insert fails
    mocker.patch("services.library_service.get_patron_borrow_count",
                 return_value=0)
    mocker.patch("services.library_service.insert_borrow_record",
                 return_value=False)
    assert borrow_book_by_patron("123456", 1)[0] is False
    # availability update fails
    mocker.patch("services.library_service.insert_borrow_record",
                 return_value=True)
    mocker.patch("services.library_service.update_book_availability",
                 return_value=False)
    assert borrow_book_by_patron("123456", 1)[0] is False
    # success
    mocker.patch("services.library_service.update_book_availability",
                 return_value=True)
    assert borrow_book_by_patron("123456", 1)[0] is True

# -------------------------------------------------------------
# Branch Coverage Tests for return_book_by_patron
def test_return_book_by_patron_branch_coverage(mocker):
    # invalid patron id
    assert return_book_by_patron("999", 1)[0] is False
    # book not found
    mocker.patch("services.library_service.get_book_by_id", return_value=None)
    assert return_book_by_patron("123456", 1)[0] is False
    # patron did not borrow this book
    mocker.patch("services.library_service.get_book_by_id", return_value={"id": 1})
    mocker.patch("services.library_service.get_patron_borrowed_books",
                 return_value=[])
    assert return_book_by_patron("123456", 1)[0] is False
    # update availability fails
    mocker.patch("services.library_service.get_patron_borrowed_books",
                 return_value=[{"book_id": 1}])
    mocker.patch("services.library_service.update_book_availability",
                 return_value=False)
    assert return_book_by_patron("123456", 1)[0] is False
    # return record insertion fails 
    mocker.patch("services.library_service.update_book_availability",
                 return_value=True)
    mocker.patch("services.library_service.update_borrow_record_return_date",
                 return_value=False)
    assert return_book_by_patron("123456", 1)[0] is False
    # late fee error branch
    mocker.patch("services.library_service.update_borrow_record_return_date",
                 return_value=True)
    mocker.patch("services.library_service.calculate_late_fee_for_book",
                 return_value={"status": "ERROR", "fee_amount": 0, "days_overdue": 0})
    assert return_book_by_patron("123456", 1)[0] is True
    # success branch
    mocker.patch("services.library_service.calculate_late_fee_for_book",
                 return_value={"status": "Book is not overdue.","fee_amount": 0, "days_overdue": 0})
    assert return_book_by_patron("123456", 1)[0] is True

# -------------------------------------------------------------
# Branch Coverage Tests for calculate_late_fee_for_book
def test_calculate_late_fee_for_book_branch_coverage(mocker):
    # invalid patron
    r = calculate_late_fee_for_book("x1", 1)
    assert r["status"].startswith("Invalid")
    # book not found
    mocker.patch("services.library_service.get_book_by_id", return_value=None)
    r = calculate_late_fee_for_book("123456", 1)
    assert r["status"] == "Book not found."
    # book not borrowed by patron
    mocker.patch("services.library_service.get_book_by_id", return_value={"id": 1})
    mocker.patch("services.library_service.get_patron_borrowing_history",
                 return_value=[])
    r = calculate_late_fee_for_book("123456", 1)
    assert r["status"] == "Book not borrowed by patron."
    # book not returned
    now = datetime.now()
    mocker.patch("services.library_service.get_patron_borrowing_history",
                 return_value=[{"book_id": 1, "return_date": None}])
    r = calculate_late_fee_for_book("123456", 1)
    assert r["status"] == "Book not returned."
    # not overdue
    mocker.patch("services.library_service.get_patron_borrowing_history",
                 return_value=[{"book_id": 1,
                                "return_date": now,
                                "due_date": now}])
    r = calculate_late_fee_for_book("123456", 1)
    assert r["status"] == "Book is not overdue."
    # fee <= 7 days
    mocker.patch("services.library_service.get_patron_borrowing_history",
                 return_value=[{"book_id": 1,
                                "return_date": now + timedelta(days=5),
                                "due_date": now}])
    r = calculate_late_fee_for_book("123456", 1)
    assert r["fee_amount"] == 2.5
    # fee > 7 days 
    mocker.patch("services.library_service.get_patron_borrowing_history",
                 return_value=[{"book_id": 1,
                                "return_date": now + timedelta(days=20),
                                "due_date": now}])
    r = calculate_late_fee_for_book("123456", 1)
    assert r["fee_amount"] == 15.0

# -------------------------------------------------------------
# Branch Coverage Tests for search_books_in_catalog
def test_search_books_in_catalog_branch_coverage(mocker):
    books = [
        {"title": "Alpha", "author": "John", "isbn": "111"},
        {"title": "Beta", "author": "Jane", "isbn": "222"}
    ]
    mocker.patch("services.library_service.get_all_books", return_value=books)
    # empty term 
    assert search_books_in_catalog("   ", "title") == []
    # title match
    assert len(search_books_in_catalog("alp", "title")) == 1
    # author match
    assert len(search_books_in_catalog("jan", "author")) == 1
    # isbn match
    assert len(search_books_in_catalog("111", "isbn")) == 1
    # invalid type 
    assert search_books_in_catalog("anything", "BAD") == []

# -------------------------------------------------------------
# Branch Coverage Tests for get_patron_status_report
def test_get_patron_status_report_branch_coverage(mocker):
    # invalid patron
    r = get_patron_status_report("12")
    assert r["status"].startswith("Invalid")
    # no borrowed books
    mocker.patch("services.library_service.get_patron_borrowed_books",
                 return_value=[])
    mocker.patch("services.library_service.get_patron_borrowing_history",
                 return_value=[])
    mocker.patch("services.library_service.calculate_late_fee_for_book",
                 return_value={"fee_amount": 0})
    r = get_patron_status_report("123456")
    assert r["num_current_borrowed_books"] == 0
    # borrowed books
    mocker.patch("services.library_service.get_patron_borrowed_books",
                 return_value=[{
                     "book_id": 1, "title": "A", "author": "B",
                     "due_date": datetime.now(), "is_overdue": False
                 }])
    # returned books
    mocker.patch("services.library_service.get_patron_borrowing_history",
                 return_value=[{
                     "book_id": 1, "title": "A", "author": "B",
                     "borrow_date": datetime.now(),
                     "due_date": datetime.now(),
                     "return_date": datetime.now()
                 }])
    # fees owed
    mocker.patch("services.library_service.calculate_late_fee_for_book",
                 return_value={"fee_amount": 1})
    # total fees owed branch
    r = get_patron_status_report("123456")
    assert r["total_fees_owed"] >= 1

# -------------------------------------------------------------
# Branch Coverage Tests for pay_late_fees
def test_pay_late_fees_branch_coverage(mocker):
    pg = Mock(spec=PaymentGateway)
    # invalid patron
    assert pay_late_fees("12", 1, pg)[0] is False
    # late fee calculation error
    mocker.patch("services.library_service.calculate_late_fee_for_book",
                 return_value=None)
    assert pay_late_fees("123456", 1, pg)[0] is False
    # no fee owed
    mocker.patch("services.library_service.calculate_late_fee_for_book",
                 return_value={"fee_amount": 0})
    assert pay_late_fees("123456", 1, pg)[0] is False
    # book not found
    mocker.patch("services.library_service.calculate_late_fee_for_book",
                 return_value={"fee_amount": 5})
    mocker.patch("services.library_service.get_book_by_id",
                 return_value=None)
    assert pay_late_fees("123456", 1, pg)[0] is False
    # success
    mocker.patch("services.library_service.get_book_by_id",
                 return_value={"title": "Book"})
    pg.process_payment.return_value = (True, "txn1", "OK")
    assert pay_late_fees("123456", 1, pg)[0] is True
    # payment fail
    pg.process_payment.return_value = (False, None, "Fail")
    assert pay_late_fees("123456", 1, pg)[0] is False
    # exception
    pg.process_payment.side_effect = Exception("X")
    assert pay_late_fees("123456", 1, pg)[0] is False

# -------------------------------------------------------------
# Branch Coverage Tests for refund_late_fee_payment
def test_refund_late_fee_payment_branch_coverage():
    pg = Mock(spec=PaymentGateway)
    # invalid transaction id
    assert refund_late_fee_payment("BAD", 5, pg)[0] is False
    # invalid amount <= 0
    assert refund_late_fee_payment("txn_1", 0, pg)[0] is False
    # amount exceeds cap
    assert refund_late_fee_payment("txn_1", 20, pg)[0] is False
    # success
    pg.refund_payment.return_value = (True, "OK")
    assert refund_late_fee_payment("txn_1", 5, pg)[0] is True
    # fail
    pg.refund_payment.return_value = (False, "ERR")
    assert refund_late_fee_payment("txn_1", 5, pg)[0] is False
    # exception
    pg.refund_payment.side_effect = Exception("ERR")
    assert refund_late_fee_payment("txn_1", 5, pg)[0] is False

# -------------------------------------------------------------
# Branch Coverage Tests for process_payment
def test_process_payment_branch_invalid_amount_zero():
    # amount <= 0 branch
    gateway = PaymentGateway()
    success, txn, msg = gateway.process_payment("123456", 0, "")
    assert success is False
    assert "Invalid amount" in msg

def test_process_payment_branch_invalid_amount_negative():
    # amount <= 0 branch
    gateway = PaymentGateway()
    success, txn, msg = gateway.process_payment("123456", -1, "")
    assert success is False
    assert "Invalid amount" in msg

def test_process_payment_branch_amount_exceeds_limit():
    # amount > 1000 branch
    gateway = PaymentGateway()
    success, txn, msg = gateway.process_payment("123456", 1500, "")
    assert not success
    assert "exceeds limit" in msg

def test_process_payment_branch_amount_valid_not_exceeds():
    # false path for amount > 1000 branch 
    gateway = PaymentGateway()
    success, txn, msg = gateway.process_payment("123456", 999.99, "")
    # valid patron ID 
    assert success
    assert txn.startswith("txn_")


def test_process_payment_branch_invalid_patron_id():
    # lenght of patron_id not equal 6 branch
    gateway = PaymentGateway()
    success, txn, msg = gateway.process_payment("12345", 50, "")
    assert not success
    assert "Invalid patron ID" in msg


def test_process_payment_branch_patron_id_valid():
    # false path for len(patron_id) != 6 branch
    gateway = PaymentGateway()
    success, txn, msg = gateway.process_payment("999999", 50, "")
    assert success
    assert txn.startswith("txn_")

# -------------------------------------------------------------
# Branch Coverage Tests for refund_payment
def test_refund_payment_branch_invalid_transaction_id_empty():
    # not transaction_id branch
    gateway = PaymentGateway()
    success, msg = gateway.refund_payment("", 5)
    assert not success
    assert "Invalid transaction ID" in msg

def test_refund_payment_branch_invalid_transaction_id_bad_prefix():
    # not transaction_id.startswith('txn_') branch
    gateway = PaymentGateway()
    success, msg = gateway.refund_payment("abc123", 5)
    assert not success
    assert "Invalid transaction ID" in msg

def test_refund_payment_branch_valid_transaction_id():
    # false path for invalid transaction IDs
    gateway = PaymentGateway()
    success, msg = gateway.refund_payment("txn_123456_01", 5)
    assert success
    assert "Refund of $" in msg


def test_refund_payment_branch_invalid_refund_amount_zero():
    # amount <= 0 branch
    gateway = PaymentGateway()
    success, msg = gateway.refund_payment("txn_1", 0)
    assert not success
    assert "Invalid refund amount" in msg

def test_refund_payment_branch_invalid_refund_amount_negative():
    # amount <= 0 branch
    gateway = PaymentGateway()
    success, msg = gateway.refund_payment("txn_1", -5)
    assert not success
    assert "Invalid refund amount" in msg

def test_refund_payment_branch_amount_valid():
    # false path
    gateway = PaymentGateway()
    success, msg = gateway.refund_payment("txn_123456", 10)
    assert success
    assert "Refund of $" in msg

# -------------------------------------------------------------
# Branch Coverage Tests for verify_payment_status
def test_verify_payment_status_branch_invalid_transaction():
    # not transaction_id or not transaction_id.startswith('txn_')
    gateway = PaymentGateway()
    result = gateway.verify_payment_status("bad_id")
    assert result["status"] == "not_found"
def test_verify_payment_status_branch_valid():
    # false path 
    gateway = PaymentGateway()
    result = gateway.verify_payment_status("txn_123456_01")
    assert result["status"] == "completed"
    assert result["transaction_id"] == "txn_123456_01"