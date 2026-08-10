"""Scenario 0 cookbook: pagination.

Pagination past the first ~100 results only works for predicate-only queries
(only predicates such as system=, parent:, aspect:, and no free text).
Natural-language and free-text queries return at most ~100 results total.
"""

from google.cloud import dataplex_v1

with dataplex_v1.CatalogServiceClient() as client:
    request = dataplex_v1.SearchEntriesRequest(
        name="projects/example-project/locations/global",
        scope="projects/example-project",
        # Predicate-only: no free text, so results are unbounded and pageable.
        query="system=bigquery",
        semantic_search=True,
        page_size=50,  # max 1000
    )
    # The pager fetches subsequent pages transparently as you iterate.
    count = 0
    for result in client.search_entries(request=request):
        count += 1
    print(f"Total BigQuery entries in project: {count}")

# Expected output (with the four tutorial tables plus the dataset entry):
#
# Total BigQuery entries in project: 5
