# Master Ticket Index Implementation Plan

This document outlines the two-phase plan to create a "master ticket index" that consolidates multiple transaction records into single, logical cases.

## Phase 1: Add Patient Name to the Data Pipeline

This phase focuses on updating the system to extract, store, and display the patient's name, which is a prerequisite for the case-grouping logic.

1.  **Database Schema Update**:
    *   Add a `patient_name` column of type `String` to the `ChargeTransaction` table in `database_models.py`.

2.  **PDF Extraction Logic**:
    *   Modify the `_parse_charge_transaction_line` method in `data_extractor.py`.
    *   The logic will identify the patient's name as the text between the ticket number (and optional 'Note' character) and the site code (e.g., "UF An").

3.  **Data Loading**:
    *   Update the `_insert_charge_transactions` method in `data_loader.py` to map the newly extracted `patient_name` to the corresponding database column.

4.  **User Interface**:
    *   Add a "Patient Name" column to the main table in `templates/tickets.html` so the new data is visible.

## Phase 2: Create the Master Case Index

With the patient's name available, this phase implements the logic to group individual transactions into a single "Master Case."

1.  **New Database Structure**:
    *   A new `MasterCase` table will be introduced to store consolidated case information.
    *   The `ChargeTransaction` table will be linked to this new table with a `master_case_id`.

    ```mermaid
    graph TD
        subgraph "New Schema"
            MasterCase -->|has many| ChargeTransaction
        end

        MasterCase[MasterCase Table<br/>- id (PK)<br/>- case_key (Unique)<br/>- patient_name<br/>- date_of_service<br/>- earliest_start_time<br/>- latest_stop_time<br/>- primary_ticket_ref]

        ChargeTransaction[ChargeTransaction Table<br/>- id (PK)<br/>- ... (existing columns) ...<br/>- <b>patient_name (New)</b><br/>- <b>master_case_id (FK to MasterCase)</b>]

        style MasterCase fill:#d4edda,stroke:#155724
    ```

2.  **Case Grouping Logic**:
    *   A new process will be created to populate the `MasterCase` table after the raw data has been imported.
    *   **Step A (Group by Ticket Number)**: First, all transactions with the same `phys_ticket_ref` will be grouped together. This handles simple cases and breaks in service.
    *   **Step B (Merge Corrected Tickets)**: After the initial grouping, the system will merge different ticket groups that represent the same case. The merge criteria are:
        *   Exact same `patient_name`.
        *   Same `date_of_service`.
        *   Service time ranges that either overlap or start within a small, configurable window (e.g., 15 minutes) of each other.

3.  **New User Interface for Master Cases**:
    *   A new page will be created at `/cases` to display the master index.
    *   This page will list each unique `MasterCase`, showing consolidated information.
    *   Clicking on a master case will show all its individual `ChargeTransaction` records.