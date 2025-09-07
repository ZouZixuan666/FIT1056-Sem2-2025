from app.user import User

class TeacherUser(User):
    """Represents a teacher."""
    # TODO: Implement the TeacherUser class, inheriting from User.
    # It should have an additional 'speciality' attribute in its __init__.
    def __init__(self, id, name, speciality, **kwargs):
        super().__init__(id or id, name)
        self.speciality = speciality
    def __repr__(self):
        return f"<Teacher {self.id}: {self.name}, Speciality: {self.speciality}>"
class Course:
    """Represents a single course offered by the school, linked to a teacher."""
    def __init__(self, id, name, instrument, teacher_id,
                 enrolled_student_ids=None, lessons=None, **kwargs):
        self.id = id
        self.name = name
        self.instrument = instrument
        self.teacher_id = teacher_id
        self.enrolled_student_ids = enrolled_student_ids if enrolled_student_ids is not None else []
        self.lessons = lessons if lessons is not None else []
    def __repr__(self):
        return f"<Course {self.id}: {self.name} ({self.instrument}), Teacher {self.teacher_id}, Students {len(self.enrolled_student_ids)}>"