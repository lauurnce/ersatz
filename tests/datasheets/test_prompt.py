from ersatz.datasheets.pages import PageText
from ersatz.datasheets.prompt import FEATURE_HELP, PARAM_HELP, SYSTEM, build_user_message
from ersatz.datasheets.schema import Feature
from ersatz.model import Category, ParamName

PAGES = [PageText(page=n, text=f"text of page {n}", chars=500) for n in range(1, 6)]


def test_every_parameter_and_feature_has_help() -> None:
    assert set(PARAM_HELP) == set(ParamName)
    assert set(FEATURE_HELP) == {f.value for f in Feature}


def test_message_holds_only_selected_pages_in_order() -> None:
    message = build_user_message(PAGES, [1, 4], Category.LDO, None)
    assert message.index("=== PAGE 1 ===") < message.index("=== PAGE 4 ===")
    assert "text of page 4" in message
    assert "text of page 2" not in message
    assert "Target device" not in message


def test_message_names_the_category_parameters() -> None:
    message = build_user_message(PAGES, [1], Category.OPAMP, "TEST-OPA1")
    assert "- slew_rate:" in message
    assert "- dropout:" not in message
    assert "Target device: TEST-OPA1." in message


def test_system_prompt_states_the_citation_rule() -> None:
    assert "=== PAGE n ===" in SYSTEM
    assert "character for character" in SYSTEM
