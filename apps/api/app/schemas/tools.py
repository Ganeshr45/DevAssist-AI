from pydantic import BaseModel, ConfigDict, Field


class ToolArguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class CalculatorArguments(ToolArguments):
    expression: str = Field(max_length=200)


class CodeExplanationArguments(ToolArguments):
    code: str = Field(max_length=12000)
    language: str = Field(max_length=40)


class ErrorAnalysisArguments(ToolArguments):
    error: str = Field(max_length=8000)
    language: str = Field(max_length=40)


class SearchArguments(ToolArguments):
    query: str = Field(min_length=1, max_length=1000)
