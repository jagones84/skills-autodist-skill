"""Known-good MCP stdio client. Launches a server as a subprocess, lists its tools,
and calls filesystem list_directory + read_file. Adapt command/args per the server
in ~/.hermes/config.yaml mcp_servers, and the tool calls to what you need."""
import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/home/jagones"],
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("== MCP server tools ==")
            print("  " + ", ".join(t.name for t in tools.tools))

            # call_tool 1: list_directory
            res = await session.call_tool("list_directory", {"path": "/home/jagones"})
            # NB: filesystem server returns text lines, not JSON.
            for line in res.content[0].text.splitlines()[:8]:
                print("  " + line)

            # call_tool 2: read_file
            res2 = await session.call_tool("read_file", {"path": "/home/jagones/mcp_example.py"})
            for line in res2.content[0].text.splitlines()[:4]:
                print("  | " + line)


asyncio.run(main())
