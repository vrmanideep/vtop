# 🎓 VIT-AP V-TOP CLI Dashboard

A high-performance, asynchronous Command Line Interface (CLI) for VIT-AP students to access V-TOP services instantly. Built with Python, this tool bypasses the heavy web UI to provide academic data in a clean, terminal-based format.

---

## 🚀 Key Features

### 📊 Academic Transcript
- **Regex-Cleaned:** Automatically filters out redundant sub-rows (ETL/ETH/ELA) to show a clean, primary course list.
- **Auto-Summary:** Displays CGPA, Credits Earned, and Registered Credits at a glance.

### 📅 Attendance Intelligence
- **Drill-down History:** Select any course by S.No to view a date-wise log of every "Present" and "Absent" mark.
- **Visual Indicators:** Quick status markers (🔴/🟢) for subjects falling below the 75% threshold.
- **Slot Formatting:** Cleaned slot names (e.g., `C1+TC1`) for better readability.

### 🕒 Smart Scheduling
- **Today's Schedule:** Instantly view your classes for the current day, sorted chronologically.
- **Full Timetable:** A comprehensive weekly breakdown organized by day order.

---
## 🔗 Acknowledgments & Sources
This CLI is powered by the core scraping logic from the **VIT-AP Student Project**. 
- **Core Library:** `vitap_vtop_client`
- **Official Documentation:** [pub.dev/documentation/vit_vtop](https://pub.dev/documentation/vit_vtop/latest/)
- **Organization:** [VITAP Student Project Team](https://github.com/VITAP-Student-Project)

## 🛠️ Installation

### 1. Prerequisites
Ensure you have **Python 3.10+** installed. You can verify this by running:
```python
python --version
```

2. Setup
Clone the project or unzip the shared folder to your preferred directory.

Install requirements: Open your terminal in the project folder and run:

```python
pip install -r requirements.txt
```

3. Configuration
The script requires a file named credentials.txt in the root directory. Create credentials.txt and format it exactly as follows:

Line 1: Your Registration Number 
Line 2: Your V-TOP Password

Note: Do not add any spaces, commas, or extra lines to this file. 

🖥️ Usage
Simply run the main script to enter the interactive dashboard:

```python
python vtop.py
```

Navigation Tips:
Option 3: After viewing the Attendance Summary, enter the S.No of a specific course to pull its date-wise history.

Option 8: Use this first if you want to view data from a previous semester.

⚠️ Security Warning
DO NOT SHARE YOUR credentials.txt FILE. This file contains your plain-text password.

If you are uploading this project to GitHub, ensure credentials.txt is added to your .gitignore file.

Before sharing this folder with friends, delete your credentials and provide a blank template.

🛠️ Tech Stack
Language: Python (Asyncio)

Networking: HTTPX (Asynchronous HTTP Client)

Parsing: BeautifulSoup4 & LXML (Robust HTML Scraping)

Client: Custom vitap_vtop_client integration
