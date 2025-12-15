from scripts.selection import deduplicate_entries, normalize_code_name, stable_pick


def test_stable_pick_deterministic():
    entries = [{"entry_id": "a"}, {"entry_id": "b"}, {"entry_id": "c"}]
    first = stable_pick(entries, seed=0)
    second = stable_pick(entries[::-1], seed=0)
    assert first == second

    changed = stable_pick(entries, seed=1)
    assert changed != first


def test_normalize_code_name_safe():
    assert normalize_code_name("VASP/6.3") == "VASP_6.3"
    assert normalize_code_name(" Quantum Espresso ") == "Quantum_Espresso"
    assert normalize_code_name("") == "unknown"


def test_deduplicate_entries_preserves_order():
    entries = [
        {"entry_id": "x", "code": "A"},
        {"entry_id": "x", "code": "B"},
        {"entry_id": "y", "code": "C"},
    ]
    unique = deduplicate_entries(entries)
    assert unique == [
        {"entry_id": "x", "code": "A"},
        {"entry_id": "y", "code": "C"},
    ]

