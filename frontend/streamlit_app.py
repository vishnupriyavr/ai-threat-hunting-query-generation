import streamlit as st
import threading
import logging
import queue
import time
from src.query_generator import AgenticThreatHunt, HuntState

# Frontend for Live Agentic Threat Hunt using Streamlit
class StreamlitLogHandler(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(self.format(record))

# --- 2. UI Setup ---
st.set_page_config(page_title="Agentic Threat Hunt", layout="wide")
st.title("Live Agentic Threat Hunt")

# Initialize Session State
if "logs" not in st.session_state:
    st.session_state.logs = []
if "hunt_result" not in st.session_state:
    st.session_state.hunt_result = None

# --- 3. The Execution Thread ---
def run_flow_thread(log_queue, hypothesis_id):
    # Setup logging to capture agent outputs
    handler = StreamlitLogHandler(log_queue)
    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    # Initialize and Run the Flow
    flow = AgenticThreatHunt()
    flow.state.current_hypothesis_id = hypothesis_id
    
    # Kickoff the flow
    result = flow.kickoff()
    st.session_state.hunt_result = flow.state
    logger.removeHandler(handler)

with st.sidebar:
    hyp_id = st.text_input("Enter Hypothesis ID", value="HYP-007")
    if st.button("Kickoff Hunt", type="primary"):
        st.session_state.logs = []
        st.session_state.hunt_result = None
        log_queue = queue.Queue()
        
        # Start the thread
        thread = threading.Thread(target=run_flow_thread, args=(log_queue, hyp_id))
        thread.start()
        st.session_state.running = True
        st.session_state.log_queue = log_queue


col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Agent Activity Log")
    log_container = st.empty()
    
    # Periodically update logs from the queue
    if "log_queue" in st.session_state:
        while not st.session_state.log_queue.empty():
            msg = st.session_state.log_queue.get()
            st.session_state.logs.append(msg)
        
        log_text = "\n".join(st.session_state.logs)
        log_container.text_area("Live Feed", value=log_text, height=400)
        
        # Auto-refresh UI to show new logs
        if any(t.is_alive() for t in threading.enumerate() if t.name == "Thread-1"):
            time.sleep(0.5)
            st.rerun()

with col2:
    st.subheader("Final State & Findings")
    if st.session_state.hunt_result:
        res = st.session_state.hunt_result
        st.success("Hunt Complete!")
        st.metric("Total Retries", res.retry_count)
        
        with st.expander("Generated Athena Query"):
            st.code(res.generated_query, language="sql")
        
        with st.expander("Query Results"):
            st.write(res.query_results)
    else:
        st.info("Results will appear here once the agents finish.")