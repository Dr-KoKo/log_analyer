import pandas as pd
from typing import List, Dict, Any
from collections import defaultdict
from datetime import datetime, timedelta
from ..interfaces import LogAnalyzerInterface, LogEntry


class ErrorAnalyzer(LogAnalyzerInterface):
    """Analyzer focused on error log analysis with time-series capabilities"""
    
    def __init__(self):
        self.analysis_results = None
        self.time_series_data = None
        self.error_patterns = defaultdict(list)
        
    def analyze(self, logs: List[LogEntry]) -> pd.DataFrame:
        """Analyze error logs and return comprehensive results"""
        if not logs:
            return pd.DataFrame()
            
        # Convert to dataframe for easier analysis
        df = pd.DataFrame([log.to_dict() for log in logs])
        
        # Filter for errors only
        error_df = df[df['exception_type'].notna()].copy()
        
        if error_df.empty:
            return pd.DataFrame()
            
        # Extract additional information
        error_df['core_exception'] = error_df['exception_type'].str.extract(r'([A-Za-z0-9]+Exception)')
        error_df[['filename', 'line']] = error_df['file_line'].str.extract(r'([^:]+):(\d+)')
        error_df['hour'] = pd.to_datetime(error_df['timestamp']).dt.floor('H')
        error_df['date'] = pd.to_datetime(error_df['timestamp']).dt.date
        
        # Store for metrics
        self.analysis_results = error_df
        
        # Create summary
        summary = self._create_summary(error_df)
        
        return summary
    
    def _create_summary(self, error_df: pd.DataFrame) -> pd.DataFrame:
        """Create error summary with multiple groupings"""
        summaries = []
        
        # 1. Basic error count by type and location
        basic_summary = (
            error_df.groupby(['filename', 'line', 'core_exception'])
            .size()
            .reset_index(name='count')
            .rename(columns={'core_exception': 'exception'})
        )
        basic_summary['summary_type'] = 'by_location'
        summaries.append(basic_summary)
        
        # 2. Time-based summary (hourly)
        hourly_summary = (
            error_df.groupby(['hour', 'core_exception'])
            .size()
            .reset_index(name='count')
            .rename(columns={'core_exception': 'exception', 'hour': 'time_bucket'})
        )
        hourly_summary['summary_type'] = 'hourly'
        summaries.append(hourly_summary)
        
        # 3. Daily summary
        daily_summary = (
            error_df.groupby(['date', 'core_exception'])
            .size()
            .reset_index(name='count')
            .rename(columns={'core_exception': 'exception', 'date': 'time_bucket'})
        )
        daily_summary['summary_type'] = 'daily'
        summaries.append(daily_summary)
        
        # 4. Thread-based summary
        thread_summary = (
            error_df.groupby(['thread', 'core_exception'])
            .size()
            .reset_index(name='count')
            .rename(columns={'core_exception': 'exception'})
        )
        thread_summary['summary_type'] = 'by_thread'
        summaries.append(thread_summary)
        
        # Combine all summaries
        combined_summary = pd.concat(summaries, ignore_index=True)
        
        return combined_summary
    
    def get_metrics(self) -> Dict[str, Any]:
        """Return detailed analysis metrics"""
        if self.analysis_results is None:
            return {}
            
        df = self.analysis_results
        
        metrics = {
            'total_errors': len(df),
            'unique_error_types': df['core_exception'].nunique(),
            'affected_files': df['filename'].nunique(),
            'error_rate_per_hour': len(df) / ((df['timestamp'].max() - df['timestamp'].min()).total_seconds() / 3600),
            'top_errors': df['core_exception'].value_counts().head(10).to_dict(),
            'top_error_locations': df.groupby(['filename', 'line']).size().sort_values(ascending=False).head(10).to_dict(),
            'error_timeline': self._create_timeline_metrics(df),
            'error_patterns': self._detect_patterns(df)
        }
        
        return metrics
    
    def _create_timeline_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Create time-based metrics"""
        df['hour'] = pd.to_datetime(df['timestamp']).dt.floor('H')
        
        hourly_counts = df.groupby('hour').size()
        
        return {
            'peak_hour': hourly_counts.idxmax().strftime('%Y-%m-%d %H:00'),
            'peak_hour_count': int(hourly_counts.max()),
            'quiet_hour': hourly_counts.idxmin().strftime('%Y-%m-%d %H:00'),
            'quiet_hour_count': int(hourly_counts.min()),
            'avg_errors_per_hour': float(hourly_counts.mean())
        }
    
    def _detect_patterns(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect error patterns and anomalies"""
        patterns = []
        
        # Pattern 1: Burst detection (many errors in short time)
        df_sorted = df.sort_values('timestamp')
        for i in range(len(df_sorted) - 10):
            window = df_sorted.iloc[i:i+10]
            time_diff = (window['timestamp'].iloc[-1] - window['timestamp'].iloc[0]).total_seconds()
            if time_diff < 60:  # 10 errors within 1 minute
                patterns.append({
                    'type': 'burst',
                    'start_time': window['timestamp'].iloc[0],
                    'end_time': window['timestamp'].iloc[-1],
                    'count': 10,
                    'duration_seconds': time_diff
                })
        
        # Pattern 2: Repeating errors
        error_groups = df.groupby(['core_exception', 'filename', 'line']).size()
        repeating = error_groups[error_groups > 5]
        for (exc, file, line), count in repeating.items():
            patterns.append({
                'type': 'repeating',
                'exception': exc,
                'location': f"{file}:{line}",
                'count': int(count)
            })
        
        return patterns[:10]  # Limit to top 10 patterns
