"""Tests for the agent's tools — including the empty-results guard.

The get_context([]) crash shipped once; this file is why it won't again.
"""

import importlib.util
import pathlib
import sys
import types
from unittest import mock

import pytest
from google.cloud import dataplex_v1

import conftest

SNIPPETS = pathlib.Path(__file__).parent.parent


@pytest.fixture
def agent_module(fake_client):
    # Stub google.adk if it isn't installed; the tools don't need it.
    if "google.adk.agents" not in sys.modules:
        try:
            import google.adk.agents  # noqa: F401
        except ImportError:
            adk = types.ModuleType("google.adk")
            agents = types.ModuleType("google.adk.agents")

            class Agent:
                def __init__(self, **kwargs):
                    self.__dict__.update(kwargs)

            agents.Agent = Agent
            adk.agents = agents
            sys.modules["google.adk"] = adk
            sys.modules["google.adk.agents"] = agents

    # The module builds its client at import time, so patch first.
    with mock.patch.object(dataplex_v1, "CatalogServiceClient", lambda: fake_client):
        spec = importlib.util.spec_from_file_location(
            "agent_under_test", SNIPPETS / "scenario3_agent" / "agent.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


def test_get_context_empty_returns_message_without_api_call(agent_module, fake_client):
    result = agent_module.get_context([])
    assert result == "No matching catalog entries found."
    assert not [r for k, r in fake_client.requests if k == "lookup_context"]


def test_get_context_caps_resources_at_ten(agent_module, fake_client):
    names = [f"projects/p/locations/us/entryGroups/g/entries/e{i}" for i in range(12)]
    agent_module.get_context(names)
    _, request = [r for r in fake_client.requests if r[0] == "lookup_context"][0]
    assert len(request.resources) == 10
    assert dict(request.options)["format"] == "yaml"


def test_search_catalog_returns_entry_names(agent_module, fake_client):
    fake_client.search_results = [
        conftest.make_table_result(t) for t in ("products", "order_items")
    ]
    names = agent_module.search_catalog("revenue by product category")
    assert len(names) == 2
    assert all(n.startswith("projects/") for n in names)
    _, request = fake_client.requests[-1]
    assert request.semantic_search is True
    assert request.page_size == 5


def test_root_agent_exposes_both_tools(agent_module):
    tool_names = {t.__name__ for t in agent_module.root_agent.tools}
    assert tool_names == {"search_catalog", "get_context"}
