import re
import os
import zipfile
from datetime import datetime
from typing import List, Dict, Any, Optional
from ..interfaces import LogSourceInterface, LogEntry


class FileLogSource(LogSourceInterface):
    """Implementation for file-based log sources (single files or zip archives)"""
    
    def __init__(self):
        self.file_path = None
        self.encoding = 'utf-8'
        self.log_patterns = {
            'tomcat': {
                'error': [
                    re.compile(
                        r"(?P<timestamp>\d{2}-\w{3}-\d{4} \d{2}:\d{2}:\d{2}\.\d{3}) "
                        r"심각 \[(?P<thread>[^\]]+)\] (?P<logger>[^\s]+) "
                        r"(?P<message>.*?)nested exception is (?P<exception>[^\:]+)"
                        r"(?:\: (?P<exc_message>.+?))?\s+at (?P<location>[^\(]+)\((?P<file>[^\)]+)\)",
                        re.DOTALL
                    ),
                    re.compile(
                        r"(?P<timestamp>\d{2}-\w{3}-\d{4} \d{2}:\d{2}:\d{2}\.\d{3}) "
                        r"심각 \[(?P<thread>[^\]]+)\] (?P<logger>[^\s]+) "
                        r"(?P<message>.*?)with root cause\s+(?P<exception>[a-zA-Z0-9\._]+): "
                        r"(?P<exc_message>.+?)\s+at (?P<location>[^\(]+)\((?P<file>[^\)]+)\)",
                        re.DOTALL
                    )
                ],
                'general': re.compile(
                    r"(?P<timestamp>\d{2}-\w{3}-\d{4} \d{2}:\d{2}:\d{2}\.\d{3}) "
                    r"(?P<level>정보|경고|심각|디버그) \[(?P<thread>[^\]]+)\] "
                    r"(?P<logger>[^\s]+) (?P<message>.*?)(?=\n\d{2}-\w{3}-\d{4}|$)",
                    re.DOTALL
                )
            }
        }
        self.month_map = {
            'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
            'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
            'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
        }
        
    def connect(self, file_path: str, encoding: str = 'utf-8', **kwargs) -> None:
        """Connect to file source"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        self.file_path = file_path
        self.encoding = encoding
        
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse Korean format timestamp to datetime object"""
        # Format: 10-Jun-2025 08:26:46.310
        parts = timestamp_str.split()
        date_parts = parts[0].split('-')
        time_parts = parts[1].split('.')
        
        day = date_parts[0]
        month = self.month_map.get(date_parts[1], '01')
        year = date_parts[2]
        time = time_parts[0]
        milliseconds = time_parts[1] if len(time_parts) > 1 else '000'
        
        datetime_str = f"{year}-{month}-{day} {time}.{milliseconds}"
        return datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S.%f")
    
    def _extract_entries_from_content(self, content: str, source_filename: str) -> List[LogEntry]:
        """Extract log entries from file content"""
        entries = []
        
        # First, try to extract error entries
        for pattern in self.log_patterns['tomcat']['error']:
            for match in pattern.finditer(content):
                try:
                    timestamp = self._parse_timestamp(match.group("timestamp"))
                    entries.append(LogEntry(
                        timestamp=timestamp,
                        level="심각",
                        thread=match.group("thread") if "thread" in match.groupdict() else "",
                        logger=match.group("logger") if "logger" in match.groupdict() else "",
                        message=match.group("message").strip() if match.group("message") else "",
                        exception_type=match.group("exception").strip(),
                        exception_message=match.group("exc_message").strip() if match.group("exc_message") else "",
                        location=match.group("location").strip(),
                        file_line=match.group("file").strip(),
                        raw_content=match.group(0)
                    ))
                except Exception as e:
                    print(f"Error parsing log entry: {e}")
                    
        # Also extract general log entries for complete analysis
        general_pattern = self.log_patterns['tomcat']['general']
        for match in general_pattern.finditer(content):
            try:
                timestamp = self._parse_timestamp(match.group("timestamp"))
                level = match.group("level")
                
                # Skip if it's an error that was already captured
                is_error = level == "심각" and any(
                    entry.timestamp == timestamp and entry.level == level 
                    for entry in entries
                )
                
                if not is_error:
                    entries.append(LogEntry(
                        timestamp=timestamp,
                        level=level,
                        thread=match.group("thread"),
                        logger=match.group("logger"),
                        message=match.group("message").strip(),
                        exception_type=None,
                        exception_message=None,
                        location=None,
                        file_line=None,
                        raw_content=match.group(0)
                    ))
            except Exception as e:
                print(f"Error parsing general log entry: {e}")
                
        return entries
    
    def fetch_logs(self, 
                   start_time: Optional[datetime] = None,
                   end_time: Optional[datetime] = None,
                   filters: Optional[Dict[str, Any]] = None) -> List[LogEntry]:
        """Fetch logs from file with optional filters"""
        if not self.file_path:
            raise ValueError("No file connected. Call connect() first.")
            
        all_entries = []
        
        if self.file_path.endswith(".zip"):
            with zipfile.ZipFile(self.file_path, "r") as z:
                for name in z.namelist():
                    if name.endswith(".log"):
                        with z.open(name) as log_file:
                            content = log_file.read().decode(self.encoding, errors="ignore")
                            entries = self._extract_entries_from_content(content, name)
                            all_entries.extend(entries)
        else:
            with open(self.file_path, "r", encoding=self.encoding) as f:
                content = f.read()
            all_entries = self._extract_entries_from_content(
                content, os.path.basename(self.file_path)
            )
        
        # Apply time filters
        if start_time:
            all_entries = [e for e in all_entries if e.timestamp >= start_time]
        if end_time:
            all_entries = [e for e in all_entries if e.timestamp <= end_time]
            
        # Apply custom filters
        if filters:
            if 'level' in filters:
                all_entries = [e for e in all_entries if e.level == filters['level']]
            if 'exception_type' in filters:
                all_entries = [e for e in all_entries if e.exception_type == filters['exception_type']]
            if 'thread_pattern' in filters:
                pattern = re.compile(filters['thread_pattern'])
                all_entries = [e for e in all_entries if pattern.search(e.thread)]
                
        return all_entries
    
    def close(self) -> None:
        """Close file connection"""
        self.file_path = None
