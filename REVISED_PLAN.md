# Updated Plan: Focused Data Import & Processing

This plan prioritizes creating a reliable data import pipeline first, then building the processing and analysis on top of that solid foundation.

---

### **Part 1: Robust Data Importation (Refined)**

We will target the specific sections of the PDF to make the import process more efficient and reliable based on the known structure of the reports.

1.  **Targeted Summary Extraction:**
    *   **File:** `data_extractor.py`
    *   **Method:** `_extract_summary_data`
    *   **Action:** Modify the method to **only scan the first 3 pages** of the PDF for compensation details. This improves accuracy and speed by focusing only on the relevant section.

2.  **Robust Table Extraction:**
    *   **File:** `data_extractor.py`
    *   **Method:** `_extract_table_data`
    *   **Action:** Refactor the method to:
        *   **Scan pages 4 onwards** for productivity data tables.
        *   Replace the current fragile regex-based text parsing with `pdfplumber`'s native `extract_tables()` function.
        *   Implement logic to identify the "ChargeTransaction" and "Ticket Tracking" tables by searching for their unique headers on the page where the tables are found.

3.  **Complete Data Capture:**
    *   **File:** `data_extractor.py`
    *   **Action:** Implement the logic to fully parse the "Ticket Tracking" table data, as it is currently skipped.

---

### **Part 2: Staged Data Processing (Unchanged)**

This part of the plan remains the same, as it provides a clean separation of concerns for a more maintainable system.

1.  **Data Loading Module (`data_loader.py`):** This script will be responsible for taking the extracted data (summary, charges, tickets) and populating the SQLite database.
2.  **Data Analysis Module (`data_analyzer.py`):** This script will connect to the populated database to perform the analyses outlined in the original project plan.
3.  **Orchestration Script (`process_reports.py`):** This will be the main script to run the entire pipeline, from identifying new files to extraction, loading, and archiving.

---

### **Updated Workflow Diagram**

This diagram illustrates the refined data flow.

```mermaid
graph TD
    A[Start: New PDF in /data] --> B{process_reports.py};
    B --> C[data_extractor.py: Extract Data<br/>- Pages 1-3: Summary<br/>- Pages 4+: Tables];
    C --> |Summary, Charges, Tickets| D[data_loader.py: Load to DB];
    D --> E[compensation.db];
    B --> F[Archive PDF];
    
    subgraph "Analysis (Separate Step)"
        G[data_analyzer.py] --> E;
        G --> H[Generate Reports/Visuals];
    end