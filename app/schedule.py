import os
import datetime
import glob
import json
from app.student import StudentUser
from app.teacher import TeacherUser, Course

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")  # points to BASE_DIR/data
DATA_FILE = os.path.join(DATA_DIR, "msms.json")  # points to BASE_DIR/data/msms.json 

class ScheduleManager:
    """The main controller for all business logic and data handling."""
    def __init__(self, data_path=DATA_FILE):
        self.data_path = data_path
        self.students = []
        self.teachers = []
        self.courses = []
        # TODO: Initialize the new attendance_log attribute as an empty list.
        self.attendance_log = []
        self.next_student_id = 1
        self.next_teacher_id = 1
        self.next_course_id = 1
        # ... (next_id counters) ...
        self._load_data()

    def _load_data(self):
        """Loads data from the JSON file and populates the object lists."""
        try:
            with open(self.data_path, 'r') as f:
                data = json.load(f)
                # TODO: Load students, teachers, and courses as before.
                # ...

                # TODO: Correctly load the attendance log.
                # Use .get() with a default empty list to prevent errors if the key doesn't exist.
                self.students = [StudentUser(**s) for s in data.get("students", [])]
                self.teachers = [TeacherUser(**t) for t in data.get("teachers", [])]
                self.courses = [Course(**c) for c in data.get("courses", [])]
                self.attendance_log = data.get("attendance", [])
                if self.students:
                    self.next_student_id = max(s.id for s in self.students) + 1
                if self.teachers:
                    self.next_teacher_id = max(t.id for t in self.teachers) + 1
                if self.courses:
                    self.next_course_id = max(c.id for c in self.courses) + 1
                
        except FileNotFoundError:
            print("Data file not found. Starting with a clean state.")
    
    def _save_data(self):
        """Converts object lists back to dictionaries and saves to JSON."""
        # TODO: Create a 'data_to_save' dictionary.
        data_to_save = {
            "students": [s.__dict__ for s in self.students],
            "teachers": [t.__dict__ for t in self.teachers],
            "courses": [c.__dict__ for c in self.courses],
            # TODO: Add the attendance_log to the dictionary to be saved.
            # Since it's already a list of dicts, no conversion is needed.
            "next_student_id": self.next_student_id,
            "next_teacher_id": self.next_teacher_id,
            "next_course_id": self.next_course_id,
            "attendance": self.attendance_log,
            # ... (next_id counters) ...
        }
        # TODO: Write 'data_to_save' to the JSON file.
        with open(self.data_path, 'w') as f:
            json.dump(data_to_save, f, indent=4)
     
    def clear_local_files(self):
        
        """Deletes all program-generated local files (msms.json and student cards) inside pst2 folder."""
        files_deleted = 0

    # Delete msms.json if it exists

        if os.path.exists(self.data_path):
            os.remove(self.data_path)
            files_deleted += 1
            print(f"Deleted {self.data_path}")

    # Delete all student card files (*.txt with _card naming) inside pst2
        for file_path in glob.glob(os.path.join(BASE_DIR, "*_card.txt")):
            os.remove(file_path)
            files_deleted += 1
            print(f"Deleted {file_path}")

        if files_deleted == 0:
            print("No local files found to delete.")
        else:
            print(f"Total files deleted: {files_deleted}")        
 # ----------------- Teachers -----------------
    def add_teacher(self, name, speciality):
        if not name.strip() or not speciality.strip():
            return None
        # prevent duplicates
        for t in self.teachers:
            if t.name.lower() == name.strip().lower():
                return None
        teacher = TeacherUser(self.next_teacher_id, name.strip(), speciality.strip())
        self.teachers.append(teacher)
        self.next_teacher_id += 1
        self._save_data()
        return teacher

    def list_teachers(self):
        return self.teachers

    def remove_teacher(self, teacher_id):
        before = len(self.teachers)
        self.teachers = [t for t in self.teachers if t.id != teacher_id]
        if len(self.teachers) < before:
            self._save_data()
            return True
        return False

    def update_teacher(self, teacher_id, **fields):
        t = next((t for t in self.teachers if t.id == teacher_id), None)
        if not t:
            return False
        if "speciality" in fields:
            t.speciality = fields["speciality"]
        if "name" in fields:
            t.name = fields["name"]
        self._save_data()
        return True

    # ----------------- Students -----------------
    def register_student(self, name: str) -> StudentUser:
        """Create a new student (no enrolment)."""
        if not name.strip():
            return None
        student = StudentUser(self.next_student_id, name.strip())
        self.students.append(student)
        self.next_student_id += 1
        self._save_data()
        return student

    def enrol_student(self, name: str, course_id: int):
        student = self.register_student(name)  # just creates student profile
        course = self.find_course_by_id(course_id)
        if student and course:
            student.enrolled_course_ids.append(course_id)
            course.enrolled_student_ids.append(student.id)
            self._save_data()
        return student

    def enrol_existing_student(self, student_id: int, course_id: int) -> bool:
        """Enrol an existing student in a new course by ID."""
        student = self.find_student_by_id(student_id)
        course = self.find_course_by_id(course_id)
        if not student or not course:
            return False
        if course_id not in student.enrolled_course_ids:
            student.enrolled_course_ids.append(course_id)
        if student_id not in course.enrolled_student_ids:
            course.enrolled_student_ids.append(student_id)
        self._save_data()
        return True

    def list_students(self):
        return self.students

    def remove_student(self, student_id):
        before = len(self.students)
        self.students = [s for s in self.students if s.id != student_id]
        if len(self.students) < before:
            self._save_data()
            return True
        return False

    def update_student(self, student_id, **fields):
        s = self.find_student(student_id)
        if not s:
            return False
        if "name" in fields:
            s.name = fields["name"]
        if "enrolled_course_ids" in fields:
            s.enrolled_course_ids = fields["enrolled_course_ids"]
        self._save_data()
        return True

    def find_student(self, student_id):
        return next((s for s in self.students if s.id == student_id), None)

    # ----------------- Lookup -----------------
    def lookup(self, term):
        term = term.lower()
        students = [s for s in self.students if term in s.name.lower()]
        teachers = [t for t in self.teachers if term in t.name.lower() or term in t.speciality.lower()]
        return students, teachers

    # ----------------- Attendance -----------------
    def check_in(self, student_id, course_id):
        ts = datetime.datetime.now().isoformat()
        if not self.find_student(student_id):
            return None
        record = {"student_id": student_id, "course_id": course_id, "timestamp": ts}
        self.attendance_log.append(record)
        self._save_data()
        return record

    def show_attendance(self, student_id=None, course_id=None):
        results = []
        for record in self.attendance_log:
            if student_id and record["student_id"] != student_id:
                continue
            if course_id and record["course_id"].lower() != course_id.lower():
                continue
            results.append(record)
        return results

    # ----------------- Cards -----------------
    def print_student_card(self, student_id):
        student = self.find_student(student_id)
        if not student:
            return None
        filename = f"{student_id}_card.txt"

        # Convert course IDs into names
        enrolled_names = []
        for cid in student.enrolled_course_ids:
            course = self.find_course_by_id(cid)
            enrolled_names.append(course.name if course else f"Course {cid}")

        with open(filename, "w") as f:
            f.write("========================\n")
            f.write("  MUSIC SCHOOL ID BADGE\n")
            f.write("========================\n")
            f.write(f"ID: {student.id}\n")
            f.write(f"Name: {student.name}\n")
            f.write(f"Enrolled In: {', '.join(enrolled_names)}\n")
        return filename

    #  Helper Methods
    def find_student_by_id(self, student_id: int) -> StudentUser | None:
        """Return a StudentUser by ID or None if not found."""
        for student in self.students:
            if student.id == student_id:
                return student
        return None
    
    def find_teacher_by_id(self, teacher_id: int):
        for teacher in self.teachers:
            if teacher.id == teacher_id:
                return teacher
        return None
    
    def find_course_by_id(self, course_id) -> Course | None:
        """Return a Course by ID (accepts str or int)."""
        try:
            course_id = int(course_id)
        except ValueError:
            return None
        for course in self.courses:
            if course.id == course_id:
                return course
        return None

    # Attendance
    def check_in(self, student_id: int, course_id: int) -> bool:
        """Records a student's attendance for a course after validation."""
        student = self.find_student_by_id(student_id)
        course = self.find_course_by_id(course_id)

        if not student or not course:
            print("Error: Check-in failed. Invalid Student or Course ID.")
            return False

        timestamp = datetime.datetime.now().isoformat()
        check_in_record = {
            "student_id": student_id,
            "course_id": course_id,
            "timestamp": timestamp
        }

        self.attendance_log.append(check_in_record)
        self._save_data()
        print(f"Success: Student {student.name} checked into {course.name}.")
        return True

    # Scheduling

    def get_lessons_by_day(self, day: str):
        lessons = []
        for course in self.courses:
            for lesson in course.lessons:
                if lesson["day"].lower() == day.lower():
                    lesson["course_id"] = course.id
                    lessons.append(lesson)
        return lessons

    def switch_student_course(self, student_id: int, from_course_id: int, to_course_id: int):
        from_course = self.find_course_by_id(from_course_id)
        to_course = self.find_course_by_id(to_course_id)
        student = self.find_student_by_id(student_id)

        if not from_course or not to_course or not student:
            print("Error: Invalid IDs for switch.")
            return False

        if student_id not in from_course.enrolled_student_ids:
            print(f"Error: Student {student_id} not enrolled in course {from_course_id}.")
            return False

        from_course.enrolled_student_ids.remove(student_id)
        if student_id not in to_course.enrolled_student_ids:
            to_course.enrolled_student_ids.append(student_id)

        if from_course_id in student.enrolled_course_ids:
            student.enrolled_course_ids.remove(from_course_id)
        if to_course_id not in student.enrolled_course_ids:
            student.enrolled_course_ids.append(to_course_id)

        self._save_data()
        return True
      # ----------------- Courses -----------------
    def list_courses(self):
        """Return all courses in the system."""
        return self.courses
    def add_course(self, name: str, instrument: str, teacher_id: int):
        # check teacher exists
        teacher = self.find_teacher_by_id(teacher_id)
        if not teacher:
            print(f"[ERROR] Teacher {teacher_id} not found.")
            return None

    # create a Course object instead of dict
        course = Course(
            id=self.next_course_id,
            name=name.strip(),
            instrument=instrument.strip(),
            teacher_id=teacher_id,
            enrolled_student_ids=[],
            lessons=[]
        )

        self.courses.append(course)
        self.next_course_id += 1
        self._save_data()
        return course