"""Verify a suggested replacement: VERIFIED, PARTIAL, MISMATCH or NOT FOUND."""

from ersatz.verify.check import CheckItem, CheckReport, check_text
from ersatz.verify.mentions import extract_mpns
from ersatz.verify.verify import Verdict, VerifyError, VerifyResult, decide, verify

__all__ = [
    "CheckItem",
    "CheckReport",
    "Verdict",
    "VerifyError",
    "VerifyResult",
    "check_text",
    "decide",
    "extract_mpns",
    "verify",
]
