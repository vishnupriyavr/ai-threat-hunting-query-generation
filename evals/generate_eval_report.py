import re
import statistics
import os

# Canonical CloudTrail fields for faithfulness check
CANONICAL_FIELDS = {
    "eventVersion", "userIdentity", "eventTime", "eventSource", "eventName", 
    "awsRegion", "sourceIPAddress", "userAgent", "errorCode", "errorMessage", 
    "requestParameters", "responseElements", "additionalEventData", "requestId", 
    "eventID", "eventType", "apiVersion", "readOnly", "resources", "recipientAccountId"
}

def calculate_faithfulness(query):
    if not query or query == "N/A": return 0.0
    # Extract words/columns used in the query
    found_fields = re.findall(r'(\w+)', query)
    if not found_fields: return 0.0
    # We filter out common SQL keywords to focus on schema fields
    sql_keywords = {'SELECT', 'FROM', 'WHERE', 'ILIKE', 'AND', 'OR', 'LIMIT', 'IS', 'NOT', 'NULL'}
    filtered_fields = [f for f in found_fields if f.upper() not in sql_keywords and not f.isdigit()]
    
    if not filtered_fields: return 100.0 # No schema fields used (rare)
    
    matches = [f for f in filtered_fields if f in CANONICAL_FIELDS or f == "logs"]
    return (len(matches) / len(set(filtered_fields))) * 100

def generate_report(log_file):
    hunts = []
    current_hunt = None
    
    if not os.path.exists(log_file):
        print(f"❌ Error: {log_file} not found.")
        return

    with open(log_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
        for i, raw_line in enumerate(lines):
            # Strip the "eval-runner-1 | " prefix if it exists
            line = raw_line.split("|", 1)[-1].strip() if "|" in raw_line else raw_line.strip()
            
            # 1. Detect ID
            id_match = re.search(r"🚀 STARTING HUNT: ID (\d+)", line)
            if id_match:
                if current_hunt: hunts.append(current_hunt)
                current_hunt = {"id": id_match.group(1), "name": "Unknown", "sql": "N/A", "rows": 0, "latency": 0.0}
                continue
            
            if not current_hunt: continue

            # 2. Detect Hypothesis
            if line.startswith("HYPOTHESIS:"):
                current_hunt["name"] = line.replace("HYPOTHESIS:", "").strip()

            # 3. Detect SQL (Looking for the line after the label)
            if "🔍 SQL QUERY GENERATED:" in line:
                if i + 1 < len(lines):
                    sql_line = lines[i+1].split("|", 1)[-1].strip()
                    current_hunt["sql"] = sql_line

            # 4. Detect Rows
            row_match = re.search(r"📊 DATA FOUND: (\d+) rows", line)
            if row_match:
                current_hunt["rows"] = int(row_match.group(1))

            # 5. Detect Latency
            lat_match = re.search(r"⏱️ Latency for ID \d+: ([\d\.]+)s", line)
            if lat_match:
                current_hunt["latency"] = float(lat_match.group(1))

        if current_hunt: hunts.append(current_hunt)

    if not hunts:
        print("❌ No hunt data found in logs. Check if '🚀 STARTING HUNT' exists in your log file.")
        return

    # Metrics
    total = len(hunts)
    success_rate = (sum(1 for h in hunts if h["rows"] > 0) / total * 100)
    avg_faith = sum(calculate_faithfulness(h["sql"]) for h in hunts) / total
    avg_lat = sum(h["latency"] for h in hunts) / total

    # Generate Markdown
    report = "# Agentic Threat Hunt Evaluation Report\n\n"
    report += "## Overall Performance\n\n"
    report += "| Metric | Value | Definition |\n"
    report += "| :--- | :--- | :--- |\n"
    report += f"| **Success Rate** | {success_rate:.1f}% | % of hunts returning results |\n"
    report += f"| **Schema Faithfulness** | {avg_faith:.1f}% | Adherence to CloudTrail schema |\n"
    report += f"| **Avg Latency** | {avg_lat:.2f}s | Speed per hypothesis |\n\n"

    report += "## Hunt Breakdown\n\n"
    report += "| ID | Hypothesis | Status | Rows | Faithfulness |\n"
    report += "| :--- | :--- | :--- | :--- | :--- |\n"
    
    for h in hunts:
        status = "✅ PASS" if h["rows"] > 0 else "❌ FAIL"
        faith = calculate_faithfulness(h["sql"])
        report += f"| {h['id']} | {h['name'][:50]}... | {status} | {h['rows']} | {faith:.1f}% |\n"

    with open("EVALUATION_REPORT_generated.md", "w") as f:
        f.write(report)
    print("✨ Created EVALUATION_REPORT_generated.md")

if __name__ == "__main__":
    generate_report('eval_runner.log')