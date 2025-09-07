from app.user import User

class StudentUser(User):
    def __init__(self, id, name, enrolled_course_ids=None, **kwargs):
        super().__init__(id, name)
        self.enrolled_course_ids = enrolled_course_ids if enrolled_course_ids is not None else []

    def __repr__(self):
        return f"<Student {self.id}: {self.name}, Enrolled in {self.enrolled_course_ids}>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "enrolled_course_ids": self.enrolled_course_ids
        }