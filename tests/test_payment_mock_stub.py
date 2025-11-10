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

from database import get_book_by_isbn, update_borrow_record_return_date, get_patron_borrowing_history
# Stubbing technique: replaces dependency that returns fixed data 
# Mocking technique: simulates a collaborator whose interactions you want to verify 


# Unit tests for pay_late_fees(patron_id, book_id, payment_gateway)
#--------------- Stub technique ------------------------------------
def test_pay_late_fees_success_stub(mocker):
    # stub late fee calculation
    mocker.patch(
        "services.library_service.calculate_late_fee_for_book",
        return_value={"fee_amount": 5.00, "days_overdue": 2, "status": "Fee amount successfully calculated."}
    )
    mocker.patch(
        "services.library_service.get_book_by_id",
        return_value={"id": 10, "title": "Mock Book"}
    )
    # mock payment gateway collaborator
    mock_gateway = Mock()
    mock_gateway.process_payment.return_value = (True, "txn_123", "Paid successfully")
    # call function
    success, message, txn = pay_late_fees("123456", 10, mock_gateway)
    assert success is True
    assert "Paid successfully" in message
    # verify interaction with mock collaborator
    mock_gateway.process_payment.assert_called_once()

def test_pay_late_fees_declined_by_gateway_stub(mocker):
    # stub fee calculation
    mocker.patch(
        "services.library_service.calculate_late_fee_for_book",
        return_value={"fee_amount": 8.00, "days_overdue": 4, "status": "Fee amount successfully calculated."}
    )
    mocker.patch("services.library_service.get_book_by_id",
                 return_value={"id": 20, "title": "Decline Book"})
    # mock gateway decline
    mock_gateway = Mock()
    mock_gateway.process_payment.return_value = (False, "", "Payment declined")
    success, message, txn = pay_late_fees("222222", 20, mock_gateway)
    assert success is False
    assert "declined" in message.lower()
    mock_gateway.process_payment.assert_called_once()

def test_pay_late_fees_invalid_patron_id_stub(mocker):
    # verify mock NOT called
    # stub but should not be used
    stub_fee = mocker.patch(
        "services.library_service.calculate_late_fee_for_book",
        return_value={"fee_amount": 5, "days_overdue": 1, "status": "Fee amount successfully calculated."}
    )
    mock_gateway = Mock()
    success, message, txn = pay_late_fees("abc123", 10, mock_gateway)
    assert success is False
    assert "Invalid patron ID" in message
    # verify no interactions
    stub_fee.assert_not_called()
    mock_gateway.process_payment.assert_not_called()

def test_pay_late_fees_zero_late_fees_stub(mocker):
    # verify mock NOT called
    mocker.patch(
        "services.library_service.calculate_late_fee_for_book",
        return_value={"fee_amount": 0, "days_overdue": 0, "status": "Book is not overdue."}
    )
    mocker.patch("services.library_service.get_book_by_id",
                 return_value={"id": 30, "title": "Zero Fee Book"})
    mock_gateway = Mock()
    success, message, txn = pay_late_fees("333333", 30, mock_gateway)
    assert success is False
    assert "no late fees" in message.lower()
    # verify no payment attempted
    mock_gateway.process_payment.assert_not_called()

def test_pay_late_fees_network_error_stub(mocker):
    # normal fee
    mocker.patch(
        "services.library_service.calculate_late_fee_for_book",
        return_value={"fee_amount": 4.25, "days_overdue": 3, "status": "Fee amount successfully calculated."}
    )
    mocker.patch("services.library_service.get_book_by_id",
                 return_value={"id": 40, "title": "Network Book"})
    mock_gateway = Mock()
    mock_gateway.process_payment.side_effect = Exception("Network down")
    success, message, txn = pay_late_fees("444444", 40, mock_gateway)
    assert success is False
    assert "network down" in message.lower()
    mock_gateway.process_payment.assert_called_once()

#--------------- Mocking technique ------------------------------------
def test_pay_late_fees_success_mock(mocker):
    # stub fee calculation (only return value needed)
    mocker.patch(
        "services.library_service.calculate_late_fee_for_book",
        return_value={"fee_amount": 7.50, "days_overdue": 5, "status": "Fee OK"}
    )
    mocker.patch(
        "services.library_service.get_book_by_id",
        return_value={"id": 10, "title": "Mock Book Title"}
    )
    # mock payment gateway with strict method spec
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.process_payment.return_value = (True, "txn_111", "Success")
    success, message, txn = pay_late_fees("123456", 10, mock_gateway)
    assert success is True
    assert "Success" in message
    mock_gateway.process_payment.assert_called_once()


def test_pay_late_fees_declined_mock(mocker):
    mocker.patch(
        "services.library_service.calculate_late_fee_for_book",
        return_value={"fee_amount": 4.00, "days_overdue": 2, "status": "Fee OK"}
    )
    mocker.patch(
        "services.library_service.get_book_by_id",
        return_value={"id": 20, "title": "Declined Book"}
    )
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.process_payment.return_value = (False, "", "Declined by bank")
    success, message, txn = pay_late_fees("222222", 20, mock_gateway)
    assert success is False
    assert "declined" in message.lower()
    mock_gateway.process_payment.assert_called_once()


def test_pay_late_fees_invalid_patron_id_mock(mocker):
    mocker.patch(
        "services.library_service.calculate_late_fee_for_book",
        return_value={"fee_amount": 3.00, "days_overdue": 1, "status": "Fee OK"}
    )
    mock_gateway = Mock(spec=PaymentGateway)
    success, message, txn = pay_late_fees("1234", 99, mock_gateway)
    assert success is False
    assert "Invalid patron ID" in message
    mock_gateway.process_payment.assert_not_called()

def test_pay_late_fees_zero_fee_mock(mocker):
    mocker.patch(
        "services.library_service.calculate_late_fee_for_book",
        return_value={"fee_amount": 0, "days_overdue": 0, "status": "Not overdue"}
    )
    mocker.patch(
        "services.library_service.get_book_by_id",
        return_value={"id": 30, "title": "No Fee Book"}
    )
    mock_gateway = Mock(spec=PaymentGateway)
    success, message, txn = pay_late_fees("999999", 30, mock_gateway)
    assert success is False
    assert "no late fees" in message.lower()
    mock_gateway.process_payment.assert_not_called()

def test_pay_late_fees_gateway_exception_mock(mocker):
    mocker.patch(
        "services.library_service.calculate_late_fee_for_book",
        return_value={"fee_amount": 5.00, "days_overdue": 3, "status": "Fee OK"}
    )
    mocker.patch(
        "services.library_service.get_book_by_id",
        return_value={"id": 77, "title": "Network Book"}
    )
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.process_payment.side_effect = Exception("Network error")
    success, message, txn = pay_late_fees("777777", 77, mock_gateway)
    assert success is False
    assert "network error" in message.lower()

    mock_gateway.process_payment.assert_called_once()

#-----------------------------------------------------------------------------------------------------------------------

# Unit tests for refund_late_fee_payment(transaction_id, amount, payment_gateway)

#--------------- Stub technique ------------------------------------
def test_refund_late_fee_payment_success_stub(mocker):
    mock_gateway = Mock()
    mock_gateway.refund_payment.return_value = (True, "Refund processed")
    success, message = refund_late_fee_payment("txn_123456_111", 5.00, mock_gateway)
    assert success is True
    assert "processed" in message.lower()
    mock_gateway.refund_payment.assert_called_once_with("txn_123456_111", 5.00)

def test_refund_late_fee_payment_invalid_transaction_id_stub(mocker):
    mock_gateway = Mock()
    success, message = refund_late_fee_payment("bad_id", 5.00, mock_gateway)
    assert success is False
    assert "invalid transaction id" in message.lower()
    mock_gateway.refund_payment.assert_not_called()

def test_refund_late_fee_payment_invalid_refund_amounts_stub(mocker):
    mock_gateway = Mock()
    # negative amount
    success1, msg1 = refund_late_fee_payment("txn_123456_222", -5, mock_gateway)
    assert success1 is False
    assert "refund amount must be greater than 0" in msg1.lower()
    # zero amount
    success2, msg2 = refund_late_fee_payment("txn_123456_222", 0, mock_gateway)
    assert success2 is False
    assert "refund amount must be greater than 0" in msg2.lower()
    # exceeds $15 cap (based on your late fee max)
    success3, msg3 = refund_late_fee_payment("txn_123456_222", 20, mock_gateway)
    assert success3 is False
    assert "exceeds" in msg3.lower()
    mock_gateway.refund_payment.assert_not_called()

#--------------- Mocking technique ------------------------------------

def test_refund_late_fee_payment_success_mock():
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.refund_payment.return_value = (True, "Refund complete")
    success, message = refund_late_fee_payment("txn_123456_01", 5.00, mock_gateway)
    assert success is True
    assert "refund complete" in message.lower()
    mock_gateway.refund_payment.assert_called_once_with("txn_123456_01", 5.00)


def test_refund_late_fee_payment_invalid_transaction_id_mock():
    mock_gateway = Mock(spec=PaymentGateway)
    success, message = refund_late_fee_payment("bad_id", 5.00, mock_gateway)
    assert success is False
    assert "invalid transaction" in message.lower()
    mock_gateway.refund_payment.assert_not_called()


def test_refund_late_fee_payment_negative_amount_mock():
    mock_gateway = Mock(spec=PaymentGateway)
    success, message = refund_late_fee_payment("txn_44444_22", -5.0, mock_gateway)
    assert success is False
    assert "refund amount must be greater than 0" in message.lower()
    mock_gateway.refund_payment.assert_not_called()


def test_refund_late_fee_payment_zero_amount_mock():
    mock_gateway = Mock(spec=PaymentGateway)
    success, message = refund_late_fee_payment("txn_99999_33", 0, mock_gateway)
    assert success is False
    assert "refund amount must be greater than 0" in message.lower()
    mock_gateway.refund_payment.assert_not_called()


def test_refund_late_fee_payment_exceeds_max_fee_cap_mock():
    mock_gateway = Mock(spec=PaymentGateway)
    success, message = refund_late_fee_payment("txn_123000_01", 20.00, mock_gateway)
    assert success is False
    assert "exceeds" in message.lower()
    mock_gateway.refund_payment.assert_not_called()