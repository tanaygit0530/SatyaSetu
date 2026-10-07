from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from app.schemas.enums import TemporalStatus


class LanguageDetectionInput(BaseModel):
    """Input payload for language detection."""
    text: str = Field(..., min_length=1, description="Input claim or message text")


class LanguageDetectionResult(BaseModel):
    """
    Standardized language and script detection result.
    Supports English, Hindi, Marathi, Hinglish, and mixed inputs.
    """
    language: str = Field(..., description="Detected ISO language code: 'en', 'hi', or 'mr'")
    script: str = Field(..., description="Script representation: 'Devanagari' or 'Latin'")
    is_mixed: bool = Field(default=False, description="Whether input contains mixed languages or scripts")
    is_hinglish: Optional[bool] = Field(
        default=None,
        description="Whether input is Hinglish (Hindi written in Latin script)",
    )

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes to the exact dictionary representation requested in specification.
        For normal inputs:
            {"language": "...", "script": "...", "is_mixed": ...}
        For Hinglish inputs:
            {"language": "hi", "script": "Latin", "is_hinglish": true}
        """
        if self.is_hinglish:
            data: Dict[str, Any] = {
                "language": self.language,
                "script": self.script,
                "is_hinglish": True,
            }
            if self.is_mixed:
                data["is_mixed"] = True
            return data

        return {
            "language": self.language,
            "script": self.script,
            "is_mixed": self.is_mixed,
        }


class LanguageNeutralFacts(BaseModel):
    """
    Language-neutral factual representation for deterministic verdict logic.
    Verdict engines must operate on structured facts rather than translated prose.
    """
    numbers: List[Union[int, float, str]] = Field(
        default_factory=list,
        description="Extracted numerical values and monetary figures (e.g. 50000, 14)",
    )
    dates: List[str] = Field(
        default_factory=list,
        description="Extracted date strings, deadlines, or temporal anchors (e.g. '2026-27', '15 October')",
    )
    entities: List[str] = Field(
        default_factory=list,
        description="Extracted statutory authorities, schemes, institutions, and platforms",
    )
    relationships: List[str] = Field(
        default_factory=list,
        description="Extracted factual relationships or action predicates (e.g. 'banned', 'sanctioned')",
    )
    temporal_status: TemporalStatus = Field(
        default=TemporalStatus.CURRENT,
        description="Temporal alignment status (CURRENT, OUTDATED, etc.)",
    )


class ClaimRepresentation(BaseModel):
    """
    Complete language-aware claim representation.
    Preserves original claim text untouched while providing a separate English search query
    and structured language-neutral facts for verdict computation.
    """
    original_claim: str = Field(
        ...,
        description="Preserved original claim text in its native vernacular language and script",
    )
    language_info: LanguageDetectionResult = Field(
        ...,
        description="Detailed language and script detection metadata",
    )
    english_search_query: str = Field(
        ...,
        description="Separate English keyword search query synthesized solely for official evidence retrieval",
    )
    neutral_facts: LanguageNeutralFacts = Field(
        ...,
        description="Structured language-neutral facts for deterministic verdict logic",
    )
