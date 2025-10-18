# gui/finance_pages.py
import streamlit as st
import pandas as pd
import datetime
def show_finance_page(manager):
    """Renders the UI for all financial operations."""
    st.header("Finance & Payments")

    # --- Section 1: Record a Payment ---
    st.subheader("Record New Payment")
    with st.form("payment_form"):
        # TODO: Create a selectbox to choose a student (e.g., from a list of names).
        student_list = {s.name: s.id for s in manager.students}
        selected_student_name = st.selectbox("Select Student", student_list.keys())
        
        # TODO: Create a number_input for amount and a text_input for method.
        amount = st.number_input("Payment Amount", min_value=0.01)
        method = st.text_input("Payment Method (e.g., Credit Card, Cash)")
        
        submitted = st.form_submit_button("Record Payment")
        if submitted:
            student_id = student_list[selected_student_name]
            # TODO: Call manager.record_payment() and show a success message.
            manager.record_payment(student_id, amount, method)
            st.success(f"Payment of {amount} for {selected_student_name} recorded.")
        else:
                st.error("Please enter a valid payment method.")

    # --- Section 2: View Payment History ---
    st.subheader("View Student Payment History")
    # TODO: Create a selectbox to choose a student.
    history_student_name = st.selectbox("Select Student to View History", list(student_list.keys()), key="history_select")
    if history_student_name:
        student_id = student_list[history_student_name]
        history = manager.get_payment_history(student_id)

        if history:
        # Convert list of dicts → DataFrame
            df = pd.DataFrame(history)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")

            st.dataframe(df, use_container_width=True)

            csv_data = df.to_csv(index=False).encode('utf-8')

            st.download_button(
                label="📥 Download Payment History as CSV",
                data=csv_data,
                file_name=f"payment_history_{history_student_name}_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                key="download_btn"
            )
        else:
            st.info(f"No payment history found for {history_student_name}.")