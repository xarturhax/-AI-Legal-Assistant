from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.legal.search_baseline import normalize_search_term

ShortText = Annotated[str, Field(min_length=1, max_length=200)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Entity(StrictModel):
    name: ShortText
    type: Literal["participant", "document", "event", "other"]
    original_text: ShortText


class Fact(StrictModel):
    key: ShortText
    value: ShortText
    present_in_user_text: bool


class DirectoryTerms(StrictModel):
    search_terms: list[ShortText] = Field(max_length=3)


class Interpretation(StrictModel):
    intent: Literal["find_legal_information", "definition", "procedure", "rights", "other"]
    domain_hints: list[ShortText] = Field(max_length=8)
    search_terms: list[ShortText] = Field(max_length=10)
    entities: list[Entity] = Field(max_length=12)
    facts: list[Fact] = Field(max_length=12)
    missing_information: list[ShortText] = Field(max_length=10)
    needs_clarification: bool

    @field_validator("search_terms")
    @classmethod
    def normalize_terms(cls, values):
        result = []
        for value in values:
            value = normalize_search_term(value)
            if value is None:
                raise ValueError("Термин содержит неподдерживаемые символы.")
            if value not in result:
                result.append(value)
        return result

    def check_grounding(self, query):
        lowered = query.casefold()
        for fact in self.facts:
            fact.present_in_user_text = (
                fact.present_in_user_text
                and bool(fact.value.strip())
                and fact.value.casefold() in lowered
            )
        self.entities = [
            entity
            for entity in self.entities
            if entity.original_text.strip() and entity.original_text.casefold() in lowered
        ]
        return self
