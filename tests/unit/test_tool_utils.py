from core.tool_utils import ToolNormalizer


def test_tool_normalization():
    shim_tools = [("get_weather", lambda x: x, "Get weather for a city")]

    # Test OpenAI
    oa = ToolNormalizer.to_openai(shim_tools)
    assert len(oa) == 1
    assert oa[0]["type"] == "function"
    assert oa[0]["function"]["name"] == "get_weather"

    # Test Gemini
    gem = ToolNormalizer.to_gemini(shim_tools)
    assert len(gem) == 1
    assert "function_declarations" in gem[0]
    assert gem[0]["function_declarations"][0]["name"] == "get_weather"

    # Test Claude
    claude = ToolNormalizer.to_claude(shim_tools)
    assert len(claude) == 1
    assert claude[0]["name"] == "get_weather"
    assert "input_schema" in claude[0]
