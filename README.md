# Advanced Log Analyzer

A sophisticated log analysis system with pluggable data sources and advanced visualization capabilities.

## Features

### 🔌 Pluggable Architecture
- **Multiple Data Sources**: Easily switch between file-based logs and Elasticsearch/ELK stack
- **Extensible Design**: Add new data sources by implementing the `LogSourceInterface`
- **Future-ready**: Prepared for database integrations like ELK

### 📊 Advanced Analytics
- **Time-series Analysis**: Track error trends over time
- **Pattern Detection**: Automatically detect error bursts and repeating patterns
- **Multi-dimensional Grouping**: Analyze by location, time, thread, and exception type
- **Statistical Metrics**: Error rates, peak hours, distribution analysis

### 📈 Rich Visualizations
- **Interactive Dashboard**: Built with Streamlit and Plotly
- **Multiple Views**: Overview, time analysis, hotspots, patterns, and raw data
- **Real-time Updates**: Auto-refresh capability for monitoring
- **Responsive Charts**: Pie charts, bar charts, line graphs, heatmaps, and treemaps

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Command Line Interface

```bash
# Analyze a single log file
python advanced_analyze.py --source file --input server.log

# Analyze logs from the last 24 hours
python advanced_analyze.py --source file --input logs.zip --last-hours 24

# Filter by exception type
python advanced_analyze.py --source file --input server.log --exception NullPointerException

# Export detailed metrics
python advanced_analyze.py --source file --input server.log --output summary.csv --metrics metrics.json
```

### Web Dashboard

```bash
# Start the interactive dashboard
streamlit run advanced_visualize.py
```

## Architecture

```
log_analyzer/
├── interfaces.py          # Abstract interfaces for sources and analyzers
├── sources/
│   ├── file_source.py    # File/ZIP log reader implementation
│   └── elk_source.py     # Elasticsearch source (placeholder)
└── analyzers/
    └── error_analyzer.py  # Advanced error analysis with patterns
```

## Data Source Interface

```python
class LogSourceInterface(ABC):
    def connect(self, **kwargs) -> None
    def fetch_logs(self, start_time, end_time, filters) -> List[LogEntry]
    def close(self) -> None
```

## Key Components

1. **FileLogSource**: Reads logs from files or ZIP archives
2. **ElkLogSource**: Connects to Elasticsearch (ready for implementation)
3. **ErrorAnalyzer**: Performs sophisticated error analysis
4. **Dashboard**: Interactive web interface for visualization

## Supported Log Format

Currently optimized for Apache Tomcat logs in Korean with format:
```
DD-Mon-YYYY HH:MM:SS.mmm 레벨 [thread] logger message
```

## Extending the System

To add a new data source:

1. Create a new class implementing `LogSourceInterface`
2. Implement the required methods (connect, fetch_logs, close)
3. Add the source option to the CLI and dashboard

Example:
```python
class MongoDBLogSource(LogSourceInterface):
    def connect(self, connection_string: str, **kwargs):
        # Connect to MongoDB
        pass
    
    def fetch_logs(self, start_time, end_time, filters):
        # Query and return logs
        pass
```