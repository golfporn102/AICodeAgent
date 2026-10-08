from langgraph import graph
from langgraph.graph import (
    StateGraph,
    END
)
from graph.state import AgentState
from nodes.find_files import find_files
from nodes.read_files import read_files
from nodes.ask_gemini import ask_gemini
from nodes.run_test import (run_test,route_test_result,analyze_test_failure)
from nodes.apply_change import apply_change

def route_mode(state):

    mode = state["mode"]
    print(f"Routing mode: {mode}")
    if mode == "ALL":
        return "CODE"

    if mode == "CODE":
        return "CODE"

    if mode =="RUN_TEST":
        return "RUN_TEST"

    return "CODE"


def create_workflow():

    graph = StateGraph(
        AgentState
    )

    # -------------------------
    # Nodes
    # -------------------------

    graph.add_node("find_files", find_files )
    graph.add_node("read_files", read_files)
    graph.add_node("detect_mode",route_mode)
    graph.add_node("ask_gemini", ask_gemini)
    graph.add_node("run_test", run_test)
    graph.add_node("apply_change", apply_change)
    graph.add_node("analyze_test_failure", analyze_test_failure)

    # -------------------------
    # Start
    # -------------------------

    graph.set_entry_point("find_files")

    # -------------------------
    # Flow
    # -------------------------

    graph.add_edge("find_files","read_files")
    graph.add_conditional_edges("read_files", route_mode,
        {
            "CODE": "ask_gemini",
            "RUN_TEST": "run_test",
        }
    )

    graph.add_edge("ask_gemini","apply_change")
    graph.add_edge("apply_change","run_test")
    graph.add_conditional_edges("run_test",route_test_result,
        {
            "PASS": END,
            "FAIL": "analyze_test_failure",
            "MAX_RETRY": END
        }
    )
    graph.add_edge("analyze_test_failure","ask_gemini")
    # -------------------------
    # Compile
    # -------------------------

    return graph.compile()