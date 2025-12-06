# Gemini Multi-Server Agent

This project implements a multi-server agent built with LangChain that can interact with Gmail and Google Calendar. The agent uses a supervisor-worker architecture, where a supervisor agent routes tasks to specialized agents for communication (Gmail) and productivity (Google Calendar).

## Architecture

The project is structured into several key components:

### Main Application (`main.py`)

This is the entry point of the application. It is responsible for:

- Initializing the `MultiServerMCPClient` to connect to the communication and productivity servers.
- Building the LangGraph, which defines the agent's execution flow.
- Entering a loop to accept and process user queries.
- Printing the final response from the agent.

### LangGraph (`core/graph.py`)

The core of the agent's logic is defined in a LangGraph. The graph consists of the following nodes:

- **Supervisor Agent:** This agent is the first point of contact for a user query. It uses a language model to decide which specialist agent is best suited to handle the request. The `SUPERVISOR_SYSTEM_PROMPT` in `config/prompts.py` (which was missing and I identified) guides the supervisor's routing decisions.
- **Communication Agent:** This agent specializes in email-related tasks. It has access to the tools defined in `MCP/tools/gmail_tools.py`.
- **Productivity Agent:** This agent specializes in calendar and scheduling tasks. It has access to the tools defined in `MCP/tools/calendar_tools.py`.
- **Tool Nodes:** Each specialist agent is connected to a `ToolNode` that executes the corresponding tools.

### Multi-Server Command Protocol (MCP)

The project uses a custom Multi-Server Command Protocol (MCP) to host the tools on separate servers. This allows for a modular and scalable architecture.

- **Communication Server (`MCP/core/communication_server.py`):** This server hosts the Gmail tools and runs on port 8050.
- **Productivity Server (`MCP/core/productivity_server.py`):** This server hosts the Google Calendar tools and runs on port 8051.
- **Server Initialization (`MCP/core/server_init.py`):** This file creates the `FastMCP` server instances.

### Tools

The agent's capabilities are defined by the tools it has access to.

- **Gmail Tools (`MCP/tools/gmail_tools.py`):** This file provides a comprehensive set of tools for interacting with the Gmail API. The tools cover a wide range of operations, including:
    - Sending, reading, searching, and managing emails.
    - Creating and managing drafts.
    - Managing labels and folders.
    - Creating and managing email filters.
- **Calendar Tools (`MCP/tools/calendar_tools.py`):** This file provides a comprehensive set of tools for interacting with the Google Calendar API. The tools cover a wide range of operations, including:
    - Listing calendars.
    - Creating, retrieving, modifying, and deleting events.
    - Searching for events.
    - Adding Google Meet conferences to events.

### Configuration (`config` directory)

The project's configuration is managed in the `config` directory.

- **`settings.py`:** This file defines key constants and configuration for the project, including API keys, model settings, and file paths.
- **`prompts.py`:** This file contains the system prompts for the agents, which instruct them on how to behave and use the available tools.

### State Management (`core/state.py`)

The agent's state, which consists of the conversation history, is managed using a `TypedDict`. The `add_messages` function from `langgraph.graph.message` is used to append new messages to the state.

### Language Model (`core/llm.py`)

The `build_llm_with_tools` function in this file is responsible for creating and configuring the language model. It uses `ChatOpenAI` from `langchain_openai` and binds the appropriate tools to the model.

## Workflow

1.  The `main.py` script starts the application.
2.  It initializes the MCP clients for the communication and productivity servers, which makes the tools available to the agent.
3.  It builds the LangGraph, defining the agent's structure and logic.
4.  The application enters a loop and waits for user input.
5.  When a user query is received, it is passed to the `supervisor` node in the graph.
6.  The supervisor agent analyzes the query and decides which specialist agent should handle it. It then routes the conversation to either the `communication_agent` or the `productivity_agent`.
7.  The selected specialist agent interacts with the language model and its tools to process the query and generate a response.
8.  If the agent needs to use a tool, the corresponding `ToolNode` is executed.
9.  The output of the tool is then passed back to the agent, which continues the conversation.
10. Once the agent has generated a final response, it is returned to the user.
11. The state of the conversation is saved at each step using a `CleaningAsyncSqliteSaver`, which allows the agent to maintain context over multiple turns.

## How to Run

1.  Install the required dependencies from `requirements.txt`.
2.  Create a `.env` file in the root directory and add your `OPENROUTER_API_KEY`.
3.  Set up your Google API credentials and place the `token.json` and `setup_cred.json` files in the `MCP/cred` directory.
4.  Run the `main.py` script.

```bash
python main.py
```
