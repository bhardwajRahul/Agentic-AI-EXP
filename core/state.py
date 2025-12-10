from typing import Annotated, Literal, Optional

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class State(TypedDict):
    messages: Annotated[list, add_messages]

    next: Optional[str]


class Route(BaseModel):
    """Routing decision for the supervisor"""

    step: Literal["communication_agent", "productivity_agent", "FINISH"] = Field(
        description="The next agent to route to, or FINISH if done"
    )


def route_after_supervisor(state: State):
    return state["next"]


def internal_agent_route(state: State):
    last_message = state["messages"][-1]

    if hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
        return "tools"

    content = last_message.content.upper()

    if "FINAL ANSWER" in content:
        return "supervisor"

    if any(
        keyword in content
        for keyword in ["CLARIFICATION NEEDED", "PLEASE SPECIFY", "?"]
    ):
        return "ASK"

    return "supervisor"
