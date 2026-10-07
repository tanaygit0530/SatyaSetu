import re
import unicodedata
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from app.core.logging import logger
from app.schemas.enums import TemporalStatus
from app.schemas.language import (
    ClaimRepresentation,
    LanguageDetectionResult,
    LanguageNeutralFacts,
)

# --- Script & Vocabulary Knowledge Bases ---

MARATHI_DISTINCTIVE_CHARS = {"\u0933", "\u0931"}  # ळ (LLA), ऱ (eyelash reph)

MARATHI_DEVANAGARI_MARKERS: Set[str] = {
    "आहे", "आहेत", "नाही", "नाहीत", "होता", "होती", "होते",
    "झाले", "झाला", "झाली", "केले", "केला", "केली", "करणार", "मिळणार",
    "द्यावे", "यांनी", "म्हणाले", "सांगितले", "असेल", "असावे", "पाहिजे",
    "मध्ये", "पासून", "त्यांना", "त्यांच्या", "याच्या", "त्याच्या", "साठी",
    "कडे", "वरून", "मुळे", "समोर", "सोबत", "बाबत", "आणि", "किंवा", "पण",
    "परंतु", "म्हणून", "मी", "आम्ही", "तुम्ही", "आपण", "शासन", "महाराष्ट्र",
    "योजना", "विद्यार्थी", "शेतकरी", "उद्या", "दिवस", "नवीन", "नियमांनुसार",
    "नागरिकांना", "करावे", "लागेल", "केल्याचे", "केल्यास", "ठरवले",
}

HINDI_DEVANAGARI_MARKERS: Set[str] = {
    "है", "हैं", "नहीं", "था", "थी", "थे", "होगा", "होगी", "होंगे",
    "किया", "किए", "करने", "मिलेगा", "मिलेगी", "देंगे", "देगा", "कहा",
    "बताया", "सकता", "सकती", "सकते", "चाहिए", "रहा", "रही", "रहे",
    "ने", "को", "से", "का", "की", "के", "में", "पर", "तक", "लिए",
    "यह", "वह", "ये", "वे", "हम", "आप", "तुम", "मेरा", "मेरी", "मेरे",
    "उसका", "उनकी", "और", "या", "लेकिन", "क्योंकि", "सरकार", "कल", "आज",
    "शुरू", "बारे", "फैसला", "देश", "भारत", "नागरिक", "पंजीकरण",
}

HINGLISH_TOKENS: Set[str] = {
    # Pronouns & determiners
    "yeh", "ye", "woh", "wo", "kya", "kyun", "kyon", "kaise", "kahan", "kab",
    "kisko", "kise", "kisne", "koi", "kuch", "sab", "sabko", "sabka",
    "hum", "humare", "humari", "humara", "aap", "aapke", "aapki", "aapka",
    "tum", "tumhara", "mera", "meri", "mere", "tera", "teri", "tere",
    "apna", "apne", "apni", "uska", "uski", "uske", "unka", "unki", "unke",
    "inhe", "unhe",
    # Postpositions & particles
    "ka", "ki", "ke", "ko", "se", "me", "mein", "pe", "par", "ne", "tak",
    "bhi", "toh", "to", "hi", "na", "mat", "nahi", "nahin",
    # Verbs & auxiliaries
    "hai", "hain", "ho", "tha", "thi", "the", "hoga", "hogi", "honge",
    "kar", "karo", "kare", "karein", "karna", "karega", "karegi",
    "diya", "diye", "liya", "liye", "raha", "rahi", "rahe",
    "gaya", "gayi", "gaye", "chahiye", "bol", "bola", "boli",
    "dekho", "suno", "bhejo", "milega", "milegi", "dega", "degi",
    "padega", "padegi", "padenge", "kaha", "bataya", "aaya", "aayi", "aaye",
    # Connectors & adverbs
    "aur", "ya", "lekin", "magar", "kyunki", "agar", "jab", "tab", "ab",
    "kal", "aaj", "parso", "jaldi", "zyada", "kam", "bahut", "bohot",
    # Slang & common vernacular nouns
    "sarkar", "sarkari", "yojana", "paisa", "paise", "rupaye", "khata",
    "dost", "dosto", "khabar", "suchna", "sach", "jhooth", "band", "chalu",
}

HINGLISH_PHRASES: List[str] = [
    "sarkar ne", "kal se", "aaj se", "band kar", "kar diya", "kar diye",
    "nahi hoga", "nahi milega", "forward karo", "share karein", "share karo",
    "padega", "mil raha", "ho gaya", "de rahi hai", "band kiya",
]

MARATHI_LATIN_TOKENS: Set[str] = {
    "aahe", "ahet", "nahi", "aamhi", "tumhi", "shasan", "yojna", "yojana",
    "mahiti", "dile", "dili", "kele", "keli", "zhale", "jhale", "karnar",
    "milnar", "sathi", "madhye", "aani", "udya", "aapan", "navin",
}

ENGLISH_COMMON_WORDS: Set[str] = {
    "the", "be", "to", "of", "and", "a", "in", "that", "have", "i", "it",
    "for", "not", "on", "with", "he", "as", "you", "do", "at", "this",
    "but", "his", "by", "from", "they", "we", "say", "her", "she", "or",
    "an", "will", "my", "one", "all", "would", "there", "their", "what",
    "so", "up", "out", "if", "about", "who", "get", "which", "go", "me",
    "when", "make", "can", "like", "time", "no", "just", "him", "know",
    "take", "people", "into", "year", "your", "good", "some", "could",
    "them", "see", "other", "than", "then", "now", "look", "only", "come",
    "its", "over", "think", "also", "back", "after", "use", "two", "how",
    "our", "work", "first", "well", "way", "even", "new", "want", "because",
    "any", "these", "give", "day", "most", "us", "is", "are", "was", "were",
    "been", "has", "had", "government", "ministry", "order", "railway",
    "police", "court", "bank", "account", "official", "portal", "scheme",
    "announced", "suspended", "circular", "verified", "breaking",
}

VERNACULAR_TO_ENGLISH_SEARCH_TERMS: Dict[str, str] = {
    "सरकार": "Government",
    "sarkar": "Government",
    "शासन": "Government",
    "मंत्रालय": "Ministry",
    "योजना": "scheme",
    "yojana": "scheme",
    "छात्रवृत्ति": "scholarship",
    "scholarship": "scholarship",
    "अनुदान": "grant DBT",
    "बंद": "banned suspended",
    "band": "banned suspended",
    "ban": "banned",
    "निलंबित": "suspended",
    "रेलवे": "Indian Railways",
    "रेल्वे": "Indian Railways",
    "ट्रेन": "train",
    "train": "train",
    "कल": "tomorrow",
    "कल से": "effective date",
    "उद्या": "tomorrow",
    "पानी": "drinking water pipeline",
    "जल": "water",
    "दूषित": "contamination",
    "अधिसूचना": "official notification",
    "आदेश": "official order",
    "परिपत्रक": "circular",
    "नियम": "rules regulations",
    "खाता": "bank account",
    "khata": "bank account",
}


class LanguageDetectorService:
    """
    Language detection service supporting English, Hindi, Marathi,
    Hinglish, and mixed vernacular code-switching.

    Guarantees:
    - Never mutates or translates the original claim.
    - Creates an English search-query representation separately.
    - Extracts language-neutral facts (numbers, dates, entities, relationships, temporal status)
      for the deterministic verdict engine.
    """

    def detect(self, text: str) -> LanguageDetectionResult:
        """
        Detects primary language ('en', 'hi', 'mr'), script ('Devanagari', 'Latin'),
        code-mixing status ('is_mixed'), and Hinglish flag ('is_hinglish').
        """
        if not text or not text.strip():
            return LanguageDetectionResult(language="en", script="Latin", is_mixed=False)

        normalized = unicodedata.normalize("NFKC", text.strip())
        lower_text = normalized.lower()

        # Count character frequencies by script
        devanagari_chars = len(re.findall(r"[\u0900-\u097F]", normalized))
        latin_chars = len(re.findall(r"[a-zA-Z]", normalized))
        total_letters = devanagari_chars + latin_chars

        if total_letters == 0:
            return LanguageDetectionResult(language="en", script="Latin", is_mixed=False)

        dev_ratio = devanagari_chars / total_letters
        lat_ratio = latin_chars / total_letters

        # Script-level mixing (both scripts present in non-trivial quantity)
        is_script_mixed = (
            devanagari_chars >= 3
            and latin_chars >= 3
            and min(dev_ratio, lat_ratio) >= 0.08
        )

        # ----------------------------------------------------
        # Case A: Devanagari content present (Hindi or Marathi, possibly mixed with English)
        # ----------------------------------------------------
        if devanagari_chars >= 2:
            # Check for distinctive Marathi characters (ळ, ऱ)
            has_marathi_chars = any(ch in normalized for ch in MARATHI_DISTINCTIVE_CHARS)
            marathi_char_weight = sum(5 for ch in normalized if ch in MARATHI_DISTINCTIVE_CHARS)

            # Tokenize Devanagari words
            words = [w.strip() for w in re.findall(r"[\u0900-\u097F]+", normalized)]
            marathi_hits = sum(1 for w in words if w in MARATHI_DEVANAGARI_MARKERS)
            hindi_hits = sum(1 for w in words if w in HINDI_DEVANAGARI_MARKERS)

            marathi_score = marathi_char_weight + (marathi_hits * 2)
            hindi_score = hindi_hits * 2

            if has_marathi_chars or (marathi_score > hindi_score and marathi_hits >= 1):
                language = "mr"
            else:
                language = "hi"

            # Check if mixed with Latin / English words
            is_mixed = latin_chars >= 3

            return LanguageDetectionResult(
                language=language,
                script="Devanagari",
                is_mixed=is_mixed,
                is_hinglish=None,
            )

        # ----------------------------------------------------
        # Case B: Latin script (English, Hinglish, or Roman Marathi)
        # ----------------------------------------------------
        words = [w.lower() for w in re.findall(r"[a-zA-Z]+", normalized)]
        total_word_count = len(words)

        if total_word_count == 0:
            return LanguageDetectionResult(language="en", script="Latin", is_mixed=False)

        # Check Hinglish n-gram phrases
        hinglish_phrase_hits = sum(1 for phrase in HINGLISH_PHRASES if phrase in lower_text)

        # Count lexical matches
        hinglish_word_hits = sum(1 for w in words if w in HINGLISH_TOKENS)
        english_word_hits = sum(1 for w in words if w in ENGLISH_COMMON_WORDS)
        marathi_latin_hits = sum(1 for w in words if w in MARATHI_LATIN_TOKENS)

        total_hinglish_weight = (hinglish_phrase_hits * 3) + hinglish_word_hits

        # Decision 1: Hinglish (Hindi written in Latin script)
        is_hinglish = (
            hinglish_phrase_hits >= 1
            or total_hinglish_weight >= 2
            or (total_hinglish_weight >= 1 and total_word_count <= 4 and english_word_hits <= 1)
        )

        if is_hinglish:
            # Code-mixing in Hinglish: has noticeable English vocabulary as well
            is_mixed = (
                is_script_mixed
                or (english_word_hits >= 3 and english_word_hits / total_word_count > 0.25)
            )
            return LanguageDetectionResult(
                language="hi",
                script="Latin",
                is_mixed=is_mixed,
                is_hinglish=True,
            )

        # Decision 2: Roman Marathi
        if marathi_latin_hits >= 2:
            return LanguageDetectionResult(
                language="mr",
                script="Latin",
                is_mixed=True,
                is_hinglish=None,
            )

        # Decision 3: Standard English
        return LanguageDetectionResult(
            language="en",
            script="Latin",
            is_mixed=is_script_mixed,
            is_hinglish=None,
        )

    def create_claim_representation(self, original_claim: str) -> ClaimRepresentation:
        """
        Creates a structured representation of the claim:
        - PRESERVES original claim text unaltered (does not translate).
        - Computes language & script detection.
        - Generates a separate English search-query representation for official retrieval.
        - Extracts language-neutral facts for verdict computation.
        """
        if not original_claim or not original_claim.strip():
            clean_claim = ""
        else:
            clean_claim = original_claim.strip()

        # 1. Detect language, script, and code mixing
        lang_res = self.detect(clean_claim)

        # 2. Synthesize English search query separately for retrieval engines
        english_search_query = self.generate_search_query(clean_claim, lang_res)

        # 3. Extract language-neutral facts for deterministic verdict logic
        neutral_facts = self.extract_language_neutral_facts(clean_claim)

        return ClaimRepresentation(
            original_claim=clean_claim,  # Preserved original claim text intact
            language_info=lang_res,
            english_search_query=english_search_query,
            neutral_facts=neutral_facts,
        )

    def generate_search_query(
        self, text: str, lang_info: Optional[LanguageDetectionResult] = None
    ) -> str:
        """
        Generates an English keyword representation for evidence retrieval.
        Preserves original text and does NOT replace the claim with this query.
        """
        if not text:
            return ""

        if lang_info is None:
            lang_info = self.detect(text)

        # If already English with Latin script and not mixed, extract core keywords
        lower = text.lower()
        search_terms: List[str] = []

        # 1. Extract proper acronyms / capitalized entities (e.g. UPI, RBI, DBT, PMSSY, NIC)
        acronyms = re.findall(r"\b[A-Z]{2,}\b", text)
        for acr in acronyms:
            if acr not in search_terms:
                search_terms.append(acr)

        # 2. Extract numeric / currency tokens (e.g. 50,000, 2026, 14)
        num_matches = re.findall(r"₹?\s*(\d[\d,]*(?:\.\d+)?)", text)
        for num in num_matches:
            cleaned_num = num.replace(",", "")
            if cleaned_num not in search_terms and int(float(cleaned_num)) > 9:
                search_terms.append(cleaned_num)

        # 3. Map vernacular domain terms to English statutory search terms
        for vernacular_term, english_target in VERNACULAR_TO_ENGLISH_SEARCH_TERMS.items():
            if vernacular_term.lower() in lower:
                for term_word in english_target.split():
                    if term_word not in search_terms:
                        search_terms.append(term_word)

        # 4. Extract English domain words present in the text
        english_keywords = [
            "government", "ministry", "railways", "train", "scholarship", "pipeline",
            "water", "contamination", "ban", "suspended", "order", "circular",
            "education", "portal", "student", "college", "deadline", "october",
        ]
        for kw in english_keywords:
            if kw in lower and kw not in [s.lower() for s in search_terms]:
                search_terms.append(kw.capitalize())

        # If terms were accumulated, join them
        if search_terms:
            return " ".join(search_terms)

        # Fallback: clean non-alphanumeric and return trimmed words
        clean_words = re.sub(r"[^\w\s]", " ", text).split()
        return " ".join(clean_words[:8])

    def extract_language_neutral_facts(self, text: str) -> LanguageNeutralFacts:
        """
        Extracts language-neutral facts (numbers, dates, entities, relationships, temporal status).
        The verdict engine computes verdicts on these structured facts rather than on prose.
        """
        if not text:
            return LanguageNeutralFacts()

        lower = text.lower()

        # 1. Numbers extraction (monetary values, thresholds, integers)
        numbers: List[Union[int, float, str]] = []
        raw_num_matches = re.findall(r"₹?\s*(\d[\d,]*(?:\.\d+)?)", text)
        for num_str in raw_num_matches:
            val_str = num_str.replace(",", "")
            try:
                if "." in val_str:
                    numbers.append(float(val_str))
                else:
                    numbers.append(int(val_str))
            except ValueError:
                numbers.append(val_str)

        # 2. Dates extraction (years, academic years, explicit calendar dates, temporal adverbs)
        dates: List[str] = []
        # Year ranges: e.g. 2026-27 or 2025
        year_matches = re.findall(r"\b\d{4}(?:-\d{2,4})?\b", text)
        dates.extend(year_matches)

        # Explicit dates: e.g. 15th October, 15 October, 15/10/2025
        cal_date_matches = re.findall(
            r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\b",
            text,
            re.IGNORECASE,
        )
        dates.extend(cal_date_matches)

        # Vernacular / English relative date anchors
        if any(w in lower for w in ["tomorrow", "kal", "कल", "उद्या"]):
            dates.append("tomorrow")
        if any(w in lower for w in ["today", "aaj", "आज"]):
            dates.append("today")

        # 3. Entities extraction (statutory bodies, platforms, acronyms, domains)
        entities: List[str] = []
        # Acronyms (e.g. UPI, RBI, PMSSY, DBT, CERT-In, UGC)
        acronyms = re.findall(r"\b[A-Z]{2,}(?:-[A-Za-z]+)?\b", text)
        entities.extend(acronyms)

        # Domain names (e.g. pmssy-gov.in)
        domain_matches = re.findall(r"\b[a-zA-Z0-9.-]+\.(?:gov\.in|nic\.in|in|org|com)\b", text)
        entities.extend(domain_matches)

        # Recognized statutory authorities & institutions
        named_bodies = [
            ("ministry of education", "Ministry of Education"),
            ("शिक्षा मंत्रालय", "Ministry of Education"),
            ("indian railways", "Indian Railways"),
            ("रेलवे", "Indian Railways"),
            ("रेल्वे", "Indian Railways"),
            ("rbi", "Reserve Bank of India"),
            ("reserve bank", "Reserve Bank of India"),
            ("government of india", "Government of India"),
            ("महाराष्ट्र शासन", "Government of Maharashtra"),
            ("ward 14", "Ward 14 Municipal Area"),
        ]
        for trigger, canonical_name in named_bodies:
            if trigger in lower and canonical_name not in entities:
                entities.append(canonical_name)

        # 4. Relationships / Action predicates
        relationships: List[str] = []
        relation_triggers = [
            (["ban", "banned", "बंद", "band"], "BANNED"),
            (["suspend", "suspended", "निलंबित"], "SUSPENDED"),
            (["notify", "notified", "अधिसूचित", "announcement", "announced"], "NOTIFIED"),
            (["grant", "granting", "अनुदान", "dbt", "milenga", "मिलेगा"], "SANCTIONED_GRANT"),
            (["contaminate", "contaminated", "दूषित"], "CONTAMINATED"),
            (["register", "registration", "पंजीकरण"], "REGISTRATION_REQUIRED"),
        ]
        for keywords, relation_name in relation_triggers:
            if any(kw in lower for kw in keywords) and relation_name not in relationships:
                relationships.append(relation_name)

        # 5. Temporal Status determination
        # If text references past years (<= 2022), it may be historical/outdated
        temporal_status = TemporalStatus.CURRENT
        for y in year_matches:
            try:
                base_year = int(y.split("-")[0])
                if base_year <= 2022:
                    temporal_status = TemporalStatus.OUTDATED
            except ValueError:
                pass

        return LanguageNeutralFacts(
            numbers=numbers,
            dates=dates,
            entities=entities,
            relationships=relationships,
            temporal_status=temporal_status,
        )


language_detector_service = LanguageDetectorService()
