  This **Music School Management System** is designed to simulate the front desk operations of a music school. 
It surpot registration of students and teachers, enrolment in instruments, listing, searching, and administrative operations like adding or removing records.

## Project Structure ##
  pst2/
├── app/
│   ├── __init__.py
│   ├── user.py         # Base User class
│   ├── student.py      # StudentUser class
│   ├── teacher.py      # TeacherUser + Course class
│   └── schedule.py     # ScheduleManager (core business logic)
├── data/
│   └── msms.json       # JSON database (students, teachers, courses, attendance)
├── main.py             # CLI entry point (front desk interface)
└── README.md           # Documentation

## How to Run the Program ###

1. **Clone the repo:**
   
   bash
   
   git clone https://github.com/ZouZixuan666/FIT1056-Sem2-2025.git
   
   git switch individual
   
2. **Then run  pst2_main.py and feel free to test it on**

**Even better download the .rar files extract it and run it full locally**

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

Lookup：
- Search for students and teachers by name or speciality

Admin Functions：
- Protected by password (123)
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

===== MSMS v3 (Object-Oriented) =====
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

Created by [ZouZixuan]. Thanks for veiwing!!!
