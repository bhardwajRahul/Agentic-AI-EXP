import asyncio
from datetime import datetime

import aiosqlite
from langchain_mcp_adapters.client import MultiServerMCPClient

from config.settings import (
    CHECKPOINT_DB,
    DEFAULT_THREAD_ID,
    communication_config,
    content_config,
    planning_config,
    supervisor_config,
)
from core.graph import build_graph
from core.voice_inference import VoiceInference
from utils.helper import (
    AsyncSqliteSaver,
    clean_text_for_tts,
    request_counter,
    setup_logger,
)
from utils.memory_manager import log_event

logger = setup_logger(__name__)


async def keyword_listener(queue, loop):
    while True:
        try:
            user_input = await loop.run_in_executor(None, input)
            if user_input.strip():
                await queue.put(("TEXT", user_input.strip()))
        except EOFError:
            break


async def voice_listener(queue, voice_agent, loop):
    while True:
        try:
            text = await loop.run_in_executor(None, voice_agent.listen_continuous)
            if text.strip():
                await queue.put(("VOICE", text.strip()))
        except Exception as e:
            logger.error(f"Error in voice listener: {e}")
            await asyncio.sleep(1)  # Avoid tight loop on error


async def main():
    start_time = datetime.now()
    logger.info("🚀 Starting Agent")
    logger.info("=" * 80)

    try:
        communication_client = MultiServerMCPClient(communication_config)
        communication_tools = await communication_client.get_tools()
        logger.info(f"📧 Communication Tools: {len(communication_tools)}")

        planning_client = MultiServerMCPClient(planning_config)
        planning_tools = await planning_client.get_tools()
        logger.info(f"✅ Planning Tools: {len(planning_tools)}")
        tool_sets = {"communication": communication_tools, "planning": planning_tools}

        content_client = MultiServerMCPClient(content_config)
        content_tools = await content_client.get_tools()
        logger.info(f"📺 Content Tools: {len(content_tools)}")

        supervisor_client = MultiServerMCPClient(supervisor_config)
        supervisor_tools = await supervisor_client.get_tools()
        logger.info(f"🔍 Supervisor Tools: {len(supervisor_tools)}")

        tool_sets = {
            "communication": communication_tools,
            "planning": planning_tools,
            "content": content_tools,
            "supervisor": supervisor_tools,
        }

        async with aiosqlite.connect(str(CHECKPOINT_DB)) as connection:
            checkpointer = AsyncSqliteSaver(connection)
            graph = build_graph(tool_sets, checkpointer)

            g = graph.get_graph()

            png_bytes = g.draw_mermaid_png()

            with open("docs/images/agent_structure_graph.png", "wb") as f:
                f.write(png_bytes)

            config = {"configurable": {"thread_id": DEFAULT_THREAD_ID}}

            voice = VoiceInference()

            event_queue = asyncio.Queue()
            loop = asyncio.get_running_loop()

            # Start listeners
            asyncio.create_task(keyword_listener(event_queue, loop))
            asyncio.create_task(voice_listener(event_queue, voice, loop))

            print("\n✅ SYSTEM READY.")
            print("   - Type anytime and press Enter.")
            print(f"   - Or say '{voice.WAKE_WORD_MODEL}' followed by command.\n")

            while True:
                source, query = await event_queue.get()

                if query.lower() in ["exit", "quit"]:
                    print("👋 Bye!")
                    break

                print(f"\n👤 User ({source}): {query}")

                try:
                    await log_event(
                        thread_id=DEFAULT_THREAD_ID,
                        actor="Human_node",
                        message=query,
                        metadata={},
                    )
                except Exception as e:
                    logger.error(f"Failed to log human_node audit event: {e}")

                state = await graph.ainvoke(
                    {"messages": [{"role": "user", "content": query}]},
                    config=config,
                )

                last_msg = state["messages"][-1]
                if last_msg.type == "ai" and last_msg.content:
                    final_response = last_msg.content
                    print(f"\n🤖 Gemini: {final_response}\n")

                    if source == "VOICE":
                        clean_resp = clean_text_for_tts(final_response)
                        await loop.run_in_executor(None, voice.speak, clean_resp)

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

            logger.info("=" * 80)
            logger.info("✅ Multi-Server Agent execution completed")

    except Exception as e:
        logger.exception(f"❌ An error occurred: {e}")
        raise e


if __name__ == "__main__":
    asyncio.run(main())
