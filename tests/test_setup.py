"""Tests for the setup script: aspect type creation and attachment."""

import importlib.util
import pathlib
from unittest import mock

from google.api_core import exceptions
from google.cloud import dataplex_v1

import conftest

SNIPPETS = pathlib.Path(__file__).parent.parent


def load_setup():
    spec = importlib.util.spec_from_file_location(
        "setup_pii_aspect", SNIPPETS / "setup_pii_aspect.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_create_aspect_type_shape(fake_client):
    setup = load_setup()
    with mock.patch.object(dataplex_v1, "CatalogServiceClient", lambda: fake_client):
        created = setup.create_pii_aspect_type()
    assert created.name.endswith("/aspectTypes/pii")
    _, (parent, aspect_type, aspect_type_id) = fake_client.requests[0]
    assert parent == "projects/example-project/locations/global"
    assert aspect_type_id == "pii"
    fields = {f.name: f for f in aspect_type.metadata_template.record_fields}
    assert set(fields) == {"pii_type", "masked"}
    assert fields["pii_type"].type_ == "enum"
    assert fields["pii_type"].constraints.required is True
    assert [v.name for v in fields["pii_type"].enum_values] == [
        "EMAIL", "NAME", "ADDRESS", "PHONE_NUMBER", "DEMOGRAPHIC", "OTHER",
    ]
    assert fields["masked"].type_ == "bool"


def test_create_is_idempotent(fake_client):
    setup = load_setup()
    fake_client.create_raises = exceptions.AlreadyExists("exists")
    with mock.patch.object(dataplex_v1, "CatalogServiceClient", lambda: fake_client):
        created = setup.create_pii_aspect_type()
    assert created.name.endswith("/aspectTypes/pii")
    assert fake_client.requests[-1][0] == "get_aspect_type"


def test_attach_writes_seven_column_aspects(fake_client):
    setup = load_setup()
    with mock.patch.object(dataplex_v1, "CatalogServiceClient", lambda: fake_client):
        entry = setup.attach_pii_aspects()
    assert len(entry.aspects) == 7
    for column, (pii_type, masked) in conftest.PII_COLUMNS.items():
        key = f"example-project.global.pii@Schema.{column}"
        assert key in entry.aspects
        aspect = entry.aspects[key]
        assert aspect.data["pii_type"] == pii_type
        assert aspect.data["masked"] is masked
    _, (sent_entry, update_mask) = fake_client.requests[0]
    assert update_mask == {"paths": ["aspects"]}
    assert "tables/users" in sent_entry.name
