from langgraph.graph import START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from core.agent import agent_node_factory
from core.llm import build_llm_with_tools
from core.state import State


def build_graph(tools, checkpointer):
    llm_with_tools = build_llm_with_tools(tools)
    agent_node = agent_node_factory(llm_with_tools)

    builder = StateGraph(State)
    builder.add_node("Agent", agent_node)
    tool_node = ToolNode(tools=tools)
    builder.add_node("tools", tool_node)
    builder.add_edge(START, "Agent")
    builder.add_conditional_edges("Agent", tools_condition)
    builder.add_edge("tools", "Agent")

    graph = builder.compile(checkpointer=checkpointer)
    return graph
