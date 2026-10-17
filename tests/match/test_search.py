import pytest

from ersatz.match.search import find_candidates, keywords, parametric_query
from ersatz.model import Category
from ersatz.providers.base import ParametricQuery
from tests.match.fakes import FakeProvider, record
from tests.match.parts import ldo, opamp

ORIGINAL = ldo("TEST-LDO-OLD").part


def test_parametric_query_uses_group_and_key_values() -> None:
    query = parametric_query(ORIGINAL, Category.LDO)
    assert query.package_groups == ("SOT23-5",)
    assert query.ranges == {"vout": (3.3, 3.3), "iout": (0.3, None)}
    opa = parametric_query(opamp("TEST-OPA-OLD").part, Category.OPAMP)
    assert opa.ranges == {"channels": (2, 2)}


def test_keywords_come_from_the_original_only() -> None:
    assert keywords(ORIGINAL, Category.LDO) == "3.3V LDO voltage regulator SOT23-5"
    assert (
        keywords(opamp("TEST-OPA-OLD").part, Category.OPAMP) == "dual operational amplifier SOIC8N"
    )


def test_parametric_provider_gets_the_query() -> None:
    provider = FakeProvider("p1", [record("TEST-A")])
    result = find_candidates(ORIGINAL, [provider])
    assert isinstance(provider.queries[0], ParametricQuery)
    assert [r.mpn for r in result.records] == ["TEST-A"]
    assert result.notes == ()


def test_keyword_fallback_when_parametric_is_not_supported() -> None:
    provider = FakeProvider("p2", [record("TEST-A")], parametric=False)
    result = find_candidates(ORIGINAL, [provider])
    assert provider.queries == ["3.3V LDO voltage regulator SOT23-5"]
    assert "used keyword search" in result.notes[0]
    assert result.queries[0].startswith("p2 keyword:")


def test_results_are_merged_deduplicated_and_skip_the_original() -> None:
    first = FakeProvider("p1", [record("TEST-A"), record("TEST-LDO-OLD"), record("TEST-B")])
    second = FakeProvider("p2", [record("test-a"), record("TEST-C", manufacturer="Other Co")])
    result = find_candidates(ORIGINAL, [first, second])
    assert [r.mpn for r in result.records] == ["TEST-A", "TEST-B", "TEST-C"]
    assert result.found == 5


def test_same_part_number_from_two_manufacturers_is_kept() -> None:
    provider = FakeProvider("p1", [record("TEST-A"), record("TEST-A", manufacturer="Other Co")])
    assert len(find_candidates(ORIGINAL, [provider]).records) == 2


def test_cap_limits_candidates_and_says_so() -> None:
    provider = FakeProvider("p1", [record(f"TEST-{n:02d}") for n in range(40)])
    result = find_candidates(ORIGINAL, [provider], cap=10)
    assert len(result.records) == 10
    assert "kept the first 10" in result.notes[-1]


def test_provider_limit_is_passed_on() -> None:
    provider = FakeProvider("p1", [record(f"TEST-{n:02d}") for n in range(40)])
    find_candidates(ORIGINAL, [provider], limit=7)
    query = provider.queries[0]
    assert isinstance(query, ParametricQuery)
    assert query.limit == 7


def test_original_without_category_cannot_search() -> None:
    bare = ORIGINAL.model_copy(update={"category": None})
    with pytest.raises(ValueError, match="no category"):
        find_candidates(bare, [])
