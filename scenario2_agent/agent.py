"""Scenario 2: search, lookup_context, forward to an agent.

A minimal ADK agent grounded in Knowledge Catalog. The agent turns a
natural-language question into a catalog search, retrieves LLM-ready context
for the top results, and answers citing actual tables and columns.

Run with `adk run scenario2_agent` or `adk web` from the parent directory.
"""

from google.adk.agents import Agent
from google.cloud import dataplex_v1

PROJECT_ID = "example-project"

# One client for both tools. Creating a client per call tears down the gRPC
# channel and adds connection overhead to every agent turn.
catalog_client = dataplex_v1.CatalogServiceClient()


def search_catalog(question: str) -> list[str]:
    """Search Knowledge Catalog and return the names of the top 5 entries.

    Args:
        question: A natural-language description of the data you need.
    """
    request = dataplex_v1.SearchEntriesRequest(
        name=f"projects/{PROJECT_ID}/locations/global",
        scope=f"projects/{PROJECT_ID}",
        query=question,
        # Keep semantic_search=True; False routes to the legacy stack.
        semantic_search=True,
        page_size=5,
    )
    return [r.dataplex_entry.name for r in catalog_client.search_entries(request=request)]


def get_context(entry_names: list[str]) -> str:
    """Retrieve LLM-ready context for up to 10 catalog entries.

    Args:
        entry_names: Entry resource names returned by search_catalog.
    """
    # lookup_context rejects an empty resources list, so return early when
    # the search found nothing instead of crashing the agent turn.
    if not entry_names:
        return "No matching catalog entries found."
    response = catalog_client.lookup_context(
        request=dataplex_v1.LookupContextRequest(
            name=f"projects/{PROJECT_ID}/locations/us",
            # Passing several tables at once also returns possible join
            # paths between them. Maximum of 10 resources per request.
            resources=entry_names[:10],
            options={"format": "yaml", "context_budget": "8000"},
        )
    )
    return response.context


root_agent = Agent(
    name="catalog_assistant",
    model="gemini-2.5-flash",
    instruction=(
        "You answer questions about the data available in this project. "
        "Always call search_catalog first to find relevant entries, then "
        "get_context on the results before answering. Cite the exact table "
        "and column names from the retrieved context. If the context does "
        "not answer the question, say what metadata is missing."
    ),
    tools=[search_catalog, get_context],
)

# Example session:
#
# user: Which tables and columns do I need to compute revenue by product category?
#
# agent: (calls search_catalog("tables for revenue by product category"))
#        (calls get_context([...top 5 entry names...]))
#
# You need two tables from thelook_ecommerce:
#   - order_items: sale_price (revenue per unit sold), product_id, status
#   - products: id, category
# Join order_items.product_id to products.id, filter status = 'Complete',
# and sum sale_price grouped by products.category.
#
# The context payload returned by get_context is a YAML block per resource:
#
# resource: ".../datasets/thelook_ecommerce/tables/order_items"
# technical_metadata:
#   schema:
#     - name: product_id
#       type: INTEGER
#     - name: sale_price
#       type: FLOAT
# operational_metadata:
#   frequent_joins:
#     - table: products
#       on: product_id
