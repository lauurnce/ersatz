"""Datasheet file in, validated extraction out.

The raw model reply is cached by file SHA-256, category, target device and
extractor version, so the same datasheet is never sent twice. Verification
and validation are cheap and deterministic, so they run again on every
call and pick up rule changes without a new model call.
"""

import json

from pydantic import BaseModel

from ersatz.budget.spend import SpendLedger
from ersatz.cache.base import Cache, DataKind
from ersatz.datasheets.extract import ExtractionRun, extractor_version, run_extraction
from ersatz.datasheets.fetch import DatasheetFile
from ersatz.datasheets.pages import (
    DEFAULT_MAX_PAGES,
    PageText,
    find_revision,
    is_unextracted,
    page_texts,
    select_pages,
)
from ersatz.datasheets.schema import RawExtraction
from ersatz.datasheets.validate import DatasheetRef, Extraction, validate
from ersatz.datasheets.verify import verify_quotes
from ersatz.llm.base import LLMClient
from ersatz.model.category import Category


class UnextractedError(Exception):
    """The PDF has no usable text layer. OCR is out of scope in v0.1."""


class ExtractionResult(BaseModel, frozen=True):
    extraction: Extraction
    run: ExtractionRun
    cached: bool


class _Cached(BaseModel, frozen=True):
    raw: RawExtraction
    run: ExtractionRun


def cache_key(file: DatasheetFile, category: Category, device: str | None, model: str) -> str:
    return f"{file.sha256}:{category.value}:{device or '-'}:{extractor_version(model)}"


def extract_datasheet(
    file: DatasheetFile,
    category: Category,
    llm: LLMClient,
    ledger: SpendLedger,
    cache: Cache,
    device: str | None = None,
    pages: list[PageText] | None = None,
    max_pages: int = DEFAULT_MAX_PAGES,
) -> ExtractionResult:
    """Extract, verify and validate one datasheet."""
    texts = pages if pages is not None else page_texts(file.path)
    if is_unextracted(texts):
        raise UnextractedError(f"{file.url}: no text layer on most pages")
    key = cache_key(file, category, device, llm.model)
    entry = cache.get(DataKind.EXTRACTION, key)
    if entry is not None:
        stored = _Cached.model_validate_json(entry.payload)
        raw, run, cached = stored.raw, stored.run, True
    else:
        selected = select_pages(texts, category, max_pages)
        raw, run = run_extraction(texts, selected, category, device, llm, ledger)
        payload = _Cached(raw=raw, run=run).model_dump(mode="json")
        cache.put(DataKind.EXTRACTION, key, json.dumps(payload).encode())
        cached = False
    verified = verify_quotes(raw, texts, category, sent=list(run.pages))
    ref = DatasheetRef(
        url=file.url,
        sha256=file.sha256,
        revision=find_revision(texts),
        fetched_at=file.fetched_at,
    )
    return ExtractionResult(extraction=validate(verified, category, ref), run=run, cached=cached)
