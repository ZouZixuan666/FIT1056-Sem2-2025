# app/reports/report_Generator.py
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import io
import os
import json
import tempfile

# DB import (tolerant)
try:
    from app.database.database_Manager import DatabaseManager
except Exception:
    class DatabaseManager:  # type: ignore
        pass

# ReportLab (optional; we fall back if missing)
try:
    import reportlab  # type: ignore
    from reportlab.lib.pagesizes import A4  # type: ignore
    from reportlab.lib.styles import getSampleStyleSheet  # type: ignore
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle  # type: ignore
    from reportlab.lib import colors  # type: ignore
except Exception:
    reportlab = None  # type: ignore


class ReportGenerator:
    """
    Patient report generator/exporter.

    You get:
      - JSON reports: generate_patient_report / generate_multi_patient_report / export_report_to_file
      - PDF bytes: export_patient_report_to_pdf_bytes(patientID, staff_id, period)
      - PDF to disk: export_patient_report_to_pdf(staff_id, patientID, out_path, period=None)

    RBAC:
      - Admin/SiteAdmin: always allowed
      - Others: must be assigned via assignment_Store.is_allowed(staff, patient)
    """

    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or DatabaseManager(data_dir="data")

    # ---------- Authorization ----------
    def _get_role_for_user(self, user_id: str) -> str:
        role = ""
        try:
            if hasattr(self.db, "user_get"):
                rec = self.db.user_get(user_id)
                if isinstance(rec, dict):
                    role = (rec.get("role") or "").lower()
                elif hasattr(rec, "role"):
                    role = str(getattr(rec, "role", "")).lower()
        except Exception:
            pass
        return role

    def _enforce_export_permission(self, staff_id: str, patient_id: str) -> None:
        role = self._get_role_for_user(staff_id)
        if role in {"admin", "siteadmin"}:
            return
        try:
            from app.core.assignment_Store import is_allowed  # late import
        except Exception:
            raise PermissionError(
                f"Authorization module unavailable; cannot verify permission for '{staff_id}'."
            )
        if not is_allowed(staff_id, patient_id):
            raise PermissionError(
                f"Staff '{staff_id}' is not authorized to export patient '{patient_id}'."
            )

    # ---------- Helpers ----------
    def _safe_to_dict(self, obj: Any) -> Dict[str, Any]:
        if obj is None:
            return {}
        if isinstance(obj, dict):
            return obj
        if is_dataclass(obj):
            return asdict(obj)
        out: Dict[str, Any] = {}
        for k in ("patientID", "userID", "id", "name", "age", "condition", "assignedStaffID"):
            if hasattr(obj, k):
                out[k] = getattr(obj, k)
        return out or {"repr": repr(obj)}

    def _get_patient_record(self, patient_id: str) -> Dict[str, Any]:
        try:
            if hasattr(self.db, "get_patient"):
                p = self.db.get_patient(patient_id)
                if p:
                    return self._safe_to_dict(p)
        except Exception:
            pass
        try:
            pmap = getattr(self.db, "patients", {}) or {}
            p = pmap.get(patient_id)
            if p:
                return self._safe_to_dict(p)
        except Exception:
            pass
        try:
            if hasattr(self.db, "user_get"):
                urec = self.db.user_get(patient_id)
                if urec:
                    d = self._safe_to_dict(urec)
                    d.setdefault("patientID", patient_id)
                    return d
        except Exception:
            pass
        return {"patientID": patient_id, "name": "", "age": None, "condition": ""}

    def _get_recent_logs(self, patient_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        logs: List[Dict[str, Any]] = []

        try:
            if hasattr(self.db, "get_logs_for_patient"):
                arr = self.db.get_logs_for_patient(patient_id) or []
                for x in arr:
                    logs.append(x if isinstance(x, dict) else self._safe_to_dict(x))
        except Exception:
            pass

        if not logs:
            try:
                raw_logs = getattr(self.db, "logs", []) or []
                for x in raw_logs:
                    if isinstance(x, dict) and x.get("patientID") == patient_id:
                        logs.append(x)
                    elif hasattr(x, "patientID") and getattr(x, "patientID") == patient_id:
                        logs.append(self._safe_to_dict(x))
            except Exception:
                pass

        def _key(d: Dict[str, Any]):
            t = d.get("timestamp") or d.get("time") or d.get("createdAt")
            try:
                return datetime.fromisoformat(str(t))
            except Exception:
                return datetime.min

        logs.sort(key=_key, reverse=True)
        return logs[:limit]

    # ---------- JSON report API ----------
    def generate_patient_report(self, patientID: str) -> Optional[Dict[str, Any]]:
        patient = self.db.get_patient(patientID) if hasattr(self.db, "get_patient") else None
        if not patient:
            return {"No Records Found": None}

        logs = [l for l in getattr(self.db, "logs", []) if getattr(l, "patientID", None) == patientID]
        if not logs:
            return {"No Records Found": None}

        logs.sort(key=lambda x: x.timestamp)
        temps = [l.temperature for l in logs if l.temperature is not None]
        hrs = [l.heartRate for l in logs if l.heartRate is not None]

        avg_temp = round(sum(temps) / len(temps), 1) if temps else None
        avg_hr = round(sum(hrs) / len(hrs), 1) if hrs else None

        return {
            "Patient ID": getattr(patient, "patientID", None),
            "Name": getattr(patient, "name", None),
            "Condition": getattr(patient, "condition", None),
            "Age": getattr(patient, "age", None),
            "Assigned Staff": getattr(patient, "assignedStaffID", None),
            "Registered On": logs[0].timestamp,
            "Average Temperature": avg_temp if avg_temp is not None else "N/A",
            "Average Heart Rate": avg_hr if avg_hr is not None else "N/A",
            "Recent Logs": [
                {
                    "Time": l.timestamp,
                    "Temp": l.temperature,
                    "HR": l.heartRate,
                    "BP": l.bloodPressure,
                    "Notes": l.notes,
                }
                for l in logs[-3:]
            ],
        }

    def generate_multi_patient_report(self, patient_ids: List[str]) -> List[Dict[str, Any]]:
        return [r for pid in patient_ids if (r := self.generate_patient_report(pid))]

    def export_report_to_file(self, reports: List[Dict[str, Any]], filename: str) -> None:
        os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(reports, f, indent=4)

    # ---------- Minimal PDF (fallback) ----------
    def _write_pdf_minimal_to_path(self, title: str, body_lines: List[str], out_path: str) -> str:
        def esc(s: str) -> str:
            return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        lines = [title, ""] + body_lines
        text = "\n".join(lines)
        xobj_stream = f"""BT
/F1 12 Tf
50 780 Td
({esc(title)}) Tj
0 -24 Td
/F1 9 Tf
({esc(text)}) Tj
ET"""
        xobj_bytes = xobj_stream.encode("latin-1", "ignore")
        xlen = len(xobj_bytes)

        pdf_parts = []
        pdf_parts.append(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        xref_positions = []

        def _pos() -> int:
            return sum(len(p) for p in pdf_parts)

        def _add(obj: bytes) -> None:
            xref_positions.append(_pos())
            pdf_parts.append(obj)

        _add(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
        _add(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
        _add(b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> /XObject << /X1 4 0 R >> >> /Contents 6 0 R >>\nendobj\n")
        _add(
            f"4 0 obj\n<< /Type /XObject /Subtype /Form /BBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Length {xlen} >>\nstream\n".encode()
            + xobj_bytes + b"\nendstream\nendobj\n"
        )
        _add(b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")
        content_stream = b"q 1 0 0 1 0 0 cm /X1 Do Q\n"
        _add(b"6 0 obj\n<< /Length " + str(len(content_stream)).encode() + b" >>\nstream\n" + content_stream + b"\nendstream\nendobj\n")

        xref_start = _pos()
        xref = ["xref", f"0 {len(xref_positions)+1}", "0000000000 65535 f "]
        for pos in xref_positions:
            xref.append(f"{pos:010d} 00000 n ")
        xref_bytes = ("\n".join(xref) + "\n").encode()
        trailer = f"""trailer
<< /Size {len(xref_positions)+1} /Root 1 0 R >>
startxref
{xref_start}
%%EOF
""".encode()

        pdf = b"".join(pdf_parts) + xref_bytes + trailer
        with open(out_path, "wb") as f:
            f.write(pdf)
        return out_path

    def _write_pdf_minimal_to_bytes(self, title: str, body_lines: List[str]) -> bytes:
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "tmp.pdf")
            self._write_pdf_minimal_to_path(title, body_lines, path)
            with open(path, "rb") as fh:
                return fh.read()

    # ---------- Rich PDF (ReportLab) ----------
    def _build_rich_pdf_bytes(self, heading: str, report: Dict[str, Any], staff_id: str) -> bytes:
        if reportlab is None:
            raise ImportError("reportlab is required for rich PDF output.")

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph(heading, styles["Title"]))
        story.append(Paragraph(f"Generated by: {staff_id or 'system'}", styles["Normal"]))
        story.append(Paragraph(f"Generated at: {datetime.now(timezone.utc).isoformat()}", styles["Normal"]))
        story.append(Spacer(1, 12))

        # Demographics
        story.append(Paragraph("Demographics", styles["Heading2"]))
        demo_rows = [
            ["Patient ID", str(report.get("Patient ID") or "-")],
            ["Name", str(report.get("Name") or "-")],
            ["Age", str(report.get("Age") or "-")],
            ["Condition", str(report.get("Condition") or "-")],
            ["Assigned Staff", str(report.get("Assigned Staff") or "-")],
        ]
        t_demo = Table(demo_rows, hAlign="LEFT", colWidths=[140, 360])
        t_demo.setStyle(TableStyle([("GRID", (0,0), (-1,-1), 0.25, colors.grey),
                                    ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f8f8f8"))]))
        story.append(t_demo)
        story.append(Spacer(1, 10))

        # Averages
        story.append(Paragraph("Averages", styles["Heading2"]))
        avg_rows = [
            ["Average Temperature (°C)", str(report.get("Average Temperature") if report.get("Average Temperature") is not None else "-")],
            ["Average Heart Rate (bpm)", str(report.get("Average Heart Rate") if report.get("Average Heart Rate") is not None else "-")],
        ]
        t_avg = Table(avg_rows, hAlign="LEFT", colWidths=[200, 300])
        t_avg.setStyle(TableStyle([("GRID", (0,0), (-1,-1), 0.25, colors.grey)]))
        story.append(t_avg)
        story.append(Spacer(1, 10))

        # Logs
        story.append(Paragraph("Recent Logs (most recent first)", styles["Heading2"]))
        logs_list = report.get("Logs") or []
        if not logs_list:
            story.append(Paragraph("No logs for the selected period.", styles["Normal"]))
        else:
            header = [["Timestamp", "Staff", "Temp(°C)", "HR(bpm)", "BP", "Notes"]]
            rows = []
            for r in logs_list:
                rows.append([
                    str(r.get("Time") or "-"),
                    str(r.get("Staff") or "-"),
                    str(r.get("Temp") or "-"),
                    str(r.get("HR") or "-"),
                    str(r.get("BP") or "-"),
                    str(r.get("Notes") or "-")[:300],
                ])
            table_data = header + rows
            tbl = Table(table_data, repeatRows=1, colWidths=[110, 70, 70, 70, 70, 240])
            tbl.setStyle(TableStyle([
                ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f2f2f2")),
            ]))
            story.append(tbl)

        doc.build(story)
        buffer.seek(0)
        return buffer.read()


    # ---------- Public PDF APIs ----------
    def export_patient_report_to_pdf(
        self,
        staff_id: str,
        patientID: str,
        out_path: str,
        period: str | None = None,
    ) -> str:
        """Write a PDF to disk. If `period` supplied, use filtered bytes API first."""
        if not staff_id or not patientID or not out_path:
            raise ValueError("staff_id, patientID and out_path are required")

        if period:
            pdf_bytes = self.export_patient_report_to_pdf_bytes(
                patientID=patientID, staff_id=staff_id, period=period
            )
            os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
            with open(out_path, "wb") as fh:
                fh.write(pdf_bytes)
            return out_path

        self._enforce_export_permission(staff_id, patientID)

        p = self._get_patient_record(patientID)
        logs = self._get_recent_logs(patientID, limit=50)

        title = f"Patient Report — {p.get('patientID') or patientID}  ({datetime.now().isoformat(timespec='seconds')})"
        body: list[str] = []
        body.append(f"Patient ID : {p.get('patientID') or patientID}")
        if p.get("name"): body.append(f"Name       : {p.get('name')}")
        if p.get("age") is not None: body.append(f"Age        : {p.get('age')}")
        if p.get("condition"): body.append(f"Condition  : {p.get('condition')}")
        if p.get("assignedStaffID"): body.append(f"Assigned   : {p.get('assignedStaffID')}")
        body.append("")
        body.append(f"Exported by: {staff_id}")
        body.append("")

        if logs:
            body.append("Recent Logs (most recent first):")
            for i, lg in enumerate(logs, 1):
                ts = (lg.get("timestamp") if isinstance(lg, dict) else getattr(lg, "timestamp", "")) or ""
                sid = (lg.get("staffID") if isinstance(lg, dict) else getattr(lg, "staffID", "")) or ""
                temp = (lg.get("temperature") if isinstance(lg, dict) else getattr(lg, "temperature", None))
                pulse = (lg.get("pulse") if isinstance(lg, dict) else None) or (lg.get("heartRate") if isinstance(lg, dict) else getattr(lg, "heartRate", None))
                note = (lg.get("note") if isinstance(lg, dict) else None) or (lg.get("notes") if isinstance(lg, dict) else getattr(lg, "notes", None)) or ""
                line = f"{i:02d}. {ts}  staff={sid}"
                if temp is not None: line += f"  temp={temp}"
                if pulse is not None: line += f"  pulse={pulse}"
                if note:
                    snip = str(note).replace("\n", " ")
                    if len(snip) > 160: snip = snip[:157] + "..."
                    line += f"  note={snip}"
                body.append(line)
        else:
            body.append("No logs found for this patient.")

        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        if reportlab is None:
            return self._write_pdf_minimal_to_path(title, body, out_path)

        try:
            prefs = self.db.get_preferences(patientID)
            prefs = prefs.to_dict() if prefs and hasattr(prefs, "to_dict") else prefs
        except Exception:
            prefs = None

        rich = {
            "Patient ID": p.get("patientID") or patientID,
            "Name": p.get("name"),
            "Condition": p.get("condition"),
            "Age": p.get("age"),
            "Assigned Staff": p.get("assignedStaffID"),
            "Average Temperature": "-",
            "Average Heart Rate": "-",
            "Preferences": prefs,
            "Logs": [
                {
                    "Time": lg.get("timestamp"),
                    "Staff": lg.get("staffID"),
                    "Temp": lg.get("temperature"),
                    "HR": lg.get("heartRate") or lg.get("pulse"),
                    "BP": lg.get("bloodPressure"),
                    "Notes": lg.get("notes") or lg.get("note"),
                }
                for lg in logs
            ],
        }
        pdf_bytes = self._build_rich_pdf_bytes(
            f"Patient Report — {rich['Patient ID']}", rich, staff_id=staff_id
        )
        with open(out_path, "wb") as fh:
            fh.write(pdf_bytes)
        return out_path

    def export_patient_report_to_pdf_bytes(self, patientID: str, staff_id: str, period: str = "weekly") -> bytes:
        """Return PDF bytes filtered by period ('weekly' or 'monthly')."""
        self._enforce_export_permission(staff_id, patientID)

        if period not in ("weekly", "monthly"):
            raise ValueError("period must be 'weekly' or 'monthly'")

        patient = self.db.get_patient(patientID) if hasattr(self.db, "get_patient") else None
        if not patient:
            raise ValueError(f"Patient '{patientID}' not found")

        days = 7 if period == "weekly" else 30
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        try:
            logs = self.db.retrieve_logs(patientID=patientID)
        except Exception:
            logs = [l for l in getattr(self.db, "logs", []) if getattr(l, "patientID", None) == patientID]

        def _parse_iso_to_dt(ts: Optional[str]) -> Optional[datetime]:
            if not ts:
                return None
            try:
                ts2 = ts[:-1] + "+00:00" if ts.endswith("Z") else ts
                dt = datetime.fromisoformat(ts2)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except Exception:
                try:
                    return datetime.strptime(ts.split(".")[0], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
                except Exception:
                    return None

        period_logs = []
        for l in logs:
            ts_raw = getattr(l, "timestamp", None)
            if ts_raw is None and isinstance(l, dict):
                ts_raw = l.get("timestamp")
            dt = _parse_iso_to_dt(ts_raw)
            if dt is None or dt >= cutoff:
                period_logs.append(l)

        temps = [getattr(l, "temperature", None) for l in period_logs if getattr(l, "temperature", None) is not None]
        hrs = [getattr(l, "heartRate", None) for l in period_logs if getattr(l, "heartRate", None) is not None]
        avg_temp = round(sum(temps) / len(temps), 1) if temps else None
        avg_hr = round(sum(hrs) / len(hrs), 1) if hrs else None

        try:
            prefs = self.db.get_preferences(patientID)
        except Exception:
            prefs = None

        report = {
            "Patient ID": getattr(patient, "patientID", None),
            "Name": getattr(patient, "name", None),
            "Condition": getattr(patient, "condition", None),
            "Age": getattr(patient, "age", None),
            "Assigned Staff": getattr(patient, "assignedStaffID", None),
            "Period": period,
            "GeneratedAt": datetime.now(timezone.utc).isoformat(),
            "Average Temperature": avg_temp,
            "Average Heart Rate": avg_hr,
            "Preferences": prefs.to_dict() if prefs is not None and hasattr(prefs, "to_dict") else (prefs if prefs is not None else None),
            "Logs": [
                {
                    "Time": getattr(l, "timestamp", None),
                    "Temp": getattr(l, "temperature", None),
                    "HR": getattr(l, "heartRate", None),
                    "BP": getattr(l, "bloodPressure", None),
                    "Notes": getattr(l, "notes", None),
                    "Staff": getattr(l, "staffID", None),
                }
                for l in reversed(period_logs[-50:])
            ],
        }

        if reportlab is None:
            title = f"Patient Report — {report.get('Patient ID') or '-'}"
            lines: List[str] = [
                f"Generated by: {staff_id}",
                f"Period: {period}    Generated at: {report.get('GeneratedAt')}",
                "",
                "Demographics",
                f"Patient ID: {report.get('Patient ID') or '-'}",
                f"Name      : {report.get('Name') or '-'}",
                f"Age       : {report.get('Age') or '-'}",
                f"Condition : {report.get('Condition') or '-'}",
                f"Assigned  : {report.get('Assigned Staff') or '-'}",
                "",
                "Averages",
                f"Avg Temp (°C): {report.get('Average Temperature') if report.get('Average Temperature') is not None else '-'}",
                f"Avg HR (bpm): {report.get('Average Heart Rate') if report.get('Average Heart Rate') is not None else '-'}",
                "",
                "Recent Logs (most recent first)",
            ]
            for r in (report.get("Logs") or []):
                lines.append(
                    f"{r.get('Time') or '-'}  staff={r.get('Staff') or '-'}  "
                    f"temp={r.get('Temp') if r.get('Temp') is not None else '-'}  "
                    f"hr={r.get('HR') if r.get('HR') is not None else '-'}  "
                    f"bp={r.get('BP') or '-'}  "
                    f"notes={(r.get('Notes') or '')[:120]}"
                )
            return self._write_pdf_minimal_to_bytes(title, lines)

        return self._build_rich_pdf_bytes(
            heading=f"Patient Report — {report.get('Patient ID') or '-'}",
            report=report,
            staff_id=staff_id,
        )

    def save_patient_pdf_to_disk(self, patientID: str, staff_id: str, out_path: str, period: str = "weekly") -> str:
        pdf_bytes = self.export_patient_report_to_pdf_bytes(patientID, staff_id, period=period)
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with open(out_path, "wb") as fh:
            fh.write(pdf_bytes)
        return out_path
