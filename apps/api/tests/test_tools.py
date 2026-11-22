import pytest
from pydantic import ValidationError

from app.schemas.tools import CalculatorArguments, SearchArguments
from app.tools.registry import safe_calculate


def test_calculator_supports_bounded_arithmetic():
    assert safe_calculate("(2 + 3) * 4 / 2") == 10
    assert safe_calculate("2 ** 8") == 256


@pytest.mark.parametrize("expression", ["__import__('os')", "2 ** 100", "1 / 0", "float('inf')"])
def test_calculator_rejects_unsafe_or_unbounded_expressions(expression):
    with pytest.raises((ValueError, ZeroDivisionError)):
        safe_calculate(expression)


def test_tool_schemas_reject_extra_fields_and_invalid_values():
    with pytest.raises(ValidationError):
        CalculatorArguments.model_validate({"expression": "1+1", "shell": "whoami"})
    with pytest.raises(ValidationError):
        SearchArguments.model_validate({"query": ""})
