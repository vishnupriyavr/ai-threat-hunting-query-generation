import re
import csv
import os

def parse_logs(log_file_path, output_csv):
    extracted_data = []
    current_entry = None
    collecting_reasoning = False
    reasoning_buffer = []
    
    if not os.path.exists(log_file_path):
        print(f"❌ Error: {log_file_path} not found.")
        return

    with open(log_file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
        for i, raw_line in enumerate(lines):
            # 1. Strip Docker prefix (e.g., 'eval-runner-1 | ')
            line_content = raw_line.split("|", 1)[-1] if "|" in raw_line else raw_line
            
            # 2. Strip Box-drawing characters (e.g., '│') and extra whitespace
            clean_line = line_content.replace('│', '').strip()
            
            # Detect Start of a New Hunt
            id_match = re.search(r"🚀 STARTING HUNT: ID (\d+)", clean_line)
            if id_match:
                if current_entry:
                    extracted_data.append(current_entry)
                current_entry = {
                    "ID": id_match.group(1), 
                    "Hypothesis": "N/A", 
                    "Reasoning": "N/A", 
                    "SQL": "N/A", 
                    "Rows": "0"
                }
                continue

            if not current_entry:
                continue

            # Detect Hypothesis
            if clean_line.startswith("HYPOTHESIS:"):
                current_entry["Hypothesis"] = clean_line.replace("HYPOTHESIS:", "").strip()

            # Detect SQL (Look-ahead logic)
            if "🔍 SQL QUERY GENERATED:" in clean_line:
                if i + 1 < len(lines):
                    sql_line = lines[i+1].split("|", 1)[-1].replace('│', '').strip()
                    current_entry["SQL"] = sql_line

            # --- Reasoning Extraction (Multi-line) ---
            
            # Start collecting when '"reasoning": "' is found
            if '"reasoning":' in clean_line:
                collecting_reasoning = True
                # Extract starting text after the colon and quote
                start_text = re.search(r'"reasoning":\s*"(.*)', clean_line)
                if start_text:
                    text = start_text.group(1).rstrip('",') # remove trailing quote/comma if on same line
                    reasoning_buffer.append(text)
                
                # If it ends on the same line, stop immediately
                if clean_line.endswith('",') or clean_line.endswith('", '):
                    collecting_reasoning = False
                    current_entry["Reasoning"] = " ".join(reasoning_buffer).strip()
                    reasoning_buffer = []
                continue

            # Continue collecting lines if in reasoning mode
            if collecting_reasoning:
                # If we hit the end marker (quote followed by comma or brace)
                if clean_line.endswith('",') or clean_line.endswith('", '):
                    end_text = clean_line.rstrip('", ')
                    reasoning_buffer.append(end_text)
                    current_entry["Reasoning"] = " ".join(reasoning_buffer).strip()
                    reasoning_buffer = []
                    collecting_reasoning = False
                else:
                    reasoning_buffer.append(clean_line)
                continue

            # Detect Results
            res_match = re.search(r"📊 DATA FOUND: (\d+) rows", clean_line)
            if res_match:
                current_entry["Rows"] = res_match.group(1)

        # Append last entry
        if current_entry:
            extracted_data.append(current_entry)

    # Save to CSV
    keys = ["ID", "Hypothesis", "Rows", "Reasoning", "SQL"]
    with open(output_csv, 'w', newline='', encoding='utf-8') as output_file:
        dict_writer = csv.DictWriter(output_file, fieldnames=keys)
        dict_writer.writeheader()
        dict_writer.writerows(extracted_data)

    print(f"✨ Successfully parsed {len(extracted_data)} hunts.")
    print(f"📄 Report saved to: {output_csv}")

if __name__ == "__main__":
    parse_logs('eval_runner.log', 'detailed_hunt_report.csv')