from toolforge import MCPServer

server = MCPServer("prompt-demo")


@server.tool
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


@server.prompt(
    name="code-review",
    description="Generate a code review prompt",
)
def code_review(language: str):
    return f"Review the following {language} code carefully."


if __name__ == "__main__":
    server.run()
