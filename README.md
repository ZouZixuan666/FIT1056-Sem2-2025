This **Music School Management System** is designed to simulate the front desk operations of a music school. 
It surpot registration of students and teachers, enrolment in instruments, listing, searching, and administrative operations like adding or removing records.

## Project Structure ##
  pst2_main.py ---- take care of all the jobs.
  msms.json # Persistent data store (auto-generated)
  *_card.txt # Student ID card files (auto-generated)

## How to Run the Program ###

1. **Clone the repo:**
   
   bash
   
   git clone https://github.com/ZouZixuan666/FIT1056-Sem2-2025.git
   
   git switch individual
   
2. **Then run  pst2_main.py and feel free to test it on**

## Features

The program supports:
- Adding, updating, removing **students** and **teachers**
- Enrolling students in **courses/instruments**
- **Attendance tracking** for students
- Searching and **printing student ID cards**
- Administrative controls for sensitive operations
- Safe data persistence in `msms.json`
- **File cleanup** to reset the system
   
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

### 8. Local File Cleanup
- Delete `msms.json` and all student cards to reset the system.

(There are totally 22 methods providing functionalities of this program, the functions of them are commented. For more deatails, please go to the inter code comments)


### Data Storage Format (msms.json)
{
    "students": [
        {
            "id": 1,
            "name": "Alice",
            "enrolled_in": ["Violin"]
        }
    ],
    "teachers": [
        {
            "id": 1,
            "name": "Dr. Keys",
            "speciality": "Piano"
        }
    ],
    "attendance": [
        {
            "student_id": 1,
            "course_id": "Violin",
            "timestamp": "2025-08-15T10:00:00"
        }
    ],
    "next_student_id": 2,
    "next_teacher_id": 2
}

### Main Menu Options

===== Music School Front Desk =====
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
q. Quit

## Warning ##
1. Admin Authentication (Option 4,5,6,7,8)
   To access these functions, you must authenticate as an admin:
   Password is hardcoded for now （password: 123）

Created by [ZouZixuan]. Thanks for veiwing!!!
