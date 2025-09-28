# gui/roster_pages.py
import streamlit as st
import pandas as pd

def show_roster_page(manager):
    """Renders the daily roster and check-in functionality."""
    st.header("Daily Roster")

    # --- View Roster Section (remains the same) ---
    day = st.selectbox("Select a day", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])

    
    # --- Student Check-in Section (now works correctly) ---
    st.subheader("Student Check-in")
    with st.form("check_in_form"):
        # To make this user-friendly, we should populate the dropdowns dynamically.
        # Get lists of student names and course names from the manager.
        student_list = {s.name: s.id for s in manager.students}
        course_list = {c.name: c.id for c in manager.courses}
        
        selected_student_name = st.selectbox("Select Student", student_list.keys())
        selected_course_name = st.selectbox("Select Course", course_list.keys())
        
        submitted = st.form_submit_button("Check-in Student")

        if submitted:
            # Convert the selected names back to IDs
            student_id = student_list[selected_student_name]
            course_id = course_list[selected_course_name]
            
            result = manager.check_in(student_id, course_id)

            if result["status"] == "ok":
                st.success(
                    f"{selected_student_name} checked in for {selected_course_name} "
                    f"at {result['record']['timestamp']}"
                )

            elif result["status"] == "duplicate":
                existing = result["existing"]
                st.warning(
                    f" {selected_student_name} has **already checked into {selected_course_name} today** "
                    f"(at {existing.get('timestamp')}).\n\n"
                    "Each student can only check in **once per day per class**."
                )

            elif result["status"] == "not_enrolled":
                st.error(f" {selected_student_name} is not enrolled in {selected_course_name}. Enrol them first.")

            elif result["status"] == "no_student":
                st.error("Student not found.")

            elif result["status"] == "no_course":
                st.error(" Course not found.")

            else:
                st.error(" Unknown error when checking in.")