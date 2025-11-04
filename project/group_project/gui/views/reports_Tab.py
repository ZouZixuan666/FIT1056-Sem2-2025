# gui/views/reports_Tab.py
from __future__ import annotations

import os
from datetime import datetime
import streamlit as st

from gui.ui import u

from app.database.controller import Controller

# Save PDFs under this directory
EXPORT_DIR = "reports"


def _current_user_id() -> str:
    """Return the signed-in username ('' if unknown)."""
    try:
        return (st.session_state.get("auth") or {}).get("username") or ""
    except Exception:
        return ""


def _patient_options(controller: Controller) -> list[str]:
    """
    Build a list of selectable patient IDs.
    Prefer patients.json keys; fall back to users.json role=patient.
    """
    ids: list[str] = []

    try:
        patients = controller.get_all_patients()
        ids = sorted([p["id"] for p in patients if "id" in p])
    except Exception:
        pass

    if not ids:
        try:
            users = controller.list_users_by_role("patient")
            ids = sorted([u.get("username") for u in users if u.get("username")])
        except Exception:
            pass

    return ids


def render():
    st.header(u("Generate Patient Report (PDF)"))
    st.caption(u("Generate a one-patient PDF report (includes preferences + logs). Confirm before exporting."))

    controller = Controller()

    # ---------- Form: pick patient + period ----------
    patients = _patient_options(controller)
    if not patients:
        st.info(u("No patients available. Create a patient first."))
        return

    with st.form("__report_prepare__", clear_on_submit=False):
        patient_id = st.selectbox(u("Select patient for report"), patients, key="__report_pid__")
        period = st.selectbox(u("Period"), ["weekly", "monthly"], index=0, key="__report_period__")

        # filename preview
        today = datetime.now().strftime("%Y-%m-%d")
        filename = f"{patient_id}-report-{today}.pdf"
        st.caption(u("File will be saved as ") + f"{filename} in `{EXPORT_DIR}/`")

        prepared = st.form_submit_button(u("Generate Report (prepare)"))

    # Store preparation into session so we can confirm in a second step
    if prepared:
        st.session_state["__report_pending__"] = {
            "patient_id": patient_id,
            "period": period,
            "filename": filename,
        }

    # ---------- Confirmation step ----------
    pending = st.session_state.get("__report_pending__")
    if pending:
        st.warning(u("Please confirm you want to generate a PDF for this patient."))

        c1, c2 = st.columns([1, 2])
        with c1:
            cancel = st.button(u("Cancel"))
        with c2:
            confirm = st.button(u("Confirm and Generate PDF"))

        if cancel:
            st.session_state.pop("__report_pending__", None)
            st.rerun()

        if confirm:
            try:
                staff_id = _current_user_id() or "system"
                os.makedirs(EXPORT_DIR, exist_ok=True)
                out_path = os.path.join(EXPORT_DIR, pending["filename"])

                # Write to disk (Option A in the generator)
                final_path = controller.export_patient_report_inpdf(
                    staff_id=staff_id,
                    patientID=pending["patient_id"],
                    out_path=out_path,
                    period=pending["period"],  # 'weekly' or 'monthly'
                )

                abs_path = os.path.abspath(final_path)
                st.success(u("Report generated successfully."))
                st.write(u("Saved to: ") + f"`{abs_path}`")

                # Optional: provide a simple download link in Streamlit (local file)
                try:
                    with open(final_path, "rb") as fh:
                        st.download_button(
                            label=u("Download PDF"),
                            data=fh.read(),
                            file_name=os.path.basename(final_path),
                            mime="application/pdf",
                        )
                except Exception:
                    pass

                st.session_state.pop("__report_pending__", None)

            except Exception as e:
                st.error(u(f"Failed to generate report: {e}"))
