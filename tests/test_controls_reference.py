"""Tests for the shared controls reference."""

from eagle1.ui.controls_reference import CATEGORY_ORDER, CONTROL_BINDINGS, bindings_by_category


def test_every_binding_category_is_known():
    assert all(b.category in CATEGORY_ORDER for b in CONTROL_BINDINGS)


def test_no_duplicate_key_labels():
    keys = [b.keys for b in CONTROL_BINDINGS]
    assert len(keys) == len(set(keys))


def test_bindings_by_category():
    assert len(bindings_by_category("FLIGHT")) == 3
    assert bindings_by_category("UNKNOWN") == []


def test_no_binding_mentions_nonexistent_1_8_slots():
    assert all("1-8" not in b.action and "1 – 8" not in b.keys for b in CONTROL_BINDINGS)
