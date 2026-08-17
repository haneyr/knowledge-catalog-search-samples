"""Shared fixtures: a fake catalog client over real proto types.

Only CatalogServiceClient is faked. Requests and responses are the real
google.cloud.dataplex_v1 types, so field names, map behavior (aspects,
Aspect.data), and pager iteration match production. A snippet that
mishandles a proto (for example, calling MessageToDict on Aspect.data)
fails here the same way it fails live.
"""

import contextlib
import io
from unittest import mock

import pytest
from google.cloud import dataplex_v1
from google.protobuf import struct_pb2

PROJECT_ID = "example-project"
USERS_ENTRY_NAME = (
    "projects/123456789012/locations/us/entryGroups/@bigquery/entries/"
    f"bigquery.googleapis.com/projects/{PROJECT_ID}/datasets/thelook_ecommerce/tables/users"
)

PII_COLUMNS = {
    "email": ("EMAIL", False),
    "first_name": ("NAME", False),
    "last_name": ("NAME", False),
    "street_address": ("ADDRESS", False),
    "postal_code": ("ADDRESS", True),
    "age": ("DEMOGRAPHIC", True),
    "gender": ("DEMOGRAPHIC", True),
}


def make_table_result(table: str) -> dataplex_v1.SearchEntriesResult:
    return dataplex_v1.SearchEntriesResult(
        dataplex_entry=dataplex_v1.Entry(
            name=USERS_ENTRY_NAME.replace("tables/users", f"tables/{table}"),
            entry_type="projects/dataplex-types/locations/global/entryTypes/bigquery-table",
            entry_source=dataplex_v1.EntrySource(system="BIGQUERY", display_name=table),
        )
    )


def make_users_entry_with_aspects() -> dataplex_v1.Entry:
    aspects = {}
    for column, (pii_type, masked) in PII_COLUMNS.items():
        aspects[f"{PROJECT_ID}.global.pii@Schema.{column}"] = dataplex_v1.Aspect(
            aspect_type=f"projects/{PROJECT_ID}/locations/global/aspectTypes/pii",
            path=f"Schema.{column}",
            data=struct_pb2.Struct(
                fields={
                    "pii_type": struct_pb2.Value(string_value=pii_type),
                    "masked": struct_pb2.Value(bool_value=masked),
                }
            ),
        )
    return dataplex_v1.Entry(
        name=USERS_ENTRY_NAME,
        entry_source=dataplex_v1.EntrySource(system="BIGQUERY", display_name="users"),
        aspects=aspects,
    )


class FakeOperation:
    def __init__(self, result):
        self._result = result

    def result(self, timeout=None):
        return self._result


class FakeCatalogClient:
    """Stands in for CatalogServiceClient; records every request it sees."""

    def __init__(self):
        self.search_results = []
        self.lookup_entry_result = None
        self.context_text = "resource: example\n"
        self.create_raises = None
        self.requests = []

    # The snippets use both `with ... as client:` and bare construction.
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def search_entries(self, request):
        self.requests.append(("search_entries", request))
        return list(self.search_results)

    def lookup_entry(self, request):
        self.requests.append(("lookup_entry", request))
        return self.lookup_entry_result

    def lookup_context(self, request):
        self.requests.append(("lookup_context", request))
        return dataplex_v1.LookupContextResponse(context=self.context_text)

    def create_aspect_type(self, parent, aspect_type, aspect_type_id):
        self.requests.append(("create_aspect_type", (parent, aspect_type, aspect_type_id)))
        if self.create_raises:
            raise self.create_raises
        return FakeOperation(
            dataplex_v1.AspectType(name=f"{parent}/aspectTypes/{aspect_type_id}")
        )

    def get_aspect_type(self, name):
        self.requests.append(("get_aspect_type", name))
        return dataplex_v1.AspectType(name=name)

    def update_entry(self, entry, update_mask):
        self.requests.append(("update_entry", (entry, update_mask)))
        return entry


@pytest.fixture
def fake_client():
    return FakeCatalogClient()


@pytest.fixture
def run_snippet(fake_client):
    """Exec a snippet file with the fake client patched in; return stdout."""

    def _run(path):
        with mock.patch.object(
            dataplex_v1, "CatalogServiceClient", lambda: fake_client
        ):
            source = open(path).read()
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                exec(compile(source, path, "exec"), {"__name__": "snippet"})
            return out.getvalue()

    return _run
