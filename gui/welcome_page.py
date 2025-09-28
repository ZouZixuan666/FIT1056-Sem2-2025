# gui/welcome_page.py
import streamlit as st

def show_welcome_page():
    st.title("Music School Management System (MSMS)")
    st.subheader("Welcome to your all-in-one school administration tool!")

    st.markdown(
        """
        ---
        ### Functions
        - **Student Management** → Register and manage student profiles.
        - **Daily Roster** → View and check-in students for today’s classes.
        - **Course Management** → Add courses and switch students between them.
        - **Admin Tools** → Secure area for listing/removing/adding teachers, students, and courses.
        - **Payments** → Manage tuition and payments.
        ---
        """
    )

    st.success("Tip: Use the left sidebar to navigate through the system.")

    # Optional: Add contact/help info
    with st.expander("About this project"):
        st.write(
            """
            - Author: *ZouZixuan*
            - Semester: 2, 2025
            - Stage: PST4 (GUI Upgrade)
            """
        )
