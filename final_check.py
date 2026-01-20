try:
    import agents
    print("agents: OK")
except ImportError:
    print("agents: MISSING")

try:
    import mcp
    print("mcp: OK")
except ImportError:
    print("mcp: MISSING")
