"""MCP client for connecting to MCP servers."""
import logging
import asyncio
from typing import Any
import sys
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession
from contextlib import AsyncExitStack

logger = logging.getLogger(__name__)

class MCPToolManager:
    """Manages connections to MCP servers and exposes their tools."""
    
    def __init__(self):
        self.servers: dict[str, dict] = {}
        self.sessions: dict[str, ClientSession] = {}
        self._exit_stack = AsyncExitStack()
    
    async def register_server(self, name: str, command: str, args: list[str] | None = None):
        """Register an MCP server configuration."""
        self.servers[name] = {
            'command': command,
            'args': args or [],
            'connected': False
        }
        logger.info(f"Registered MCP server: {name}")
    
    async def connect_server(self, name: str) -> bool:
        """Connect to a registered MCP server using stdio."""
        if name not in self.servers:
            logger.warning(f"MCP server '{name}' not registered")
            return False
            
        if name in self.sessions:
            return True
            
        server_info = self.servers[name]
        try:
            # We use AsyncExitStack to keep the connection alive
            server_params = StdioServerParameters(
                command=server_info['command'],
                args=server_info['args'],
                env=None
            )
            
            stdio_transport = await self._exit_stack.enter_async_context(stdio_client(server_params))
            stdio, write = stdio_transport
            session = await self._exit_stack.enter_async_context(ClientSession(stdio, write))
            
            await session.initialize()
            
            self.sessions[name] = session
            self.servers[name]['connected'] = True
            logger.info(f"Connected to MCP server '{name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to connect MCP server '{name}': {e}")
            return False
            
    async def call_tool(self, server_name: str, tool_name: str, arguments: dict) -> Any:
        """Call a specific tool on a server."""
        if server_name not in self.sessions:
            await self.connect_server(server_name)
            
        session = self.sessions.get(server_name)
        if not session:
            raise RuntimeError(f"Server {server_name} is not connected.")
            
        try:
            result = await session.call_tool(tool_name, arguments)
            return result
        except Exception as e:
            logger.error(f"Tool execution failed {tool_name} on {server_name}: {e}")
            raise
    
    def get_available_tools(self) -> list[str]:
        """List all available tools from connected servers."""
        # This is a simplified mockup function for listing
        return []
    
    def is_server_connected(self, name: str) -> bool:
        return self.servers.get(name, {}).get('connected', False)
        
    async def close(self):
        """Close all connections."""
        await self._exit_stack.aclose()
        self.sessions.clear()
        for s in self.servers.values():
            s['connected'] = False

_manager: MCPToolManager | None = None

def get_mcp_manager() -> MCPToolManager:
    global _manager
    if _manager is None:
        _manager = MCPToolManager()
    return _manager

def reset_mcp_manager():
    global _manager
    if _manager is not None:
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(_manager.close())
            else:
                loop.run_until_complete(_manager.close())
        except Exception:
            pass
    _manager = None
