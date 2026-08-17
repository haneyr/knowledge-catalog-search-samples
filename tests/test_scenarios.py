"""Run every scenario snippet end to end against the fake client."""

import pathlib

import conftest

SNIPPETS = pathlib.Path(__file__).parent.parent


def test_search_semantic_prints_names_and_searches_org_wide(run_snippet, fake_client):
    fake_client.search_results = [conftest.make_table_result("users")]
    out = run_snippet(SNIPPETS / "scenario1_search_semantic.py")
    assert "tables/users" in out
    kind, request = fake_client.requests[0]
    assert kind == "search_entries"
    assert request.semantic_search is True
    assert request.scope == ""  # org-wide by default: scope omitted


def test_search_keyword_prints_display_name(run_snippet, fake_client):
    fake_client.search_results = [conftest.make_table_result("users")]
    out = run_snippet(SNIPPETS / "scenario1_search_keyword.py")
    assert out.startswith("users: ")
    _, request = fake_client.requests[0]
    assert request.semantic_search is True
    assert request.scope == ""


def test_scope_project_sets_scope(run_snippet, fake_client):
    fake_client.search_results = [conftest.make_table_result(t) for t in ("users", "orders")]
    out = run_snippet(SNIPPETS / "scenario1_scope_project.py")
    assert out.count("\n") == 2
    _, request = fake_client.requests[0]
    assert request.scope == "projects/example-project"
    assert request.semantic_search is True


def test_pagination_counts_all_results(run_snippet, fake_client):
    fake_client.search_results = [
        conftest.make_table_result(f"t{i}") for i in range(4)
    ]
    out = run_snippet(SNIPPETS / "scenario1_pagination.py")
    assert "Total BigQuery tables in project: 4" in out
    _, request = fake_client.requests[0]
    assert request.query == "system=bigquery type=table"
    assert request.semantic_search is True


def test_pii_audit_reports_unmasked_columns(run_snippet, fake_client):
    fake_client.search_results = [conftest.make_table_result("users")]
    fake_client.lookup_entry_result = conftest.make_users_entry_with_aspects()
    out = run_snippet(SNIPPETS / "scenario2_pii_audit.py")
    assert "Matched 1 entries" in out
    assert "4 unmasked PII columns:" in out
    for column, kind in (
        ("email", "EMAIL"),
        ("first_name", "NAME"),
        ("last_name", "NAME"),
        ("street_address", "ADDRESS"),
    ):
        assert f"users.{column}  ({kind})" in out
    # Masked columns must not be reported.
    assert "postal_code" not in out.split("unmasked PII columns:")[1]
    # One lookup per search result, with the CUSTOM view filter.
    lookups = [r for k, r in fake_client.requests if k == "lookup_entry"]
    assert len(lookups) == 1
    assert list(lookups[0].aspect_types) == [
        "projects/example-project/locations/global/aspectTypes/pii"
    ]


def test_pii_audit_handles_zero_matches(run_snippet, fake_client):
    fake_client.search_results = []
    out = run_snippet(SNIPPETS / "scenario2_pii_audit.py")
    assert "Matched 0 entries" in out
    assert "0 unmasked PII columns:" in out
