# Automated Employee Data Analysis Pipeline in the F&B Industry

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Google Sheets API](https://img.shields.io/badge/Google%20Sheets%20API-v4-green.svg)](https://developers.google.com/sheets/api)
[![Looker Studio](https://img.shields.io/badge/Looker%20Studio-Visualization-orange.svg)](https://lookerstudio.google.com/)
[![Windows Task Scheduler](https://img.shields.io/badge/Automation-Task%20Scheduler-lightgrey.svg)](https://learn.microsoft.com/en-us/windows/win32/taskschd/task-scheduler-start-page)

An end-to-end automated ETL (Extract, Transform, Load) pipeline designed to optimize workforce efficiency and operational visibility in the Food & Beverage (F&B) industry. 
This project automates the extraction of daily sales logs, transaction histories, and cooking durations from the **iPOS (Fabi)** system, transforms nested raw structures into clean analytical datasets, and pushes them to Google Sheets to power real-time **Looker Studio (Data Studio)** business intelligence dashboards.

---

## 🚀 Key Business Impact
* **Labor Cost Optimization:** Identifies workforce peak-hour workloads and tracks active employee sales performance ($%$ Combo vs. Alacarte sales).
* **Operational Bottleneck Discovery:** Tracks kitchen cooking time details to minimize customer wait times and optimize kitchen workflows.
* **Audit & Fraud Prevention:** Monitors order change logs (voided items, quantity adjustments) linked to specific staff accounts.
* **Customer Loyalty Analysis:** Measures customer retention rates ($%$ of returning customers), new sign-ups, and evolving consumer spending trends.

---

## 🏗️ System Architecture
```text
 [ iPOS (Fabi) System ]
          │
          ▼ (Extract)
 ┌─────────────────────────────────────────────────────────────┐
 │ Python Crawl Scripts (Triggered daily via taskschd.msc)     │
 └─────────────────────────────────────────────────────────────┘
          │
          ▼ (Raw File Storage)
 ┌─────────────────────────────────────────────────────────────┐
 │ Data Transformation Engine (Employee_Report.py)             │
 │  — Transformed nested JSON/Strings & Multi-tables           │
 │  — Aggregated KPI matrix (Working durations, Sales)         │
 └─────────────────────────────────────────────────────────────┘
          │
          ▼ (Load via Google Sheets API)
 [ Google Sheets Database ]
          │
          ▼ (Live Connection)
 [ Looker Studio BI Dashboard ] ──► End-user Report (Managers/Owners)
```
---

## 📂 Repository Structure

* `.github/` - Github actions and workflow configurations.
* `data/` - include: Cleaned, aggregated, and final processed data and Raw data snapshots crawled from iPOS.
* `reports/` - PDF Exported case studies / static dashboards
* `scripts/` - Core Python engine (github.py) and automation scripts (.sh/.bat).
* `.gitignore/` - Ensures sensitive config/credentials are not committed.
* `README.md` - Project documentation.
* `requirements.txt` - Python dependencies

---

## 🛠️ Data Pipeline & ETL Technical Details

### 1. Extract
* Automated requests target the iPOS endpoint using custom Python scrapers. (`scripts/crawl_*.py`).
* Scheduled to run autonomously every midnight using Windows Task Scheduler (`taskschd.msc`) to capture the previous day's complete dataset without manual intervention.

### 2. Transform
* **Data Cleansing:** Handles missing values, unifies date-time formats across distinct data tables (`%Y-%m-%d %H:%M:%S`).
* **Feature Engineering & Aggregation:** Map transactional logs (`data_invoice_sample`) with operational logs (`data_cooking_time_detail_sampe`) to calculate net service time per employee.
* **Audit Tracing:** Parse change log types (e.g., item cancellation, discount overrides) to flags out anomalies tied to specific cashiers.

### 3. Load
* Pushes incremental updates directly into separate worksheets on Google Sheets using the OAuth2 `google-api-python-client`.
* Overwrites or appends temporal analytical caches dynamically to ensure lightweight, fast-loading storage while maintaining history.

---

## 📊 Business Intelligence Dashboard (Looker Studio)

The transformed data updates live visualizations optimized for F&B operations managers:
* **Employee Performance Dashboard**: Revenue generated per shift, checkouts handled, and combo sales conversion rates. [See PDF preview in reports](https://github.com/thuhang24ld/Employee_Report/blob/main/reports/Employee_Sales_Performance.pdf)
* **Kitchen Efficiency Tracker**: Monitors item processing speed against standard SLAs to optimize kitchen line preparation. [See PDF preview in reports](https://github.com/thuhang24ld/Employee_Report/blob/main/reports/order-to-serve_time.pdf)
* **Customer Loyalty Monitor**: Tracks returning customer percentages, behavior shifts, and VIP metrics. [See PDF preview in reports](https://github.com/thuhang24ld/Employee_Report/blob/main/reports/Royal_customer.pdf)

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
```
2. Install required packages:
```bash
pip install pandas requests google-auth google-api-python-client
```
3. Place your Google API credentials credentials.json into the root directory.

### Automation Scheduling (Windows)
1. Open Task Scheduler (`taskschd.msc`).
2. Create a new Basic Task and set the Trigger to Daily (e.g., 12:05 AM).
3. Action: Start a Program.
4. Program/Script: Path to your `python.exe` (or an orchestrated .bat wrapper).
5. Add arguments: `scripts/crawl_sale_by_date.py` (Repeat configuration for other extraction scripts as needed).

Developed as a data-driven business solution for optimizing workforce operations in the F&B domain.



