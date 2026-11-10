from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class QueryInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    query: str = Field(min_length=2, max_length=1500)
    mode: Literal["baseline", "llm"] = "baseline"

    @field_validator("query")
    @classmethod
    def trim_query(cls, value):
        value = value.strip()
        if len(value) < 2 or "\x00" in value:
            raise ValueError("Введите запрос длиной от 2 символов.")
        return value
