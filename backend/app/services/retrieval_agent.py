"""Tool-calling loop for retrieval-grounded generation via a web-search and page-fetch tool.

No longer wired into module generation: as of the module-generation rework
(see docs/course_creation_websearch_flow.md), search is planned and executed
deterministically up front (see module_retrieval.py) rather than left to a
model deciding for itself whether/what to search, which also removes the
BYOM tool-use reliability tradeoff this module used to carry for that path.
Kept as-is (untested-by-removal, still independently tested) since it may be
reused for a future in-course Q&A feature.
"""

import json

from app.services.llm import complete, complete_with_tools
from app.services.retrieval import fetch_page, web_search

# Caps how many rounds of tool calls a model gets before being asked to
# just answer with what it has. Guards against a model (especially a
# weaker BYOM one) looping indefinitely instead of converging.
MAX_TOOL_ITERATIONS = 5

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the public web for material relevant to a query.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "The search query."}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_page",
            "description": "Fetch the full text content of a specific web page by URL.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "The page URL to fetch."}},
                "required": ["url"],
            },
        },
    },
]


def run_agent(messages: list[dict], model_config: dict, tavily_api_key: str) -> str:
    """Run the search/fetch/evaluate tool-use loop, returning the model's final text response.

    Args:
        messages: The conversation so far (typically a single user prompt to start).
        model_config: kwargs for the completion call, from resolve_model_config().
        tavily_api_key: The learner's Tavily API key, used for every tool call.

    Returns:
        The model's final response content, once it stops calling tools. If
        it's still calling tools after MAX_TOOL_ITERATIONS rounds, it's asked
        to answer with what it has instead of looping indefinitely.
    """
    messages = list(messages)

    for _ in range(MAX_TOOL_ITERATIONS):
        message = complete_with_tools(messages=messages, tools=TOOLS, **model_config)
        if not message.tool_calls:
            return message.content

        messages.append(
            {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {"name": call.function.name, "arguments": call.function.arguments},
                    }
                    for call in message.tool_calls
                ],
            }
        )
        for call in message.tool_calls:
            result = _execute_tool(call, tavily_api_key)
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

    messages.append({"role": "user", "content": "Please give your final answer now, without using any more tools."})
    return complete(messages=messages, **model_config)


def _execute_tool(call, tavily_api_key: str) -> str:
    args = json.loads(call.function.arguments)
    if call.function.name == "web_search":
        result = web_search(args["query"], tavily_api_key)
    else:
        result = fetch_page(args["url"], tavily_api_key)
    return json.dumps(result)
