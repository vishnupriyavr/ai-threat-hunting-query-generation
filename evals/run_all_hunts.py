import json
import os
from src.query_generator import AgenticThreatHunt, HuntState
from evals.evaluation import export_agent_outputs_to_hypotheses_outcomes
from typing import Dict, List # Import Dict and List

# Define paths
HYPOTHESES_FILE = 'assignment/hypotheses.json'
OUTCOMES_FILE = 'evals/hypotheses_outcomes_generated.json'

def load_hypotheses(file_path: str) -> list:
    with open(file_path, 'r') as f:
        return json.load(f)

def run_all_hunts() -> Dict[str, List[Dict]]:
    hypotheses = load_hypotheses(HYPOTHESES_FILE)
    all_hunt_results = {}

    for hypo in hypotheses:
        hypo_id = str(hypo['id'])
        hypo_text = hypo['hypothesis']
        print(f"Running hunt for Hypothesis ID: {hypo_id}, Text: '{hypo_text}'")

        # Initialize and Run the Flow
        flow = AgenticThreatHunt()
        flow.state.current_hypothesis_id = hypo_id
        flow.state.hypothesis_text = hypo_text # Need to set this as well
        
        # Reset retry count for each new hypothesis
        flow.state.retry_count = 0
        flow.state.max_retries = 3 # Ensure it's set for each hunt

        result_state = flow.kickoff()
        
        # The result_state is a HuntState object. We need to extract query_results.
        # export_agent_outputs_to_hypotheses_outcomes expects:
        # 1) Dict[str, List[Dict]]: mapping hypothesis_id -> list of row dicts
        # 2) List[ { 'hypothesis_id': id, 'rows': [ {...}, ... ] }, ... ]
        
        # Let's use the first format: Dict[str, List[Dict]]
        all_hunt_results[hypo_id] = result_state.query_results
        
        print(f"Hunt for {hypo_id} completed. Results count: {len(result_state.query_results)}")
        # Optionally, log other details from result_state for debugging
        # print(f"  Generated Query: {result_state.generated_query}")
        # print(f"  Confidence: {result_state.confidence_score}")
        # print(f"  Interpretation: {result_state.hypothesis_interpretation}")

    return all_hunt_results

if __name__ == "__main__":
    print("Starting all threat hunts...")
    agent_outputs = run_all_hunts()
    
    print(f"Exporting results to {OUTCOMES_FILE}...")
    export_agent_outputs_to_hypotheses_outcomes(agent_outputs, out_path=OUTCOMES_FILE)
    print("All hunts completed and results exported.")

    # Now run the evaluation script
    print("Generating evaluation report...")
    # This assumes 'evaluation.py' is in 'evals/' relative to the current script.
    # Adjust if necessary.
    os.system(f"python evals/evaluation.py --outcomes {OUTCOMES_FILE} --hypotheses {HYPOTHESES_FILE} --out EVALUATION_REPORT_generated.md")
    print("Evaluation report generated: EVALUATION_REPORT_generated.md")