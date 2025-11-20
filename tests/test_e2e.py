import subprocess
import time
import pytest

import re
from playwright.sync_api import Page, expect

# start Flask app automatically before running tests (don’t need a separate terminal)
# pytest fixture that runs the Flask app as a subprocess and ensures it shuts down after the tests
@pytest.fixture(scope="session", autouse=True)
def start_flask_app():
    """Start the Flask app in a subprocess before tests and stop afterward."""
    # Run Flask in a subprocess
    proc = subprocess.Popen(
        ["python", "app.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    # wait a few seconds for Flask to start
    time.sleep(3) 
    yield  # run tests
    # terminate Flask after tests
    proc.terminate()
    proc.wait()

# Add a new book to the catalog (fill title, author, ISBN, copies)
def test_add_new_book_to_catalog_and_borrow(page: Page):
    # go to catalog page and click "Add New Book"
    page.goto("http://localhost:5000/catalog")
    page.click("a.btn:has-text('➕ Add New Book')")
    # wait for navigation to add book page
    page.wait_for_url(re.compile(r".*/add_book$"))
    # fill in the book details and submit the form
    page.fill("input[name='title']", "Wicked")
    page.fill("input[name='author']", "Gregory Maguire")
    page.fill("input[name='isbn']", "9785560286821")
    page.fill("input[name='total_copies']", "5")
    page.click("button[type='submit']")

    # expect to be redirected back to catalog page
    expect(page).to_have_url(re.compile(r"/catalog$"))
    # verify flash success message visible
    expect(page.locator('div.flash-success', has_text='Book "Wicked" has been successfully added to the catalog.')).to_be_visible()

    #expect the new book to be listed in the catalog
    row = page.locator("tr:has(td:has-text('Wicked'))")
    expect(row.locator("td:has-text('Wicked')")).to_be_visible()
    expect(row.locator("td:has-text('Gregory Maguire')")).to_be_visible()
    expect(row.locator("td:has-text('9785560286821')")).to_be_visible()
    expect(row.locator("td:has-text('5/5 Available')")).to_be_visible()

    # find the table row containing the book "Wicked"
    row = page.locator("tr:has-text('Wicked')")
    # fill patron ID inside that same row
    row.locator("input[name='patron_id']").fill("202876")
    # click the Borrow button (it's a <button>, not <a>)
    row.locator("button.btn-success:has-text('Borrow')").click()
    # verify flash success message visible
    expect(page.locator('div.flash-success', has_text='Successfully borrowed \"Wicked\"')).to_be_visible()
    # verify available copies are updated
    expect(page.locator("text=4/5 Available")).to_be_visible()


# Add a book, borrow the book, verify book in patron status report, then return it, check again
def test_borrow_book_check_status_return_book(page: Page):
    # add new book first
    page.goto("http://localhost:5000/catalog")
    page.click("a.btn:has-text('➕ Add New Book')")
    page.wait_for_url(re.compile(r".*/add_book$"))
    page.fill("input[name='title']", "Hunger Games")
    page.fill("input[name='author']", "Suzanne Collins")
    page.fill("input[name='isbn']", "9785560286333")
    page.fill("input[name='total_copies']", "4")
    page.click("button[type='submit']")
    expect(page).to_have_url(re.compile(r"/catalog$"))
    expect(page.locator('div.flash-success', has_text='Book "Hunger Games" has been successfully added to the catalog.')).to_be_visible()

    # borrow the book
    row = page.locator("tr:has-text('Hunger Games')")
    book_id = row.locator("td").nth(0).inner_text()
    row.locator("input[name='patron_id']").fill("559001")
    row.locator("button.btn-success:has-text('Borrow')").click()
    expect(page.locator('div.flash-success', has_text='Successfully borrowed \"Hunger Games\"')).to_be_visible()
    expect(page.locator("text=3/4 Available")).to_be_visible()

    # go to patron status report page
    page.goto("http://localhost:5000/reports")
    page.locator("input[name='patron_id']").fill("559001")
    page.click("button[type='submit']")
    expect(page).to_have_url(re.compile(r"/reports\?patron_id=559001$"))
    # verify that "Hunger Games" is listed in current borrowed books
    current_table = page.locator("h4:has-text('📚 Current Borrowed Books') + table tbody")
    borrowed_row = current_table.locator("tr:has-text('Hunger Games')")
    expect(borrowed_row.locator("td:has-text('Hunger Games')")).to_be_visible()
    expect(borrowed_row.locator("td:has-text('Suzanne Collins')")).to_be_visible()

    # return the book
    page.goto("http://localhost:5000/return")
    # fill patron ID inside that same row and click process button
    page.fill("input[name='patron_id']", "559001")
    page.fill("input[name='book_id']", book_id)
    page.locator("button[type='submit']").click()
    # verify flash success message visible
    expect(page.locator('div.flash-success', has_text='Book successfully returned.')).to_be_visible()

    # verify book availability back in catalog
    page.goto("http://localhost:5000/catalog")
    expect(page.locator("tr:has-text('Hunger Games') >> text=4/4 Available")).to_be_visible()