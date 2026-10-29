"""Page text from a datasheet PDF, page selection and revision detection.

pdfplumber reads the text layer only. A page with almost no characters is
an image; a datasheet made mostly of such pages is UNEXTRACTED in v0.1,
because OCR is out of scope (DOMAIN.md section 6).
"""

import re
from pathlib import Path

import pdfplumber
from pydantic import BaseModel

from ersatz.model.category import Category

# Fewer characters than this on a page means the page is an image [X20].
IMAGE_PAGE_CHARS = 50
DEFAULT_MAX_PAGES = 12


class PageText(BaseModel, frozen=True):
    page: int  # 1-indexed, as printed in citations
    text: str
    chars: int

    @property
    def is_image(self) -> bool:
        return self.chars < IMAGE_PAGE_CHARS


def page_texts(path: Path) -> list[PageText]:
    """Return the text of every page, 1-indexed."""
    pages: list[PageText] = []
    with pdfplumber.open(path) as pdf:
        for number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            pages.append(PageText(page=number, text=text, chars=len(page.chars)))
            page.close()
    return pages


def is_unextracted(pages: list[PageText]) -> bool:
    """True when most pages have no text layer."""
    if not pages:
        return True
    images = sum(page.is_image for page in pages)
    return images * 2 > len(pages)


# Section headings that hold the values Ersatz extracts (D-021, step 1).
_COMMON = {
    r"absolute maximum ratings": 2,
    r"recommended operating conditions": 3,
    r"electrical characteristics": 4,
    r"pin (configuration|functions|assignments?|descriptions?)": 3,
    r"(ordering|order) information|part number": 1,
    r"package (information|outline|options)|device information": 1,
    r"features": 1,
}
_CATEGORY = {
    Category.LDO: {
        r"dropout": 2,
        r"quiescent|ground current": 2,
        r"output capacitor|\besr\b|ceramic": 2,
        r"line regulation|load regulation": 1,
        r"output voltage": 1,
    },
    Category.OPAMP: {
        r"slew rate": 2,
        r"gain[- ]bandwidth|\bgbw\b|\bgbp\b": 2,
        r"input offset voltage": 2,
        r"input bias current": 2,
        r"rail[- ]to[- ]rail": 1,
        r"supply voltage": 1,
    },
}


def score_page(page: PageText, category: Category) -> int:
    text = page.text.lower()
    weights = {**_COMMON, **_CATEGORY[category]}
    return sum(weight for pattern, weight in weights.items() if re.search(pattern, text))


def select_pages(
    pages: list[PageText], category: Category, max_pages: int = DEFAULT_MAX_PAGES
) -> list[int]:
    """Pick the pages most likely to hold the extracted values.

    Page 1 is always kept: it carries the features list and often the
    pinout. The rest are the highest-scoring pages, returned in page order.
    """
    if not pages:
        return []
    chosen = {pages[0].page}
    ranked = sorted(
        (p for p in pages[1:] if not p.is_image),
        key=lambda p: (-score_page(p, category), p.page),
    )
    for page in ranked:
        if len(chosen) >= max_pages:
            break
        if score_page(page, category) > 0:
            chosen.add(page.page)
    return sorted(chosen)


_REVISION = [
    re.compile(r"\b(S[A-Z]{3}\d{3}[A-Z]{0,2})\s*[\u2013-]\s*[A-Z]+\s+\d{4}"),
    re.compile(r"\b(DS\d{8}[A-Z]?)\b"),
    re.compile(r"Document number:\s*(DS\d+\s+Rev\.\s*[\d]+\s*-\s*\d+)"),
    re.compile(r"No\.\s?(EA-\d+-\d+)"),
]
_ROHM = re.compile(r"\b(TSZ02201-\S+)")
_ROHM_REV = re.compile(r"\b(Rev\.\d{3})\b")


def find_revision(pages: list[PageText]) -> str | None:
    """Return the literature number and revision printed on the datasheet."""
    for page in pages[:2] + pages[-1:]:
        for pattern in _REVISION:
            match = pattern.search(page.text)
            if match:
                return re.sub(r"\s+", " ", match.group(1))
        rohm = _ROHM.search(page.text)
        if rohm:
            rev = _ROHM_REV.search(page.text)
            return f"{rohm.group(1)} {rev.group(1)}" if rev else rohm.group(1)
    return None
