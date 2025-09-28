# gui/admin_pages.py
import streamlit as st
import hashlib

ADMIN_PASSWORD_HASH = hashlib.sha256("123".encode()).hexdigest()

def authenticate(password: str) -> bool:
    return hashlib.sha256(password.encode()).hexdigest() == ADMIN_PASSWORD_HASH

def show_admin_tools_page(manager):
    st.header("Admin Tools")

    # --- Authentication ---
    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False
    if st.session_state["admin_authenticated"]:
        show_admin_panel(manager)
        return
    if not st.session_state.admin_authenticated:
        pwd = st.text_input("Enter admin password", type="password")
        if st.button("Authenticate"):
            if authenticate(pwd):
                st.session_state.admin_authenticated = True
                st.success("Admin authenticated.")
                show_admin_panel(manager)
            else:
                st.error("Wrong password")
        st.stop()  # stop rendering the rest until authenticated
def show_admin_panel(manager):
    st.subheader("Admin Control Panel")
    st.write("Welcome — you are authenticated.")
    # --- Secondary menu: choose an admin function ---
    st.markdown("### Choose an admin action")
    action = st.selectbox(
        "Action",
        [
            "List Students",
            "List Teachers",
            "List Courses",
            "Add Teacher",
            "Add Course",
            "Remove Student",
            "Remove Teacher",
            "Remove Course",
            "Show Attendance",
            "Clear Local Files"
        ],
    )

    st.markdown("---")

    # --- LISTS ---
    if action == "List Students":
        st.subheader("All Students")
        students = manager.list_students()
        if students:
            # Show as table if items are dict-like or JSON otherwise
            try:
                rows = [s.__dict__ for s in students]
                st.dataframe(rows)
            except Exception:
                for s in students:
                    st.json(getattr(s, "__dict__", str(s)))
        else:
            st.info("No students found.")

    elif action == "List Teachers":
        st.subheader("All Teachers")
        teachers = manager.list_teachers()
        if teachers:
            rows = [t.__dict__ for t in teachers]
            st.dataframe(rows)
        else:
            st.info("No teachers found.")

    elif action == "List Courses":
        st.subheader("All Courses")
        courses = manager.list_courses()
        if courses:
            rows = [c.__dict__ for c in courses]
            st.dataframe(rows)
        else:
            st.info("No courses found.")

    # --- ADD ---
    elif action == "Add Teacher":
        st.subheader("Add Teacher")
        with st.form("add_teacher_form"):
            name = st.text_input("Teacher Name")
            speciality = st.text_input("Speciality")
            submitted = st.form_submit_button("Add Teacher")
            if submitted:
                t = manager.add_teacher(name, speciality)
                if t:
                    st.success(f"Added teacher: {t.name} (id={getattr(t,'id', 'N/A')})")
                else:
                    st.error("Failed to add teacher. Check input.")

    elif action == "Add Course":
        st.subheader("Add Course")
        with st.form("add_course_form"):
            name = st.text_input("Course Name")
            instrument = st.text_input("Instrument")
            teacher_id = st.number_input("Teacher ID", min_value=0, step=1)
            submitted = st.form_submit_button("Add Course")
            if submitted:
                course = manager.add_course(name, instrument, int(teacher_id))
                if course:
                    st.success(f"Course added: {course.name} (id={getattr(course,'id','N/A')})")
                else:
                    st.error("Could not add course. Confirm teacher ID exists.")

    # --- REMOVE ---
    elif action == "Remove Student":
        st.subheader("Remove Student")
        with st.form("remove_student_form"):
            sid = st.number_input("Student ID to remove", min_value=0, step=1)
            submitted = st.form_submit_button("Remove Student")
            if submitted:
                manager.remove_student(int(sid))
                st.success(f"Removed student {sid}")

    elif action == "Remove Teacher":
        st.subheader("Remove Teacher")
        with st.form("remove_teacher_form"):
            tid = st.number_input("Teacher ID to remove", min_value=0, step=1)
            submitted = st.form_submit_button("Remove Teacher")
            if submitted:
                manager.remove_teacher(int(tid))
                st.success(f"Removed teacher {tid}")

    elif action == "Remove Course":
        st.subheader("Remove Course")
        with st.form("remove_course_form"):
            cid = st.number_input("Course ID to remove", min_value=0, step=1)
            submitted = st.form_submit_button("Remove Course")
            if submitted:
                manager.remove_course(int(cid))
                st.success(f"Removed course {cid}")

    # --- ATTENDANCE & FILES ---
    elif action == "Show Attendance":
        st.subheader("Attendance Records")
        records = manager.show_attendance()
        if records:
            # we assume records are list-like of dicts or tuples
            try:
                st.dataframe(records)
            except Exception:
                for r in records:
                    st.write(r)
        else:
            st.info("No attendance records available.")

    elif action == "Clear Local Files":
        st.subheader("Clear Local Files")
        st.warning("This will remove local storage files used by the manager.")
        if st.button("Clear Now"):
            manager.clear_local_files()
            st.success("Local files cleared.")

    # --- Footer: allow logging out of admin session ---
    st.markdown("---")
    if st.button("Log out admin"):
        st.session_state["admin_authenticated"] = False
        st.session_state.admin_authenticated = False
        # the button click will rerun, so we can just return.
        if hasattr(st, "experimental_rerun"):
            st.experimental_rerun()
        else:
            return
