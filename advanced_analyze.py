#!/usr/bin/env python3
"""
Advanced Log Analyzer - CLI tool for sophisticated log analysis
Supports multiple data sources and provides detailed analytics
"""

import argparse
import sys
from datetime import datetime, timedelta
from typing import Optional
from log_analyzer.sources.file_source import FileLogSource
from log_analyzer.sources.elk_source import ElkLogSource
from log_analyzer.analyzers.error_analyzer import ErrorAnalyzer
import pandas as pd
import json


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Advanced Log Analyzer with pluggable data sources",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a log file
  python advanced_analyze.py --source file --input server.log
  
  # Analyze a zip archive
  python advanced_analyze.py --source file --input logs.zip --output analysis.csv
  
  # Connect to Elasticsearch (future)
  python advanced_analyze.py --source elk --host localhost --port 9200 --index logs-*
  
  # Filter by time range
  python advanced_analyze.py --source file --input server.log --last-hours 24
  
  # Export detailed metrics
  python advanced_analyze.py --source file --input server.log --metrics metrics.json
        """
    )
    
    # Source selection
    parser.add_argument(
        '--source', '-s',
        choices=['file', 'elk'],
        default='file',
        help='Log source type (default: file)'
    )
    
    # File source options
    parser.add_argument(
        '--input', '-i',
        help='Input file path (for file source)'
    )
    
    # ELK source options
    parser.add_argument(
        '--host',
        default='localhost',
        help='Elasticsearch host (for elk source)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=9200,
        help='Elasticsearch port (for elk source)'
    )
    parser.add_argument(
        '--index',
        default='logs-*',
        help='Elasticsearch index pattern (for elk source)'
    )
    parser.add_argument(
        '--username',
        help='Elasticsearch username (optional)'
    )
    parser.add_argument(
        '--password',
        help='Elasticsearch password (optional)'
    )
    
    # Time filters
    parser.add_argument(
        '--start-time',
        help='Start time (ISO format: YYYY-MM-DD HH:MM:SS)'
    )
    parser.add_argument(
        '--end-time',
        help='End time (ISO format: YYYY-MM-DD HH:MM:SS)'
    )
    parser.add_argument(
        '--last-hours',
        type=int,
        help='Analyze logs from last N hours'
    )
    parser.add_argument(
        '--last-days',
        type=int,
        help='Analyze logs from last N days'
    )
    
    # Output options
    parser.add_argument(
        '--output', '-o',
        help='Output CSV file for analysis results'
    )
    parser.add_argument(
        '--metrics', '-m',
        help='Output JSON file for detailed metrics'
    )
    parser.add_argument(
        '--format',
        choices=['summary', 'detailed', 'json'],
        default='summary',
        help='Output format (default: summary)'
    )
    
    # Analysis options
    parser.add_argument(
        '--level',
        choices=['정보', '경고', '심각'],
        help='Filter by log level'
    )
    parser.add_argument(
        '--exception',
        help='Filter by exception type'
    )
    parser.add_argument(
        '--thread-pattern',
        help='Filter by thread name pattern (regex)'
    )
    
    return parser.parse_args()


def get_time_filters(args) -> tuple[Optional[datetime], Optional[datetime]]:
    """Parse time filter arguments"""
    start_time = None
    end_time = None
    
    if args.start_time:
        start_time = datetime.fromisoformat(args.start_time)
    elif args.last_hours:
        start_time = datetime.now() - timedelta(hours=args.last_hours)
    elif args.last_days:
        start_time = datetime.now() - timedelta(days=args.last_days)
    
    if args.end_time:
        end_time = datetime.fromisoformat(args.end_time)
    
    return start_time, end_time


def main():
    args = parse_arguments()
    
    # Initialize the appropriate source
    if args.source == 'file':
        if not args.input:
            print("Error: --input is required for file source")
            sys.exit(1)
        
        source = FileLogSource()
        try:
            source.connect(args.input)
            print(f"✅ Connected to file: {args.input}")
        except Exception as e:
            print(f"❌ Error connecting to file: {e}")
            sys.exit(1)
            
    elif args.source == 'elk':
        source = ElkLogSource()
        try:
            source.connect(
                host=args.host,
                port=args.port,
                index_pattern=args.index,
                username=args.username,
                password=args.password
            )
            print(f"✅ Connected to Elasticsearch: {args.host}:{args.port}")
        except Exception as e:
            print(f"❌ Error connecting to Elasticsearch: {e}")
            sys.exit(1)
    
    # Prepare filters
    start_time, end_time = get_time_filters(args)
    filters = {}
    if args.level:
        filters['level'] = args.level
    if args.exception:
        filters['exception_type'] = args.exception
    if args.thread_pattern:
        filters['thread_pattern'] = args.thread_pattern
    
    # Fetch logs
    print("📊 Fetching logs...")
    try:
        logs = source.fetch_logs(
            start_time=start_time,
            end_time=end_time,
            filters=filters
        )
        print(f"✅ Fetched {len(logs)} log entries")
    except Exception as e:
        print(f"❌ Error fetching logs: {e}")
        sys.exit(1)
    
    if not logs:
        print("⚠️  No logs found matching the criteria")
        sys.exit(0)
    
    # Analyze logs
    print("🔍 Analyzing logs...")
    analyzer = ErrorAnalyzer()
    summary_df = analyzer.analyze(logs)
    metrics = analyzer.get_metrics()
    
    # Display results based on format
    if args.format == 'summary':
        print("\n📈 ANALYSIS SUMMARY")
        print("=" * 50)
        print(f"Total Errors: {metrics.get('total_errors', 0):,}")
        print(f"Unique Error Types: {metrics.get('unique_error_types', 0)}")
        print(f"Affected Files: {metrics.get('affected_files', 0)}")
        print(f"Error Rate: {metrics.get('error_rate_per_hour', 0):.2f} errors/hour")
        
        if metrics.get('top_errors'):
            print("\n🔝 Top Error Types:")
            for error_type, count in list(metrics['top_errors'].items())[:5]:
                print(f"  - {error_type}: {count} occurrences")
        
        if metrics.get('error_timeline'):
            timeline = metrics['error_timeline']
            print(f"\n⏰ Peak Hour: {timeline['peak_hour']} ({timeline['peak_hour_count']} errors)")
            print(f"⏰ Quiet Hour: {timeline['quiet_hour']} ({timeline['quiet_hour_count']} errors)")
        
        if metrics.get('error_patterns'):
            patterns = metrics['error_patterns']
            burst_count = len([p for p in patterns if p['type'] == 'burst'])
            repeat_count = len([p for p in patterns if p['type'] == 'repeating'])
            if burst_count > 0:
                print(f"\n⚠️  Detected {burst_count} error burst(s)")
            if repeat_count > 0:
                print(f"⚠️  Detected {repeat_count} repeating error pattern(s)")
    
    elif args.format == 'detailed':
        # Show detailed breakdown
        if not summary_df.empty:
            location_summary = summary_df[summary_df['summary_type'] == 'by_location']
            if not location_summary.empty:
                print("\n📋 Detailed Error Breakdown:")
                print(location_summary.to_string(index=False))
    
    elif args.format == 'json':
        # Output as JSON
        output = {
            'metrics': metrics,
            'summary': summary_df.to_dict(orient='records') if not summary_df.empty else []
        }
        print(json.dumps(output, indent=2, default=str))
    
    # Save outputs if requested
    if args.output and not summary_df.empty:
        summary_df.to_csv(args.output, index=False, encoding='utf-8-sig')
        print(f"\n✅ Analysis results saved to: {args.output}")
    
    if args.metrics:
        with open(args.metrics, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2, default=str)
        print(f"✅ Metrics saved to: {args.metrics}")
    
    # Close the source
    source.close()
    print("\n✨ Analysis complete!")


if __name__ == "__main__":
    main()
