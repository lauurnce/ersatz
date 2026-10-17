"""Verify a suggested replacement: VERIFIED, PARTIAL, MISMATCH or NOT FOUND."""

from ersatz.verify.verify import Verdict, VerifyError, VerifyResult, decide, verify

__all__ = ["Verdict", "VerifyError", "VerifyResult", "decide", "verify"]
