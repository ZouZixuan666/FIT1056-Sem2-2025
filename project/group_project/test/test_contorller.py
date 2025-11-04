import pytest
from unittest.mock import Mock, patch
from app.database.controller import Controller  
from app.users.patient import Patient
from app.users.staff import Staff
from app.users.preferences import Preferences
from app.core.validator import Validator
from unittest.mock import patch, MagicMock
from app.core import assignment_Store as Assignment


# Fixtures (only showing those that need changes or are used in fixed tests)
@pytest.fixture
def real_controller(mock_db, mock_patient_log, mock_report_generator, mock_search_engine, mock_user_store):
    """A controller fixture for tests that need the real log_action method."""
    ctrl = Controller(currentuser=mock_user_store)
    ctrl.db = mock_db
    ctrl.patient_log = mock_patient_log
    ctrl.report_generator = mock_report_generator
    ctrl.search_engine = mock_search_engine
    ctrl.current_user = Mock(userID="test_staff")
    return ctrl

@pytest.fixture
def mock_db():
    """Mock DatabaseManager instance."""
    mock = Mock()
    mock.patients = {}
    mock.staffs = {}
    mock.alerts = []
    # Mock common methods
    mock.get_patient.return_value = None
    mock.get_staff.return_value = None
    mock.get_preferences.return_value = None
    mock.get_alerts_for_staff.return_value = []
    mock.add_patient.return_value = None
    mock.add_staff.return_value = None
    mock.add_preferences.return_value = None
    mock.update_preferences.return_value = None
    mock.save_all.return_value = None
    mock.store_system_log.return_value = None
    mock.create_user.return_value = None
    mock.ensure_user.return_value = None
    mock.delete_user.return_value = True
    mock.get_user.return_value = None
    mock.get_all_users.return_value = []
    mock.verify_user.return_value = True
    mock.list_users_by_role.return_value = []
    mock.find_patient_id_by_name_exact.return_value = (None, None)
    return mock

@pytest.fixture
def mock_patient_log():
    mock = Mock()
    mock.get_logs.return_value = []
    mock.add_log.return_value = None
    mock.find_by_patient.return_value = []
    mock.find_by_staff.return_value = []
    mock.find_by_date.return_value = []
    mock.delete_log.return_value = None
    mock.find_patient_ids_by_note_keyword.return_value = []
    mock.filter_by_metric.return_value = []
    return mock


@pytest.fixture
def mock_report_generator(mock_db):
    mock = Mock()
    mock.db = mock_db
    mock.generate_patient_report.return_value = []
    mock.generate_multi_patient_report.return_value = []
    mock.export_report_to_file.return_value = None
    return mock


@pytest.fixture
def mock_search_engine(mock_db):
    mock = Mock()
    mock.db = mock_db
    mock.search_logs.return_value = []
    mock.refresh_index.return_value = None
    mock.highlight_matches.return_value = "highlighted text"
    mock.get_index_size.return_value = 0
    return mock


@pytest.fixture
def mock_user_store():
    mock = Mock()
    mock.get_user_by_id.return_value = Mock(userID="test_staff")
    return mock


@pytest.fixture
def controller(mock_db, mock_patient_log, mock_report_generator, mock_search_engine, mock_user_store):
    ctrl = Controller(currentuser=mock_user_store)
    ctrl.db = mock_db
    ctrl.patient_log = mock_patient_log
    ctrl.report_generator = mock_report_generator
    ctrl.search_engine = mock_search_engine
    ctrl.current_user = Mock(userID="test_staff")
    # Mock log_action as a method
    ctrl.log_action = Mock()
    return ctrl


class TestController:
    """Test suite for Controller class."""

    def test_init(self, controller):
        """Test Controller initialization."""
        assert controller.db is not None
        assert controller.patient_log is not None
        assert controller.report_generator is not None
        assert controller.search_engine is not None
        assert controller.current_user.userID == "test_staff"

    def test_refresh_current_user(self, controller, mock_user_store):
        """Test refreshing current user."""
        user_id = "test_user"
        mock_user = Mock(userID=user_id)
        mock_user_store.get_user_by_id.return_value = mock_user

        controller.refresh_current_user(user_id)

        mock_user_store.get_user_by_id.assert_called_once_with(user_id)
        assert controller.current_user == mock_user

    # PATIENT MANAGEMENT
    @patch.object(Validator, 'validate_patient_id')
    def test_register_patient(self, mock_validate_patient_id, controller, mock_db):
        """Test registering a new patient."""
        patient_data = {"patientID": "P001", "name": "John Doe", "condition": "Healthy"}
        mock_patient = Mock(patientID="P001")
        with patch.object(Patient, 'from_dict', return_value=mock_patient):
            with patch.object(controller, 'log_action') as mock_log_action:
                result = controller.register_patient(patient_data)

        mock_validate_patient_id.assert_called_once_with("P001")
        mock_db.add_patient.assert_called_once_with(mock_patient)
        mock_log_action.assert_called_once_with(
        controller.current_user.userID,
        f"Patient {mock_patient.patientID} registered by {controller.current_user.userID}."
    )
        assert result == mock_patient

    def test_get_patient(self, controller, mock_db):
        """Test retrieving a patient."""
        patient_id = "P001"
        mock_patient = Mock()
        mock_db.get_patient.return_value = mock_patient

        with patch.object(controller, 'log_action') as mock_log_action:
            result = controller.get_patient(patient_id)

        mock_db.get_patient.assert_called_once_with(patient_id)
        mock_log_action.assert_called_once_with(
        controller.current_user.userID,
        f"Request for patient ID:{patient_id} by {controller.current_user.userID}"
    )
        assert result == mock_patient

    def test_update_patient_info(self, controller, mock_db):
        """Test updating patient info."""
        patient_id = "P001"
        updates = {"name": "Jane Doe"}
        mock_patient = Mock()
        mock_db.get_patient.return_value = mock_patient

        with patch.object(controller, 'log_action') as mock_log_action:
            controller.update_patient_info(patient_id, updates)

        mock_db.get_patient.assert_called_once_with(patient_id)
        assert mock_patient.name == "Jane Doe"
        mock_db.save_all.assert_called_once()
        mock_log_action.assert_called_once_with(
        controller.current_user.userID,
        f"Patient info updated: {list(updates.keys())} by {controller.current_user.userID}"
    )

    # STAFF MANAGEMENT
    @patch.object(Validator, 'validate_staff_id')
    def test_register_staff(self, mock_validate_staff_id, controller, mock_db):
        """Test registering new staff."""
        staff_data = {"staffID": "S001", "name": "Dr. Smith"}
        mock_staff = Mock(staffID="S001")
        with patch.object(Staff, 'from_dict', return_value=mock_staff):
            with patch.object(controller, 'log_action') as mock_log_action:
                result = controller.register_staff(staff_data)

        mock_validate_staff_id.assert_called_once_with("S001")
        mock_db.add_staff.assert_called_once_with(mock_staff)
        mock_log_action.assert_called_once_with(
        controller.current_user.userID,
        f"Staff {mock_staff.staffID} registered by {controller.current_user.userID}."
    )
        assert result == mock_staff

    def test_get_staff(self, controller, mock_db):
        """Test retrieving staff."""
        staff_id = "S001"
        mock_staff = Mock()
        mock_db.get_staff.return_value = mock_staff

        with patch.object(controller, 'log_action') as mock_log_action:
            result = controller.get_staff(staff_id)

        mock_db.get_staff.assert_called_once_with(staff_id)
        mock_log_action.assert_called_once_with(
    controller.current_user.userID,
    f"Request for staff ID:{staff_id} by {controller.current_user.userID}"
)
        assert result == mock_staff

    # PREFERENCES MANAGEMENT
    def test_set_preferences(self, controller, mock_db):
        patient_id = "P001"
        pref_data = {"pref_key": "value"}
        mock_pref = Mock()
        with patch.object(Preferences, 'from_dict', return_value=mock_pref):
            result = controller.set_preferences(patient_id, pref_data)

        mock_db.add_preferences.assert_called_once_with(mock_pref)
        controller.log_action.assert_called_once_with(
    controller.current_user.userID,
    f"Preferences set/updated by {controller.current_user.userID}"
)
        assert result == mock_pref

    def test_edit_preferences(self, controller, mock_db):
        patient_id = "P001"
        updates = {"pref_key": "new_value"}

        controller.edit_preferences(patient_id, updates)

        mock_db.update_preferences.assert_called_once_with(patient_id, updates)
        controller.log_action.assert_called_once_with(
    controller.current_user.userID,
    f"Preferences edited: {list(updates.keys())} by {controller.current_user.userID}"
)
    def test_get_preferences(self, controller, mock_db):
        patient_id = "P001"
        mock_pref = Mock()
        mock_db.get_preferences.return_value = mock_pref

        result = controller.get_preferences(patient_id)

        mock_db.get_preferences.assert_called_once_with(patient_id)
        controller.log_action.assert_called_once_with(
    patient_id,
    f"Request for preference of ID:{patient_id} by {controller.current_user.userID}"
)
        assert result == mock_pref

    # ASSIGNMENT MANAGEMENT
    @patch('app.core.assignment_Store.assign')
    def test_assign_patient_to_staff(self, mock_assign, controller):
        patient_id = "P001"
        staff_id = "S001"
        admin_username = "admin"
        mock_assign.return_value = (True, "Assigned")

        # Mock actor_id to a known value
        controller._actor_id = MagicMock(return_value="test_staff")

        result = controller.assign_patient_to_staff(patient_id, staff_id, admin_username)

        mock_assign.assert_called_once_with(patient_id, staff_id, admin_username)
        controller.log_action.assert_called_once_with(
            admin_username,
            f"Assigned patient {patient_id} to staff test_staff"
        )


    @patch('app.core.assignment_Store.unassign')
    def test_unassign_patient_from_staff(self, mock_unassign, controller):
        patient_id = "P001"
        staff_id = "S001"
        admin_username = "admin"
        mock_unassign.return_value = (True, "Unassigned")

        controller._actor_id = MagicMock(return_value="test_staff")

        result = controller.unassign_patient_from_staff(patient_id, staff_id, admin_username)

        mock_unassign.assert_called_once_with(patient_id, staff_id, admin_username)
        controller.log_action.assert_called_once_with(
            admin_username,
            f"Unassigned patient {patient_id} from staff test_staff"
        )


    @patch('app.core.assignment_Store.replace_assignments')
    def test_replace_patient_staff(self, mock_replace, controller):
        patient_id = "P001"
        new_staff_id = "S002"
        admin_username = "admin"
        mock_replace.return_value = (True, "Replaced")

        controller._actor_id = MagicMock(return_value="test_staff")

        result = controller.replace_patient_staff(patient_id, new_staff_id, admin_username)

        mock_replace.assert_called_once_with(patient_id, new_staff_id, admin_username)
        controller.log_action.assert_called_once_with(
            admin_username,
            f"Reassigned patient {patient_id} to staff test_staff"
        )

    @patch('app.core.assignment_Store.patients_for_staff')
    def test_get_patients_for_staff(self, mock_patients_for_staff, controller):
        """Test getting patients for staff."""
        staff_id = "S001"
        expected = ["P001", "P002"]

        mock_patients_for_staff.return_value = expected

        result = controller.get_patients_for_staff(staff_id)

        mock_patients_for_staff.assert_called_once_with(staff_id)
        assert result == expected

    @patch('app.core.assignment_Store.staff_for_patient')
    def test_get_staff_for_patient(self, mock_staff_for_patient, controller):
        """Test getting staff for patient."""
        patient_id = "P001"
        expected = ["S001", "S002"]

        mock_staff_for_patient.return_value = expected

        result = controller.get_staff_for_patient(patient_id)

        mock_staff_for_patient.assert_called_once_with(patient_id)
        assert result == expected

    @patch('app.core.assignment_Store.is_allowed')
    def test_is_staff_allowed_for_patient(self, mock_is_allowed, controller):
        """Test checking staff allowance for patient."""
        staff_id = "S001"
        patient_id = "P001"
        expected = True

        mock_is_allowed.return_value = expected

        result = controller.is_staff_allowed_for_patient(staff_id, patient_id)

        mock_is_allowed.assert_called_once_with(staff_id, patient_id)
        assert result == expected

    # SEARCH OPERATIONS
    def test_search_logs(self, controller, mock_search_engine):
        """Test searching logs."""
        keyword = "fever"
        patient_id = "P001"
        start_date = "2023-01-01T00:00:00"
        end_date = "2023-01-02T23:59:59"
        expected = [Mock()]

        mock_search_engine.search_logs.return_value = expected

        result = controller.search_logs(keyword, patient_id, start_date, end_date)

        mock_search_engine.search_logs.assert_called_once_with(keyword, patient_id, (start_date, end_date))
        assert result == expected

    def test_refresh_log_index(self, controller, mock_search_engine):
        """Test refreshing log index."""
        expected_size = 100
        mock_search_engine.get_index_size.return_value = expected_size

        result = controller.refresh_log_index()

        mock_search_engine.refresh_index.assert_called_once()
        assert f"{expected_size}" in result

    def test_highlight_text(self, controller, mock_search_engine):
        """Test highlighting text."""
        text = "This is a test fever log."
        keyword = "fever"
        expected = "This is a test <highlight>fever</highlight> log."

        mock_search_engine.highlight_matches.return_value = expected

        result = controller.highlight_text(text, keyword)

        mock_search_engine.highlight_matches.assert_called_once_with(text, keyword)
        assert result == expected

   # LOG MANAGEMENT
    def test_add_patient_log(self, controller, mock_patient_log):
        """Test adding patient log."""
        patient_id = "P001"
        staff_id = "S001"
        temperature = 98.6
        heart_rate = 72
        blood_pressure = "120/80"
        notes = "Feeling well"
        expected_log_id = "L001"

        with patch('app.database.controller.LogEntry') as mock_log_entry, \
             patch('app.database.controller.datetime') as mock_datetime_module:
            mock_now = Mock()
            mock_datetime_module.datetime.now.return_value = mock_now
            mock_now.strftime.return_value = "2023-01-01 00:00:00"

            mock_log = Mock(logID=expected_log_id)
            mock_log.to_dict.return_value = {}
            mock_log_entry.return_value = mock_log

            result = controller.add_patient_log(patient_id, staff_id, temperature, heart_rate, blood_pressure, notes)

        mock_log_entry.assert_called_once_with(
            logID=f"L{len(controller.patient_log.get_logs()) + 1:03}",
            patientID=patient_id,
            staffID=staff_id,
            timestamp="2023-01-01 00:00:00",
            temperature=temperature,
            heartRate=heart_rate,
            bloodPressure=blood_pressure,
            notes=notes
        )
        mock_patient_log.add_log.assert_called_once_with(mock_log.to_dict.return_value)
        assert result == mock_log
        
    def test_log_action(self, real_controller, mock_db):
        """Test logging action."""
        user_id = "S001"
        action = "Test action"

        with patch('app.database.controller.SystemLog') as mock_system_log, \
            patch('app.database.controller.datetime') as mock_datetime_module:
            mock_now = Mock()
            mock_datetime_module.datetime.now.return_value = mock_now
            mock_now.isoformat.return_value = "2023-01-01T00:00:00"

            mock_entry = Mock()
            mock_system_log.return_value = mock_entry

            real_controller.log_action(user_id, action)

        mock_system_log.assert_called_once_with(
            logID=f"L{len(real_controller.patient_log.get_logs()) + 1:03}",
            userID=user_id,
            action=action,
            timestamp="2023-01-01T00:00:00"
        )
        mock_db.store_system_log.assert_called_once_with(mock_entry)
        
    def test_get_patient_logs(self, controller, mock_patient_log):
        """Test getting patient logs."""
        patient_id = "P001"
        expected = [Mock()]

        mock_patient_log.find_by_patient.return_value = expected

        result = controller.get_patient_logs(patient_id)

        mock_patient_log.find_by_patient.assert_called_once_with(patient_id)
        assert result == expected

    def test_find_by_staff(self, controller, mock_patient_log):
        """Test finding logs by staff."""
        staff_id = "S001"
        expected = [Mock()]

        mock_patient_log.find_by_staff.return_value = expected

        result = controller.find_by_staff(staff_id)

        mock_patient_log.find_by_staff.assert_called_once_with(staff_id)
        assert result == expected

    def test_find_by_date(self, controller, mock_patient_log):
        """Test finding logs by date."""
        start = "2023-01-01"
        end = "2023-01-02"
        expected = [Mock()]

        mock_patient_log.find_by_date.return_value = expected

        result = controller.find_by_date(start, end)

        mock_patient_log.find_by_date.assert_called_once_with(start, end)
        assert result == expected

    def test_delete_log(self, controller, mock_patient_log):
        """Test deleting log."""
        log_id = "L001"

        controller.delete_log(log_id)

        mock_patient_log.delete_log.assert_called_once_with(log_id)

    def test_filter_patients_by_condition(self, controller, mock_db):
        # Mock db.patients with proper patientID attributes
        mock_patient1 = Mock(patientID="P001", condition="fever")
        mock_patient2 = Mock(patientID="P002", condition="cold")
        mock_db.patients = {"P001": mock_patient1, "P002": mock_patient2}

        result = controller.filter_patients_by_condition("fever")

        assert result == ["P001"]
        assert "P002" not in result

    def test_filter_patients_by_metric(self, controller, mock_patient_log):
        """Test filtering patients by metric."""
        def comparison(value: float) -> bool:
            return value > 100

        expected = ["P001"]
        mock_patient_log.filter_by_metric.return_value = expected

        result = controller.filter_patients_by_metric("heartRate", comparison)

        mock_patient_log.filter_by_metric.assert_called_once_with("heartRate", comparison)
        assert result == expected

    # ALERTS
    def test_create_alert(self, controller, mock_db):
        """Test creating alert."""
        severity = "high"
        patient_id = "P001"
        staff_id = "S001"
        message = "High fever detected"

        with patch('app.database.controller.Alert') as mock_alert_class, \
             patch('app.database.controller.datetime') as mock_datetime_module, \
             patch.object(controller, 'log_action') as mock_log_action:
            mock_now = Mock()
            mock_datetime_module.datetime.now.return_value = mock_now
            mock_now.isoformat.return_value = "2023-01-01T00:00:00"

            mock_alert = Mock()
            mock_alert_class.return_value = mock_alert

            controller.create_alert(severity, patient_id, staff_id, message)

        mock_alert_class.assert_called_once_with(
            alertID=f"A{len(controller.db.alerts) + 1:03}",
            staffID=staff_id,
            message=message,
            patientID=patient_id,
            severity=severity,
            timestamp="2023-01-01T00:00:00"
        )
        mock_db.add_alert.assert_called_once_with(mock_alert)
        mock_log_action.assert_called_once_with(staff_id, f"Alert created: {message}")
        
    def test_get_staff_alerts(self, controller, mock_db):
        """Test getting staff alerts."""
        staff_id = "S001"
        expected = [Mock()]

        mock_db.get_alerts_for_staff.return_value = expected

        result = controller.get_staff_alerts(staff_id)

        mock_db.get_alerts_for_staff.assert_called_once_with(staff_id)
        assert result == expected

    # REPORT GENERATION
    def test_get_patient_report(self, controller, mock_report_generator):
        """Test getting patient report."""
        patient_id = "P001"
        expected = [{"data": "report"}]

        mock_report_generator.generate_patient_report.return_value = expected

        result = controller.get_patient_report(patient_id)

        mock_report_generator.generate_patient_report.assert_called_once_with(patient_id)
        assert result == expected

    def test_get_multi_patient_report(self, controller, mock_report_generator):
        """Test getting multi-patient report."""
        patient_ids = ["P001", "P002"]
        expected = [{"data": "multi report"}]

        mock_report_generator.generate_multi_patient_report.return_value = expected

        result = controller.get_multi_patient_report(patient_ids)

        mock_report_generator.generate_multi_patient_report.assert_called_once_with(patient_ids)
        assert result == expected

    def test_get_filter_report_by_keywords(self, controller, mock_patient_log, mock_report_generator):
        """Test getting filtered report by keywords."""
        keywords = "fever"
        expected_ids = ["P001"]
        expected_report = [{"data": "filtered report"}]

        mock_patient_log.find_patient_ids_by_note_keyword.return_value = expected_ids
        mock_report_generator.generate_multi_patient_report.return_value = expected_report

        result = controller.get_filter_report_by_keywords(keywords)

        mock_patient_log.find_patient_ids_by_note_keyword.assert_called_once_with(keywords)
        mock_report_generator.generate_multi_patient_report.assert_called_once_with(expected_ids)
        assert result == expected_report

    def test_get_filter_report_by_metric(self, controller, mock_patient_log, mock_report_generator):
        """Test getting filtered report by metric."""
        metric = "temperature"
        def comparison(value: float) -> bool:
            return value > 100

        expected_ids = ["P001"]
        expected_report = [{"data": "metric report"}]

        mock_patient_log.filter_by_metric.return_value = expected_ids
        mock_report_generator.generate_multi_patient_report.return_value = expected_report

        result = controller.get_filter_report_by_metric(metric, comparison)

        mock_patient_log.filter_by_metric.assert_called_once_with(metric, comparison)
        mock_report_generator.generate_multi_patient_report.assert_called_once_with(expected_ids)
        assert result == expected_report

    def test_export_patient_report(self, controller, mock_report_generator):
        """Test exporting patient report."""
        patient_id = "P001"
        filename = "report.pdf"

        with patch.object(controller, 'get_patient_report', return_value=[{"data": "report"}]):
            controller.export_patient_report(patient_id, filename)

        mock_report_generator.export_report_to_file.assert_called_once()

    # Similar tests for other export methods can be added analogously

    # USER MANAGEMENT
    def test_create_user(self, controller, mock_db):
        """Test creating user."""
        username = "testuser"
        password = "pass"
        role = "staff"
        name = "Test User"

        controller.create_user(username, password, role, name)

        mock_db.create_user.assert_called_once_with(username, password, role, name)

    def test_ensure_user(self, controller, mock_db):
        """Test ensuring user."""
        username = "testuser"
        password = "pass"
        role = "staff"
        name = "Test User"

        controller.ensure_user(username, password, role, name)

        mock_db.ensure_user.assert_called_once_with(username, password, role, name)

    def test_delete_user(self, controller, mock_db):
        """Test deleting user."""
        username = "testuser"

        result = controller.delete_user(username)

        mock_db.delete_user.assert_called_once_with(username)
        assert result is True

    def test_get_user(self, controller, mock_db):
        """Test getting user."""
        user_id = "testuser"
        expected = {"id": user_id}

        mock_db.get_user.return_value = expected

        result = controller.get_user(user_id)

        mock_db.get_user.assert_called_once_with(user_id)
        assert result == expected

    def test_get_all_users(self, controller, mock_db):
        """Test getting all users."""
        expected = [{"id": "user1"}, {"id": "user2"}]

        mock_db.get_all_users.return_value = expected

        result = controller.get_all_users()

        mock_db.get_all_users.assert_called_once()
        assert result == expected

    def test_verify_user(self, controller, mock_db):
        """Test verifying user."""
        username = "testuser"
        password = "pass"

        result = controller.verify_user(username, password)

        mock_db.verify_user.assert_called_once_with(username, password)
        assert result is True

    def test_list_users_by_role(self, controller, mock_db):
        """Test listing users by role."""
        role = "staff"
        expected = [{"role": role}]

        mock_db.list_users_by_role.return_value = expected

        result = controller.list_users_by_role(role)

        mock_db.list_users_by_role.assert_called_once_with(role)
        assert result == expected

    # PATIENT UTILITIES
    def test_find_patient_id_by_name_exact(self, controller, mock_db):
        """Test finding patient ID by exact name."""
        name = "John Doe"
        expected = ("P001", None)

        mock_db.find_patient_id_by_name_exact.return_value = expected

        result = controller.find_patient_id_by_name_exact(name)

        mock_db.find_patient_id_by_name_exact.assert_called_once_with(name)
        assert result == expected

    def test_patients_property(self, controller, mock_db):
        """Test patients property."""
        expected = {"P001": Mock()}

        controller.db.patients = expected
        result = controller.patients

        assert result == expected

    def test_staffs_property(self, controller, mock_db):
        """Test staffs property."""
        expected = {"S001": Mock()}

        controller.db.staffs = expected
        result = controller.staffs

        assert result == expected
    
import app.database.controller as controller_module
class TestControllerFailures:
    """Test suite with intentional failures for demonstration."""

    @patch.object(Validator, 'validate_patient_id')
    def test_register_patient_failure(self, mock_validate_patient_id, controller, mock_db):
        """Intentionally failing test: wrong log message assertion."""
        patient_data = {"patientID": "P001", "name": "John Doe", "condition": "Healthy"}
        mock_patient = Mock(patientID="P001")
        with patch.object(Patient, 'from_dict', return_value=mock_patient):
            with patch.object(controller, 'log_action') as mock_log_action:
                result = controller.register_patient(patient_data)

        mock_validate_patient_id.assert_called_once_with("P001")
        mock_db.add_patient.assert_called_once_with(mock_patient)
        mock_log_action.assert_called_once_with(
            controller.current_user.userID,
            f"Wrong log message"  # Intentional failure: actual is different
        )
        assert result == mock_patient

    def test_get_patient_failure(self, controller, mock_db):
        """Intentionally failing test: assert patient not found when it is."""
        patient_id = "P001"
        mock_patient = Mock()
        mock_db.get_patient.return_value = mock_patient

        with patch.object(controller, 'log_action') as mock_log_action:
            result = controller.get_patient(patient_id)

        mock_db.get_patient.assert_called_once_with(patient_id)
        mock_log_action.assert_called_once_with(
            controller.current_user.userID,
            f"Request for instant value of patient ID:{patient_id} by Staff {controller.current_user.userID}"
        )
        assert result is None  # Intentional failure: actual is mock_patient

    def test_update_patient_info_failure(self, controller, mock_db):
        """Intentionally failing test: update non-existent attribute."""
        patient_id = "P001"
        updates = {"non_existent": "value"}  # Intentional: attribute doesn't exist
        mock_patient = Mock(spec=Patient)  # ✅ constrain attributes
        mock_db.get_patient.return_value = mock_patient

        with patch.object(controller, 'log_action') as mock_log_action:
            controller.update_patient_info(patient_id, updates)

        mock_db.get_patient.assert_called_once_with(patient_id)
        assert hasattr(mock_patient, "non_existent")  
        mock_db.save_all.assert_called_once()
        mock_log_action.assert_called_once_with(
            controller.current_user.userID,
            f"Patient info updated: {list(updates.keys())} by Staff {controller.current_user.userID}"
        )

    def test_add_patient_log_failure(self, controller, mock_patient_log):
        """Intentionally failing test: wrong timestamp."""
        patient_id = "P001"
        staff_id = "S001"
        temperature = 98.6
        heart_rate = 72
        blood_pressure = "120/80"
        notes = "Feeling well"
        expected_log_id = "L001"

        with patch.object(controller_module, 'LogEntry') as mock_log_entry, \
             patch.object(controller_module, 'datetime') as mock_datetime_module:
            mock_now = Mock()
            mock_datetime_module.datetime.now.return_value = mock_now
            mock_now.strftime.return_value = "2023-01-01 00:00:00"

            mock_log = Mock(logID=expected_log_id)
            mock_log.to_dict.return_value = {}
            mock_log_entry.return_value = mock_log

            result = controller.add_patient_log(patient_id, staff_id, temperature, heart_rate, blood_pressure, notes)

        mock_log_entry.assert_called_once_with(
            logID=f"L{len(controller.patient_log.get_logs()) + 1:03}",
            patientID=patient_id,
            staffID=staff_id,
            timestamp="wrong timestamp",  # Intentional failure
            temperature=temperature,
            heartRate=heart_rate,
            bloodPressure=blood_pressure,
            notes=notes
        )
        mock_patient_log.add_log.assert_called_once_with(mock_log.to_dict.return_value)
        assert result == mock_log

    def test_create_alert_failure(self, controller, mock_db):
        """Intentionally failing test: wrong alert ID."""
        severity = "high"
        patient_id = "P001"
        staff_id = "S001"
        message = "High fever detected"

        with patch.object(controller_module, 'Alert') as mock_alert_class, \
             patch.object(controller_module, 'datetime') as mock_datetime_module, \
             patch.object(controller, 'log_action') as mock_log_action:
            mock_now = Mock()
            mock_datetime_module.datetime.now.return_value = mock_now
            mock_now.isoformat.return_value = "2023-01-01T00:00:00"

            mock_alert = Mock()
            mock_alert_class.return_value = mock_alert

            controller.create_alert(severity, patient_id, staff_id, message)

        mock_alert_class.assert_called_once_with(
            alertID="wrong_id",  # Intentional failure
            staffID=staff_id,
            message=message,
            patientID=patient_id,
            severity=severity,
            timestamp="2023-01-01T00:00:00"
        )
        mock_db.add_alert.assert_called_once_with(mock_alert)
        mock_log_action.assert_called_once_with(staff_id, f"Alert created: {message}")
# Run with: pytest test_controller.py -v