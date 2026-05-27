# Automated Employee Data Analysis in the F&B Industry

## Overview
This project is a complete ETL (Extract, Transform, Load) pipeline that automates the extraction of daily sales data from the iPOS (Fabi) system. It transforms raw, nested transaction logs into structured data and loads it directly into Google Sheets to power real-time Data Studio dashboards.

Impact: It eliminates 5+ hours of manual data entry/week, ensures 100% data integrity for financial reconciliation, and provides instant business visibility.

## Tools
- Python
- Data Studio
- Google Sheets

## Features
- Revenue tracking
- Peak hour analysis
- Employee performance
- Sales trends
- 

## Dashboard Preview
New
# Automated Employee Data Analysis Pipeline in the F&B Industry

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Google Sheets API](https://img.shields.io/badge/Google%20Sheets%20API-v4-green.svg)](https://developers.google.com/sheets/api)
[![Looker Studio](https://img.shields.io/badge/Looker%20Studio-Visualization-orange.svg)](https://lookerstudio.google.com/)
[![Windows Task Scheduler](https://img.shields.io/badge/Automation-Task%20Scheduler-lightgrey.svg)](https://learn.microsoft.com/en-us/windows/win32/taskschd/task-scheduler-start-page)

An end-to-end automated ETL (Extract, Transform, Load) pipeline designed to optimize workforce efficiency and operational visibility in the Food & Beverage (F&B) industry. This project automates the extraction of daily sales logs, transaction histories, and cooking durations from the **iPOS (Fabi)** system, transforms nested raw structures into clean analytical datasets, and pushes them to Google Sheets to power real-time **Looker Studio (Data Studio)** business intelligence dashboards.

---

## 🚀 Key Business Impact
* **Labor Cost Optimization:** Identifies workforce peak-hour workloads and tracking active employee sales performance.
* **Operational Bottleneck Discovery:** Tracks kitchen cooking time detail to minimize customer wait times.
* **Audit & Fraud Prevention:** Monitors order change logs (voided items, quantity adjustments) linked to specific staff accounts.

---

## 🏗️ System Architecture
[ iPOS (Fabi) System ]

▼ (Extract)
┌────────────────────────────────────────────────────────┐
│ Python Crawl Scripts (Triggered daily via taskschd.msc)│
└────────────────────────────────────────────────────────┘

▼ (Raw CSV Storage)
┌────────────────────────────────────────────────────────┐
│ Data Transformation Engine (Employee_Report.py)        │
│ ── Transformed nested JSON/Strings & Multi-tables      │
│ ── Aggregated KPI matrices (Working durations, Sales)  │
└────────────────────────────────────────────────────────┘

▼ (Load via Google Sheets API)
[ Google Sheets Database ]

▼ (Live Connection)
[ Looker Studio BI Dashboard ] ──► End-user Report (Managers/Owners)

---

## 📂 Repository Structure

* `.github/` - Github actions and workflow configurations.
* `crawl_sale_by_date.py` - Script responsible for daily sales extraction filterable by operational date.
* `crawl_sale_change_log.py` - Extracts audit trails and transactional modifications.
* `crawl_sale_detail.py` - Fetches granular item-level breakdowns for each receipt.
* `crawl_time.py` - Tracks kitchen operational metrics and item preparation times.
* `Employee_Report.py` - The core **Transformation & Loading Engine** that cleans records and synchronizes with Google Sheets.
* `README.md` - Project documentation.

---

## 🛠️ Data Pipeline & ETL Technical Details

### 1. Extract
* Automated requests target the iPOS endpoint using custom Python scrapers.
* Scheduled to run autonomously every midnight using Windows Task Scheduler (`taskschd.msc`) to capture the previous day's complete dataset without manual intervention.

### 2. Transform
* **Data Cleansing:** Handles missing values, unifies date-time formats across distinct data tables (`%Y-%m-%d %H:%M:%S`).
* **Feature Engineering & Aggregation:** Map transactional logs (`data_invoice_sample`) with operational logs (`data_cooking_time_detail_sampe`) to calculate net service time per employee.
* **Audit Tracing:** Parse change log types (e.g., item cancellation, discount overrides) to flags out anomalies tied to specific cashiers.

### 3. Load
* Pushes incremental updates directly into separate worksheets on Google Sheets using the OAuth2 `google-api-python-client`.
* Automatically clears outdated temporal caches to ensure lightweight storage while maintaining analytical integrity.

---

## 📊 Business Intelligence Dashboard (Looker Studio)

The transformed data updates live visualizations optimized for F&B operations managers:
* **Employee Performance Table:** Revenue generated per shift, checkouts handled, and average processing error rates.
* **Kitchen Efficiency Tracker:** Monitor item processing speed against standard SLAs.
* **Risk & Fraud Control Monitor:** Highlighting unusual item cancellations or manual price overrides.

---

## ⚙️ Getting Started & Setup

### Prerequisites
* Python 3.9+
* Google Cloud Platform Console account with **Google Sheets API** enabled.
* Service Account Credentials saved as a JSON key.

### Installation
1. Clone the repository:
   ```bash
   git clone [https://github.com/your-username/automated-fb-employee-analysis.git](https://github.com/your-username/automated-fb-employee-analysis.git)
   cd automated-fb-employee-analysis




