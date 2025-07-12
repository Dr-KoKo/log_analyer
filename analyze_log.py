import pandas as pd
import re
import os
import zipfile

def extract_errors_from_log(file_content, source_filename):
    error_patterns = [
        re.compile(r"(?P<timestamp>\d{2}-\w{3}-\d{4} \d{2}:\d{2}:\d{2}\.\d{3}) 심각.*?nested exception is (?P<exception>[^\:]+)(?:\: (?P<message>.+?))?\s+at (?P<location>[^\(]+)\((?P<file>[^\)]+)\)", re.DOTALL),
        re.compile(r"(?P<timestamp>\d{2}-\w{3}-\d{4} \d{2}:\d{2}:\d{2}\.\d{3}).+?with root cause\s+(?P<exception>[a-zA-Z0-9\._]+): (?P<message>.+?)\s+at (?P<location>[^\(]+)\((?P<file>[^\)]+)\)", re.DOTALL)
    ]

    entries = []
    for pattern in error_patterns:
        for match in pattern.finditer(file_content):
            entries.append({
                "log_file": source_filename,
                "timestamp": match.group("timestamp"),
                "exception": match.group("exception").strip(),
                "message": match.group("message").strip() if match.group("message") else "",
                "location": match.group("location").strip(),
                "file": match.group("file").strip()
            })
    return entries

def process_log_file(file_path):
    if file_path.endswith(".zip"):
        all_entries = []
        with zipfile.ZipFile(file_path, "r") as z:
            for name in z.namelist():
                if name.endswith(".log"):
                    with z.open(name) as log_file:
                        content = log_file.read().decode("utf-8", errors="ignore")
                        all_entries.extend(extract_errors_from_log(content, source_filename=name))
        return all_entries
    else:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return extract_errors_from_log(content, source_filename=os.path.basename(file_path))

def summarize_errors(entries):
    df_errors = pd.DataFrame(entries)
    df_errors["core_exception"] = df_errors["exception"].str.extract(r"([A-Za-z0-9]+Exception)")
    df_errors[["filename", "line"]] = df_errors["file"].str.extract(r"([^:]+):(\d+)")
    
    summary = (
        df_errors.groupby(["log_file", "filename", "line", "core_exception"])
        .size()
        .reset_index(name="count")
        .rename(columns={"core_exception": "exception"})
    )
    return summary.reset_index(drop=True)

# ========== 실행 ==========
if __name__ == "__main__":
    import sys

    def usage():
        print("Usage: python parse_log.py <log_file_or_zip> [--output <output_file.csv>]")
        sys.exit(1)

    if len(sys.argv) < 2:
        usage()

    input_path = sys.argv[1]
    output_path = None
    if "--output" in sys.argv:
        try:
            output_index = sys.argv.index("--output") + 1
            output_path = sys.argv[output_index]
        except IndexError:
            print("Error: --output 옵션 뒤에 파일명을 지정해야 합니다.")
            sys.exit(1)

    entries = process_log_file(input_path)
    summary_df = summarize_errors(entries)

    if output_path:
        summary_df.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"✅ 로그 요약 결과가 '{output_path}'에 저장되었습니다.")
    else:
        # 기본 저장 경로 자동 지정
        default_output = f"summary_{os.path.basename(input_path).split('.')[0]}.csv"
        summary_df.to_csv(default_output, index=False, encoding="utf-8-sig")
        print(f"✅ 로그 요약 결과가 '{default_output}'에 저장되었습니다.")
