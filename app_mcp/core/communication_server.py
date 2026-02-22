from app_mcp.core.server_init import communication_server
import app_mcp.tools.gmail_tools
# import app_mcp.tools.gchat_tools              # Temporarily disabled due to unavailability of gchat API for personal accounts

if __name__ == "__main__":
    communication_server.run()
