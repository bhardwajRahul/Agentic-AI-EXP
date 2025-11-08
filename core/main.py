from dotenv import load_dotenv
import os
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.store.postgres import PostgresStore
from langgraph.checkpoint.postgres import PostgresSaver
import psycopg
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
import aiosqlite
from pathlib import Path
from langchain_core.messages import trim_messages
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

# from langchain.chat_models import init_chat_model
from langgraph.types import Command
import asyncio
import logging
import json
from datetime import datetime

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)
request_counter = {"count": 0}

client = MultiServerMCPClient(
    {
        "gmail": {
            "transport": "stdio",
            "command": "python",
            "args": ["D:/Agentic AI/MCP/server.py"],
        }
    }
)

SYSTEM_PROMPT = """
You are a Gmail assistant with access to various email management tools.
Always ask for user confirmation before sending or deleting emails.
Use the provided tools appropriately based on user intent.
"""


class State(TypedDict):
    messages: Annotated[list, add_messages]


DB_PATH = Path("D:/Agentic AI/data/memory.db")
api_key = os.getenv("OPENROUTER_API_KEY")
base_url = "https://openrouter.ai/api/v1"


def build_llm_with_tools(tools):
    # llm = init_chat_model("google_genai:gemini-2.0-flash")
    llm = ChatOpenAI(
        model="openai/gpt-oss-safeguard-20b",
        openai_api_key=api_key,
        openai_api_base=base_url,
    )
    return llm.bind_tools(tools)


def strip_message_metadata(message):
    if isinstance(message, AIMessage):
        return AIMessage(
            content=message.content,
            tool_calls=message.tool_calls if hasattr(message, "tool_calls") else [],
        )
    elif isinstance(message, HumanMessage):
        return HumanMessage(content=message.content)
    elif isinstance(message, ToolMessage):
        return ToolMessage(
            content=message.content,
            tool_call_id=message.tool_call_id,
            name=message.name if hasattr(message, "name") else None,
        )
    else:
        return message


def clean_messages(messages):
    """Clean all messages in the list"""
    return [strip_message_metadata(msg) for msg in messages]


def agent_node_factory(llm_with_tools):
    def agent_node(state: State):
        request_counter["count"] += 1
        request_num = request_counter["count"]

        logger.info("=" * 80)
        logger.info(f"🔄 LLM REQUEST #{request_num}")
        logger.info("=" * 80)

        logger.info(f"📨 Messages in conversation: {len(state['messages'])}")

        last_messages = trim_messages(
            state["messages"],
            max_tokens=2000,
            strategy="last",
            token_counter=llm_with_tools,
            include_system=True,
            start_on="human",
        )
        logger.info("=" * 80)
        logger.info(f"💬 Last message type: {last_messages}")
        if hasattr(last_messages, "content"):
            logger.info(f"💬 Last message type: {last_messages.__class__.__name__}")
            content_preview = (
                str(last_messages.content)[:200] + "..."
                if len(str(last_messages.content)) > 200
                else str(last_messages.content)
            )
            logger.info(f"📝 Content preview: {content_preview}")

        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + last_messages

        logger.info("=" * 80)

        msg = llm_with_tools.invoke(messages)
        logger.info(f"✅ LLM RESPONSE RECEIVED: {msg}")
        logger.info(f"📊 Response type: {msg.__class__.__name__}")

        if hasattr(msg, "tool_calls") and msg.tool_calls:
            logger.info(f"🔧 Tool calls made: {len(msg.tool_calls)}")
            for i, tool_call in enumerate(msg.tool_calls, 1):
                logger.info(f"   Tool #{i}:")
                logger.info(f"      Name: {tool_call.get('name', 'N/A')}")
                logger.info(
                    f"      Args: {json.dumps(tool_call.get('args', {}), indent=10)}"
                )
                logger.info(f"      ID: {tool_call.get('id', 'N/A')}")
        else:
            logger.info("💭 No tool calls - Direct response")

        if hasattr(msg, "content") and msg.content:
            content_preview = (
                msg.content[:300] + "..." if len(msg.content) > 300 else msg.content
            )
            logger.info(f"📄 Response content: {content_preview}")

        if hasattr(msg, "usage_metadata") and msg.usage_metadata:
            usage = msg.usage_metadata
            logger.info("📈 Token usage:")
            logger.info(f"   Input tokens: {usage.get('input_tokens', 'N/A')}")
            logger.info(f"   Output tokens: {usage.get('output_tokens', 'N/A')}")
            logger.info(f"   Total tokens: {usage.get('total_tokens', 'N/A')}")

        logger.info("=" * 80)

        return {"messages": [msg]}

    return agent_node


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


async def main():
    start_time = datetime.now()
    logger.info("🚀 Starting Gmail Agent")
    logger.info("=" * 80)

    tools = await client.get_tools()
    logger.info(f"✅ Tools loaded: {len(tools)} tools")

    async with aiosqlite.connect(str(DB_PATH)) as conn:
        checkpointer = AsyncSqliteSaver(conn)
        graph = build_graph(tools, checkpointer)
        config = {"configurable": {"thread_id": "gmail_thread_001"}}

        while True:
            user_query = input("You: ").strip()

            if user_query.lower() in ["exit", "quit", "bye"]:
                logger.info("👋 User ended conversation")
                break

            if not user_query:
                continue

            logger.info(f"👤 User Query: {user_query}")
            logger.info("=" * 80)

            state = await graph.ainvoke(
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": user_query,
                        }
                    ]
                },
                config=config,
            )
            if "__interrupt__" in state:
                prompt = state["__interrupt__"]
                print(f"🟡 Agent: {prompt}")
                user_response = input("🧍 Your answer: ")
                state = graph.invoke(Command(resume=user_response), config=config)

    logger.info("=" * 80)
    logger.info("🎯 EXECUTION SUMMARY")
    logger.info("=" * 80)
    logger.info("✅ Status: Success")
    logger.info(f"📊 Total LLM requests: {request_counter['count']}")
    logger.info(f"💬 Total messages in conversation: {len(state['messages'])}")

    logger.info("📝 Conversation flow:")
    for i, msg in enumerate(state["messages"], 1):
        msg_type = msg.__class__.__name__
        logger.info(f"   {i}. {msg_type}")

    end_time = datetime.now()
    execution_time = (end_time - start_time).total_seconds()
    logger.info(f"⏱️  Execution time: {execution_time:.2f} seconds")
    logger.info("=" * 80)

    final_response = state["messages"][-1]
    logger.info("📤 FINAL RESPONSE:")
    logger.info("=" * 80)
    if hasattr(final_response, "content") and final_response.content:
        print(f"\n{final_response.content}\n")
    else:
        print(f"\n{final_response}\n")

    logger.info("=" * 80)
    logger.info("✅ Gmail Agent execution completed")


if __name__ == "__main__":
    asyncio.run(main())
