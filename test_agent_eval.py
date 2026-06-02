import json
import pytest
from langchain_core.messages import HumanMessage, AIMessage
from shopping_agent import agent, llm

# ---------------------------------------------------------------------------
# TEST SET 1: Tool Call Accuracy Evaluation Matrix
# (User Query, Expected Tool Name, Expected Arguments Dictionary)
# ---------------------------------------------------------------------------
tool_accuracy_cases = [
    (
        [HumanMessage(content="Find me organic honey under $20")],
        "search_products",
        {"query": "honey", "max_price": 20.0, "is_organic": True}
    ),
    (
        [HumanMessage(content="Check what I ordered before")],
        "get_order_history",
        {}
    ),
    (
        [
            HumanMessage(content="Show me organic honey"),
            AIMessage(content="#1. Organic Raw Honey (ID:3) — $15.00 ★4.8 — organic"),  # Mock Context
            HumanMessage(content="I want to order product 3")
        ],
        "checkout",
        {"product_id": 3}
    ),
    (
        [HumanMessage(content="Don't show me any items above fifty dollars")],
        "update_user_preferences", # Corrected target assertion string
        {"max_price": 50.0}
    )
]

# ---------------------------------------------------------------------------
# TEST SET 2: Response Quality Evaluation Matrix
# (User Query, Context/Criteria to judge against)
# ---------------------------------------------------------------------------
response_quality_cases = [
    (
        "Find me organic honey under $20",
        "Relevance: Must find honey. Correctness: Items must be organic and under $20. Formatting: Must follow '#<number>. <name> (ID:<product_id>) — $<price> ★<rating> — <organic or non-organic>' format strictly."
    ),
    (
        "Can you write a poem about shoes?",
        "Guardrail Compliance: The agent must refuse to write the poem and output the exact guardrail text reminder."
    )
]

# ---------------------------------------------------------------------------
# EVALUATION 1: Tool Call Accuracy Execution
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("messages, expected_tool, expected_args", tool_accuracy_cases)
def test_tool_call_accuracy(messages, expected_tool, expected_args):
    """Asserts the agent calls the right tools with the right parameters."""
    result = agent.invoke({"messages": messages})
    
    tool_calls = []
    for msg in result["messages"]:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tool_call in msg.tool_calls:
                tool_calls.append(tool_call)

    assert len(tool_calls) > 0, f"The agent failed to trigger any tools for input history."
    
    target_call = next((tc for tc in tool_calls if tc["name"] == expected_tool), None)
    assert target_call is not None, f"Expected tool '{expected_tool}' was not called. Found: {[tc['name'] for tc in tool_calls]}"
    
    actual_args = target_call["args"]
    for key, expected_value in expected_args.items():
        assert key in actual_args, f"Argument key '{key}' missing from tool call. Actual args: {actual_args}"
        if isinstance(expected_value, float):
            assert actual_args[key] == pytest.approx(expected_value)
        else:
            assert actual_args[key] == expected_value

# ---------------------------------------------------------------------------
# EVALUATION 2: Response Quality Execution (LLM-as-a-Judge)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("query, evaluation_criteria", response_quality_cases)
def test_response_quality_judge(query, evaluation_criteria):
    """Uses LLM-as-judge to score relevance, correctness, and format compliance."""
    # 1. Generate the live agent response
    result = agent.invoke({"messages": [HumanMessage(content=query)]})
    agent_response = result["messages"][-1].content

    # 2. Construct the Judge Prompt
    judge_prompt = f"""
    You are an expert Quality Assurance Judge evaluating an AI Shopping Assistant.
    
    [USER QUERY]
    {query}
    
    [AGENT RESPONSE]
    {agent_response}
    
    [EVALUATION CRITERIA]
    {evaluation_criteria}
    
    Evaluate the agent's response based on the criteria provided. Specifically check for:
    1. Relevance: Did it stay within scope?
    2. Correctness: Is it contextually accurate?
    3. Format Compliance: Did it match the strict list format rules (#1. Name (ID:X) — $Price ★Rating — Status) if products were returned? Or did it match the exact guardrail text if it was an off-topic task?
    
    Respond with a JSON object containing exactly two keys:
    - "passed": true or false
    - "reasoning": A single sentence explaining your grade.
    
    Return ONLY raw valid JSON text. No markdown blocks, no backticks.
    """

    # 3. Call the judge model
    judge_output = llm.invoke([HumanMessage(content=judge_prompt)]).content.strip()
    
    try:
        evaluation = json.loads(judge_output)
    except json.JSONDecodeError:
        # Strip markdown code blocks if the judge returns them accidentally
        clean_output = judge_output.replace("```json", "").replace("```", "").strip()
        evaluation = json.loads(clean_output)

    assert evaluation["passed"] is True, f"LLM Judge failed the response. Reason: {evaluation['reasoning']} | Response was: '{agent_response}'"