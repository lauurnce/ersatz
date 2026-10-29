"""Language model clients behind one interface.

The provider and model come from settings (ERSATZ_LLM_PROVIDER and
ERSATZ_LLM_MODEL). Tests use a fake client and never call the network.
"""

from ersatz.llm.base import LLMClient, LLMError, LLMResult, Usage

__all__ = ["LLMClient", "LLMError", "LLMResult", "Usage"]
