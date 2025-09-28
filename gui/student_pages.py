# gui/student_pages.py
import streamlit as st

def show_student_management_page(manager):
    """Renders all components for the student management page."""
    
    st.header("Student Management")

    # --- Search Section (remains the same) ---
    st.subheader("Find a Student")
    # ...

    # --- Registration Section (now works correctly) ---
    st.subheader("Register New Student")
    with st.form("registration_form"):
        reg_name = st.text_input("New Student Name")
        reg_instrument = st.text_input("First Instrument")
        submitted = st.form_submit_button("Register Student")
        
        if submitted:
            # This call now works because we implemented the method in PST3.
            # TODO: Add a check for blank name/instrument.
            
            if reg_name.strip() and reg_instrument.strip():
                new_student = manager.register_new_student(reg_name.strip(), reg_instrument.strip())
                if new_student:
                    st.success(f"Successfully registered {reg_name.strip()}!")
                    # You can use st.balloons() for extra flair.
                else:
                    st.error(f"Could not register student. A teacher for {reg_instrument.strip()} might not be available.")
            else:
                st.warning("Please enter both a name and an instrument.")