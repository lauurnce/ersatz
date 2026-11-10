"""One extraction call: selected pages in, raw cited values out."""

from pydantic import BaseModel, ValidationError

from ersatz.budget.spend import CallRecord, SpendLedger, estimate_tokens
from ersatz.datasheets.pages import PageText
from ersatz.datasheets.prompt import PROMPT_VERSION, SYSTEM, build_user_message
from ersatz.datasheets.schema import SCHEMA_VERSION, RawExtraction, json_schema
from ersatz.llm.base import LLMClient, LLMError
from ersatz.model.category import Category

MAX_OUTPUT_TOKENS = 32000


class ExtractionRun(BaseModel, frozen=True):
    provider: str
    model: str
    schema_version: str
    prompt_version: str
    pages: tuple[int, ...]
    request_id: str | None
    call: CallRecord


def extractor_version(model: str) -> str:
    """Cache key part: changes when the model, schema or prompt changes."""
    return f"{model}/s{SCHEMA_VERSION}/p{PROMPT_VERSION}"


def run_extraction(
    pages: list[PageText],
    selected: list[int],
    category: Category,
    device: str | None,
    llm: LLMClient,
    ledger: SpendLedger,
    max_tokens: int = MAX_OUTPUT_TOKENS,
) -> tuple[RawExtraction, ExtractionRun]:
    """Send the selected pages and parse the reply into RawExtraction.

    The spend ledger is checked before the call and updated after it, also
    when the reply turns out to be unusable.
    """
    user = build_user_message(pages, selected, category, device)
    ledger.check(llm.model, estimate_tokens(SYSTEM, user), max_tokens)
    result = llm.complete_json(SYSTEM, user, json_schema(category), max_tokens)
    call = ledger.record(llm.model, result.usage, purpose=f"extract:{category.value}")
    try:
        raw = RawExtraction.model_validate(result.data)
    except ValidationError as exc:
        raise LLMError(f"reply does not match the extraction schema: {exc}") from exc
    run = ExtractionRun(
        provider=llm.provider,
        model=result.model,
        schema_version=SCHEMA_VERSION,
        prompt_version=PROMPT_VERSION,
        pages=tuple(selected),
        request_id=result.request_id,
        call=call,
    )
    return raw, run
