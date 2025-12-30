from src.query_generator import AgenticThreatHunt, HuntState

def main():
    # Example of how to run the flow
    initial_state = HuntState(
        current_hypothesis_id="1",
        hypothesis_text="Suspicious user agent",
    )
    flow = AgenticThreatHunt()
    final_state = flow.run(initial_state)
    print(final_state)

if __name__ == "__main__":
    main()
