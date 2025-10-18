# tests/test_schedule_manager.py
import pytest
import os

from app.schedule import ScheduleManager

@pytest.fixture
def fresh_manager(tmp_path):
    """Creates a fresh ScheduleManager instance using a temporary test data file."""
    test_file = tmp_path /"test_data.json"
    if os.path.exists(test_file):
        os.remove(test_file)
    return ScheduleManager(data_path=str(test_file))

def test_add_course(fresh_manager):
    """Test that a new course can be added correctly."""
    # ARRANGE
    teacher = type("DummyTeacher", (), {"id": 1, "name": "Test Teacher", "speciality": "Piano"})()
    fresh_manager.teachers.append(teacher)

    # ACT
    course = fresh_manager.add_course("Beginner Piano", "Piano", 1)

    # ASSERT
    assert len(fresh_manager.courses) == 1
    assert course.name == "Beginner Piano"
    assert course.instrument == "Piano"

def test_record_payment_and_history(fresh_manager):
    """Test recording and retrieving a payment."""
    # ARRANGE
    student = fresh_manager.register_student("Alice")
    student_id = student.id

    # ACT
    fresh_manager.record_payment(student_id, 100.00, "Credit Card")

    # ASSERT
    history = fresh_manager.get_payment_history(student_id)
    assert len(history) == 1
    assert history[0]["amount"] == 100.00
    assert history[0]["method"] == "Credit Card"

def test_get_payment_history_no_results(fresh_manager):
    """Test that a student with no payments returns an empty list."""
    # ARRANGE
    student = fresh_manager.register_student("Bob")

    # ACT
    history = fresh_manager.get_payment_history(student.id)

    # ASSERT
    assert isinstance(history, list)
    assert len(history) == 0
    
# CORE FUNCTIONALITY
# -------------------------------

def test_register_and_find_student(fresh_manager):
    student = fresh_manager.register_student("Alice")
    assert student.name == "Alice"
    assert fresh_manager.find_student_by_id(student.id) == student

def test_add_teacher_and_list(fresh_manager):
    teacher = fresh_manager.add_teacher("John", "Guitar")
    assert teacher.name == "John"
    assert teacher.speciality == "Guitar"
    assert len(fresh_manager.list_teachers()) == 1

def test_remove_teacher(fresh_manager):
    t = fresh_manager.add_teacher("Paul", "Drums")
    assert fresh_manager.remove_teacher(t.id) is True
    assert len(fresh_manager.teachers) == 0

def test_update_teacher(fresh_manager):
    t = fresh_manager.add_teacher("Tom", "Violin")
    updated = fresh_manager.update_teacher(t.id, speciality="Piano")
    assert updated is True
    assert t.speciality == "Piano"

def test_add_course_and_list(fresh_manager):
    teacher = fresh_manager.add_teacher("Amy", "Piano")
    course = fresh_manager.add_course("Intro Piano", "Piano", teacher.id)
    assert course.name == "Intro Piano"
    assert len(fresh_manager.list_courses()) == 1

def test_find_course_by_id(fresh_manager):
    teacher = fresh_manager.add_teacher("Steve", "Drums")
    course = fresh_manager.add_course("Percussion", "Drums", teacher.id)
    assert fresh_manager.find_course_by_id(course.id) == course

def test_register_and_remove_student(fresh_manager):
    s = fresh_manager.register_student("Charlie")
    assert len(fresh_manager.students) == 1
    assert fresh_manager.remove_student(s.id) is True
    assert len(fresh_manager.students) == 0

def test_update_student_name(fresh_manager):
    s = fresh_manager.register_student("Bob")
    updated = fresh_manager.update_student(s.id, name="Bobby")
    assert updated is True
    assert s.name == "Bobby"

def test_lookup_students_and_teachers(fresh_manager):
    fresh_manager.register_student("Jane")
    fresh_manager.add_teacher("Janet", "Piano")
    students, teachers = fresh_manager.lookup("jan")
    assert len(students) == 1
    assert len(teachers) == 1
    
# FINANCE & REPORTING

def test_record_payment_and_get_history(fresh_manager):
    s = fresh_manager.register_student("Diana")
    fresh_manager.record_payment(s.id, 150, "Cash")
    history = fresh_manager.get_payment_history(s.id)
    assert len(history) == 1
    assert history[0]["amount"] == 150

def test_export_finance_report(fresh_manager, tmp_path):
    s = fresh_manager.register_student("Eli")
    fresh_manager.record_payment(s.id, 200, "Credit Card")
    csv_path = tmp_path / "finance_report.csv"
    fresh_manager.export_report("finance", csv_path)
    assert csv_path.exists()
    with open(csv_path, "r") as f:
        content = f.read()
    assert "student_id" in content
        
# ATTENDANCE

def test_check_in_and_show_attendance(fresh_manager):
    teacher = fresh_manager.add_teacher("Mark", "Flute")
    course = fresh_manager.add_course("Flute Basics", "Flute", teacher.id)
    student = fresh_manager.register_student("Sally")
    fresh_manager.enrol_existing_student(student.id, course.id)

    result = fresh_manager.check_in(student.id, course.id)
    assert result["status"] == "ok"

    results = fresh_manager.show_attendance(student_id=student.id)
    assert len(results) == 1
    assert results[0]["student_id"] == student.id

def test_check_in_duplicate_same_day(fresh_manager):
    teacher = fresh_manager.add_teacher("Jim", "Saxophone")
    course = fresh_manager.add_course("Jazz 101", "Saxophone", teacher.id)
    student = fresh_manager.register_student("Ron")
    fresh_manager.enrol_existing_student(student.id, course.id)

    first = fresh_manager.check_in(student.id, course.id)
    second = fresh_manager.check_in(student.id, course.id)
    assert first["status"] == "ok"
    assert second["status"] == "duplicate"    
    
# COURSE MANAGEMENT

def test_switch_student_course(fresh_manager):
    teacher = fresh_manager.add_teacher("Leo", "Drums")
    c1 = fresh_manager.add_course("Rock Drums", "Drums", teacher.id)
    c2 = fresh_manager.add_course("Jazz Drums", "Drums", teacher.id)
    student = fresh_manager.register_student("Nina")
    fresh_manager.enrol_existing_student(student.id, c1.id)

    switched = fresh_manager.switch_student_course(student.id, c1.id, c2.id)
    assert switched is True
    assert c1.id not in student.enrolled_course_ids
    assert c2.id in student.enrolled_course_ids

def test_get_lessons_by_day(fresh_manager):
    teacher = fresh_manager.add_teacher("Tina", "Guitar")
    course = fresh_manager.add_course("Guitar 101", "Guitar", teacher.id)
    course.lessons.append({"day": "Monday", "time": "9AM"})
    lessons = fresh_manager.get_lessons_by_day("monday")
    assert len(lessons) == 1
    assert lessons[0]["day"].lower() == "monday"
        
# FILE MANAGEMENT
def test_print_student_card_creates_file(fresh_manager):
    student = fresh_manager.register_student("Kevin")
    filename = fresh_manager.print_student_card(student.id)
    assert os.path.exists(filename)
    with open(filename, "r") as f:
        content = f.read()
    assert "MUSIC SCHOOL ID BADGE" in content
    os.remove(filename)

def test_clear_local_files_removes_json(fresh_manager):
    fresh_manager._save_data()
    assert os.path.exists(fresh_manager.data_path)
    fresh_manager.clear_local_files()
    assert not os.path.exists(fresh_manager.data_path)