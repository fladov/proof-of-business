"""API request/response models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class GeneratePassportRequest(BaseModel):
    business_slug: str
    theme: str = Field(default="light")


class GeneratePassportResponse(BaseModel):
    api_route_prefix: str
    business_slug: str
    passport: dict
