# app/core/search.py
import re
from datetime import datetime
from typing import List, Optional, Tuple
from app.database.database_Manager import DatabaseManager
from app.logging.logentry import LogEntry
from app.core.audit import audit

class SearchEngine:
    """
    Provides keyword and filter-based searching for log entries.
    Supports patient filtering, date range filtering, and keyword highlighting.
    """
    
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.index = []  # cached list of (logID, searchable text)
        self.index_logs()
    
    # ----------------------------
    # Indexing
    # ----------------------------
    def index_logs(self):
        """Build or refresh the in-memory log search index."""
        self.index.clear()
        for log in self.db.logs:
            if isinstance(log, LogEntry):
                # Combine searchable text fields
                note = getattr(log, 'note', '') or ''
                searchable_text = f"{log.logID} {log.patientID} {log.staffID} {note}".lower()
                self.index.append((log.logID, searchable_text))
        
        audit("search.index.refresh", None, None, {"total_logs": len(self.index)})
    
    # ----------------------------
    # Keyword Search
    # ----------------------------
    def search_logs(
        self,
        keyword: str,
        patient_id: Optional[str] = None,
        date_range: Optional[Tuple[str, str]] = None,
    ) -> List[LogEntry]:
        """
        Search logs by keyword, optional patientID, and optional date range.
        
        Args:
            keyword: string to search for (case-insensitive)
            patient_id: limit results to this patient
            date_range: (start_iso, end_iso) inclusive
        
        Returns:
            List of matching LogEntry objects
        """
        # Validate inputs
        if not keyword or not isinstance(keyword, str):
            return []
        
        keyword = keyword.lower().strip()
        if not keyword:
            return []
        
        # Parse date range once if provided
        start_dt = None
        end_dt = None
        if date_range:
            try:
                start_dt = self._parse_datetime(date_range[0])
                end_dt = self._parse_datetime(date_range[1])
                if start_dt > end_dt:
                    # Swap if reversed
                    start_dt, end_dt = end_dt, start_dt
            except (ValueError, TypeError, IndexError) as e:
                audit(
                    "search.logs.error",
                    who=None,
                    role=None,
                    details={"error": f"Invalid date range: {str(e)}"}
                )
                return []
        
        results = []
        matching_log_ids = set()
        
        # First pass: use index for keyword matching
        for log_id, searchable_text in self.index:
            if keyword in searchable_text:
                matching_log_ids.add(log_id)
        
        # Second pass: filter actual logs by ID and apply additional filters
        for log in self.db.logs:
            if not isinstance(log, LogEntry):
                continue
            
            # Check if log matched keyword search
            if log.logID not in matching_log_ids:
                continue
            
            # Apply patient filter
            if patient_id and log.patientID != patient_id:
                continue
            
            # Apply date range filter
            if date_range and start_dt and end_dt:
                try:
                    log_dt = self._parse_datetime(log.timestamp)
                    if not (start_dt <= log_dt <= end_dt):
                        continue
                except (ValueError, TypeError, AttributeError):
                    # Skip logs with invalid timestamps
                    continue
            
            results.append(log)
        
        # Audit the search
        audit(
            "search.logs",
            who=None,
            role=None,
            details={
                "keyword": keyword,
                "patient_filter": patient_id,
                "date_range_applied": date_range is not None,
                "matches": len(results),
            },
        )
        
        return results
    
    # ----------------------------
    # Helper Methods
    # ----------------------------
    def _parse_datetime(self, dt_str: str) -> datetime:
        """
        Parse ISO format datetime string, handling 'Z' suffix.
        
        Args:
            dt_str: ISO format datetime string
            
        Returns:
            datetime object
            
        Raises:
            ValueError: If datetime string is invalid
        """
        if not dt_str:
            raise ValueError("Empty datetime string")
        
        # Remove 'Z' suffix and parse
        cleaned = dt_str.replace("Z", "").replace("z", "")
        
        # Try different ISO formats
        for fmt in ["%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]:
            try:
                return datetime.strptime(cleaned, fmt)
            except ValueError:
                continue
        
        # Fallback to fromisoformat (Python 3.7+)
        try:
            return datetime.fromisoformat(cleaned)
        except ValueError:
            raise ValueError(f"Unable to parse datetime: {dt_str}")
    
    # ----------------------------
    # Alternative search function (alias)
    # ----------------------------
    def searchLogs(self, keyword: str) -> List[LogEntry]:
        """Alias for `search_logs` without filters."""
        return self.search_logs(keyword)
    
    # ----------------------------
    # Highlight Helper
    # ----------------------------
    def highlight_matches(self, text: str, keyword: str) -> str:
        """
        Highlight all keyword occurrences in the given text.
        Returns text with matches wrapped in << >> markers.
        
        Args:
            text: The text to highlight matches in
            keyword: The keyword to highlight
            
        Returns:
            Text with matches highlighted
        """
        if not keyword or not text:
            return text
        
        # Escape special regex characters to prevent injection
        escaped_keyword = re.escape(keyword.strip())
        
        try:
            pattern = re.compile(escaped_keyword, re.IGNORECASE)
            return pattern.sub(lambda m: f"<<{m.group(0)}>>", text)
        except re.error:
            # If regex compilation fails, return original text
            return text
    
    # ----------------------------
    # Index Management
    # ----------------------------
    def refresh_index(self):
        """Public method to manually refresh the search index."""
        self.index_logs()
    
    def get_index_size(self) -> int:
        """Return the number of indexed logs."""
        return len(self.index)