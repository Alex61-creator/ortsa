from pydantic import BaseModel, Field
import re

class LLMResponseSchema(BaseModel):
    raw_content: str
    sections: dict = Field(default_factory=dict)

    @classmethod
    def from_markdown(cls, markdown: str) -> "LLMResponseSchema":
        sections = {}
        pattern = r"##\s*\[(.*?)\](.*?)(?=##\s*\[|\Z)"
        matches = re.findall(pattern, markdown, re.DOTALL)
        for name, content in matches:
            sections[name.strip()] = content.strip()
        return cls(raw_content=markdown, sections=sections)