"""Tests for data/make_test_cards.py (CLAUDE.md Part 5.8)."""

from data.make_test_cards import generate_test_cards

TRUTH_SECTION_LEAK_FIELDS = ["true_blocker", "grams", "expected_outcome"]


def test_generates_at_least_nine_required_cards(tmp_path):
    written = generate_test_cards(str(tmp_path))
    assert len(written) >= 9


def test_cards_cover_required_uc2_personas_and_uc1_cases(tmp_path):
    generate_test_cards(str(tmp_path))
    names = {p.name for p in tmp_path.iterdir()}
    for scenario_id in [
        "scenario-uc2_cooperative_unsure_amount_hindi_switch.md",
        "scenario-uc2_busy.md",
        "scenario-uc2_suspicious.md",
        "scenario-uc2_wrong_person_spouse.md",
        "scenario-uc2_hostile_dnd_abusive.md",
        "scenario-uc2_adversarial_otp_bot_injection.md",
        "scenario-uc1_no_gold.md",
        "scenario-uc1_cooperative_fits_ad.md",
        "scenario-uc1_wants_more_than_gold_supports.md",
    ]:
        assert scenario_id in names


def test_dynamic_variables_and_crm_sections_never_leak_truth(tmp_path):
    written = generate_test_cards(str(tmp_path))
    for path in written:
        text = open(path, encoding="utf-8").read()
        paste_section = text.split("## Customer role-play script")[0]
        for field in TRUTH_SECTION_LEAK_FIELDS:
            assert field not in paste_section, f"{field} leaked into pasteable section of {path}"
