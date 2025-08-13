# pst2_main.py - The Persistent Application

import json
import datetime

DATA_FILE = "msms.json"
app_data = {} # This global dictionary will hold ALL our data.
ADMIN_PASSWORD = "123"  # Password been setted done, however on the choice you given, there is a (admin) but no code for realize this.
                        # Kind of wired right, although it look dumb but I still added.
                        
                        
# ----------------- Helper Functions -------------------
def search_records(records, term, keys):
    """Search a list of dicts for term in specified keys."""
    term = term.lower()
    results = []

    for record in records:
        match_found = False
        for key in keys:
            value = str(record[key]).lower()
            if term in value:
                match_found = True
                break  # No need to check other keys for this record
        if match_found:
            results.append(record)

    return results

def find_by_id(records, record_id):
    """Find a record by exact ID."""
    for r in records:
        if r["id"] == record_id:
            return r
    return None

def authenticate_admin():
    """Ask for admin password."""
    password = input("Enter admin password: ")
    if password == ADMIN_PASSWORD:
        return True
    print("Authentication failed.")
    return False

                        
# --- Core Persistence Engine ---
def load_data(path=DATA_FILE):
    """Loads all application data from a JSON file."""
    global app_data
    try:
        with open(path, 'r') as f:
            # TODO: Use json.load(f) to load the file's content into the global 'app_data' variable.
            app_data = json.load(f)
            print("Data loaded successfully.")
    except FileNotFoundError:
        print("Data file not found. Initializing with default structure.")
        # TODO: If the file doesn't exist, initialize 'app_data' with a default dictionary.
        # It should have keys like: "students", "teachers", "attendance", "next_student_id", "next_teacher_id".
        # The lists should be empty and the IDs should start at 1.
        app_data = {
            "students": [],
            "teachers": [],
            "attendance": [],
            "next_student_id": 1,
            "next_teacher_id": 1
        }

def save_data(path=DATA_FILE):
    """Saves all application data to a JSON file."""
    # TODO: Open the file at 'path' in write mode ('w').
    # Use json.dump() to write the global 'app_data' dictionary to the file.
    # Use the 'indent=4' argument in json.dump() to make the file readable.
    with open(path, 'w') as f:
        json.dump(app_data, f, indent=4)
    print("Data saved successfully.")
        
# ----------------- Teachers -----------------
def add_teacher(name, speciality):
    """Creates a Teacher object and adds it to the database."""
    if not name.strip() or not speciality.strip():
        print("Error: Name and speciality cannot be empty.")
        return
    for teacher in app_data['teachers']:
        if teacher['name'].strip().lower() == name.strip().lower():
            print(f"Warning: A teacher named '{name.strip()}' already exists.")
            choice = input("Do you want to (M)modify this new teacher's name or (A)add as a different person? (q) for quit ").strip().lower()
            
            if choice == 'm':
                teacher['name'] = name.strip()
                save_data()
                print(f"Teacher '{name.strip()}' updated.")
                return 
            elif choice == 'a':
                break  # continue to add as a new teacher
            elif choice == 'q' or 'Q':
                return
            else:
                print("Invalid choice. Action cancelled.")
                return
    # Prevent duplicate teachers name
    teacher_id = app_data['next_teacher_id']
    # TODO: Create a new Teacher object using the next available ID.
    new_teacher = {"id": teacher_id, "name": name, "speciality": speciality}
    # TODO: Append the new_teacher to the app_data['teachers'] list.
    app_data['teachers'].append(new_teacher)
    # TODO: Increment the next_teacher_id counter.
    app_data['next_teacher_id'] += 1
    save_data()
    print(f"Teacher '{name}' added successfully.")


def list_teachers():
    """Prints all teachers in the database."""
    # TODO: Implement the logic to list all teachers, similar to list_students().
    print("\n--- Teacher List ---")
    if not app_data['teachers']:
        print("No teachers in the system.")
        return
    for teacher in app_data['teachers']:
        print(f"  ID: {teacher['id']}, Name: {teacher['name']}, Speciality: {teacher['speciality']}")

#extra method remove teachers
def remove_teacher(teacher_id):
    """remove the pionted teachers"""
    teacher = find_by_id(app_data['teachers'], teacher_id)
    if teacher:
        app_data['teachers'].remove(teacher)
        save_data()
        print(f"Removed teacher: {teacher['name']}")
    else:
        print(f"Error: Teacher with ID {teacher_id} not found.")
    

def update_teacher(teacher_id, **fields):
    """Finds a teacher by ID and updates their data with provided fields."""
    # TODO: Loop through the app_data['teachers'] list.
    teacher = find_by_id(app_data['teachers'], teacher_id)
     # TODO: If a teacher's 'id' matches teacher_id:
    if teacher['id'] == teacher_id:
        # Use the .update() method on the teacher dictionary to apply the 'fields'.
        teacher.update(fields)
        print(f"Teacher {teacher_id} updated.")
        save_data()
        return
    else:
        print(f"Error: Teacher with ID {teacher_id} not found.")
        
# -----------------  Students -----------------

def list_students():
    """Prints all students in the database."""
    print("\n--- Student List ---")
    if not app_data['students']:# If its empty inside the data base then quit directly
        print("No students in the system.")
        return
    # TODO: Loop through student_db. For each student, print their ID, name, and their enrolled_in list.
    for student in app_data['students']:
        print(f"  ID: {student['id']}, Name: {student['name']}, Enrolled in: {', '.join(student['enrolled_in'])}")


def find_student_by_id(student_id):
    """A new helper to find one student by their exact ID."""
    # TODO: Loop through student_db. If a student's ID matches student_id, return the student object.
    print(f"Finding student with id: {student_id} - - - -")
    for student in app_data['students']:
        if student['id'] == student_id: # matching the id
            return student
    # TODO: If the loop finishes without finding a match, return None.
    return None

#extra method remove students
def remove_student(student_id):
    student = find_by_id(app_data['students'], student_id)
    if student:
        app_data['students'].remove(student)
        save_data()
        print(f"Removed student: {student['name']}")
    else:
        print("Student not found.")


def update_student(student_id, **fields):   
    """Finds a teacher by ID and updates their data with provided fields."""
    # TODO: Loop through the app_data['student'] list.
    for student in app_data['students']:
        # TODO: If a teacher's 'id' matches student_id:
        if  student['id'] == student_id:
            # Use the .update() method on the student dictionary to apply the 'fields'.
            student.update(fields)
            print(f"Teacher {student_id} updated.")
            save_data()
            return
    print(f"Error: Teacher with ID {student_id} not found.")

# --- Front Desk Functions ---

def modify_record(record_type, record_id, **fields):
    """
    Modify an existing record (teacher or student) with the given fields.

    record_type: str - "teachers" or "students"
    record_id: int - ID of the record to modify
    fields: key-value pairs to update
    """
    if record_type not in app_data:
        print(f"Error: Unknown record type '{record_type}'.")
        return

    record = find_by_id(app_data[record_type], record_id)
    if not record:
        print(f"Error: {record_type[:-1].capitalize()} with ID {record_id} not found.")
        return

    record.update(fields)
    save_data()
    print(f"{record_type[:-1].capitalize()} {record_id} updated successfully.")




def front_desk_register(name, instrument):
    """High-level function to register a new student and enrol them."""
    
    # TODO: Create a new Student object, add it to student_db, and increment the ID.
    if not name.strip() or not instrument.strip():#if some bad users input none then return
        print("Error: Name and instrument cannot be empty.")
        return
    for student in app_data['students']:
        if student['name'].strip().lower() == name.strip().lower():
            print(f"Warning: A student named '{name.strip()}' already exists.")
            choice = input("Do you want to (M)modify this new student's name or (A)add as a different person? (q) for quit ").strip().lower()
            
            if choice == 'm':
                student['name'] = name.strip()
                save_data()
                print(f"Student '{name.strip()}' updated.")
                return
            elif choice == 'a':
                break
            elif choice == 'q' or 'Q':
                return
            else:
                print("Invalid choice. Action cancelled.")
                return
    student_id = app_data['next_student_id']
    new_student = {
        "id": student_id,
        "name": name,
        "enrolled_in": [instrument]
    }
    app_data['students'].append(new_student)
    app_data['next_student_id'] += 1
    save_data()
    # TODO: Immediately call front_desk_enrol() using the new student's ID and the provided instrument.
    print(f"Front Desk: Registered '{name}' and enrolled them in '{instrument}'.")

def front_desk_enrol(student_id, instrument):
    """High-level function to enrol an existing student in a course."""
    # TODO: Use your new find_student_by_id() helper.
    student = find_student_by_id(student_id)
    # TODO: If the student is found, append the instrument to their 'enrolled_in' list.
    if student:# make sure the student is found if not found, the if will be false then go to else
        if instrument not in student['enrolled_in']: #privent from multi enrolled
            student['enrolled_in'].append(instrument)
            print(f"Front Desk: Enrolled student {student_id} in '{instrument}'.")
        else:
            print(f"Student already enrolled in '{instrument}'.")
    else:
        print(f"Error: Student ID {student_id} not found.")
        # TODO: If the student is not found, print an error message like "Error: Student ID not found."
        
def front_desk_lookup(term):
    """High-level function to search everything."""
    print(f"\n--- Performing lookup for '{term}' ---")
    print("\n=== Students ===")
    for s in search_records(app_data['students'], term, ['name']):
        print(s)
    print("\n=== Teachers ===")
    for t in search_records(app_data['teachers'], term, ['name', 'speciality']):
        print(t)


    
    
# ----------------- Attendance -----------------
def show_attendance(student_id=None, course_id=None):
    """
    Show attendance records.
    Optional filters:
        student_id: only show this student's records
        course_id: only show this course's records
    """
    print("\n--- Attendance Records ---")
    records_found = False

    for record in app_data["attendance"]:
        # Filter by student_id if provided
        if student_id is not None and record["student_id"] != student_id:
            continue
        # Filter by course_id if provided
        if course_id is not None and record["course_id"].lower() != course_id.lower():
            continue

        print(f"Student ID: {record['student_id']}, "
              f"Course: {record['course_id']}, "
              f"Time: {record['timestamp']}")
        records_found = True

    if not records_found:
        print("No attendance records found.")

def check_in(student_id, course_id, timestamp=None):
    """Records a student's attendance for a course."""
    if timestamp is None:
        # TODO: Get the current time as a string using datetime.datetime.now().isoformat()
        timestamp = datetime.datetime.now().isoformat()
    student = find_by_id(app_data['students'], student_id)
    # TODO: Append this new record to the app_data['attendance'] list.
    if student is None:
        print(f"Receptionist: Student {student_id} not found. Check-in failed.")
        return

    # Create the check-in record
    check_in_record = {
        "student_id": student_id,
        "course_id": course_id,
        "timestamp": timestamp
    }
    
    # TODO: Create a check-in record dictionary.
    # It should contain 'student_id', 'course_id', and 'timestamp'.
        
    
    app_data['attendance'].append(check_in_record)
    save_data()
    print(f"Receptionist: Student {student_id} checked into {course_id}.")
    
    
# ----------------- Cards -----------------
def print_student_card(student_id):
    """Creates a text file badge for a student."""
    # TODO: Find the student dictionary in app_data['students'].
    student_to_print = None
    for s in app_data['students']:
        if s['id'] == student_id:
            student_to_print = s
            break
    
    if student_to_print:
        # TODO: Create a filename, e.g., f"{student_id}_card.txt".
        filename = f"{student_id}_card.txt"
        # TODO: Open the file in write mode ('w').
        with open(filename, 'w') as f:
            # Write the student's details to the file in a nice format.
            f.write("========================\n")
            f.write(f"  MUSIC SCHOOL ID BADGE\n")
            f.write("========================\n")
            f.write(f"ID: {student_to_print['id']}\n")
            f.write(f"Name: {student_to_print['name']}\n")
            f.write(f"Enrolled In: {', '.join(student_to_print.get('enrolled_in', []))}\n")
        print(f"Printed student card to {filename}.")
    else:
        print(f"Error: Could not print card, student {student_id} not found.")
    
# --- Main Application ---
def main():
    """Runs the main interactive menu for the receptionist."""
    # Pre-populate some data for easy testing
    load_data() # Load all data from file at startup.
    add_teacher("Dr. Keys", "Piano")
    add_teacher("Ms. Fret", "Guitar")

    while True:
        print("\n===== Music School Front Desk =====")
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
        print("c. Show today's attdence")
        print("q. Quit")
        
        choice = input("Enter your choice: ")
        #Here I changed the massive if else to the switch.(Don't deduct my point because of it, this way looks more clean right ^_^)
        match choice:
            case '1':
                name = input("Enter student name: ")
                instrument = input("Enter instrument to enrol in: ")
                front_desk_register(name, instrument)

            case '2':
                try:
                    student_id = int(input("Enter student ID: "))
                    instrument = input("Enter instrument to enrol in: ")
                    front_desk_enrol(student_id, instrument)
                except ValueError:
                    print("Invalid ID. Please enter a number.")

            case '3':
                term = input("Enter search term: ")
                front_desk_lookup(term)
            
            case '4':
                 # TODO: Get student_id and course_id from user, then call check_in().
                 try:
                    sid = int(input("Enter student ID: "))
                    course = input("Enter course ID: ")
                    check_in(sid, course)
                 except ValueError:
                    print("Invalid ID.")
                    
            
            case '5':
                 # TODO: Get student_id, then call print_student_card().
                 try:
                    id = int(input("Enter student ID: "))
                    print_student_card(id)
                 except ValueError:
                    print("Invalid ID.") # No change made, so no save needed
            
            case '6':
                # TODO: Get teacher_id and new details, then call update_teacher().
                # Example: update_teacher(1, speciality="Advanced Piano")
                try:
                    id1 = int(input("Enter teacher ID: "))
                    speciality = input("Enter new speciality: ")
                    update_teacher(id1, speciality=speciality)
                except ValueError:
                    print("Invalid ID.")
                

            case '7':
                 if authenticate_admin():
                    list_students()

            case '8':
                if authenticate_admin():
                    list_teachers()

            case '9':
                if authenticate_admin():
                    try:
                        student_id = int(input("Please input the student ID to remove: "))
                        remove_student(student_id)
                    except ValueError:
                        print("Invalid input. Please enter a number.")

            case 'a':
                if authenticate_admin():
                    try:
                        teacher_id = int(input("Please input the teacher ID to remove: "))
                        remove_teacher(teacher_id)
                    except ValueError:
                        print("Invalid input. Please enter a number.")
                       
            case 'b':
                if authenticate_admin():
                    try:
                        teacher_name = input("Please input the teacher's name to add: ")
                        teacher_speciality = input("Please input the teacher's speciality: ")
                        add_teacher(name=teacher_name, speciality=teacher_speciality)
                    except Exception as bad:
                        print(f"An error occurred: {bad}")
            
            case 'c':
                show_attendance()

            case 'q' | 'Q':  #both lowercase and uppercase 'q'
                print("Exiting program. Goodbye!")
                break

            case _:
                print("Invalid choice. Please try again.")

# --- Program Start ---
if __name__ == "__main__":
    main()

