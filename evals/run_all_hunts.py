import json
import os
import pandas as pd
from src.query_generator import AgenticThreatHunt, HuntState
from typing import Dict, List, Any

# Define paths
HYPOTHESES_FILE = 'assignment/hypotheses.json'
OUTCOMES_FILE = 'evals/hypotheses_outcomes_generated.json'

def load_hypotheses(file_path: str) -> list:
    with open(file_path, 'r') as f:
        return json.load(f)

def run_all_hunts() -> List[Dict[str, Any]]:
    """
    Runs threat hunts for all hypotheses and returns results in a 
    list of dictionaries, matching the required column-oriented format.
    """
    hypotheses = load_hypotheses(HYPOTHESES_FILE)
    all_hunt_results = []

    for hypo in hypotheses:
        hypo_id = str(hypo['id'])
        hypo_text = hypo['hypothesis']
        print(f"\n" + "═"*60)
        print(f"🚀 STARTING HUNT: ID {hypo_id}")
        print(f"HYPOTHESIS: {hypo_text}")
        print("═"*60)

        # 1. Initialize the Flow
        flow = AgenticThreatHunt()
        
        # 2. Kickoff
        flow_output = flow.kickoff(inputs={
            "current_hypothesis_id": hypo_id,
            "hypothesis_text": hypo_text,
            "retry_count": 0,
            "max_retries": 3
        })

        # 3. Extract final state safely
        final_state = getattr(flow_output, 'result', None)
        if not isinstance(final_state, HuntState):
            final_state = flow.state

        # 4. DEBUG LOGS
        print(f"\n[DEBUG - ID {hypo_id}]")
        if hasattr(final_state, 'generated_query'):
            print(f"🔍 SQL QUERY GENERATED:\n{final_state.generated_query}")
        
        # 5. Transform Results to Column-Oriented Format
        results_list = final_state.query_results if final_state.query_results else []
        
        formatted_data = {}
        if results_list:
            # Convert list of dicts (rows) to DataFrame
            df = pd.DataFrame(results_list)
            # Use orient='dict' to get {column: {index: value}}
            # This matches the structure in hypotheses_outcomes.json
            formatted_data = df.to_dict(orient='dict')
        
        # Wrap in the ID key and append to the final list
        all_hunt_results.append({hypo_id: formatted_data})

        print(f"\n✅ COMPLETED ID {hypo_id}")
        print(f"📊 DATA FOUND: {len(results_list)} rows")
        print("─"*60)

    return all_hunt_results

def save_outcomes(data: List[Dict], out_path: str):
    """Saves the results to a JSON file with proper formatting."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w') as f:
        json.dump(data, f, indent=4)

if __name__ == "__main__":
    print("Starting all threat hunts...")
    
    # Generate the formatted results list
    agent_outputs = run_all_hunts()
    
    print(f"\n💾 Exporting results to {OUTCOMES_FILE}...")
    save_outcomes(agent_outputs, OUTCOMES_FILE)
    
    print("📝 Generating evaluation report...")
    # Execute the evaluation script using the newly generated file
    os.system(f"python evals/generate_eval_report.py")
    
    print("✨ Process complete. Review EVALUATION_REPORT_generated.md for details.")