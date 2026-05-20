"""Tool-call parser testleri."""

from ajanox.core.parser import extract_tool_call, strip_tool_call_tags


def test_tagged_tool_call():
    content = """<tool_call>
{"name": "read_file", "arguments": {"path": "/tmp/foo.txt"}}
</tool_call>"""
    result = extract_tool_call(content)
    assert result is not None
    assert result["name"] == "read_file"
    assert result["arguments"]["path"] == "/tmp/foo.txt"


def test_raw_json_fallback():
    content = 'Tabii, çağırıyorum: {"name": "bash", "arguments": {"command": "ls"}}'
    result = extract_tool_call(content)
    assert result is not None
    assert result["name"] == "bash"


def test_invalid_json_returns_none():
    content = "<tool_call>not json at all</tool_call>"
    assert extract_tool_call(content) is None


def test_empty_content():
    assert extract_tool_call("") is None
    assert extract_tool_call(None) is None  # type: ignore[arg-type]


def test_natural_language_no_tool_call():
    content = "Merhaba, size nasıl yardımcı olabilirim?"
    assert extract_tool_call(content) is None


def test_strip_tags():
    content = "<tool_call>foo</tool_call>"
    assert strip_tool_call_tags(content) == "foo"
    assert strip_tool_call_tags("hello") == "hello"
