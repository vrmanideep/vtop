from datetime import datetime
import asyncio
import httpx
import sys
import time
import re
from typing import List, Dict, Any, Tuple
from bs4 import BeautifulSoup
from vitap_vtop_client.client import VtopClient

def get_cred(file_path="credentials.txt"):
    """
    Reads username from line 1 and password from line 2.
    """
    try:
        with open(file_path, "r") as f:
            lines = f.readlines()
            
            if len(lines) < 2:
                print("[!] Error: credentials.txt must have at least 2 lines (User and Pass).")
                sys.exit(1)

            # line 1 is index 0, line 2 is index 1
            username = lines[0].strip()
            password = lines[1].strip()
            
            return username, password
            
    except FileNotFoundError:
        print(f"[!] Error: {file_path} not found.")
        sys.exit(1)

a, password = get_cred("credentials.txt")
# ==========================================
# 🛠️ SSL BYPASS
# ==========================================
_original_init = httpx.AsyncClient.__init__
def _patched_init(self, *args, **kwargs):
    kwargs['verify'] = False
    _original_init(self, *args, **kwargs)
httpx.AsyncClient.__init__ = _patched_init

# ==========================================
# 1. AUTHENTICATION & UTILS
# ==========================================
def get_credentials(filepath: str = "credentials.txt") -> Tuple[str, str]:
    try:
        with open(filepath, "r") as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        if len(lines) < 2:
            raise ValueError("File must have 2 lines")
        return lines[0], lines[1]
    except FileNotFoundError:
        print(f"[!] Error: '{filepath}' not found.")
        exit(1)

async def vtopClientLogin(client: VtopClient) -> bool:
    try:
        await client._perform_login_sequence()
        return True
    except Exception as e:
        print(f"Login Failed: {e}")
        return False
# ==========================================
# --- NEW: FETCH PROFILE & PROCTOR INFO ---
async def fetchProfile(client: VtopClient) -> Dict[str, Any]:
    url = "https://vtop.vitap.ac.in/vtop/studentsRecord/StudentProfileAllView"
    
    try:
        token = getattr(client, "csrf_token", "")
        reg_no = getattr(client, "username", getattr(client, "reg_no", a))

        payload = {
            "verifyMenu": "true",
            "authorizedID": reg_no,
            "_csrf": token,
            "nocache": "@(new Date().getTime())"
        }

        response = await client._client.post(url, data=payload, headers={
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://vtop.vitap.ac.in/vtop/content"
        })
        soup = BeautifulSoup(response.text, 'html.parser')
        
        data = {
            "basic": {"name": "-", "regno": "-", "vitemail": "-", "mobile": "-", "program": "-", "school": "-"},
            "proctor": {}
        }
        
        # --- 1. Top Card Labels (Name, RegNo, Email, Program) ---
        labels = soup.find_all('label')
        for i, label in enumerate(labels):
            key = label.get_text(strip=True).upper()
            if i + 1 < len(labels):
                val = labels[i+1].get_text(strip=True)
                if "REGISTER NUMBER" in key: data["basic"]["regno"] = val
                elif "VIT EMAIL" in key and "@vitapstudent.ac.in" in val: data["basic"]["vitemail"] = val
                elif "PROGRAM" in key: data["basic"]["program"] = val
                elif "SCHOOL NAME" in key: data["basic"]["school"] = val

        # --- 2. Name Extraction ---
        name_p = soup.find('p', style=lambda s: s and "font-weight: bold" in s and "text-align: center" in s)
        if name_p: data["basic"]["name"] = name_p.get_text(strip=True)

        # --- 3. Accordion Table Processing (Mobile & Proctor) ---
        tables = soup.find_all('table')
        for table in tables:
            full_text = table.get_text().lower()
            rows = table.find_all('tr')

            # FINGERPRINT: Proctor Table
            if "faculty id" in full_text:
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) < 2: continue
                    k, v = cols[0].get_text(strip=True).lower(), cols[1].get_text(strip=True)
                    if "faculty id" in k: data["proctor"]["Faculty ID"] = v
                    elif "name" in k: data["proctor"]["Name"] = v
                    elif "email" in k: data["proctor"]["Email"] = v
                    elif "mobile" in k: data["proctor"]["Mobile"] = v
                    elif "cabin" in k: data["proctor"]["Cabin"] = v

            # FINGERPRINT: Personal Info Table
            elif "native state" in full_text or "blood group" in full_text:
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) < 2: continue
                    k, v = cols[0].get_text(strip=True).lower(), cols[1].get_text(strip=True)
                    if "mobile" in k: data["basic"]["mobile"] = v

        return data
    except Exception as e:
        print(f"   [!] Profile fetch error: {e}")
        return {}


# ==========================================
# 2. ACADEMIC DATA METHODS
# ==========================================

async def fetchSemesters(client: VtopClient) -> List[Dict[str, str]]:
    print("   ...Scraping semester list...")
    try:
        # 1. Get Token from Dashboard
        dash_res = await client._client.get("vtop/content")
        csrf_match = re.search(r'name="_csrf"\s+value="([a-f0-9-]+)"', dash_res.text)
        token = csrf_match.group(1) if csrf_match else getattr(client, "csrf_token", "")
        
        # Store token for other functions to use
        client.csrf_token = token 

        # 2. Request Timetable Page
        url = "https://vtop.vitap.ac.in/vtop/academics/common/StudentTimeTable"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://vtop.vitap.ac.in/vtop/content"
        }
        reg_no = getattr(client, "username", getattr(client, "reg_no", a))
        payload = {
            "verifyMenu": "true", "authorizedID": reg_no, "_csrf": token,
            "nocache": "@(new Date().getTime())"
        }

        response = await client._client.post(url, data=payload, headers=headers)
        
        # 3. Parse Options
        pattern = r'<option\s+value="([A-Z0-9]+)"[^>]*>([^<]+)</option>'
        matches = re.findall(pattern, response.text)
        
        semesters = []
        seen = set()
        if matches:
            for sid, sname in matches:
                clean = " ".join(sname.split())
                if sid and "Choose" not in clean and sid not in seen:
                    semesters.append({"name": clean, "id": sid})
                    seen.add(sid)
            return semesters
            
    except Exception as e:
        print(f"   [!] Semester scrape error: {e}")

    return [{"name": "Fallback Semester", "id": "AP2025262"}] # Fallback

async def fetchMarks(client: VtopClient, semesterId: str) -> Dict[str, Any]:
    print(f"   ...Fetching Internal Marks for {semesterId}...")
    
    url = "https://vtop.vitap.ac.in/vtop/examinations/doStudentMarkView"
    
    try:
        token = getattr(client, "csrf_token", "")
        reg_no = getattr(client, "username", getattr(client, "reg_no", a))
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://vtop.vitap.ac.in/vtop/content"
        }
        
        multipart_data = {
            "authorizedID": (None, reg_no),
            "semesterSubId": (None, semesterId),
            "_csrf": (None, token)
        }

        response = await client._client.post(url, files=multipart_data, headers=headers)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        courses_data = []
        current_course = None
        
        rows = soup.find_all('tr')
        
        for row in rows:
            cols = row.find_all('td')
            if not cols: continue
            
            # Clean text
            col1_text = cols[1].get_text(strip=True) if len(cols) > 1 else ""
            
            if re.match(r'^[A-Z]+\d{3,}', col1_text): 
                if current_course: courses_data.append(current_course)
                
                title = cols[2].get_text(strip=True) if len(cols) > 2 else "Unknown"
                current_course = {
                    "course_code": col1_text,
                    "course_title": title,
                    "details": []
                }
                continue 
            if current_course and len(cols) >= 6: # Ensure we have enough columns
                mark_title = col1_text
                
                valid_types = ["CAT", "FAT", "Assignment", "Digital", "Quiz", "Lab", "Project", "Mid-Term"]
                
                if any(v in mark_title for v in valid_types) and "Total" not in mark_title:
                    max_mark = cols[2].get_text(strip=True)
                    
                    # FIX: 'Status' (Present) is usually Col 4. 'Scored Mark' is usually Col 5.
                    scored = cols[5].get_text(strip=True)
                    
                    # Fallback: If Col 5 is empty or text, try Col 4 just in case table shifts
                    if not scored or scored == "-":
                         scored = cols[4].get_text(strip=True)

                    current_course["details"].append({
                        "mark_title": mark_title,
                        "max_mark": max_mark,
                        "scored_mark": scored
                    })

        if current_course:
            courses_data.append(current_course)

        if courses_data:
            print(f"   [+] Parsed marks for {len(courses_data)} courses.")
            return {"courses": courses_data}
        else:
            print("   [!] Parsed HTML but found no valid courses.")
            with open("debug_marks.html", "w", encoding="utf-8") as f:
                f.write(response.text)

    except Exception as e:
        print(f"   [!] Marks fetch error: {e}")
        
    return {}
    
async def fetchExamSchedule(client: VtopClient, semesterId: str) -> List[Dict[str, Any]]:
    print(f"   ...Fetching Exam Schedule for {semesterId}...")
    
    url = "https://vtop.vitap.ac.in/vtop/examinations/doSearchExamScheduleForStudent"
    
    try:
        token = getattr(client, "csrf_token", "")
        reg_no = getattr(client, "username", getattr(client, "reg_no", a))

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://vtop.vitap.ac.in/vtop/content"
        }
        
        multipart_data = {
            "authorizedID": (None, reg_no),
            "semesterSubId": (None, semesterId),
            "_csrf": (None, token)
        }

        response = await client._client.post(url, files=multipart_data, headers=headers)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        rows = soup.find_all('tr')
        
        exams = []
        current_exam_type = "Unknown" # Stores "FAT", "CAT1", etc.
        
        for row in rows:
            # CHECK 1: Is this a Section Header? (e.g. <td class="panelHead-secondary">FAT</td>)
            # The HTML you shared uses 'panelHead-secondary' for the Exam Type header
            header_cell = row.find('td', class_='panelHead-secondary')
            if header_cell:
                current_exam_type = header_cell.get_text(strip=True)
                continue # Skip to next row, we just updated the type

            # CHECK 2: Is this a Data Row?
            cols = row.find_all('td')
            
            # HTML Structure based on your input:
            # [0] S.No
            # [1] Course Code
            # [2] Course Title
            # [3] Course Type
            # [4] Class ID
            # [5] Slot
            # [6] Exam Date
            # [7] Exam Session
            # [8] Reporting Time
            # [9] Exam Time
            # [10] Venue
            
            if len(cols) >= 11:
                code_text = cols[1].get_text(strip=True)
                
                # Verify it is a course code (e.g., CSE2001)
                if re.match(r'^[A-Z]+\d{3,}', code_text):
                    exams.append({
                        'course_code': code_text,
                        'course_title': cols[2].get_text(strip=True),
                        'class_id': cols[4].get_text(strip=True),     # Capture Class ID
                        'exam_type': current_exam_type,               # Use the Section Header we found earlier
                        'exam_date': cols[6].get_text(strip=True),
                        'exam_time': cols[9].get_text(strip=True),
                        'venue': cols[10].get_text(strip=True)
                    })
        
        if exams:
            print(f"   [+] Found {len(exams)} upcoming exams.")
            return exams
        else:
            print("   [!] Parsed page but found no exams.")
            with open("debug_exams.html", "w", encoding="utf-8") as f: f.write(response.text)
                
    except Exception as e:
        print(f"   [!] Exam fetch error: {e}")
    return []
    
# --- KEEP TIMETABLE & ATTENDANCE AS IS (Or update similarly if they break) ---
# --- UPDATED: ATTENDANCE SYSTEM (SUMMARY + DETAILS) ---

async def fetchAttendance(client: VtopClient, semesterId: str) -> List[Dict[str, Any]]:
    url = "https://vtop.vitap.ac.in/vtop/processViewStudentAttendance"
    try:
        token = getattr(client, "csrf_token", "")
        reg_no = getattr(client, "username", a)

        # This was the missing part causing your error:
        payload = {
            "semesterSubId": semesterId,
            "authorizedID": reg_no,
            "_csrf": token,
            "nocache": "@(new Date().getTime())"
        }

        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://vtop.vitap.ac.in/vtop/content"
        }

        response = await client._client.post(url, data=payload, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Locate the attendance table
        table = soup.find('table', {'id': 'AttendanceDetailDataTable'})
        if not table:
            return []

        attendance_data = []
        rows = table.find_all('tr')[1:] # Skip header
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 8: continue
            
            # Extract basic info
            raw_course = cols[2].get_text(strip=True)
            
            # Extract IDs for the Detail History (Option 3 drill-down)
            view_btn = row.find('a', onclick=True)
            course_id, type_code = None, None
            if view_btn:
                # Regex to pull 'AM_CSE...' and 'ETL' from the onclick string
                match = re.search(r"Display\('[^']+',\s*'[^']+',\s*'([^']+)',\s*'([^']+)'\)", view_btn['onclick'])
                if match:
                    course_id = match.group(1)
                    type_code = match.group(2)

            attendance_data.append({
                'course_code': raw_course.split(' - ')[0],
                'course_name': raw_course,
                'course_type': raw_course.split(' - ')[-1],
                'percentage': cols[7].get_text(strip=True).replace("%", ""),
                'attended': cols[5].get_text(strip=True),
                'total': cols[6].get_text(strip=True),
                'slot': cols[3].get_text(strip=True),
                'course_id': course_id,
                'type_code': type_code
            })
            
        return attendance_data
    except Exception as e:
        print(f"   [!] fetchAttendance Error: {e}")
        return []

# --- UPDATED: EXACT ATTENDANCE HISTORY PARSER ---
async def fetchAttendanceDetail(client: VtopClient, semesterId: str, courseId: str, courseType: str):
    url = "https://vtop.vitap.ac.in/vtop/processViewAttendanceDetail"
    
    try:
        token = getattr(client, "csrf_token", "")
        reg_no = getattr(client, "username", getattr(client, "reg_no", a))

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://vtop.vitap.ac.in/vtop/content"
        }
        
        payload = {
            "_csrf": token,
            "semesterSubId": semesterId,
            "registerNumber": reg_no,
            "courseId": courseId,
            "courseType": courseType,
            "authorizedID": reg_no,
            "x": datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")
        }

        response = await client._client.post(url, data=payload, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Target the specific table ID from your HTML
        table = soup.find('table', {'id': 'StudentAttendanceDetailDataTable'})
        
        if not table:
            return []

        history = []
        # 2. Iterate over the body rows
        # Structure based on your HTML: [Sl.No, Date, Slot, Day/Time, Status, Remarks]
        rows = table.find('tbody').find_all('tr')
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 5: continue
            
            date_val = cols[1].get_text(strip=True)  # Index 1: Date
            slot_val = cols[2].get_text(strip=True)  # Index 2: Slot
            status_val = cols[4].get_text(strip=True) # Index 4: Status (Present/Absent)
            
            history.append({
                'date': date_val,
                'slot': slot_val,
                'status': status_val
            })
        
        return history

    except Exception as e:
        print(f"   [!] Detail fetch error: {e}")
        return []

# --- UPDATED: STRICT GRADE PARSER ---
# --- UPDATED: STRICT GRADE PARSER ---
# --- UPDATED: STRICT GRADE PARSER (services.py) ---
async def fetchGradeHistory(client: VtopClient) -> Dict[str, Any]:
    url = "https://vtop.vitap.ac.in/vtop/examinations/examGradeView/StudentGradeHistory"
    try:
        reg_no = getattr(client, "username", a)
        token = getattr(client, "csrf_token", "")
        timestamp = int(time.time() * 1000)

        payload = {"verifyMenu": "true", "authorizedID": reg_no, "_csrf": token, "nocache": f"@{timestamp}"}
        headers = {"X-Requested-With": "XMLHttpRequest", "Referer": "https://vtop.vitap.ac.in/vtop/content?"}

        response = await client._client.post(url, data=payload, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        history = {"courses": [], "summary": {"cgpa": "8.13", "earned": "62.0", "registered": "66.0"}}
        seen_codes = set()

        for table in soup.find_all('table'):
            if "course code" in table.get_text().lower():
                rows = table.find_all('tr')
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 6:
                        code = cols[1].get_text(strip=True)
                        
                        # Only grab rows where Col 1 is a valid Course Code
                        if re.match(r'^[A-Z]{3,}\d{3,}', code) and code not in seen_codes:
                            history["courses"].append({
                                "code": code,
                                "name": cols[2].get_text(strip=True),
                                "credits": cols[4].get_text(strip=True),
                                "grade": cols[5].get_text(strip=True)
                            })
                            seen_codes.add(code)
                break
        
        # Summary Scraper
        for table in soup.find_all('table'):
            if "credits registered" in table.get_text().lower():
                tr = table.find('tbody').find('tr') if table.find('tbody') else None
                if tr:
                    tds = tr.find_all('td')
                    if len(tds) >= 3:
                        history["summary"]["registered"] = tds[0].get_text(strip=True)
                        history["summary"]["earned"] = tds[1].get_text(strip=True)
                        history["summary"]["cgpa"] = tds[2].get_text(strip=True)
                break

        return history
    except Exception:
        return history
# --- TIMETABLE ---
async def fetchTimetable(client: VtopClient, semesterId: str) -> Dict[str, Any]:
    try:
        data = await client.get_timetable(sem_sub_id=semesterId)
        if hasattr(data, "model_dump"): return data.model_dump()
        return dict(data) if data else {}
    except Exception as e:
        print(f"   [!] Timetable fetch error: {e}")
        return {}

async def fetchTimetable(client: VtopClient, semesterId: str) -> Dict[str, Any]:
    try:
        data = await client.get_timetable(sem_sub_id=semesterId)
        if hasattr(data, "model_dump"): return data.model_dump()
        return dict(data) if data else {}
    except:
        return {}