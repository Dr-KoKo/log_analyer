import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
from log_analyzer.sources.file_source import FileLogSource
from log_analyzer.sources.elk_source import ElkLogSource
from log_analyzer.analyzers.error_analyzer import ErrorAnalyzer

st.set_page_config(page_title="Advanced Log Analytics Dashboard", layout="wide", initial_sidebar_state="expanded")

# Custom CSS for better styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🔍 Advanced Log Analytics Dashboard")
st.markdown("---")

# Demo data versions configuration
DEMO_VERSIONS = {
    "v2.0.0 (~ 25-05-31)": {
        "file": "logs/2_0_0_logs.zip",
        "date_range": "old days to 2025-05-31",
        "description": "비아에서 작업하기 전의 기존 소스 코드"
    },
    "v2.0.1 (25-06-01 ~ 25-06-11)": {
        "file": "logs/2_0_1_logs.zip",
        "date_range": "2025-06-01 to 2025-06-11",
        "description": "기본적인 오류 수정 및 개선 사항 적용"
    },
    "v2.0.2 (25-06-12 ~ 25-08-05)": {
        "file": "logs/2_0_2_logs.zip",
        "date_range": "2025-06-12 to 2025-08-05",
        "description": "2.0.1의 오류 수정"
    },
    "v2.1.0 (25-08-06 ~ 25-08-11)": {
        "file": "logs/2_1_0_logs.zip",
        "date_range": "2025-08-06 to 2025-08-11",
        "description": "v2.1.0의 새로운 기능 및 개선 사항 적용"
    },
    "v2.1.1 (25-08-12 ~ present)": {
        "file": "logs/2_1_1_logs.zip",
        "date_range": "2025-08-12 to present",
        "description": "MS-SQL jdbc 드라이버 오류 수정 및 기타 개선 사항 적용"
    },
}

# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Data Source Selection
    st.subheader("📊 Data Source")
    
    # Create source options list
    source_options = list(DEMO_VERSIONS.keys()) + ["File/ZIP", "Elasticsearch (ELK)"]
    
    source_type = st.selectbox(
        "Select Log Source",
        source_options,
        help="Choose where to load logs from"
    )
    
    if source_type == "File/ZIP":
        uploaded_file = st.file_uploader(
            "Upload Log File",
            type=["log", "zip"],
            help="Upload a log file or zip archive"
        )
    elif source_type == "Elasticsearch (ELK)":
        st.info("ELK integration is in development")
        elk_host = st.text_input("Host", "localhost")
        elk_port = st.number_input("Port", value=9200)
        elk_index = st.text_input("Index Pattern", "logs-*")
    elif source_type in DEMO_VERSIONS:
        # Show demo version info
        demo_info = DEMO_VERSIONS[source_type]
        st.info(f"📅 {demo_info['date_range']}")
        st.caption(demo_info['description'])
    
    # Time Range Filter
    st.subheader("🕒 Time Range")
    time_filter = st.selectbox(
        "Select Time Range",
        ["All Time", "Last 24 Hours", "Last 7 Days", "Last 30 Days", "Custom"]
    )
    
    if time_filter == "Custom":
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date")
        with col2:
            end_date = st.date_input("End Date")
    
    # Analysis Options
    st.subheader("🔧 Analysis Options")
    show_patterns = st.checkbox("Detect Error Patterns", value=True)
    show_predictions = st.checkbox("Show Trend Predictions", value=False)
    refresh_interval = st.slider("Auto-refresh (seconds)", 0, 300, 0)

# Main content area
if source_type in DEMO_VERSIONS or (source_type == "File/ZIP" and uploaded_file):
    # Load data
    if source_type in DEMO_VERSIONS:
        # Use demo version data
        import os
        demo_info = DEMO_VERSIONS[source_type]
        demo_file_path = demo_info["file"]
        
        if os.path.exists(demo_file_path):
            source = FileLogSource()
            source.connect(demo_file_path)
            st.info(f"📁 Using {source_type}: {demo_info['description']}")
            st.caption(f"Date range: {demo_info['date_range']}")
        else:
            st.error(f"Demo file '{demo_file_path}' not found. Please check your deployment.")
            st.stop()
    else:
        source = FileLogSource()
        # Save uploaded file temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=uploaded_file.name) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            source.connect(tmp_file.name)
    
    # Fetch logs with time filter
    start_time = None
    end_time = None
    if time_filter == "Last 24 Hours":
        start_time = datetime.now() - timedelta(days=1)
    elif time_filter == "Last 7 Days":
        start_time = datetime.now() - timedelta(days=7)
    elif time_filter == "Last 30 Days":
        start_time = datetime.now() - timedelta(days=30)
    elif time_filter == "Custom":
        start_time = datetime.combine(start_date, datetime.min.time())
        end_time = datetime.combine(end_date, datetime.max.time())
    
    logs = source.fetch_logs(start_time=start_time, end_time=end_time)
    
    # Analyze logs
    analyzer = ErrorAnalyzer()
    summary_df = analyzer.analyze(logs)
    metrics = analyzer.get_metrics()
    
    # Display key metrics
    st.header("📈 Key Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Errors",
            f"{metrics.get('total_errors', 0):,}",
            delta=None,
            help="Total number of errors in selected time range"
        )
    
    with col2:
        st.metric(
            "Error Types",
            metrics.get('unique_error_types', 0),
            delta=None,
            help="Number of unique error types"
        )
    
    with col3:
        st.metric(
            "Affected Files",
            metrics.get('affected_files', 0),
            delta=None,
            help="Number of files with errors"
        )
    
    with col4:
        st.metric(
            "Errors/Hour",
            f"{metrics.get('error_rate_per_hour', 0):.1f}",
            delta=None,
            help="Average error rate per hour"
        )
    
    # Tabbed interface for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Overview", "📈 Time Analysis", "🔥 Hotspots", "🔍 Patterns", "📋 Raw Data"])
    
    with tab1:
        st.header("Error Distribution Overview")
        
        # Top errors pie chart and bar chart
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Top Error Types")
            if metrics.get('top_errors'):
                fig_pie = px.pie(
                    values=list(metrics['top_errors'].values()),
                    names=list(metrics['top_errors'].keys()),
                    title="Error Type Distribution"
                )
                st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            st.subheader("Error Frequency")
            if not summary_df.empty:
                location_summary = summary_df[summary_df['summary_type'] == 'by_location']
                if not location_summary.empty:
                    top_errors = location_summary.nlargest(10, 'count')
                    fig_bar = px.bar(
                        top_errors,
                        x='count',
                        y='exception',
                        orientation='h',
                        title="Top 10 Error Types by Count",
                        color='count',
                        color_continuous_scale='Reds'
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)
    
    with tab2:
        st.header("Time-based Analysis")
        
        # Time series visualization
        if not summary_df.empty:
            hourly_data = summary_df[summary_df['summary_type'] == 'hourly']
            
            if not hourly_data.empty:
                # Convert time_bucket to datetime if it isn't already
                hourly_data['time_bucket'] = pd.to_datetime(hourly_data['time_bucket'])
                
                # Line chart for error trends
                fig_timeline = px.line(
                    hourly_data,
                    x='time_bucket',
                    y='count',
                    color='exception',
                    title="Error Trends Over Time",
                    labels={'time_bucket': 'Time', 'count': 'Error Count'}
                )
                fig_timeline.update_layout(height=500)
                st.plotly_chart(fig_timeline, use_container_width=True)
                
                # Heatmap for hourly patterns
                st.subheader("Hourly Error Heatmap")
                pivot_hourly = hourly_data.pivot_table(
                    index='exception',
                    columns=hourly_data['time_bucket'].dt.hour,
                    values='count',
                    aggfunc='sum',
                    fill_value=0
                )
                
                fig_heatmap = px.imshow(
                    pivot_hourly,
                    labels=dict(x="Hour of Day", y="Exception Type", color="Error Count"),
                    aspect="auto",
                    color_continuous_scale='YlOrRd'
                )
                st.plotly_chart(fig_heatmap, use_container_width=True)
    
    with tab3:
        st.header("Error Hotspots")
        
        # File-based error distribution
        if not summary_df.empty:
            location_data = summary_df[summary_df['summary_type'] == 'by_location']
            
            if not location_data.empty:
                # Treemap for file hierarchy
                st.subheader("Error Distribution by File")
                location_data['file_exception'] = location_data['filename'] + ' - ' + location_data['exception']
                
                fig_treemap = px.treemap(
                    location_data,
                    path=['filename', 'exception'],
                    values='count',
                    title="Error Distribution Hierarchy",
                    color='count',
                    color_continuous_scale='OrRd'
                )
                fig_treemap.update_layout(height=600)
                st.plotly_chart(fig_treemap, use_container_width=True)
                
                # Top error locations table
                st.subheader("Top Error Locations")
                top_locations = location_data.nlargest(20, 'count')[['filename', 'line', 'exception', 'count']]
                st.dataframe(
                    top_locations,
                    use_container_width=True,
                    hide_index=True
                )
    
    with tab4:
        st.header("Error Patterns & Insights")
        
        if show_patterns and metrics.get('error_patterns'):
            patterns = metrics['error_patterns']
            
            # Burst patterns
            burst_patterns = [p for p in patterns if p['type'] == 'burst']
            if burst_patterns:
                st.subheader("🚨 Error Bursts Detected")
                for pattern in burst_patterns[:5]:
                    st.warning(
                        f"**Burst Alert**: {pattern['count']} errors in "
                        f"{pattern['duration_seconds']:.1f} seconds at "
                        f"{pattern['start_time'].strftime('%Y-%m-%d %H:%M:%S')}"
                    )
            
            # Repeating errors
            repeating_patterns = [p for p in patterns if p['type'] == 'repeating']
            if repeating_patterns:
                st.subheader("🔄 Repeating Errors")
                repeat_df = pd.DataFrame(repeating_patterns)
                st.dataframe(repeat_df, use_container_width=True, hide_index=True)
        
        # Timeline metrics
        if metrics.get('error_timeline'):
            timeline = metrics['error_timeline']
            st.subheader("📊 Timeline Statistics")
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"**Peak Hour**: {timeline['peak_hour']} ({timeline['peak_hour_count']} errors)")
            with col2:
                st.success(f"**Quiet Hour**: {timeline['quiet_hour']} ({timeline['quiet_hour_count']} errors)")
    
    with tab5:
        st.header("Raw Log Data")
        
        # Filters for raw data
        col1, col2, col3 = st.columns(3)
        with col1:
            level_filter = st.selectbox("Filter by Level", ["All"] + ["정보", "경고", "심각"])
        with col2:
            if not summary_df.empty:
                exception_types = summary_df['exception'].dropna().unique().tolist()
                exception_filter = st.selectbox("Filter by Exception", ["All"] + exception_types)
        with col3:
            search_term = st.text_input("Search in messages")
        
        # Convert logs to dataframe for display
        if logs:
            log_df = pd.DataFrame([log.to_dict() for log in logs])
            
            # Apply filters
            if level_filter != "All":
                log_df = log_df[log_df['level'] == level_filter]
            if exception_filter != "All":
                log_df = log_df[log_df['exception_type'] == exception_filter]
            if search_term:
                log_df = log_df[log_df['message'].str.contains(search_term, case=False, na=False)]
            
            # Display filtered data
            st.dataframe(
                log_df[['timestamp', 'level', 'thread', 'exception_type', 'message']].head(1000),
                use_container_width=True,
                hide_index=True
            )
            
            # Download button
            csv = log_df.to_csv(index=False)
            st.download_button(
                "📥 Download Filtered Data",
                csv,
                "filtered_logs.csv",
                "text/csv",
                key='download-csv'
            )

else:
    st.info("👈 Please configure a data source in the sidebar to begin analysis")

# Auto-refresh functionality
if refresh_interval > 0:
    import time
    time.sleep(refresh_interval)
    st.rerun()
