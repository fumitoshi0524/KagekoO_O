import pytest
from kageko.tools.ast_tool import ast_summarize


def test_summarize_python():
    source = """
def hello():
    return "world"

class MyClass:
    def method(self):
        pass
"""
    result = ast_summarize(source, "python")
    assert "function_definition" in result
    assert "class_definition" in result


def test_summarize_empty():
    result = ast_summarize("", "python")
    assert "no declarations" in result


def test_summarize_unsupported_language():
    with pytest.raises(Exception, match="Unsupported language"):
        ast_summarize("x", "fortran")
