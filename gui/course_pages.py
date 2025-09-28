import streamlit as st

def show_course_management_page(manager):
    st.header("Course Management")

    # --- Add Course ---
    st.subheader("Add a New Course")
    with st.form("add_course_form"):
        name = st.text_input("Course Name")
        instrument = st.text_input("Instrument")
        teacher_id = st.number_input("Teacher ID", step=1, min_value=1)
        submitted = st.form_submit_button("Add Course")
        if submitted:
            course = manager.add_course(name, instrument, int(teacher_id))
            if course:
                st.success(f"Course added: {course.name}")
            else:
                st.error("Could not add course (check teacher ID).")

    st.markdown("---")

    # --- Switch Student Between Courses ---
    st.subheader("Switch Student Between Courses")
    with st.form("switch_course_form"):
        sid = st.number_input("Student ID", step=1, min_value=1)
        from_course = st.number_input("From Course ID", step=1, min_value=1)
        to_course = st.number_input("To Course ID", step=1, min_value=1)
        submitted = st.form_submit_button("Switch Course")
        if submitted:
            success = manager.switch_student_course(int(sid), int(from_course), int(to_course))
            if success:
                st.success(f"Student {sid} switched from {from_course} to {to_course}.")
            else:
                st.error("Switch failed. Please check IDs and try again.")
