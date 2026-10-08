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

    def __str__(self) -> str:
        return self.value



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
    """
    Chronological alignment status distinguishing TRUE THEN from TRUE NOW:
    - CURRENT: Policy/fact is actively in effect and supported by latest evidence.
    - HISTORICAL_TRUE: Historical claim (e.g. 'Announced in 2024') accurately describing a past event.
    - EXPIRED: Order, scheme, or decree reached its end date / validity expired.
    - CONTRADICTED_BY_NEWER_EVIDENCE: Was true then, but superseded/discontinued by newer evidence.
    - DATE_UNKNOWN: No reliable temporal anchors found in claim or evidence.
    """
    CURRENT = "CURRENT"
    HISTORICAL_TRUE = "HISTORICAL_TRUE"
    EXPIRED = "EXPIRED"
    CONTRADICTED_BY_NEWER_EVIDENCE = "CONTRADICTED_BY_NEWER_EVIDENCE"
    DATE_UNKNOWN = "DATE_UNKNOWN"

    # Backwards compatibility aliases
    OUTDATED = "OUTDATED"
    HISTORICAL_MISMATCH = "HISTORICAL_MISMATCH"
    UNDATED = "UNDATED"


class ContradictionStrength(str, Enum):
    """Strength of contradiction against an assertion."""
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    NONE = "NONE"


class ClaimType(str, Enum):
    """
    Lightweight claim classification types influencing targeted retrieval:
    FACT, RELATIONSHIP, DATE, NUMBER, LOCATION, PERSON, ORGANIZATION, EVENT, POLICY, CURRENT_STATUS, COMPARISON.
    """
    FACT = "FACT"
    RELATIONSHIP = "RELATIONSHIP"
    DATE = "DATE"
    NUMBER = "NUMBER"
    LOCATION = "LOCATION"
    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    EVENT = "EVENT"
    POLICY = "POLICY"
    CURRENT_STATUS = "CURRENT_STATUS"
    COMPARISON = "COMPARISON"


