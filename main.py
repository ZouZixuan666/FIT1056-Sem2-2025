from app.schedule import ScheduleManager

import hashlib
def front_desk_daily_roster(manager, day):
    print(f"\n--- Daily Roster for {day} ---")
    lessons = manager.get_lessons_by_day(day)
    if not lessons:
        print("No lessons scheduled.")
        return
    for lesson in lessons:
        course = manager.find_course_by_id(lesson["course_id"])
        teacher = manager.find_teacher_by_id(course.teacher_id) if course else None
        print(f"Lesson {lesson['lesson_id']}: {course.name if course else 'Unknown Course'}")
        print(f"  Day/Time: {lesson['day']} {lesson['start_time']} in {lesson['room']}")
        print(f"  Teacher: {teacher.name if teacher else 'Unknown'}")
        print(f"  Students: {course.enrolled_student_ids if course else []}")
        print("-" * 40)


def switch_course(manager, student_id, from_course_id, to_course_id):
    success = manager.switch_student_course(student_id, from_course_id, to_course_id)
    if success:
        print(f"Student {student_id} switched from Course {from_course_id} to Course {to_course_id}.")
    else:
        print("Switch failed. Please check IDs and try again.")


ADMIN_PASSWORD_HASH = hashlib.sha256("123".encode()).hexdigest()
#hash the code
def authenticate_admin():
    password = input("Enter admin password: ")
    entered_hash = hashlib.sha256(password.encode()).hexdigest()
    return entered_hash == ADMIN_PASSWORD_HASH

def main():
    manager = ScheduleManager()

    while True:
        print("\n===== MSMS v3 (Object-Oriented) =====")
        print("1. Register New Student")
        print("2. Enrol Existing Student")
        print("3. Lookup Student or Teacher")
        print("4. Check-in Student")
        print("5. Print Student Card")
        print("6. Update Teacher Info")
        print("7. (Admin) List all Students")
        print("8. (Admin) List all Teachers")
        print("9. (Admin) Remove student")
        print("a. (Admin) Remove teacher")
        print("b. (Admin) Add teacher")
        print("c. Show attdence")
        print("d. Clear all the local files")
        print("e. Show Daily Roster")
        print("f. Switch Student Between Courses")
        print("g. add a course")
        print("h. （Admin）List all Courses")
        print("q. Quit")

        choice = input("Enter your choice: ").lower()
        match choice:
            case "1":
            # Just register profile
                name = input("Enter student name: ")
                s = manager.register_student(name)   # <-- profile only
                print("Registered:", s)

            case "2":
                # Enrol existing student into a course
                sid = int(input("Enter student ID: "))
                course_id = int(input("Enter course ID: "))
                if manager.enrol_existing_student(sid, course_id):
                    print("Enrolled successfully.")
                else:
                    print("Failed to enrol.")

            case "3":
                term = input("Search term: ")
                students, teachers = manager.lookup(term)
                print("=== Students ===")
                for s in students:
                    print(s.__dict__)
                print("=== Teachers ===")
                for t in teachers:
                    print(t.__dict__)

            case "4":
                sid = int(input("Student ID: "))
                course = input("Course: ")
                ts = manager.check_in(sid, course)
                print(f"Checked in at {ts}")

            case "5":
                sid = int(input("Student ID: "))
                filename = manager.print_student_card(sid)
                if filename:
                    print("Card saved to", filename)
                else:
                    print("Student not found.")

            case "6":
                tid = int(input("Teacher ID: "))
                speciality = input("New speciality: ")
                if manager.update_teacher(tid, speciality=speciality):
                    print("Teacher updated.")
                else:
                    print("Teacher not found.")

            case "7":
                if authenticate_admin():
                    for s in manager.list_students():
                        print(s.__dict__)

            case "8":
                if authenticate_admin():
                    for t in manager.list_teachers():
                        print(t.__dict__)

            case "9":
                if authenticate_admin():
                    sid = int(input("Student ID to remove: "))
                    manager.remove_student(sid)
                    print("Removed.")

            case "a":
                if authenticate_admin():
                    tid = int(input("Teacher ID to remove: "))
                    manager.remove_teacher(tid)
                    print("Removed.")

            case "b":
                if authenticate_admin():
                    name = input("Teacher name: ")
                    spec = input("Speciality: ")
                    t = manager.add_teacher(name, spec)
                    print("Added:", t.__dict__)

            case "c":
                records = manager.show_attendance()
                for r in records:
                    print(r)

            case "d":
                manager.clear_local_files()
                
            case "e":
                day = input("Enter day (e.g., Monday): ")
                front_desk_daily_roster(manager, day)
            
            case "f":
                try:
                    student_id = int(input("Enter student ID: "))
                    from_course_id = int(input("Enter FROM course ID: "))
                    to_course_id = int(input("Enter TO course ID: "))
                    switch_course(manager, student_id, from_course_id, to_course_id)
                except ValueError:
                    print("Invalid input. IDs must be numbers.")
            case "g":
                name = input("Enter course name: ")
                instrument = input("Enter instrument: ")
                teacher_id = int(input("Enter teacher ID: "))
                course = manager.add_course(name, instrument, teacher_id)
                if course:
                    print("Course added:", course)
            case "h":
                if authenticate_admin():
                    for c in manager.list_courses():
                        print(c.__dict__)
            case "q":
                print("Goodbye!")
                break
            
            
            
            case _:
                print("Invalid choice.")

if __name__ == "__main__":
    main()
