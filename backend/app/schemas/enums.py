from enum import Enum


class Verdict(str, Enum):
    """The 5 canonical evidentiary verdicts defined by SachCheck."""
    VERIFIED = "VERIFIED"
    FALSE = "FALSE"
    OUTDATED = "OUTDATED"
    PARTLY_SUPPORTED = "PARTLY_SUPPORTED"
    CANNOT_BE_CONFIRMED = "CANNOT_BE_CONFIRMED"


class SourceTier(str, Enum):
    """Authoritative source precedence tiers."""
    TIER_1_PRIMARY = "TIER_1_PRIMARY"      # Gazettes, PIB Fact Check, Court decrees, Official Portals
    TIER_2_SECONDARY = "TIER_2_SECONDARY"  # Statutory regulators (UGC, RBI, CERT-In, CBSE)
    TIER_3_REPUTABLE = "TIER_3_REPUTABLE"  # IFCN Signatories, National Press Archives


class InputType(str, Enum):
    """Ingestion channel / format."""
    TEXT = "TEXT"
    SCREENSHOT = "SCREENSHOT"
    VOICE = "VOICE"
    PDF = "PDF"
    URL = "URL"
    WHATSAPP = "WHATSAPP"


class Language(str, Enum):
    """Supported vernacular languages."""
    EN = "en"
    HI = "hi"
    MR = "mr"


class TemporalStatus(str, Enum):
    """Chronological alignment flag."""
    CURRENT = "CURRENT"
    OUTDATED = "OUTDATED"
    HISTORICAL_MISMATCH = "HISTORICAL_MISMATCH"
    UNDATED = "UNDATED"
