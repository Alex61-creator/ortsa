from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SubjectInstanceSchema(BaseModel):
    planets: list[dict[str, Any]] = Field(default_factory=list)
    houses: list[dict[str, Any]] = Field(default_factory=list)
    angles: list[dict[str, Any]] = Field(default_factory=list)


class ChartResultSchema(BaseModel):
    report: dict[str, Any] = Field(default_factory=dict)
    svg: str = ""
    png: bytes
    instance: SubjectInstanceSchema
    llm_context: str = ""


class SynastryResultSchema(BaseModel):
    png: bytes
    subject1: SubjectInstanceSchema
    subject2: SubjectInstanceSchema
    aspects: list[dict[str, Any]] = Field(default_factory=list)
    chart_data: dict[str, Any] = Field(default_factory=dict)
    llm_context: str = ""
