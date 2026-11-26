from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.legal.search_baseline import contains_phrase, normalize_search_term

ShortText = Annotated[str, Field(min_length=1, max_length=200)]
BARE_ANSWERS = {"да", "нет", "неизвестно"}


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


class RelevantSource(StrictModel):
    number: int
    query_quote: ShortText


class SourceRelevance(StrictModel):
    relevant: list[RelevantSource] = Field(max_length=12)


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
            value = fact.value.casefold().strip()
            fact.present_in_user_text = (
                fact.present_in_user_text
                and value not in BARE_ANSWERS
                and contains_phrase(lowered, value)
            )
        self.entities = [
            entity
            for entity in self.entities
            if entity.original_text.casefold().strip() not in BARE_ANSWERS
            and contains_phrase(lowered, entity.original_text.casefold().strip())
        ]
        return self
