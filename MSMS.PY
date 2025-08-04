# --- Data Models ---
class Student:
    """A blueprint for student objects. Holds their info."""
    def __init__(self, student_id, name):
        self.id = student_id
        self.name = name
        # Initialize an empty list called 'enrolled_in' to store instrument names.DONE
        self.enrolled_in = []
        

class Teacher:
    """A blueprint for teacher objects."""
    def __init__(self, teacher_id, name, speciality):
        #Assign all three parameters (teacher_id, name, speciality)DONE
        self.id = teacher_id
        self.name = name
        self.speciality = speciality
        
# --- Core Helper Functions ---
def add_teacher(name, speciality):
    """Creates a Teacher object and adds it to the database."""
    global next_teacher_id
    # TODO: Create a new Teacher object using the next available ID.
    new_teacher = Teacher(next_teacher_id, name, speciality)
    # TODO: Append the new_teacher to the teacher_db list.
    teacher_db.append(new_teacher)
    # TODO: Increment the next_teacher_id counter.
    next_teacher_id += 1
    print(f"Core: Teacher '{name}' added successfully.")

def list_students():
    """Prints all students in the database."""
    print("\n--- Student List ---")
    if not student_db:
        print("No students in the system.")
        return
    # TODO: Loop through student_db. For each student, print their ID, name, and their enrolled_in list.
    for student in student_db:
        print(f"  ID: {student.id}, Name: {student.name}, Enrolled in: {student.enrolled_in}")

def list_teachers():
    """Prints all teachers in the database."""
    # TODO: Implement the logic to list all teachers, similar to list_students().
    print("\n--- Teacher List ---")
    for teacher in teacher_db:
        print(f"  ID: {teacher.id}, Name: {teacher.name}, Speciality: {teacher.speciality}")

def find_students(term):
    """Finds students by name."""
    print(f"\n--- Finding Students matching '{term}' ---")
    # TODO: Create an empty list to store results.
    # Loop through student_db. If the search 'term' (case-insensitive) is in the student's name,
    # add them to your results list.
    # After the loop, if the results list is empty, print "No match found."
    # Otherwise, print the details for each student in the results list.
    pass

def find_teachers(term):
    """Finds teachers by name or speciality."""
    # TODO: Implement this function similar to find_students, but check
    # for the term in BOTH the teacher's name AND their speciality.
    pass

# --- In-Memory Databases ---
#Create the global data stores.DONE
student_db = []
teacher_db = []
next_student_id = 1
next_teacher_id = 1