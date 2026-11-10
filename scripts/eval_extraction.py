"""Run datasheet extraction on the gold set and write docs/EXTRACTION_EVAL.md.

Costs money: each datasheet not yet in the extraction cache is one model
call. The spend ledger refuses any call that could cross --max-usd for this
run or the v0.1 total cap.

    uv run python scripts/eval_extraction.py --max-usd 5
    uv run python scripts/eval_extraction.py --cached-only   # rescore, no calls
"""

import argparse
import re
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from ersatz.budget.spend import SpendCapError, SpendLedger
from ersatz.cache import SqliteCache
from ersatz.cache.base import Cache, DataKind
from ersatz.datasheets.extract import extractor_version
from ersatz.datasheets.fetch import DatasheetFetchError, DatasheetFile, fetch, load_local
from ersatz.datasheets.pipeline import UnextractedError, cache_key, extract_datasheet
from ersatz.datasheets.report import DatasheetRun, EvalRun, render
from ersatz.datasheets.scoring import GoldFile, LabelScore, load_gold, score
from ersatz.datasheets.validate import Confidence
from ersatz.llm.base import LLMClient, LLMError
from ersatz.settings import get_settings

ROOT = Path(__file__).resolve().parent.parent
GetFile = Callable[[GoldFile], DatasheetFile]


def _reason_group(reason: str) -> str:
    text = re.sub(r"'[^']*'", "'X'", reason)
    return re.sub(r"\d+(\.\d+)?", "N", text)


def evaluate(
    gold_files: list[GoldFile],
    get_file: GetFile,
    llm: LLMClient,
    ledger: SpendLedger,
    cache: Cache,
    cached_only: bool = False,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> EvalRun:
    started = clock()
    runs: list[DatasheetRun] = []
    scores: list[LabelScore] = []
    for gold in gold_files:
        base = {"id": gold.id, "manufacturer": gold.manufacturer, "category": gold.category.value}
        try:
            file = get_file(gold)
            if file.sha256 != gold.sha256:
                raise DatasheetFetchError(f"hash {file.sha256[:12]} differs from the label file")
            key = cache_key(file, gold.category, gold.device, llm.model)
            if cached_only and cache.get(DataKind.EXTRACTION, key) is None:
                raise LLMError("no cached reply and --cached-only is set")
            result = extract_datasheet(file, gold.category, llm, ledger, cache, device=gold.device)
        except (DatasheetFetchError, UnextractedError, LLMError, SpendCapError) as exc:
            runs.append(DatasheetRun(**base, error=f"{type(exc).__name__}: {exc}"))
            continue
        ex = result.extraction
        usage = result.run.call.usage
        low = sum(p.confidence is Confidence.LOW for p in ex.parameters)
        low += sum(p.confidence is Confidence.LOW for p in ex.pinouts)
        runs.append(
            DatasheetRun(
                **base,
                pages_sent=result.run.pages,
                kept=len(ex.parameters) + len(ex.packages) + len(ex.pinouts) + len(ex.features),
                dropped=len(ex.dropped),
                low_confidence=low,
                cost_usd=0.0 if result.cached else result.run.call.cost_usd,
                input_tokens=0 if result.cached else usage.input_tokens,
                output_tokens=0 if result.cached else usage.output_tokens,
                cached=result.cached,
                drop_reasons=tuple(_reason_group(d.reason) for d in ex.dropped),
            )
        )
        scores.extend(score(gold, ex))
    statuses = {g.status for g in gold_files}
    return EvalRun(
        started_at=started,
        model=llm.model,
        extractor=extractor_version(llm.model),
        label_status=statuses.pop() if len(statuses) == 1 else "MIXED",
        datasheets=tuple(runs),
        scores=tuple(scores),
    )


def file_getter(cache: Cache, cache_dir: Path, pdf_dir: Path | None) -> GetFile:
    """Use a local copy named <id>.pdf when there is one, else download."""

    def get(gold: GoldFile) -> DatasheetFile:
        if pdf_dir is not None and (pdf_dir / f"{gold.id}.pdf").exists():
            return load_local(pdf_dir / f"{gold.id}.pdf", gold.url, cache_dir)
        return fetch(gold.url, cache, cache_dir)

    return get


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--gold-dir", type=Path, default=ROOT / "eval" / "extraction" / "gold")
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "EXTRACTION_EVAL.md")
    parser.add_argument("--pdf-dir", type=Path, default=None, help="local PDFs named <id>.pdf")
    parser.add_argument("--max-usd", type=float, default=5.0, help="spend cap for this run")
    parser.add_argument("--cached-only", action="store_true", help="never call the model")
    parser.add_argument("--only", action="append", default=[], help="datasheet id to run")
    args = parser.parse_args(argv)

    from ersatz.llm.factory import make_llm

    settings = get_settings()
    cache = SqliteCache(settings.ersatz_cache_dir / "ersatz.sqlite")
    gold = [g for g in load_gold(args.gold_dir) if not args.only or g.id in args.only]
    llm = make_llm(settings)
    ledger = SpendLedger(cache, run_cap_usd=args.max_usd)
    getter = file_getter(cache, settings.ersatz_cache_dir, args.pdf_dir)
    run = evaluate(gold, getter, llm, ledger, cache, cached_only=args.cached_only)
    args.out.write_text(render(run))
    print(f"wrote {args.out}")
    print(f"run cost {ledger.run_spent:.4f} USD, total recorded {ledger.total_spent():.4f} USD")
    errors = [d for d in run.datasheets if d.error]
    for d in errors:
        print(f"{d.id}: {d.error}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
