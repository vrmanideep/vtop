# VIT-AP V-TOP Interactive CLI 🚀

A fast, lightweight, and asynchronous command-line interface for accessing VIT-AP V-TOP data. This tool allows students to check their academic records without navigating the slow web portal.

## ✨ Features
- **Profile & Proctor:** Quick view of your basic details and faculty proctor info.
- **Academic Transcript:** Clean view of grades, credits, and overall CGPA (duplicates filtered).
- **Smart Attendance:** Summary view with "Safe Bunks" and "Required Classes" indicators.
- **Attendance Drill-down:** Select a subject to see exactly when you were marked absent.
- **Timetable:** View your full weekly schedule or just "Today's Schedule."
- **Internal Marks:** Detailed breakdown of CAT-1, CAT-2, and Quizzes.

## 🛠️ Prerequisites
- Python 3.10 or higher
- `pip` (Python package manager)

## 🚀 Installation & Setup

1. **Clone/Download** this repository to your local machine.
2. **Install Dependencies**:
   Open your terminal in the project folder and run:
   ```bash
   pip install -r requirements.txt

   Configure Credentials:

Locate the credentials.txt file (or create one).

Line 1: Enter your Registration Number (e.g., 24BCE7058).

Line 2: Enter your V-TOP Password. Note: Ensure there are no extra spaces or characters.

🖥️ Usage
Run the main script to start the interactive dashboard:

Bash
python vtop.py
🔒 Security & Privacy
Local Only: Your credentials are stored only on your computer in credentials.txt.

Privacy Tip: Never push your credentials.txt to a public GitHub repository. Use a .gitignore file to prevent accidental uploads.
