"""Static checks: the conventions every snippet promises to keep."""

import pathlib
import re

SNIPPETS = pathlib.Path(__file__).parent.parent
SCENARIO_FILES = sorted(SNIPPETS.glob("scenario*_*.py")) + [
    SNIPPETS / "scenario3_agent" / "agent.py"
]


def test_every_search_request_sets_semantic_search_true():
    for path in SCENARIO_FILES:
        source = path.read_text()
        if "SearchEntriesRequest(" in source:
            assert "semantic_search=True" in source, path.name


def test_every_snippet_documents_expected_output():
    for path in SCENARIO_FILES:
        source = path.read_text()
        assert "# Expected output" in source or "# Example session" in source, path.name


def test_scenario1_snippets_carry_cli_equivalents():
    for path in SNIPPETS.glob("scenario1_*.py"):
        assert "# CLI equivalent" in path.read_text(), path.name


def test_placeholders_are_consistent():
    for path in SCENARIO_FILES + [SNIPPETS / "setup_pii_aspect.py"]:
        source = path.read_text()
        # Runnable code must use the replaceable placeholder, never a
        # literal-looking project number.
        for line in source.splitlines():
            if line.strip().startswith("#"):
                continue
            assert "123456789012" not in line, f"{path.name}: {line.strip()}"


def test_no_stale_scenario_numbering():
    pattern = re.compile(r"scenario0|scope_org|scenario1_pii_audit|scenario2_agent")
    for path in SCENARIO_FILES + [SNIPPETS / "README.md"]:
        assert not pattern.search(path.read_text()), path.name
