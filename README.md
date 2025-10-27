# 🏥 Hospital Control Panel
Zou Zixuan Workshop 02 Group 4


A modern **Streamlit-based hospital management system** designed for clinics, teaching hospitals, or research facilities.  
Built for administrators, staff, and patients — all roles are integrated with authentication, multilingual UI, alerts, assignments, and audit logging.

---

## 📘 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Core Flow](#core-flow)
- [Modules Overview](#modules-overview)
- [Setup & Installation](#setup--installation)
- [Directory Structure](#directory-structure)
- [Authentication System](#authentication-system)
- [Assignment System](#assignment-system)
- [Dashboards](#dashboards)
- [Logging & Auditing](#logging--auditing)
- [Development Notes](#development-notes)

---

## 🩺 Overview

The **Hospital Control Panel** manages user accounts, staff–patient assignments, logs, alerts, and reporting through a secure Streamlit UI.  
It stores persistent data in JSON files under the `data/` directory.

Roles include:
- **SiteAdmin** — full system control + 2FA (TOTP)
- **Admin** — manage staff/patient accounts and assignments
- **Staff** — view and log patient vitals, alerts, and reports
- **Patient** — view preferences and translated notes

---

## 👤 Demo Accounts

You can log in using the following demo accounts to explore the system:

| ID    | Role    | Username | Password   |
|-------|----------|-----------|-------------|
| A001  | Admin    | Admin     | Admin123    |
| S001  | Staff    | Staff     | Staff123    |
| P001  | Patient  | Patient   | Patient123  |

> ⚠️ **Note:** These demo credentials are for testing and demonstration purposes only.  
> Change or remove them before deploying in a production environment.

---

## ⚙️ Features

✅ Secure login with PBKDF2-SHA256 and 2FA (for SiteAdmin)  
✅ Role-based access control (RBAC)  
✅ JSON-backed database with auto-save and schema validation  
✅ Persistent audit trail (`audit_log.jsonl`)  
✅ Patient–Staff assignment system (`assignments.json`)  
✅ Report generation (CSV/PDF export)  
✅ Alerts on abnormal clinical thresholds  
✅ Searchable logs and preference editor  
✅ Multilingual UI with on-device translation cache  
✅ Real-time Streamlit interface for dashboards

---

## 🧩 Architecture

```

file  →  controller  →  database
database  →  controller  →  file

````

- **Files** = UI views (`gui/views/`)
- **Controller** = business logic (`app/database/controller.py`)
- **DatabaseManager** = handles JSON persistence (`app/database/database_Manager.py`)

The controller mediates *every* operation — it validates, updates the DB, triggers logs, and syncs with the `assignment_Store`.

---

## 🧠 Core Flow

| Layer | Responsibility |
|-------|----------------|
| **UI (Streamlit)** | User interaction, forms, buttons, role views |
| **Controller** | Validation, assignment logic, CRUD delegation |
| **DatabaseManager** | JSON file I/O, hashing, audit, and persistence |
| **Core Modules** | Auth, Alerts, Assignments, Reports, Translation |

---

## 🧱 Modules Overview

### 🔐 `app/core/auth_Manager.py`
- Handles login, password validation, OTP for SiteAdmin  
- No seeding; users created through Admin/Staff Management  
- Tracks lockouts (`fails` and `until`)  
- Uses PBKDF2 via DatabaseManager for password hashing  

### 📋 `app/database/controller.py`
Central logic hub.  
- CRUD for patients, staff, and preferences  
- Delegates persistence to `DatabaseManager`  
- Coordinates with `assignment_Store` for linking staff ↔ patients  
- Cleans up orphaned references on user deletion  
- Syncs assignments both to `assignments.json` and `patients.json`  
- Generates and exports reports and audit logs  

### 💾 `app/database/database_Manager.py`
- Stores all persistent data in JSON:
  - `users.json`
  - `patients.json`
  - `staffs.json`
  - `assignments.json`
  - `audit_log.jsonl`
- Handles hashing, validation, and locking

### 🔗 `app/core/assignment_Store.py`
Manages **assignments.json** as the *source of truth*.
- `assign(patientID, staffID, by)`
- `unassign(patientID, staffID, by)`
- `patients_for_staff(staffID)`
- `staff_for_patient(patientID)`
- Persists data in `data/assignments.json`

### 📡 `app/core/alertengine.py`
- Evaluates vitals → triggers `Alert`  
- Alerts are saved to `alerts.json`

### 🧾 `app/reports/report_Generator.py`
- Aggregates logs for patients  
- Exports to PDF/CSV  
- Integrated with Staff and Admin dashboards

### 🧍 `app/users/patient.py` / `staff.py`
- Dataclasses representing patients and staff  
- JSON serializable models for DatabaseManager

---

## 🧰 Setup & Installation

### Prerequisites
- Python 3.10+
- Streamlit (`pip install streamlit`)
- Pandas
- Argostranslate or googletrans (for translations)
- ReportLab (for PDF export)
- Requests (sends and receives data from web APIs)
- Pytest (for code testing)
- Cryptography and fernet (Secures data using encryption and hashing)

### Installation

```bash
pip install -r requirements.txt
````

### Run the App

```bash
python main.py
```

App will auto-launch at:
🔗 `http://localhost:8501`

---

## 🗂 Directory Structure

```
app/
 ├── core/
 │    ├── alert.py
 │    ├── alertengine.py
 │    ├── assignment_Store.py
 │    ├── audit.py
 │    ├── auth_Manager.py
 │    ├── config.py
 │    ├── translate.py
 │    ├── validator.py
 │    └── ...
 │
 ├── database/
 │    ├── controller.py
 │    ├── database_Manager.py
 │    └── __init__.py
 │
 ├── logging/
 │    ├── logentry.py
 │    ├── system_log.py
 │    └── patient_Log.py
 │
 ├── users/
 │    ├── patient.py
 │    ├── staff.py
 │    ├── preferences.py
 │
 └── reports/
      ├── report_Generator.py

gui/
 └── views/
      ├── welcome_page.py
      ├── admin_Dashboard.py
      ├── staff_Management.py
      ├── patient_Management.py
      ├── staff_Dashboard.py
      ├── patient_Dashboard.py

data/
 ├── users.json
 ├── patients.json
 ├── staffs.json
 ├── assignments.json
 ├── audit_log.jsonl
 └── alerts.json
```

---

## 🔑 Authentication System

| Role          | Access                                    |
| ------------- | ----------------------------------------- |
| **SiteAdmin** | Full system control, OTP-secured login    |
| **Admin**     | Manage staff/patients, assignments, audit |
| **Staff**     | View logs, generate reports, edit alerts  |
| **Patient**   | View preferences, translated notes        |

Passwords are hashed with PBKDF2-SHA256 (200k iterations).
SiteAdmin 2FA uses 20-second rotating TOTP tokens.

---

## 🔄 Assignment System

* Source of truth: `data/assignments.json`
* Managed through:

  * `app/core/assignment_Store.py`
  * `Controller.assign_patient_to_staff()`
* Auto-synced on assignment/unassignment
* Staff deletion cleans up related assignments

Each record looks like:

```json
{
  "patientID": "P001",
  "staffID": "S001",
  "assignedBy": "admin",
  "ts": "2025-10-26T19:25:23Z"
}
```

---

## 🖥️ Dashboards

### 🧑‍💼 Admin Dashboard

* Assign/unassign staff to patients
* View audit logs
* Export logs (CSV/JSONL)

### 🧑‍⚕️ Staff Dashboard

* View assigned patients
* Log vitals and observations
* Receive alerts and generate patient reports

### 👩‍🦰 Patient Dashboard

* Edit language and preferences
* View translated clinical notes

---

## 🪵 Logging & Auditing

All actions are logged via:

* `app.logging.system_log.SystemLog`
* Stored in `data/audit_log.jsonl`
* Accessible in the Admin Dashboard with export options

Example entry:

```json
{
  "ts": "2025-10-27T13:15:58Z",
  "who": "admin",
  "role": "admin",
  "event": "staff.delete",
  "details": {"username": "S001"}
}
```

---

## 🧠 Development Notes

* **Assignment persistence** now mirrors `assignment_Store` → `assignments.json`
* **Controller** is the only component that talks to `DatabaseManager`
* **AuthService** removed any redundant seeding or double-hashing
* **SiteAdmin** OTP handled via `app/core/totp.py` and `otp_console.py`
* **Staff deletion** automatically unassigns from all patients
