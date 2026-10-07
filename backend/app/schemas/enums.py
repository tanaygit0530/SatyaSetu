from enum import Enum


class Verdict(str, Enum):
    """The 5 canonical evidentiary verdicts defined by SachCheck."""
    VERIFIED = "VERIFIED"
    FALSE = "FALSE"
    OUTDATED = "OUTDATED"
    PARTLY_SUPPORTED = "PARTLY_SUPPORTED"
    CANNOT_BE_CONFIRMED = "CANNOT_BE_CONFIRMED"


class InputType(str, Enum):
    """Ingestion channel / format types."""
    TEXT = "TEXT"
    SCREENSHOT = "SCREENSHOT"
    VOICE = "VOICE"
    PDF = "PDF"
    URL = "URL"
    WHATSAPP = "WHATSAPP"


class ProcessingStatus(str, Enum):
    """Lifecycle stages for verification pipeline processing."""
    RECEIVED = "RECEIVED"
    EXTRACTING = "EXTRACTING"
    CLAIMING = "CLAIMING"
    RETRIEVING = "RETRIEVING"
    VALIDATING = "VALIDATING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ConfidenceLevel(str, Enum):
    """Qualitative confidence ratings."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class UserRole(str, Enum):
    """Access control roles."""
    CITIZEN = "CITIZEN"
    AUDITOR = "AUDITOR"
    ADMIN = "ADMIN"


class FeedbackType(str, Enum):
    """Citizen and reviewer feedback classification."""
    ACCURATE = "ACCURATE"
    DISPUTE = "DISPUTE"
    INCOMPLETE = "INCOMPLETE"
    NEW_EVIDENCE = "NEW_EVIDENCE"


class SourceTier(str, Enum):
    """Authoritative source precedence tiers."""
    TIER_1_PRIMARY = "TIER_1_PRIMARY"      # Gazettes, PIB Fact Check, Court decrees, Official Portals
    TIER_2_SECONDARY = "TIER_2_SECONDARY"  # Statutory regulators (UGC, RBI, CERT-In, CBSE)
    TIER_3_REPUTABLE = "TIER_3_REPUTABLE"  # IFCN Signatories, National Press Archives


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
