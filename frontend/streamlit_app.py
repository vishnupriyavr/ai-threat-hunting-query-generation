import streamlit as st
import logging
import sys
import re
import os
import time
import json
from src.query_generator import AgenticThreatHunt
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Load hypotheses from JSON file
try:
    with open("assignment/hypotheses.json", "r") as f:
        HYPOTHESES = json.load(f)
except FileNotFoundError:
    st.error("Error: hypotheses.json not found. Make sure it's in the 'assignment/' directory.")
    HYPOTHESES = []

# --- 1. Custom Buffer to Capture Agent Thoughts ---
class SimpleCapture:
    """Captures the agent's 'thought process' from stdout for the UI."""
    def __init__(self):
        self.content = ""
    def write(self, data):
        # Remove ANSI color codes that look like [32m in the UI
        clean_data = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', data)
        self.content += clean_data
    def flush(self):
        pass

# --- 2. Page Configuration ---
st.set_page_config(page_title="Agentic Threat Hunt", layout="wide")
st.title("🛡️ Agentic Threat Hunt")

# Initialize Session State
if "hunt_result" not in st.session_state:
    st.session_state.hunt_result = None
if "final_answer" not in st.session_state:
    st.session_state.final_answer = None
if "raw_logs" not in st.session_state:
    st.session_state.raw_logs = ""
if "running" not in st.session_state:
    st.session_state.running = False

# --- 3. Sidebar Control ---
with st.sidebar:
    st.header("Hunt Configuration")
    
    # Create a mapping from ID to full hypothesis string for the selectbox
    hypothesis_options = {hyp["id"]: f"{hyp['id']}: {hyp['name']} - {hyp['hypothesis']}" for hyp in HYPOTHESES}
    
    selected_hyp_id = st.selectbox(
        "Select Hypothesis",
        options=list(hypothesis_options.keys()),
        format_func=lambda x: hypothesis_options[x]
    )
    
    start_btn = st.button("Kickoff Hunt", type="primary", disabled=st.session_state.running)

# --- 4. Main Logic Execution ---
if start_btn:
    st.session_state.running = True
    st.session_state.raw_logs = "" # Clear previous logs
    
    # Retrieve the selected hypothesis text
    selected_hypothesis_text = next(
        (hyp["hypothesis"] for hyp in HYPOTHESES if hyp["id"] == selected_hyp_id),
        "No hypothesis found for this ID."
    )
    
    with st.spinner("Agents are analyzing logs and generating queries..."):
        # Redirect stdout to our capture object to grab terminal logs
        capture_buffer = SimpleCapture()
        old_stdout = sys.stdout
        sys.stdout = capture_buffer

        try:
            # Instantiate and run the flow
            flow = AgenticThreatHunt()
            flow.state.current_hypothesis_id = selected_hyp_id
            flow.state.hypothesis_text = selected_hypothesis_text # Pass the hypothesis text
            
            # kickoff() returns the Final Answer (JSON findings) from the Triage Agent
            final_ans = flow.kickoff()
            
            # Save results to session state
            st.session_state.final_answer = final_ans
            st.session_state.hunt_result = flow.state
            st.session_state.raw_logs = capture_buffer.content
            
        except Exception as e:
            st.error(f"An error occurred during the hunt: {e}")
        finally:
            # Restore standard output and update status
            sys.stdout = old_stdout
            st.session_state.running = False
            st.rerun()

# --- 5. UI Layout ---
col1, col2 = st.columns([1, 1])

# LEFT COLUMN: Live/Static Process Logs
with col1:
    st.subheader("Agent Activity Log")
    if st.session_state.raw_logs:
        st.text_area(
            "Agent Reasoning Process", 
            value=st.session_state.raw_logs, 
            height=700,
            help="This shows the step-by-step logic the agents used."
        )
    elif st.session_state.running:
        st.info("The agents are working. Results will appear here shortly...")
    else:
        st.info("Log will appear here after execution.")

# RIGHT COLUMN: Structured Results
with col2:
    st.subheader("Final State & Findings")
    
    if st.session_state.hunt_result:
        res = st.session_state.hunt_result
        st.success("Hunt Complete!")
        
        # A. Metrics Row
        m1, m2 = st.columns(2)
        m1.metric("Retries", getattr(res, 'retry_count', 0))
        conf = getattr(res, 'confidence_score', None)
        if conf:
            m2.metric("Confidence", f"{conf}%")

        # B. Hypothesis and Reasoning (MOVED UP)
        st.markdown(f"**Hypothesis Interpretation:**\n{getattr(res, 'hypothesis_interpretation', 'N/A')}")
        
        with st.expander("🔍 Reasoning & Assumptions", expanded=True):
            reasoning = getattr(res, 'query_reasoning', None)
            if reasoning:
                st.info(reasoning)
            else:
                st.write("No reasoning found in flow state.")
                
            if hasattr(res, 'assumptions_made') and res.assumptions_made:
                st.divider()
                st.caption(f"**Assumptions:** {res.assumptions_made}")
        
        # C. Generated SQL Query (MOVED UP)
        with st.expander("🛠️ Generated SQL Query", expanded=True):
            query = getattr(res, 'generated_query', '')
            if query:
                st.code(query, language="sql")
            else:
                st.write("No query generated.")

        st.divider()

        # D. Triage Findings (MOVED DOWN)
        if st.session_state.final_answer:
            st.markdown("### 🎯 Triage Findings")
            # Displays the JSON findings from the final box in your terminal
            if isinstance(st.session_state.final_answer, (dict, list)):
                st.json(st.session_state.final_answer)
            else:
                st.info(st.session_state.final_answer)
                
    elif st.session_state.running:
        st.warning("Agents are currently analyzing data...")
        st.progress(0.5)
    else:
        st.info("Results will appear here once the hunt finishes.")