import argparse
import asyncio
import json
import time
import sys
import subprocess
from datetime import datetime
from vitap_vtop_client.client import VtopClient
from services import (
    vtopClientLogin,
    fetchSemesters,
    fetchAttendance,
    fetchAttendanceDetail,
    fetchMarks,
    fetchTimetable,
    fetchExamSchedule,
    fetchGradeHistory,
    fetchProfile,
    get_credentials
)

#If your current `vitap_vtop_client` folder contains Python code (using `httpx` and `BeautifulSoup`), you likely have a **Python port** or a specific implementation designed for CLI tools. However, the logic (function names like `fetchAttendance`, `fetchTimetable`, and `vtopClientLogin`) is identical across both versions.
async def ensure_core_client():
    """Checks for vitap_vtop_client and downloads it if missing."""
    
    if not os.path.exists("vitap_vtop_client"):
        print("\n[!] Core client folder 'vitap_vtop_client' is missing.")
        print("[-] This is required to communicate with VIT-AP servers.")
        
        choice = input("[?] Download the core client from GitHub? (y/n): ").strip().lower()
        
        if choice == 'y':
            try:
                # This clones the official student project repository
                source_url = "[https://github.com/VITAP-Student-Project/vitap_vtop_client.git](https://github.com/VITAP-Student-Project/vitap_vtop_client.git)"
                print(f"[-] Cloning from {source_url}...")
                
                subprocess.run(["git", "clone", source_url], check=True)
                print("[+] Download complete!\n")
            except Exception as e:
                print(f"[!] Auto-download failed: {e}")
                print("[!] Please manually download from: [https://github.com/VITAP-Student-Project](https://github.com/VITAP-Student-Project)")
                sys.exit(1)
        else:
            print("[!] Exiting. The CLI cannot run without the core client.")
            sys.exit(1)

def install_dependencies():
    try:
        import httpx
        import bs4
    except ImportError:
        print("[-] Missing dependencies. Installing now...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("[+] Done! Restarting script...\n")
# ==========================================
#  DISPLAY HELPERS
# ==========================================
def print_header(title):
    print(f"\n{title}")
    print("=" * 60)

def print_profile(data):
    if not data or not data.get("basic"):
        print("   (No profile data found)")
        return

    b = data["basic"]
    print(f"\n   {'STUDENT PROFILE':^60}")
    print("   " + "=" * 60)
    print(f"   {'Name':<15} : {b.get('name')}")
    print(f"   {'Reg No':<15} : {b.get('regno')}")
    print(f"   {'Program':<15} : {b.get('program')}")
    print(f"   {'VIT Email':<15} : {b.get('vitemail')}")
    print(f"   {'Mobile':<15} : {b.get('mobile')}")
    print("   " + "-" * 60)

    p = data.get("proctor")
    if p and p.get("Name"):
        print(f"\n   {'PROCTOR INFORMATION':^60}")
        print("   " + "=" * 60)
        # Organized Display
        fields = [("Name", "Name"), ("ID", "Faculty ID"), ("Email", "Email"), ("Mobile", "Mobile"), ("Cabin", "Cabin")]
        for label, key in fields:
            if key in p:
                print(f"   {label:<15} : {p[key]}")
    else:
        print("\n   [!] Proctor Information section was not found or is empty.")
    
    print("   " + "=" * 60 + "\n")

def print_grade_history(data):
    if not data or not data.get("courses"):
        print("\n   [!] No grade history found.")
        return

    print("\n   ACADEMIC TRANSCRIPT")
    print("   " + "─" * 95)
    print(f"   {'CODE':<15} {'GRADE':<12} {'CREDITS':<12} {'COURSE NAME'}")
    print("   " + "─" * 95)
    
    for c in data["courses"]:
        # Standard columns without type or exam attributes
        print(f"   {c['code']:<15} {c['grade']:<12} {c['credits']:<12} {c['name']}")
    
    print("   " + "─" * 95 + "\n")
    
    s = data.get("summary", {})
    print(f"   ACADEMIC STANDING (OVERALL)")
    print(f"   -------------------------------------------")
    print(f"   CURRENT CGPA          : {s.get('cgpa')}")
    print(f"   CREDITS EARNED        : {s.get('earned')}")
    print(f"   CREDITS REGISTERED    : {s.get('registered')}")
    print(f"   -------------------------------------------\n")

def print_today_schedule(data):
    if not data:
        print("   (No timetable data available)")
        return
    current_day = datetime.now().strftime("%A").upper()
    print(f"\n   {'SCHEDULE FOR ' + current_day:^60}")
    print("   " + "=" * 60)
    classes = data.get(current_day, [])
    if not classes:
        print(f"   🎉 No classes scheduled for {current_day.title()}!")
        print("   " + "=" * 60)
        return
    try: classes.sort(key=lambda x: x.get('time', '23:59').split('-')[0].strip())
    except: pass
    print(f"   {'TIME':<15} {'VENUE':<8} {'CODE':<10} {'SLOT':<10} {'COURSE NAME'}")
    print("   " + "-" * 60)
    for c in classes:
        time_str = c.get('time', '-')        
        venue    = c.get('venue', '-')       
        code     = c.get('course_code', '-') 
        name     = c.get('course_name', '-')[:25]
        slot     = c.get('slot', '-')        
        if slot.endswith('-'): slot = slot[:-1].strip()
        print(f"   {time_str:<15} {venue:<8} {code:<10} {slot:<10} {name}")
    print("   " + "-" * 60)

async def print_attendance_with_details(client, semester_id, summary_data):
    if not summary_data:
        print("   (No data found)")
        return

    print(f"\n   {'ATTENDANCE REPORT (Detailed History)':^80}")
    print("   " + "=" * 80)

    for sub in summary_data:
        code = sub.get('course_code', '-')
        name = sub.get('course_name', '-')
        ctype = sub.get('course_type', '-')
        perc = sub.get('percentage', '0')
        attended = sub.get('attended', '0')
        total = sub.get('total', '0')
        
        try: is_low = float(perc) < 75
        except: is_low = False
        status_icon = "🔴" if is_low else "🟢"
        
        print(f"\n   {status_icon} {code} : {name} ({ctype})")
        print(f"       Attendance: {perc}% ({attended}/{total})")
        
        c_id = sub.get('course_id')
        c_type = sub.get('type_code')
        
        if c_id and c_type:
            history = await fetchAttendanceDetail(client, semester_id, c_id, c_type)
            if history:
                absents = [h for h in history if "Present" not in h['status']]
                
                # Sort Chronologically
                def safe_date_sort(x):
                    # Trying both common formats to be safe
                    for fmt in ("%d-%m-%Y", "%d-%b-%Y"):
                        try: return datetime.strptime(x['date'], fmt)
                        except: continue
                    return datetime.min
                
                absents.sort(key=safe_date_sort, reverse=True)

                if absents:
                    print(f"       [!] Found {len(absents)} Absences:")
                    for h in absents:
                         print(f"           {h['date']:<12} {h['slot']:<8} ❌ {h['status']}")
                else:
                     print(f"       (History fetched: {len(history)} classes, All Present)")
            else:
                print("       (No history records found)")
        else:
            print("       [!] Cannot fetch details (ID missing).")
        print("   " + "-" * 40)

def print_attendance(data):
    if not data:
        print("   (No data found)")
        return

    # Header with refined spacing
    print(f"\n   {'S.No':<5} {'CODE':<9} {'TYPE':<12} {'SLOT':<12} {'%':<5} {'ATT/TOT':<9} {'STATUS'}")
    print("   " + "─" * 70)

    for i, sub in enumerate(data):
        code = sub.get('course_code', '-')
        
        # Clean TYPE (Shortened)
        ctype = sub.get('course_type', '').replace("Embedded Theory", "Emb. Th.").replace("Embedded Lab", "Emb. Lab").replace("Theory Only", "Th. Only")
        
        # Clean SLOT (Extracts just the middle part: C1+TC1)
        raw_slot = sub.get('slot', '-')
        slot = raw_slot.split(' - ')[1] if ' - ' in raw_slot else raw_slot
        
        perc = sub.get('percentage', '0')
        att = sub.get('attended', '0')
        tot = sub.get('total', '0')
        
        # Clean NAME (Removes the redundant "CSE1005 - " from the start)
        full_name = sub.get('course_name', '-')
        name = full_name.split(' - ')[1] if ' - ' in full_name else full_name

        # Status Logic
        try:
            status = "LOW ⚠️" if float(perc) < 75 else "OK"
        except:
            status = "-"

        # Print the clean row
        print(f"   {i+1:<5} {code:<9} {ctype:<12} {slot:<12} {perc:<5} {att:>2}/{tot:<6} {status}")
    
    print("   " + "─" * 70)

def print_marks(data):
    if not data or "courses" not in data:
        print("   (No marks found)")
        return
    courses = data["courses"]
    courses.sort(key=lambda x: x.get('course_code', ''))
    print(f"   {'CODE':<10} {'COURSE TITLE':<35} {'MARK TITLE':<20} {'SCORE':<8} {'MAX'}")
    print("   " + "-" * 85)
    for course in courses:
        code = course.get('course_code', '-')
        title = course.get('course_title', '-')[:30]
        details = course.get('details', [])
        if not details:
             print(f"   {code:<10} {title:<35} {'-':<20} {'-':<8} {'-'}")
             print("   " + "-" * 85)
             continue
        first_line = True
        for mark in details:
            m_title = mark.get('mark_title', '-')
            score   = mark.get('scored_mark', '-')
            max_m   = mark.get('max_mark', '-')
            if first_line:
                print(f"   {code:<10} {title:<35} {m_title:<20} {score:<8} {max_m}")
                first_line = False
            else:
                print(f"   {'':<10} {'':<35} {m_title:<20} {score:<8} {max_m}")
        print("   " + "-" * 85)

def print_timetable(data):
    if not data:
        print("   (No timetable found)")
        return
    print(f"   {'TIME':<15} {'VENUE':<8} {'CODE':<10} {'SLOT':<15} {'COURSE NAME'}")
    print("   " + "-" * 100)
    day_order = {"MONDAY": 1, "TUESDAY": 2, "WEDNESDAY": 3, "THURSDAY": 4, "FRIDAY": 5, "SATURDAY": 6, "SUNDAY": 7}
    sorted_days = sorted(data.keys(), key=lambda d: day_order.get(d.upper(), 99))
    for day in sorted_days:
        classes = data[day]
        if not isinstance(classes, list) or not classes: continue
        print(f"   [{day.upper()}]")
        try: classes.sort(key=lambda x: x.get('time', '23:59').split('-')[0].strip())
        except: pass
        for c in classes:
            time_str = c.get('time', '-')        
            venue    = c.get('venue', '-')       
            code     = c.get('course_code', '-') 
            name     = c.get('course_name', '-') 
            slot     = c.get('slot', '-')        
            if slot.endswith('-'): slot = slot[:-1].strip()
            print(f"   {time_str:<15} {venue:<8} {code:<10} {slot:<15} {name}")
        print("")

def print_exam_schedule(data):
    if not data:
        print("   (No exams scheduled)")
        return
    def parse_date(d):
        try: return datetime.strptime(d, "%d-%b-%Y")
        except: return datetime.max
    data.sort(key=lambda x: parse_date(x.get('exam_date', '')))
    print(f"   {'DATE':<12} {'TIME':<20} {'CODE':<10} {'CLASS ID':<15} {'TYPE':<8} {'VENUE':<8} {'TITLE'}")
    print("   " + "-" * 110)
    for ex in data:
        date  = ex.get('exam_date', '-')
        time  = ex.get('exam_time', '-')
        code  = ex.get('course_code', '-')
        cid   = ex.get('class_id', '-')
        etype = ex.get('exam_type', '-')[:8]
        venue = ex.get('venue', '-')
        venue = " ".join(venue.split())
        title = ex.get('course_title', '-')
        print(f"   {date:<12} {time:<20} {code:<10} {cid:<15} {etype:<8} {venue:<8} {title}")
    print("   " + "-" * 110)

def print_attendance_history(name, history):
    if not history:
        print("   [!] No records found.")
        return

    print(f"\n   {'─'*60}")
    print(f"   LOG: {name[:50]}...")
    print(f"   {'─'*60}")
    print(f"   {'DATE':<15} {'SLOT':<15} {'STATUS'}")
    print(f"   {'─'*60}")
    
    for entry in history:
        # Visual cue for Absents
        status = entry['status']
        if status.upper() == "ABSENT":
            status = f"!! {status} !!"
            
        print(f"   {entry['date']:<15} {entry['slot']:<15} {status}")
    print(f"   {'─'*60}")
# ==========================================
#  MAIN CLI LOGIC
# ==========================================
async def main():
    reg_no, password = get_credentials("credentials.txt")
    print(f"[-] Connecting to V-TOP as {reg_no}...")
    
    async with VtopClient(reg_no, password) as client:
        if not await vtopClientLogin(client):
            print(f"[!] Login Failed.")
            return

        # 1. FORCE DASHBOARD LOAD (The "Unlock" Step)
        # This tells the server you are officially on the dashboard
        await client._client.get("https://vtop.vitap.ac.in/vtop/content")
        
        # 2. FETCH SEMESTERS FIRST
        # This is usually the "lighter" request and helps stabilize the CSRF
        available_sems = await fetchSemesters(client)
        
        # 3. FETCH PROFILE SECOND
        # Now that the session is warm, fetch the profile
        profile_data = await fetchProfile(client)
        
        # 4. DATA ASSIGNMENT
        student_name = profile_data.get("basic", {}).get("name", "Student")
        target_sem = available_sems[0]['id'] if available_sems else None
        current_sem_name = available_sems[0]['name'] if available_sems else "None"

        print(f"\n{'='*55}")
        print(f" SUCCESS  : Logged in as {student_name}")
        print(f" REG NO   : {reg_no}")
        print(f" CURR SEM : {current_sem_name}")
        print(f"{'='*55}")

        # 3. DISPLAY SUCCESS DASHBOARD
        print(f"\n{'='*55}")
        print(f" SUCCESS  : Logged in as {student_name}")
        print(f" REG NO   : {reg_no}")
        print(f" CURR SEM : {current_sem_name}")
        print(f"{'='*55}")

        # 4. INTERACTIVE LOOP
        while True:
            print("\nAVAILABLE OPTIONS:")
            print("  1. View Profile & Proctor Details")
            print("  2. View Grade History (Transcript)")
            print("  3. View Attendance Summary")
            print("  4. View Full Timetable")
            print("  5. View Today's Schedule")
            print("  6. View Internal Marks")
            print("  7. View Exam Schedule")
            print("  8. Change/Select Semester")
            print("  0. Exit")
            
            choice = input(f"\n[{reg_no}] Enter choice (0-8): ").strip()

            if choice == '0':
                print("Logging out... Goodbye!")
                break
            
            # Choice 1 & 2 are semester-independent
            if choice == '1':
                print_header("STUDENT PROFILE")
                print_profile(profile_data)

            elif choice == '2':
                print_header("ACADEMIC TRANSCRIPT")
                g_data = await fetchGradeHistory(client)
                print_grade_history(g_data)

            # Choices 3-7 require a semester to be selected
            elif choice in ['3', '4', '5', '6', '7']:
                if not target_sem:
                    print("[!] No semester selected. Please use option 8 first.")
                    continue

                if choice == '3':
                    # 1. Show the Summary
                    data = await fetchAttendance(client, target_sem)
                    print_attendance(data) 
                    
                    # 2. Drill Down into Details
                    print("\n   " + "─" * 45)
                    sel = input("   Select S.No for Detail History (Enter to skip): ").strip()
                    
                    if sel.isdigit():
                        idx = int(sel) - 1
                        if 0 <= idx < len(data):
                            course = data[idx]
                            if course.get('course_id'):
                                print(f"   ...Fetching history for {course['course_id']}...")
                                history = await fetchAttendanceDetail(
                                    client, target_sem, course['course_id'], course['type_code']
                                )
                                print_attendance_history(course['course_name'], history)
                            else:
                                print("   [!] No detail link found for this course.")
                
                elif choice == '4':
                    print_header(f"FULL TIMETABLE - {current_sem_name}")
                    data = await fetchTimetable(client, target_sem)
                    print_timetable(data)

                elif choice == '5':
                    print_header(f"TODAY'S SCHEDULE - {current_sem_name}")
                    data = await fetchTimetable(client, target_sem)
                    print_today_schedule(data)

                elif choice == '6':
                    print_header(f"INTERNAL MARKS - {current_sem_name}")
                    data = await fetchMarks(client, target_sem)
                    print_marks(data)

                elif choice == '7':
                    print_header(f"EXAM SCHEDULE - {current_sem_name}")
                    data = await fetchExamSchedule(client, target_sem)
                    print_exam_schedule(data)

            elif choice == '8':
                if not available_sems:
                    print("   ...No semester data available. Re-scraping...")
                    available_sems = await fetchSemesters(client)

                if available_sems:
                    print_header("SELECT SEMESTER")
                    for i, s in enumerate(available_sems):
                        print(f"   {i+1}. {s['name']}")
                    
                    sel = input("\nSelect a semester number (0 to cancel): ").strip()
                    if sel == '0': continue

                    try:
                        idx = int(sel) - 1
                        if 0 <= idx < len(available_sems):
                            target_sem = available_sems[idx]['id']
                            current_sem_name = available_sems[idx]['name']
                            print(f"[+] Active Semester set to: {current_sem_name}")
                        else:
                            print("[!] Invalid selection.")
                    except ValueError:
                        print("[!] Please enter a valid number.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] Scraper stopped by user.")
    except Exception as e:
        print(f"\n[!] Fatal Error: {e}")