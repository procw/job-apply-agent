"""Detect staffing / recruiting agencies that repost client roles.

Used during ingest (job_inclusion) and evaluate (scoring) so agency listings
are skipped or rejected. Toggle with preferences.exclude_staffing_agencies.
"""
from __future__ import annotations

import re
from typing import Any

# Normalized lowercase substrings — matched against normalized company name.
# Prefer distinctive names; generic words use _COMPANY_PATTERNS instead.
KNOWN_STAFFING_AGENCIES: frozenset[str] = frozenset(
    {
        "adecco",
        "aerotek",
        "actalent",
        "allegis group",
        "allegis",
        "apex systems",
        "ascendion",
        "aston carter",
        "astrix technology",
        "atrium",
        "bcforward",
        "beacon hill",
        "belcan",
        "brooksource",
        "burtch works",
        "collabera",
        "comrise",
        "creative circle",
        "cybercoders",
        "disys",
        "diversant",
        "eclaro",
        "experis",
        "express employment",
        "fast switch",
        "firstpro",
        "first pro",
        "genuent",
        "gdh consulting",
        "hired by matrix",
        "hiredbymatrix",
        "hudson",
        "huxley",
        "iconma",
        "insight global",
        "intelletec",
        "interis",
        "judge group",
        "judge consulting",
        "jobot",
        "kelly services",
        "kforce",
        "korn ferry",
        "lance soft",
        "lancesoft",
        "lhh",
        "lucas group",
        "manpower",
        "manpowergroup",
        "michael page",
        "mindlance",
        "modis",
        "mondo",
        "motion recruitment",
        "motion recruiting",
        "motionrecruitment",
        "nesco resource",
        "nextech",
        "next phase",
        "on assignment",
        "optomi",
        "oxford global",
        "parker lynch",
        "peopleready",
        "pridestaff",
        "protingent",
        "procom",
        "princeton information",
        "princeton consulting",
        "randstad",
        "remx",
        "remedy staffing",
        "robert half",
        "robert half technology",
        "russell tobin",
        "sageit",
        "sage it",
        "signature consultants",
        "softworld",
        "solomon page",
        "spherion",
        "staffmark",
        "stefanini",
        "sthree",
        "talent burst",
        "talentburst",
        "tapfin",
        "teksystems",
        "tek systems",
        "the judge group",
        "trident consulting",
        "trueblue",
        "tundra technical",
        "upside group",
        "vaco",
        "volt",
        "vsoft consulting",
        "w3global",
        "w3 global",
        "yoh",
        "zavient",
        "nityo",
        "nitya software",
        "ask consulting",
        "addison group",
        "vitality group",
        "cypress hcm",
        "cxc",
    }
)


_COMPANY_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bstaffing\b",
        r"\brecruiting\b",
        r"\brecruitment\b",
        r"\btalent solutions\b",
        r"\btalent partners\b",
        r"\bworkforce solutions\b",
        r"\bpersonnel services\b",
        r"\bemployment services\b",
        r"\bstaffing agency\b",
        r"\brecruiting firm\b",
        r"\bsearch firm\b",
        r"\bexecutive search\b",
        r"\bcontract staffing\b",
        r"\bit staffing\b",
        r"\btech staffing\b",
        r"\btechnology staffing\b",
    )
)

_DESCRIPTION_AGENCY_HINTS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bon behalf of (?:our )?client\b",
        r"\bour client(?:'s)?\b.*\b(?:seeking|looking|hiring)\b",
        r"\bstaffing (?:firm|agency|company)\b",
        r"\brecruiting (?:firm|agency)\b",
        r"\bcontract (?:role|position|assignment) (?:for|with) (?:our )?client\b",
        r"\bthird[- ]party (?:recruiter|agency)\b",
    )
)

_MIN_KNOWN_LEN = 5


def _normalize_company(name: str) -> str:
    text = re.sub(r"[^\w\s&+]", " ", (name or "").lower())
    return re.sub(r"\s+", " ", text).strip()


def _known_agency_hit(company_norm: str) -> str | None:
    if not company_norm:
        return None
    for needle in sorted(KNOWN_STAFFING_AGENCIES, key=len, reverse=True):
        if len(needle) < _MIN_KNOWN_LEN and needle not in company_norm.split():
            continue
        if needle in company_norm:
            return needle
    return None


def _pattern_hit(company: str) -> str | None:
    if not company.strip():
        return None
    for pat in _COMPANY_PATTERNS:
        m = pat.search(company)
        if m:
            return m.group(0).lower()
    return None


def _description_hit(description: str) -> str | None:
    text = (description or "")[:4000]
    if not text.strip():
        return None
    for pat in _DESCRIPTION_AGENCY_HINTS:
        m = pat.search(text)
        if m:
            return m.group(0).lower()
    return None


def company_is_staffing_agency(company: str) -> bool:
    """True when the employer name looks like a staffing/recruiting agency (UI grouping)."""
    company_norm = _normalize_company(company)
    if _known_agency_hit(company_norm):
        return True
    return _pattern_hit(company or "") is not None


def staffing_agency_reason(
    company: str,
    description: str = "",
    *,
    allow_description: bool = True,
) -> str | None:
    """Return a short reason string if the job looks like a staffing agency post."""
    company_norm = _normalize_company(company)
    hit = _known_agency_hit(company_norm)
    if hit:
        return f'Known staffing agency "{hit}"'
    pat = _pattern_hit(company)
    if pat:
        return f'Company name matches staffing pattern "{pat}"'
    if allow_description:
        desc = _description_hit(description)
        if desc:
            return f"Description indicates agency post ({desc})"
    return None


def staffing_agency_exclusion(
    job: dict[str, Any] | Any,
    profile: dict[str, Any] | None,
) -> tuple[str, str] | None:
    """Return (reject_code, detail) when staffing agencies should be excluded."""
    if not profile:
        return None
    prefs = profile.get("preferences") or {}
    if not prefs.get("exclude_staffing_agencies"):
        return None

    if isinstance(job, dict):
        company = str(job.get("company") or "")
        description = " ".join(
            str(job.get(k) or "") for k in ("description_text", "description", "title")
        )
    else:
        company = str(getattr(job, "company", "") or "")
        description = " ".join(
            str(getattr(job, k, "") or "")
            for k in ("description_text", "description", "title")
        )

    company_norm = _normalize_company(company)
    allowlist = {
        _normalize_company(str(x)) for x in (prefs.get("staffing_agency_allowlist") or []) if str(x).strip()
    }
    if company_norm and company_norm in allowlist:
        return None
    for allowed in allowlist:
        if allowed and allowed in company_norm:
            return None

    reason = staffing_agency_reason(company, description)
    if reason:
        return ("staffing_agency", reason)
    return None
