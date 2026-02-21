'''
This modul defines the DAG: Directed Acyclic Graph, it orchestrates the Video compliance
audit processes.
It connects the nodes using the StateGraph from LangGraph.

START -> index_video_node -> audit_content_node -> END
'''

from langgraph.graph import StateGraph, END
from backend.src.graph.state import VideoAuditState
from backend.src.graph.nodes import (
    index_video_node,
    audit_content_node)

def create_graph():
    '''
    Constructs and Compiles the LangGraph workflow
    REturns:
    Compiled Graph: runnable graph object for execution
    '''

    ## initialize the graph with state schema
    workflow = StateGraph(state_schema=VideoAuditState)

    ##add nodes to the graph
    workflow.add_node("indexer", index_video_node)
    workflow.add_node("auditor", audit_content_node)

    ## define the entry point: indexer node
    workflow.set_entry_point('indexer')

    ##define the edges of the graph
    workflow.add_edge("indexer", "auditor")

    ## onece the audit is complete, the workflow ends
    workflow.add_edge("auditor", END)

    ## compile the graph
    app = workflow.compile()

    return app

## expose this runnable app
app = create_graph()