# gui/main_dashboard.py
import streamlit as st
from app.schedule import ScheduleManager
from gui.student_pages import show_student_management_page
from gui.roster_pages import show_roster_page

def set_font_color(color: str = "white"):
    """
    Override default text color in the Streamlit app.
    Example: set_font_color("white") or set_font_color("#FF5733")
    """
    css = """
    <style>
    .stApp, .stApp div, .stApp p, .stApp span, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {{
        color: {color} !important;
    }}
    </style>
    """.format(color=color)
    st.markdown(css, unsafe_allow_html=True)
    
def set_background_image_from_url(url: str, overlay_rgba: str = "rgba(0,0,0,0.35)"):
    """
    Set the Streamlit app background to an image at `url`.
    Uses str.format(...) to avoid f-string brace-escaping issues.
    Call this once near the top of your Streamlit script (before UI widgets).
    """
    css = """
    <style>
    /* Full-page background */
    .stApp {{
        background-image: url("{url}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}

    /* Optional overlay for better text contrast */
    .stApp::before {{
        content: "";
        position: fixed;
        inset: 0;
        background: {overlay};
        z-index: 0;
        pointer-events: none;
    }}

    /* Ensure main content sits above overlay */
    .main {{
        position: relative;
        z-index: 1;
    }}

    /* Small tweak: make cards/panels slightly translucent so bg shows through.
       Note: internal classnames may vary between Streamlit versions. */
    .stCard, .stButton, .stForm, .css-1d391kg {{
        backdrop-filter: blur(3px);
    }}
    </style>
    """.format(url=url, overlay=overlay_rgba)

    st.markdown(css, unsafe_allow_html=True)
def launch():
    """Sets up the main Streamlit application window and navigation."""
    st.set_page_config(layout="wide", page_title="Music School Management System")
    set_background_image_from_url("https://i.pinimg.com/originals/88/ec/b2/88ecb200366538db336167e4ea4ebb6f.gif")
    set_font_color("black")
    # Instantiate the "brain" of our app ONCE and store it in the session state.
    # This is crucial so the manager object persists as we switch pages.
    if 'manager' not in st.session_state:
        st.session_state.manager = ScheduleManager()

    st.sidebar.title("MSMS Navigation")
    # Create a radio button menu in the sidebar for page navigation.
    page = st.sidebar.radio(
    "Go to",
    [
        "Welcome",
        "Student Management",
        "Daily Roster",
        "Course Management",
        "Admin Tools",
        "Payments (stub)"
    ]
)

    # Use an if/elif block to call the correct function to render the selected page.
    if page == "Welcome":
        from gui.welcome_page import show_welcome_page
        show_welcome_page()
    elif page == "Student Management":
        show_student_management_page(st.session_state.manager)
    elif page == "Daily Roster":
        show_roster_page(st.session_state.manager)
    elif page == "Course Management":
        from gui.course_pages import show_course_management_page
        show_course_management_page(st.session_state.manager)
    elif page == "Admin Tools":
        from gui.admin_pages import show_admin_tools_page
        show_admin_tools_page(st.session_state.manager)
    elif page == "Payments (stub)":
        from gui.finance_pages import show_finance_page
        show_finance_page(st.session_state.manager)
        

# In Pst 1, the basic idea of this music manege system had been formed. By using in-memory prototype some functions can be domostrated.
# With in the upgrades in Pst2 datas are nolonger temparery it been saved in a MSMS.josn provided a consistet storage for data
# For PST 3 the codes been redesigned based on Object-Oriented (OOP) design provide more felexable editing more modular coding and prevent from code leak.
# In order to make it more user friendly a GUI formed by streamlit is implemented, it sepereas the fornmt end and back end ont only better looking but also increase the system security, Scalability and maintainability.
#current PST 5, few more function been added including the log function make the system "crash-proof" always can backtracking from the log as well as the auto tester using Pytest.
# Spam the code with edge cases and large numbers autometicly can filtter out some hiden indecents that human test can't indentified.