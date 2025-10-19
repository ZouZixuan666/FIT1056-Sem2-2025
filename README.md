  This **Music School Management System** is designed to simulate the front desk operations of a music school. 
Overview
It provides both a Command-Line Interface (CLI) and a Streamlit GUI to manage:
  - Students

  - Teachers

  - Courses

  - Daily Rosters

  - Attendance / Check-ins

  - (Upcoming) Payments
    
It surpot registration of students and teachers, enrolment in instruments, listing, searching, and administrative operations like adding or removing records.

## Project Structure ##
FIT1056-Sem2-2025/

│── app/

│   ├── __init__.py

│   └── schedule.py          # Core ScheduleManager (students, teachers, courses, attendance)

│   └── admin_utils.py       # surpport for logging

│   └── console_main.py      # initail frontend and provide code base UI

│   └── student.py           # a student object inharist user

│   └── teacher.py           # a teacher object inharist user

│   └── user.py              # a abstract class for basic implemention for student and teacher

│

│── gui/

│   ├── __init__.py

│   ├── main_dashboard.py    # Streamlit navigation & layout

│   ├──  dashboard_page.py   # summary for the system going

│   ├── welcome_page.py      # Welcome / landing page

│   ├── student_pages.py     # Student management UI

│   ├── roster_pages.py      # Daily roster + check-in UI

│   ├── course_pages.py      # Course management UI

│   ├── finance_pages.py         # Finance GUI page

│   └── admin_pages.py       # Admin-only features

│

│── data/

│   └── *.json / *.csv       # Saved student, teacher, attendance data

├── tests/

│   └── test_schedule_manager.py  # Pytest test suite

│

│── cli_main.py              # CLI interface

│── test_data.json           # For pytest

│── main.py                  # Streamlit entry point

│── requirements.txt         # Dependencies

│── README.md                # This file


## How to Run the Program ###

1. **Clone the repo:**
   
    bash
   
    git clone https://github.com/ZouZixuan666/FIT1056-Sem2-2025.git
   
    git switch individual
   
2. **Create a virtual environment:**

    python -m venv .venv
    Activate it.
   
4. Install Dependencies
    pip install -r requirements.txt

**Usage**

    Option 1 — Streamlit GUI (recommended)
    
    Run:
    
    streamlit run main.py
    
    
    Navigate using the sidebar.
    
    Start at the Welcome Page.
    
    Use Student Management, Daily Roster, Admin Tools, Course Management, etc.
    
    Admin password is 123 (hashed in code).
    
    Option 2 — CLI Mode
    
    Run:
    
    python cli_main.py
    
    
    This gives a text-based menu for student, teacher, and course operations.
    

## Running Tests

This project uses pytest for unit testing.

From the project root:

    pytest -v

 Tests cover:

    Students, teachers, and courses (CRUD)
    
    Attendance recording and duplicate checks
    
    Payment recording and finance history
    
    Report exporting
    
    File management and data persistence

## Features

The program supports:
Features:
- Student Management
- Register new students
- Enrol in courses
- Print student ID cards
- Remove or update students

Teacher Management:
- Add new teachers
- List teachers
- Update teacher details
- Remove teachers

Course & Lesson Scheduling：
- Create courses linked to teachers
- Add lessons (with day, time, and room)
- add course
- list course
- Show daily rosters

Attendance Tracking：
- Student check-in for lessons
- View attendance logs

Finance
Record student payments, view payment history, export finance reports to CSV
Lookup：
- Search for students and teachers by name or speciality

Admin Functions：
- Protected by hashed password (123)
- List all students/teachers
- Remove students/teachers
- Clear local files (reset database and student cards)
   
## Main functions ##

### 1. Student Management
- Register a new student with their first instrument.
- Enrol existing students in new instruments.
- Update student details.
- Remove students.
- Search students by name.

### 2. Teacher Management
- Add new teachers with specialities.
- Update teacher details.
- Remove teachers.
- Search teachers by name or speciality.

### 3. Attendance Tracking
- Check-in students for courses.
- View attendance records (with optional filters).
- Show Daily Roster

### 4. Search & Lookup
- Search across both students and teachers.

### 5. Student Card Printing
- Generate a text file badge for a student (`*_card.txt`) with their details.

### 6. Data Persistence
- All data stored in `msms.json`.
- Loads data on startup, saves changes automatically.

### 7. Admin-Only Actions
- Listing all students/teachers.
- Removing records.
- Adding teachers.
- Requires password authentication (`123` by default).
- List all Courses

### 8. Admin password been hashed

### 9. course modification

- add course 
- list course
- Switch Student Between Courses

### 9. Local File Cleanup
- Delete `msms.json` and all student cards to reset the system.

(more explainations are in the comments inside the code)


### Data Storage Format (msms.json)
{


    "students": [
        {
            "id": 1,
            "name": "Alice Johnson",
            "enrolled_course_ids": [
                101,
                103
            ]
        },
        {
            "id": 2,
            "name": "Bob Williams",
            "enrolled_course_ids": [
                102
            ]
        }
    ],
    "teachers": [
        {
            "id": 1,
            "name": "Dr. Evelyn Keys",
            "speciality": "Piano"
        },
        {
            "id": 2,
            "name": "Mr. David Fret",
            "speciality": "Guitar"
        }
    ],
    "courses": [
        {
            "id": 101,
            "name": "Beginner Piano",
            "instrument": "Piano",
            "teacher_id": 1,
            "enrolled_student_ids": [
                1
            ],
            "lessons": [
                {
                    "lesson_id": 1,
                    "day": "Monday",
                    "start_time": "16:00",
                    "room": "Room A"
                },
                {
                    "lesson_id": 2,
                    "day": "Wednesday",
                    "start_time": "16:00",
                    "room": "Room A"
                }
            ]
        },
        {
            "id": 102,
            "name": "Acoustic Guitar Fundamentals",
            "instrument": "Guitar",
            "teacher_id": 2,
            "enrolled_student_ids": [
                2
            ],
            "lessons": [
                {
                    "lesson_id": 3,
                    "day": "Tuesday",
                    "start_time": "17:00",
                    "room": "Room C"
                }
            ]
        },
        {
            "id": 103,
            "name": "Intermediate Piano",
            "instrument": "Piano",
            "teacher_id": 1,
            "enrolled_student_ids": [
                1
            ],
            "lessons": []
        }
    ],
    "attendance": [
        {
            "student_id": 1,
            "course_id": 101,
            "timestamp": "2025-07-14T15:58:30.123456"
        },
        {
            "student_id": 2,
            "course_id": 102,
            "timestamp": "2025-07-14T16:02:45.654321"
        }
    ]

    
}
Command-Line Interface: (No longer updated)
1. Register New Student
2. Enrol Existing Student
3. Lookup Student or Teacher
4. Check-in Student
5. Print Student Card
6. Update Teacher Info
7. (Admin) List all Students
8. (Admin) List all Teachers
9. (Admin) Remove student
    
a. (Admin) Remove teacher

b. (Admin) Add teacher

c. Show today's attendance

d. Clear all the local files

e. Show Daily Roster

f. Switch Student Between Courses

g. add a course

h. (Admin）List all Courses

q. Quit

## Warning ##
1. Admin Authentication
   To access these functions, you must authenticate as an admin:
   Password is hardcoded for now （password: 123）
   
## summary for all PSTS ##

In Pst 1, the basic idea of this music manege system had been formed. By using in-memory prototype some functions can be domostrated.
With in the upgrades in Pst2 datas are nolonger temparery it been saved in a MSMS.josn provided a consistet storage for data
For PST 3 the codes been redesigned based on Object-Oriented (OOP) design provide more felexable editing more modular coding and prevent from code leak.
In order to make it more user friendly a GUI formed by streamlit is implemented, it sepereas the fornmt end and back end ont only better looking but also increase the system security, Scalability and maintainability.
Current PST 5, few more function been added including the log function make the system "crash-proof" always can backtracking from the log as well as the auto tester using Pytest.
Spam the code with edge cases and large numbers autometicly can filtter out some hiden indecents that human test can't indentified.

Created by [ZouZixuan]. Thanks for veiwing!!!
