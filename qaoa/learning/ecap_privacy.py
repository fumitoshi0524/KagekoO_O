from __future__ import annotations

import re

from .experience_models import ExperienceCapsule, PrivacyLevel


def _mask_paths(s: str) -> str:
    return re.sub(r"(/|[A-Za-z]:\\\\)[^\\s`'\"]+", "[PATH]", s)


def _mask_tokens(s: str) -> str:
    s = re.sub(r"(api[_-]?key|token|secret|password)\s*[:=]\s*\S+", r"\1=[REDACTED]", s, flags=re.I)
    s = re.sub(r"([?&](token|key|secret)=)[^&\\s]+", r"\1[REDACTED]", s, flags=re.I)
    return s


def _mask_email(s: str) -> str:
    return re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+", "[EMAIL]", s)


def sanitize_ecap(c: ExperienceCapsule, *, level: PrivacyLevel = "balanced") -> ExperienceCapsule:
    # mutate a copy-ish object expected by caller
    if level == "full":
        return c
    c.context.repo_fingerprint = _mask_paths(_mask_tokens(_mask_email(c.context.repo_fingerprint)))
    c.context.constraints = [_mask_paths(_mask_tokens(_mask_email(x))) for x in c.context.constraints]
    for st in c.solution_trace.steps:
        st.summary = _mask_paths(_mask_tokens(_mask_email(st.summary)))
        st.params_summary = _mask_paths(_mask_tokens(_mask_email(st.params_summary)))
        st.expected_effect = _mask_paths(_mask_tokens(_mask_email(st.expected_effect)))
        st.pre_conditions = [_mask_paths(_mask_tokens(_mask_email(x))) for x in st.pre_conditions]
    c.links.related_files = [re.sub(r"^.*[\\/]", "", _mask_paths(x)) for x in c.links.related_files]
    if level == "strict":
        c.solution_trace.decision_rationale_summary = ""
        c.links.related_files = []
        c.context.repo_fingerprint = ""
    c.governance.redaction_applied = True
    c.governance.privacy_level = level
    return c
