"""Headless smoke tests: every page renders and the key interactions work.

Uses Streamlit's AppTest, so no browser is needed. Run with:  pytest -q
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "streamlit_app.py")
PAGES = ["home", "concepts", "prevention", "avoidance", "detection", "ignorance", "games",
         "test_lab", "ai_usage", "resources"]


def open_page(name: str) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    at.switch_page(f"app_pages/{name}.py").run()
    return at


def button(at: AppTest, label: str):
    return next(b for b in at.button if b.label == label)


@pytest.mark.parametrize("name", PAGES)
def test_page_renders(name):
    at = open_page(name)
    assert not at.exception, [e.value for e in at.exception]


def test_avoidance_stepper_walks_reset_and_ends():
    at = open_page("avoidance")
    assert at.session_state.bk_step == 0
    button(at, "Next step").click().run()
    button(at, "Next step").click().run()
    assert at.session_state.bk_step == 2
    assert any("P1 can finish" in s.value for s in at.success)       # step 2 = P1 finishes
    button(at, "Previous").click().run()
    assert at.session_state.bk_step == 1
    button(at, "Run to end").click().run()
    assert at.session_state.bk_step == 7
    assert any("Every Finish entry is true" in s.value for s in at.success)
    button(at, "Reset").click().run()
    assert at.session_state.bk_step == 0 and not at.exception


def test_avoidance_request_outcomes_unchanged():
    at = open_page("avoidance")
    for label, expected in (("Scenario B: P2 asks for (4, 0, 0)", "must wait"),
                            ("Scenario C: P4 asks for (3, 3, 0)", "is denied"),
                            ("P1 asks for (1, 0, 2)", "is granted")):
        button(at, label).click().run()
        texts = [x.value for x in (*at.info, *at.warning, *at.success)]
        assert any(expected in t for t in texts), (label, texts)
    assert at.session_state.bk_step == 0                                # grant changed state → stepper reset


def test_detection_tables_and_scenarios():
    at = open_page("detection")
    assert len(at.dataframe) >= 2 and not at.exception
    for key in ("single_deadlock", "multi_cycle_no_deadlock"):
        at.segmented_control(key="det_choice").set_value(key).run()
        assert not at.exception
    at.segmented_control(key="det_view").set_value("Wait-for graph").run()
    assert not at.exception


def test_games_scoring_and_replay():
    at = open_page("games")
    at.radio(key="game_coffman_0_c1").set_value("Starvation").run()
    at.radio(key="game_coffman_0_c2").set_value("Mutual exclusion").run()
    assert any("Correct" in s.value for s in at.success)
    assert any("Not quite" in e.value for e in at.error)
    assert at.metric[0].value == "1 / 18"
    button(at, "Replay this round").click().run()
    assert at.session_state.game_attempt["coffman"] == 1
    assert at.metric[0].value == "0 / 18"


def test_ignorance_feedback():
    at = open_page("ignorance")
    at.pills(key="ign_pacemaker").set_value("Ignorance").run()
    assert any("Not a good fit" in e.value for e in at.error)
    at.pills(key="ign_database").set_value("Detection & recovery").run()
    assert any("Best choice" in s.value for s in at.success)
