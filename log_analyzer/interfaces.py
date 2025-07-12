from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd


class LogEntry:
    """Represents a single log entry with parsed information"""
    def __init__(self, 
                 timestamp: datetime,
                 level: str,
                 thread: str,
                 logger: str,
                 message: str,
                 exception_type: Optional[str] = None,
                 exception_message: Optional[str] = None,
                 location: Optional[str] = None,
                 file_line: Optional[str] = None,
                 raw_content: Optional[str] = None):
        self.timestamp = timestamp
        self.level = level
        self.thread = thread
        self.logger = logger
        self.message = message
        self.exception_type = exception_type
        self.exception_message = exception_message
        self.location = location
        self.file_line = file_line
        self.raw_content = raw_content

    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp,
            'level': self.level,
            'thread': self.thread,
            'logger': self.logger,
            'message': self.message,
            'exception_type': self.exception_type,
            'exception_message': self.exception_message,
            'location': self.location,
            'file_line': self.file_line
        }


class LogSourceInterface(ABC):
    """Abstract interface for different log sources"""
    
    @abstractmethod
    def connect(self, **kwargs) -> None:
        """Connect to the log source"""
        pass
    
    @abstractmethod
    def fetch_logs(self, 
                   start_time: Optional[datetime] = None,
                   end_time: Optional[datetime] = None,
                   filters: Optional[Dict[str, Any]] = None) -> List[LogEntry]:
        """Fetch logs from the source with optional time range and filters"""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close connection to the log source"""
        pass


class LogAnalyzerInterface(ABC):
    """Abstract interface for log analysis operations"""
    
    @abstractmethod
    def analyze(self, logs: List[LogEntry]) -> pd.DataFrame:
        """Analyze logs and return results as DataFrame"""
        pass
    
    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """Return analysis metrics"""
        pass
