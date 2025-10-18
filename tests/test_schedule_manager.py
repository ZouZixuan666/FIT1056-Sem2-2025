# tests/test_schedule_manager.py
import pytest
import os
from app.schedule import ScheduleManager

@pytest.fixture
def fresh_manager():
    """Creates a fresh ScheduleManager instance using a temporary test data file."""
    test_file = "test_data.json"
    if os.path.exists(test_file):
        os.remove(test_file)
    return ScheduleManager(data_path=test_file)

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
