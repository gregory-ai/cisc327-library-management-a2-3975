# Project Implementation Status

| **Function Name**               | **Implementation** | **What is Missing**           | 
|---------------------------------|--------------------|-------------------------------|
| **add_book_to_catalog**         | Complete           | Not Applicable                | 
| **catalog**                     | Complete           | Not Applicable                |
| **borrow_book_by_patron**       | Complete           |- Validation that the user is in the system| 
| **return_book_by_patron**       | Partial            |- Validation of patron ID (6-digit ID) <br>- Validation that book ID is in database <br>- Verification that book was borrow by the patron <br>- Update of the available copies of the borrowed book <br>- Update of the records return date <br>- Calculation of late fees <br>- Display of late fees | 
| **calculate_late_fee_for_book** | Parial             |- Validation of patron ID (6-digit ID) <br>- Validation that book ID is in database <br> - New API route /api/late_fee/<patron_id>/<book_id> that looks up a book’s due date for a patron <br> - Calculate the number of days the book has been borrowed <br>- Check if the book is overdue (borrowed for > 14 days) <br>- Calculate how many days the book is overdue (beyond 14 days) <br>- Based on the number of days overdue the book is, calculate the late fees <br>&nbsp;&nbsp;• ≤7 days: `days_overdue × $0.50` <br> &nbsp;&nbsp;• >7 days: `$3.50 + (days_overdue − 7)` <br> - Cap fee at $15 <br> - Return JSON response with `fee_amount`, `days_overdue`, and `status`| 
| **search_books_in_catalog**     | Partial            |- Input validations <br> - Determine what the type of search is (Ensure it is either title, author, isbn) <br> - If the type is title: <br> &nbsp;&nbsp;• check if the book exists in the database <br> &nbsp;&nbsp;• return results from the search (display books that match the search) <br> - If the type is author: <br> &nbsp;&nbsp;• check if the author exists in the database <br> &nbsp;&nbsp;• return results from the search (display books that match the search)<br> - If the type is isbn: <br> &nbsp;&nbsp;• check if the isbn exists in the database <br> &nbsp;&nbsp;• return results from the search (display books that match the search)| 
| **get_patron_status_report**    | Partial            |-Validation of patron ID (6-digit ID) <br>- Access the database <br>- Query the database and save the following value: currently borrowed books with due dates, total late fees owed, number of books currently borrowed, borrowing history <br>- Display the values for the user| 

# Summary of Test Scripts

**R1: Add Book to Catalog:**
Tests cover different input validation rules for adding books to the catalog.
- **Valid input** -> book is added successfully.  
- **Title too long** (>200 chars) -> rejected.  
- **Author too long** (>100 chars) -> rejected.  
- **ISBN too long** (>13 digits) -> rejected.  
- **Negative copies** -> rejected.  
- **Duplicate ISBN** -> rejected.  
- **Empty title** -> rejected.  
- **Empty author** -> rejected.  

---

**R2: Book Catalog Display:**
Tests verify catalog display using a temporary Flask app.
- **Valid input** -> shows newly added book in HTML.  
- **Book fields present** -> title, author, ISBN appear correctly.  
- **Borrowed book** -> available copies decrease in catalog.  
- **Duplicate ISBN** -> displayed only once.  

---

**R3: Book Borrowing Interface:**
Tests the borrowing rules for patrons.
- **Valid borrow** -> success with due date returned.  
- **Invalid patron ID** -> rejected.  
- **Invalid book ID** -> rejected.  
- **Unavailable book** -> rejected.  
- **Patron is exceeding 5 book limit** -> rejected.  

---

**R4: Book Return Processing:** 
Test covers different input validation rules and return rules for patrons. <br>
- **Valid return** -> should be successfully returns.  
- **Invalid patron ID** -> rejected.  
- **Invalid book ID** -> rejected.  
- **Book not borrowed** -> rejected.  

---

**R5: Late Fee Calculation API:** 
Tests late fee calculations for overdue books. <br>
- **Valid calculation** -> returns a fee and status.  
- **Invalid patron ID** -> rejected.  
- **Invalid book ID** -> rejected.  
- **Book not borrowed** -> rejected.  

---

**R6: Book Search Functionality:**
Tests searching catalog by title, author, and ISBN. <br>
- **Partial title search** -> matches multiple books (case-insensitive).  
- **Partial author search** -> matches correct author (case-insensitive).  
- **Exact ISBN search** -> returns correct book.  
- **No results** -> returns empty list.  
- **Invalid search type** -> returns empty list. 

---

**R7: Patron Status Report** <br>
Tests generating a status report for patrons. 
- **Valid patron** -> includes borrowed books, late fees, borrow count, history, and status.  
- **Invalid patron ID** -> rejected.  
- **No borrowed books** -> displays appropriately.  
- **borrow_count equals the number of books borrowed** -> borrow_count equals 2, size of books borrowed list equals 2.
