# gui/views/staff_Dashboard.py
import uuid
from datetime import datetime, date
import json

import pandas as pd
import streamlit as st

from gui.ui import u, language_names, name_to_code, code_to_name
from app.core.translate import translate_text
from app.core.assignment_Store import patients_for_staff, is_allowed  # kept for RBAC check used by Reports tab
from app.database.controller import Controller                        # <- use Controller, not DatabaseManager
from app.core.audit import audit

try:
    from app.reports.report_Generator import ReportGenerator
except Exception:
    ReportGenerator = None

# one Controller instance for this Streamlit session
def _get_ctrl() -> Controller:
    if "__CTRL__" not in st.session_state:
        st.session_state["__CTRL__"] = Controller()
    return st.session_state["__CTRL__"]


def _normalize_log(obj):
    """Return a dict with fields we use, whether obj is a dict or a model."""
    if hasattr(obj, "to_dict"):
        d = obj.to_dict()
    elif isinstance(obj, dict):
        d = obj
    else:
        # best-effort attribute read
        d = {
            "logID": getattr(obj, "logID", None),
            "timestamp": getattr(obj, "timestamp", None),
            "patientID": getattr(obj, "patientID", None),
            "staffID": getattr(obj, "staffID", None),
            "temperature": getattr(obj, "temperature", None),
            "heartRate": getattr(obj, "heartRate", None),
            "bloodPressure": getattr(obj, "bloodPressure", None),
            "notes": getattr(obj, "notes", getattr(obj, "note", None)),
        }
    # ensure consistent keys
    d.setdefault("notes", d.get("note"))
    return d


def render():
    st.title("🧑‍⚕️ " + u("Staff Workspace"))
    st.caption(u("FR: Patient Logs, Search, Alerts, Preferences view"))

    ctrl = _get_ctrl()
    auth = st.session_state.get("auth") or {}
    role = (auth.get("role") or "").lower()
    staff_like = role in {"staff", "admin", "siteadmin"}
    staff_id = auth.get("staff_id") or auth.get("username")

    # Scope: admins/siteadmins = ALL, staff = assigned
    if staff_like and role in {"admin", "siteadmin"}:
        try:
            all_patients = list(getattr(ctrl, "patients", {}).keys())  # Controller.patients property -> dict
        except Exception:
            all_patients = []
        my_patients = sorted(all_patients)
    else:
        # keep existing helper for now; you can swap to ctrl.get_patients_for_staff(staff_id)
        my_patients = patients_for_staff(staff_id) if staff_id else []

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [u("Patient Logs"), u("Search"), u("Alerts"), u("Patient Preferences"), u("Reports")]
    )

    # ---------------------------
    # TAB 1: CREATE / MANAGE LOGS
    # ---------------------------
    with tab1:
        st.subheader(u("Daily Patient Logs"))
        st.info(u("Only assigned patients are allowed (RBAC). Admin/SiteAdmin: all patients."))

        col_top1, col_top2 = st.columns([1, 2])
        with col_top1:
            pid = st.selectbox(
                u("My Patients"),
                my_patients if my_patients else [u("No assignments")],
                index=0,
                key="__pid_select__",
            )
        with col_top2:
            st.caption(u("If empty, ask admin to assign you patients in Admin → Assignments."))

        # Translation preview-first flow
        st.session_state.setdefault("__notes_nonce__", 0)
        st.session_state.setdefault("__notes_prefill__", "")

        with st.container(border=True):
            st.caption(u("Translate notes (preview first, then optionally use it)"))
            tc1, tc2 = st.columns([4, 1], vertical_alignment="bottom")
            with tc1:
                tgt_name = st.selectbox(u("Target language"), language_names(), index=0, key="__xlate_tgt__")
                tgt_code = name_to_code(tgt_name)
            with tc2:
                translate_clicked = st.button(u("Translate"), key="__xlate_go__", use_container_width=True)

        notes_key = f"__notes__{st.session_state['__notes_nonce__']}"
        notes_default = st.session_state.get("__notes_prefill__", "")
        notes = st.text_area(u("Observations / Notes"), value=notes_default, key=notes_key, height=180)

        translated_preview = None
        if translate_clicked:
            try:
                raw = notes or ""
                translated_preview = translate_text(raw, tgt_code) if raw.strip() else ""
            except Exception as e:
                st.error(u(f"Translation failed: {e}"))

        if translated_preview is not None:
            with st.container(border=True):
                st.markdown(u("**Translated preview**"))
                st.text_area(u("Preview"), value=translated_preview, key="__preview__", height=160, disabled=True)
                if st.button(u("Use this in Notes"), key="__apply_translation__", use_container_width=True):
                    st.session_state["__notes_prefill__"] = translated_preview
                    st.session_state["__notes_nonce__"] += 1
                    st.rerun()

        c_v1, c_v2, c_v3 = st.columns(3)
        with c_v1:
            temp = st.number_input(u("Temperature (°C)"), value=36.8, step=0.1, format="%.1f")
        with c_v2:
            hr = st.number_input(u("Heart Rate (bpm)"), value=78, step=1, min_value=0)
        with c_v3:
            bp = st.text_input(u("Blood Pressure (e.g., 120/80)"))

        if st.button(u("Save (validates → audit → persist)"), key="__save_new_log__", use_container_width=True):
            if not my_patients or pid not in my_patients:
                st.error(u("You are not assigned to this patient. Ask admin to assign first."))
                try:
                    audit(
                        "log.save_unauthorized",
                        who=staff_id,
                        role=role or "staff",
                        details={"patientID": pid, "reason": "not_assigned"},
                    )
                except Exception:
                    pass
            else:
                try:
                    # Controller handles creation/persistence
                    log = ctrl.add_patient_log(
                        patient_id=pid,
                        staff_id=staff_id,
                        temperature=float(temp) if temp is not None else None,
                        heart_rate=int(hr) if hr is not None else None,
                        blood_pressure=bp.strip() or None,
                        notes=(notes.strip() or "")
                    )
                    try:
                        audit("log.create", who=staff_id, role=role or "staff",
                              details={"patientID": pid, "logID": getattr(log, "logID", None)})
                        audit("log.saved", who=staff_id, role=role or "staff",
                              details={"patientID": pid, "logID": getattr(log, "logID", None)})
                    except Exception:
                        pass
                    st.success(u("Saved."))
                    st.session_state["__notes_prefill__"] = ""
                    st.session_state["__notes_nonce__"] += 1
                    st.rerun()
                except Exception as e:
                    st.error(u(f"Failed to save: {e}"))
                    try:
                        audit("log.save_failed", who=staff_id, role=role or "staff",
                              details={"patientID": pid, "error": str(e)})
                    except Exception:
                        pass

        st.divider()
        st.subheader(u("Recent logs (assigned patients only)"))

        # Gather logs via Controller per-patient
        logs = []
        try:
            for _pid in (my_patients or []):
                for l in (ctrl.get_patient_logs(_pid) or []):
                    logs.append(_normalize_log(l))
        except Exception:
            logs = []

        # sort desc by timestamp
        def _ts_key(d):
            return d.get("timestamp") or ""
        logs.sort(key=_ts_key, reverse=True)

        if not logs:
            st.caption(u("No logs yet for your scope."))
        else:
            recent_rows = [
                {
                    "ts": d.get("timestamp"),
                    "patientID": d.get("patientID"),
                    "staffID": d.get("staffID"),
                    "temp": d.get("temperature"),
                    "hr": d.get("heartRate"),
                    "bp": d.get("bloodPressure"),
                    "notes": d.get("notes"),
                    "logID": d.get("logID"),
                }
                for d in logs
            ][:50]
            st.dataframe(recent_rows, use_container_width=True)

            st.divider()
            col_export1, col_export2 = st.columns(2)
            with col_export1:
                csv = pd.DataFrame(recent_rows).to_csv(index=False)
                st.download_button(
                    label=u("📥 Download recent logs (CSV)"),
                    data=csv,
                    file_name=f"recent_logs_{staff_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    key="__dl_logs_csv__",
                    use_container_width=True,
                )
            with col_export2:
                json_str = json.dumps(recent_rows, indent=2, ensure_ascii=False)
                st.download_button(
                    label=u("📥 Download recent logs (JSON)"),
                    data=json_str,
                    file_name=f"recent_logs_{staff_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    key="__dl_logs_json__",
                    use_container_width=True,
                )

            with st.expander(u("Log Management")):
                selectable_ids = [r["logID"] for r in recent_rows if r.get("logID")]
                chosen = st.selectbox(u("Select Log ID"), options=selectable_ids, key="__edit_log_id__")

                sel = next((d for d in logs if d.get("logID") == chosen), None)

                # Per-log downloads
                d1, d2 = st.columns(2)
                with d1:
                    if st.button("📥 " + u("Download (JSON)"), key="__dl_json__", use_container_width=True):
                        if sel:
                            payload = json.dumps(sel, ensure_ascii=False, indent=2)
                            st.download_button(
                                label=u("Click to save JSON"),
                                data=payload,
                                file_name=f"log_{sel['logID']}.json",
                                mime="application/json",
                                key="__dl_json_btn__",
                                use_container_width=True,
                            )
                        else:
                            st.warning(u("Select a valid log first."))
                with d2:
                    if st.button("📥 " + u("Download (CSV)"), key="__dl_csv__", use_container_width=True):
                        if sel:
                            csv1 = pd.DataFrame([sel]).to_csv(index=False)
                            st.download_button(
                                label=u("Click to save CSV"),
                                data=csv1,
                                file_name=f"log_{sel['logID']}.csv",
                                mime="text/csv",
                                key="__dl_csv_btn__",
                                use_container_width=True,
                            )
                        else:
                            st.warning(u("Select a valid log first."))

                if sel:
                    # staff can edit own logs; admins/siteadmins can edit any
                    allowed = (sel.get("staffID") == staff_id and sel.get("patientID") in my_patients) or (role in {"admin", "siteadmin"})
                    ekey = f"{chosen}"

                    ec1, ec2, ec3 = st.columns(3)
                    with ec1:
                        e_temp = st.number_input(
                            u("Edit Temp (°C)"),
                            value=sel.get("temperature") if sel.get("temperature") is not None else 36.8,
                            step=0.1, format="%.1f", key=f"__e_temp__{ekey}"
                        )
                    with ec2:
                        base_hr = sel.get("heartRate") if sel.get("heartRate") is not None else 78
                        e_hr = st.number_input(
                            u("Edit HR (bpm)"), value=base_hr, step=1, min_value=0, key=f"__e_hr__{ekey}"
                        )
                    with ec3:
                        e_bp = st.text_input(u("Edit BP"), value=sel.get("bloodPressure") or "", key=f"__e_bp__{ekey}")

                    e_notes = st.text_area(u("Edit Notes"), value=sel.get("notes") or "", key=f"__e_notes__{ekey}", height=120)

                    cc1, cc2 = st.columns(2)
                    with cc1:
                        confirm_edit = st.checkbox(u("Confirm edit"), key=f"__confirm_edit__{ekey}")
                        if st.button(
                            u("Save changes"),
                            disabled=not (confirm_edit and allowed),
                            type="primary",
                            key=f"__save_changes__{ekey}",
                            use_container_width=True,
                        ):
                            # Controller does not expose update; use its DB once (still via Controller)
                            ok = hasattr(ctrl, "db") and hasattr(ctrl.db, "update_log") and ctrl.db.update_log(
                                log_id=sel["logID"],
                                updates={
                                    "temperature": e_temp,
                                    "heartRate": e_hr,
                                    "bloodPressure": e_bp,
                                    "notes": e_notes,
                                },
                                who=staff_id,
                                role=("admin" if role in {"admin", "siteadmin"} else "staff"),
                            )
                            if ok:
                                st.success(u("Log updated."))
                                try:
                                    audit("log.update", who=staff_id, role=role,
                                          details={"patientID": sel.get("patientID"), "logID": sel.get("logID")})
                                except Exception:
                                    pass
                                st.rerun()
                            else:
                                st.error(u("Update failed (RBAC or not found)."))
                                try:
                                    audit("log.update_failed", who=staff_id, role=role,
                                          details={"patientID": sel.get("patientID"), "logID": sel.get("logID"),
                                                   "reason": "rbac_or_not_found"})
                                except Exception:
                                    pass

                    with cc2:
                        confirm_delete = st.checkbox(u("Confirm delete"), key=f"__confirm_delete__{ekey}")
                        if st.button(
                            u("Delete log"),
                            disabled=not (confirm_delete and allowed),
                            key=f"__delete_log__{ekey}",
                            use_container_width=True,
                        ):
                            # Controller exposes delete_log
                            ok = hasattr(ctrl, "delete_log") and ctrl.delete_log(sel["logID"])
                            if ok:
                                st.success(u("Log deleted."))
                                try:
                                    audit("log.delete", who=staff_id, role=role,
                                          details={"patientID": sel.get("patientID"), "logID": sel.get("logID")})
                                except Exception:
                                    pass
                                st.rerun()
                            else:
                                st.error(u("Delete failed (not found)."))
                                try:
                                    audit("log.delete_failed", who=staff_id, role=role,
                                          details={"patientID": sel.get("patientID"), "logID": sel.get("logID"),
                                                   "reason": "not_found"})
                                except Exception:
                                    pass
                else:
                    st.info(u("Select a log to manage."))

    # ---------------------------
    # TAB 2: SEARCH
    # ---------------------------
    with tab2:
        st.subheader(u("Search Patient Logs"))
        st.info(u("Search patient logs by keyword, with optional filters."))

        # Refresh index
        if st.button(u("🔄 Refresh Index"), help=u("Refresh search index with latest logs"), key="__refresh_idx__"):
            try:
                msg = ctrl.refresh_log_index()  # use Controller
                st.success(u(msg))
            except Exception:
                st.success(u("Index refreshed."))

        keyword = st.text_input(
            u("Enter keyword"), key="__search_kw__", placeholder=u("Enter search term..."),
            help=u("Search across log IDs, patient IDs, staff IDs, and notes")
        ).strip()

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            patient_filter = st.text_input(u("Filter by Patient ID (optional)"),
                                        key="__search_pid__", placeholder=u("e.g., P001")).strip()
        with col_f2:
            date_range = st.date_input(u("Date Range (optional)"), value=[],
                                    key="__search_dates__", help=u("Select start and end dates (click twice)"),
                                    max_value=date.today())

        date_tuple = None
        if date_range and isinstance(date_range, (list, tuple)):
            if len(date_range) == 2:
                date_tuple = (date_range[0].isoformat() + "T00:00:00", date_range[1].isoformat() + "T23:59:59")
            elif len(date_range) == 1:
                st.warning(u("⚠️ Please select both start and end dates."))

        col_btn1, col_btn2 = st.columns([3, 1])
        with col_btn1:
            search_clicked = st.button(u("🔍 Search Logs"), key="__do_search__", type="primary", use_container_width=True)
        with col_btn2:
            if "search_results" in st.session_state and st.session_state.search_results:
                if st.button(u("🧹 Clear"), key="__clear_search__", use_container_width=True):
                    st.session_state.search_results = None
                    st.rerun()

        if search_clicked:
            if not keyword:
                st.warning(u("⚠️ Please enter a keyword to search."))
            else:
                with st.spinner(u("Searching logs...")):
                    try:
                        start, end = (date_tuple or (None, None))
                        results = ctrl.search_logs(
                            keyword=keyword,
                            patient_id=(patient_filter or None),
                            start_date=start,
                            end_date=end
                        )
                        st.session_state.search_results = [_normalize_log(r) for r in (results or [])]
                        st.session_state.search_keyword = keyword
                        try:
                            audit("search.executed", who=staff_id, role=role,
                                details={"keyword": keyword, "patient_filter": patient_filter or None,
                                        "date_range": date_tuple, "results_count": len(results or [])})
                        except Exception:
                            pass
                    except Exception as e:
                        st.error(u(f"❌ Search failed: {str(e)}"))
                        st.session_state.search_results = None
                        try:
                            audit("search.failed", who=staff_id, role=role, details={"keyword": keyword, "error": str(e)})
                        except Exception:
                            pass

        if "search_results" in st.session_state and st.session_state.search_results is not None:
            results = st.session_state.search_results
            keyword = st.session_state.get("search_keyword", "")

            if not results:
                st.info(u("ℹ️ No matching logs found."))
            else:
                st.success(u(f"✅ Found {len(results)} matching log(s)."))

                # Use Controller highlight_text
                def mark(text: str):
                    try:
                        return ctrl.highlight_text(text or "", keyword).replace("<<", "<mark>").replace(">>", "</mark>")
                    except Exception:
                        return text or ""

                data = []
                for d in results:
                    data.append({
                        u("Log ID"): mark(d.get("logID")),
                        u("Timestamp"): d.get("timestamp"),
                        u("Patient ID"): mark(d.get("patientID")),
                        u("Staff ID"): mark(d.get("staffID")),
                        u("Temperature"): d.get("temperature", "N/A"),
                        u("Heart Rate"): d.get("heartRate", "N/A"),
                        u("Blood Pressure"): d.get("bloodPressure", "N/A"),
                        u("Notes"): mark(d.get("notes") or ""),
                    })

                df_results = pd.DataFrame(data)
                df_results[u("Timestamp")] = pd.to_datetime(df_results[u("Timestamp")], errors="coerce", utc=True)
                df_results = df_results.sort_values(by=u("Timestamp"), ascending=False)

                page_size = 15
                total_pages = (len(df_results) + page_size - 1) // page_size
                current_page = st.number_input(u("Page"), min_value=1, max_value=max(total_pages, 1), value=1, step=1, key="__page__")
                start_idx = (current_page - 1) * page_size
                end_idx = start_idx + page_size
                df_page = df_results.iloc[start_idx:end_idx]

                st.caption(u(f"Page {current_page} of {total_pages}"))
                st.dataframe(df_page, use_container_width=True)

                st.divider()
                col_export1, col_export2 = st.columns(2)
                with col_export1:
                    csv2 = df_results.to_csv(index=False)
                    st.download_button(
                        label=u("📥 Download as CSV"),
                        data=csv2,
                        file_name=f"search_results_{keyword}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        key="__dl_search_csv__",
                        use_container_width=True,
                    )
                with col_export2:
                    json_str2 = json.dumps(results, indent=2, ensure_ascii=False)
                    st.download_button(
                        label=u("📥 Download as JSON"),
                        data=json_str2,
                        file_name=f"search_results_{keyword}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        key="__dl_search_json__",
                        use_container_width=True,
                    )

                with st.expander(u("📊 Search Statistics")):
                    c1, c2, c3 = st.columns(3)
                    c1.metric(u("Unique Patients"), len(set(d.get("patientID") for d in results)))
                    c2.metric(u("Unique Staff"), len(set(d.get("staffID") for d in results)))
                    c3.metric(u("Total Logs"), len(results))

    # ---------------------------
    # TAB 3: ALERTS
    # ---------------------------
    with tab3:
        st.subheader(u("Alerts"))
        st.info(u("View, acknowledge, or export alerts related to your assigned patients."))

        # Use Controller wrapper instead of AlertEngine directly
        try:
            staff_alerts = ctrl.get_staff_alerts(staff_id) or []
        except Exception:
            staff_alerts = []

        if not staff_alerts:
            st.caption(u("No alerts available."))
        else:
            col1, col2 = st.columns([2, 1])
            with col1:
                severity_filter = st.selectbox("Filter by Severity", ["All", "Low", "Medium", "High"], key="sev_filter")
            with col2:
                show_unread = st.checkbox("Show Unread Only", value=False)

            alerts = staff_alerts
            if severity_filter != "All":
                alerts = [a for a in alerts if a.severity.lower() == severity_filter.lower()]
            if show_unread:
                alerts = [a for a in alerts if not a.isRead]

            alerts.sort(key=lambda a: a.timestamp, reverse=True)

            for alert in alerts:
                with st.container(border=True):
                    st.write(f"**Alert ID:** {alert.alertID}")
                    st.write(f"**Severity:** {alert.severity.capitalize()}")
                    st.write(f"**Patient ID:** {alert.patientID}")
                    st.write(f"**Timestamp:** {alert.timestamp}")
                    st.write(f"**Message:** {alert.message}")
                    st.write(f"**Read:** {'✅ Yes' if alert.isRead else '❌ No'}")

                    if not alert.isRead:
                        if st.button(f"Acknowledge {alert.alertID}", key=f"ack_{alert.alertID}", use_container_width=True):
                            try:
                                ctrl.mark_alert_as_read(alert.alertID, staff_id)  # call Controller method
                                st.success(f"Alert {alert.alertID} marked as read.")
                                audit("alert.acknowledged", who=staff_id, role=role, details={"alertID": alert.alertID})
                            except Exception:
                                st.error("Failed to acknowledge alert.")
                            st.rerun()

            st.divider()
            st.subheader("Summary")
            total = len(staff_alerts)
            unread = len([a for a in staff_alerts if not a.isRead])
            high = len([a for a in staff_alerts if a.severity.lower() == "high"])
            med = len([a for a in staff_alerts if a.severity.lower() == "medium"])
            low = len([a for a in staff_alerts if a.severity.lower() == "low"])

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Total Alerts", total)
            c2.metric("Unread", unread)
            c3.metric("High", high)
            c4.metric("Medium", med)
            c5.metric("Low", low)

            # Export alerts
            try:
                df_alerts = pd.DataFrame([a.to_dict() for a in alerts])
            except Exception:
                df_alerts = pd.DataFrame()

            if not df_alerts.empty:
                csv3 = df_alerts.to_csv(index=False)
                st.download_button(
                    label="📥 Export Alerts as CSV",
                    data=csv3,
                    file_name=f"alerts_{staff_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    key="__dl_alerts_csv__",
                    use_container_width=True,
                )

    # ---------------------------
    # TAB 4: PATIENT PREFERENCES (READ-ONLY)
    # ---------------------------
    with tab4:
        st.subheader(u("Patient Preferences (read-only)"))
        st.info(u("View the preferences for patients in your scope (Admin/SiteAdmin: all patients)."))

        if not staff_like:
            st.error(u("Access denied: staff/admin/siteadmin only."))
        else:
            if not my_patients:
                st.caption(u("No patients in your scope."))
            else:
                def _get(obj, key, default=None):
                    """Read attr or dict key safely."""
                    if obj is None:
                        return default
                    if hasattr(obj, key):
                        try:
                            val = getattr(obj, key)
                            return val if val not in (None, "") else default
                        except Exception:
                            pass
                    if isinstance(obj, dict):
                        val = obj.get(key, default)
                        return val if val not in (None, "") else default
                    return default

                def _to_list(v):
                    if v is None or v == "":
                        return []
                    if isinstance(v, list):
                        return v
                    if isinstance(v, str):
                        return [x.strip() for x in v.split(",") if x.strip()]
                    return []

                rows = []
                for pid in my_patients:
                    try:
                        prefs = ctrl.get_preferences(pid)  # via Controller
                    except Exception:
                        prefs = None

                    # Preferred language -> human name
                    lang_code = (
                        _get(prefs, "preferred_language")
                        or _get(prefs, "language")
                        or "-"
                    )
                    if isinstance(lang_code, str) and lang_code not in ("-", ""):
                        try:
                            lang_name = code_to_name(lang_code) or lang_code
                        except Exception:
                            lang_name = lang_code
                    else:
                        lang_name = "-"

                    # Dietary / cultural / religious / room type
                    dietary_list = _to_list(
                        _get(prefs, "dietaryNeeds")
                        or _get(prefs, "dietary")
                        or _get(prefs, "diet")
                    )
                    dietary_str = ", ".join(dietary_list) if dietary_list else "-"

                    room_type = (
                        _get(prefs, "roomType")
                        or _get(prefs, "preferred_room")
                        or _get(prefs, "room")
                        or "-"
                    )

                    cultural = _get(prefs, "culturalNeeds") or _get(prefs, "cultural") or "-"
                    religious_list = _to_list(_get(prefs, "religiousNeeds") or _get(prefs, "religious"))
                    religious = ", ".join(religious_list) if religious_list else "-"

                    rows.append({
                        u("Patient ID"): pid,
                        u("Preferred Language"): lang_name,
                        u("Dietary Needs"): dietary_str,
                        u("Room Type"): room_type,
                        u("Cultural Needs"): cultural,
                        u("Religious Needs"): religious,
                    })

                if rows:
                    df = pd.DataFrame(rows)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.caption(u("No preferences found for your patients."))

    # ---------------------------
    # TAB 5: REPORTS
    # ---------------------------
    with tab5:
        st.subheader(u("Generate Patient Report (PDF)"))
        st.info(u("Generate a one-patient PDF report (includes preferences + logs). Confirm before exporting."))

        if not staff_like:
            st.error(u("Access denied: staff/admin/siteadmin only."))
        else:
            if not my_patients:
                st.caption(u("No patients in your scope."))
            else:
                sel_pid = st.selectbox(u("Select patient for report"), options=my_patients, key="__report_pid__")
                period = st.selectbox(u("Period"), options=["weekly", "monthly"], index=0, key="__report_period__")
                st.caption(u("File name will be <patientID>_report_<YYYY-MM-DD>.pdf"))

                prev_pending = st.session_state.get("__report_pending_pid__")
                if prev_pending and prev_pending != sel_pid:
                    st.session_state.pop("__report_confirm__", None)
                    st.session_state.pop("__report_pending_pid__", None)

                if st.button(u("Generate Report (prepare)"), key="__prepare_report__"):
                    st.session_state["__report_pending_pid__"] = sel_pid
                    st.session_state["__report_confirm__"] = False
                    st.rerun()

                if st.session_state.get("__report_pending_pid__") == sel_pid:
                    st.markdown("---")
                    st.warning(u("Please confirm you want to generate a PDF for this patient."))
                    colc1, colc2 = st.columns([1, 1])
                    with colc1:
                        if st.button(u("Cancel"), key="__report_cancel__"):
                            st.session_state.pop("__report_pending_pid__", None)
                            st.session_state.pop("__report_confirm__", None)
                            st.rerun()
                    with colc2:
                        if st.button(u("Confirm and Generate PDF"), key="__report_confirm_btn__"):
                            st.session_state["__report_confirm__"] = True
                            st.rerun()

                if st.session_state.get("__report_confirm__") and st.session_state.get("__report_pending_pid__") == sel_pid:
                    if ReportGenerator is None:
                        st.error(u("Report generator not available. Install reportlab and ensure module import."))
                    else:
                        # Admin/SiteAdmin bypass assignment check
                        if role in {"admin", "siteadmin"} or is_allowed(staff_id, sel_pid):
                            with st.spinner(u("Generating PDF...")):
                                try:
                                    rg = ReportGenerator(getattr(ctrl, "db", None))  # pass Controller's DB to the generator
                                    pdf_bytes = rg.export_patient_report_to_pdf_bytes(
                                        patientID=sel_pid, staff_id=staff_id, period=period
                                    )
                                    filename = f"{sel_pid}_report_{date.today().isoformat()}.pdf"
                                    st.success(u("Report generated. Click to download."))
                                    st.download_button(
                                        label=u("📥 Download PDF"),
                                        data=pdf_bytes,
                                        file_name=filename,
                                        mime="application/pdf",
                                        key=f"__dl_report_{sel_pid}__",
                                    )
                                    try:
                                        audit("ui.report.generated", who=staff_id, role=role or "staff",
                                              details={"patientID": sel_pid, "period": period})
                                    except Exception:
                                        pass
                                except Exception as e:
                                    st.error(u(f"Failed to generate report: {e}"))
                                    try:
                                        audit("report.generate_failed", who=staff_id, role=role or "staff",
                                              details={"patientID": sel_pid, "error": str(e)})
                                    except Exception:
                                        pass
                                    st.session_state.pop("__report_confirm__", None)
                                    st.session_state.pop("__report_pending_pid__", None)
                        else:
                            st.error(u("You are not authorized to generate a report for this patient."))
                            try:
                                audit("report.generate_unauthorized", who=staff_id, role=role or "staff",
                                      details={"patientID": sel_pid, "reason": "not_allowed"})
                            except Exception:
                                pass