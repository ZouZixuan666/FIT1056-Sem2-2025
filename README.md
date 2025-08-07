This is a application designed to simulate the front desk operations of a music school. 
It surpot registration of students and teachers, enrolment in instruments, listing, searching, and administrative operations like adding or removing records.

## Project Structure ##
  MSMS.py ---- take care of all the jobs.

## How to Run the Program ###

1. **Clone the repo:**
   
   bash
   
   git clone https://github.com/ZouZixuan666/FIT1056-Sem2-2025.git
   
   git switch individual
   
   Then run MSMS.py and feel free to test it on
   
## Main functions ##

Menu Options Option	Description

1	           Register a new student

2	           Enrol an existing student in an instrument

3	           Lookup a student by name or instrument

4            List all students (Admin only)

5	           List all teachers (Admin only)

6	           Remove a student by ID (Admin only)

7	           Remove a teacher by ID (Admin only)

8	           Add a teacher (Admin only)

Q/q	         Quit the program

(For more deatails, please go to the inter code comments)

## Warning ##
1. Admin Authentication (Option 4,5,6,7,8)
   To access these functions, you must authenticate as an admin:
   Password is hardcoded for now （password: 123）
2. For now this application is all In-Memory Storage.
   All data is stored in memory (student_db, teacher_db) for simplicity.
   Data is lost when the program ends.

Created by [ZouZixuan]. Thanks for veiwing!!!
