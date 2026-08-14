"""Scenario 1b: the same minimal search with a keyword query.

Always set semantic_search=True; it enables both semantic and keyword
matching. Only use semantic_search=False (or omit it) when you need
keyword-only search for backward compatibility.
"""

from google.cloud import dataplex_v1

with dataplex_v1.CatalogServiceClient() as client:
    request = dataplex_v1.SearchEntriesRequest(
        name="projects/example-project/locations/global",
        scope="projects/example-project",
        # Keyword query: free text ("users") matches display names and
        # descriptions; the predicate (system=bigquery) filters to BigQuery.
        query="users system=bigquery",
        semantic_search=True,
    )
    for result in client.search_entries(request=request):
        entry = result.dataplex_entry
        print(f"{entry.entry_source.display_name}: {entry.name}")

# Expected output:
#
# users: projects/123456789012/locations/us/entryGroups/@bigquery/entries/bigquery.googleapis.com/projects/example-project/datasets/thelook_ecommerce/tables/users
#
# CLI equivalent:
#   gcloud dataplex entries search 'users system=bigquery' \
#       --project=example-project --scope=projects/example-project --semantic-search
