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
        


# --- In-Memory Databases ---
#Create the global data stores.DONE
student_db = []
teacher_db = []
next_student_id = 1
next_teacher_id = 1