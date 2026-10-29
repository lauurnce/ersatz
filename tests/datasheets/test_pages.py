from pathlib import Path

from ersatz.datasheets.pages import (
    PageText,
    find_revision,
    is_unextracted,
    page_texts,
    score_page,
    select_pages,
)
from ersatz.model import Category
from tests.datasheets.pdfgen import write_pdf

EN_DASH = chr(0x2013)


def page(number: int, text: str, chars: int | None = None) -> PageText:
    return PageText(page=number, text=text, chars=500 if chars is None else chars)


def test_page_texts_are_one_indexed(tmp_path: Path) -> None:
    pdf = write_pdf(tmp_path / "a.pdf", [["TEST-LDO1 front page"], ["Dropout voltage 350 mV"]])
    pages = page_texts(pdf)
    assert [p.page for p in pages] == [1, 2]
    assert "Dropout voltage 350 mV" in pages[1].text
    assert pages[1].chars > 0


def test_image_pages_make_a_datasheet_unextracted() -> None:
    assert is_unextracted([page(1, "", 0), page(2, "", 3), page(3, "Electrical")])
    assert not is_unextracted([page(1, "Features"), page(2, "", 0)])
    assert is_unextracted([])


def test_ldo_pages_with_dropout_tables_score_higher() -> None:
    table = page(5, "Electrical Characteristics\nDropout voltage 350 mV\nQuiescent current")
    other = page(9, "Typical application circuit")
    assert score_page(table, Category.LDO) > score_page(other, Category.LDO)
    assert score_page(other, Category.LDO) == 0


def test_select_pages_keeps_page_one_and_returns_page_order() -> None:
    pages = [
        page(1, "TEST-OPA1 front page"),
        page(2, "Typical application"),
        page(3, "Electrical Characteristics slew rate input offset voltage"),
        page(4, "Pin Configuration"),
        page(5, "", 0),
    ]
    assert select_pages(pages, Category.OPAMP) == [1, 3, 4]


def test_select_pages_respects_the_cap() -> None:
    pages = [page(1, "front")] + [
        page(n, "Electrical Characteristics dropout" if n % 2 else "Pin Configuration")
        for n in range(2, 30)
    ]
    chosen = select_pages(pages, Category.LDO, max_pages=4)
    assert len(chosen) == 4
    assert chosen[0] == 1
    assert all(n % 2 for n in chosen[1:])


def test_select_pages_on_empty_input() -> None:
    assert select_pages([], Category.LDO) == []


def test_revision_formats() -> None:
    cases = {
        f"SNOS412Q {EN_DASH} FEBRUARY 2000 {EN_DASH} REVISED JANUARY 2023": "SNOS412Q",
        "2016 Microchip Technology Inc. DS20001826E-page 1": "DS20001826E",
        "Document number: DS39724 Rev. 2 - 2 www.diodes.com": "DS39724 Rev. 2 - 2",
        "No.EA-236-240517": "EA-236-240517",
        "TSZ02201-0RBR0A300030-1-2 22.Feb.2016 Rev.005": "TSZ02201-0RBR0A300030-1-2 Rev.005",
        "TSZ02201-0RBR0A300030-1-2": "TSZ02201-0RBR0A300030-1-2",
    }
    for text, expected in cases.items():
        assert find_revision([page(1, text)]) == expected


def test_revision_unknown() -> None:
    assert find_revision([page(1, "DUAL OPERATIONAL AMPLIFIER")]) is None
