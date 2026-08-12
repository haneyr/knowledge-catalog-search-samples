"""Scenario 0 cookbook: pagination.

Only predicate-only queries page past the first ~100 results. A query
qualifies when it is built from predicates alone (system=, parent:, aspect:)
without any free text; natural-language and free-text queries top out around
100 results total.
"""

from google.cloud import dataplex_v1

with dataplex_v1.CatalogServiceClient() as client:
    request = dataplex_v1.SearchEntriesRequest(
        name="projects/example-project/locations/global",
        scope="projects/example-project",
        # Predicates only, no free text: no result cap, fully pageable.
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
#
# CLI equivalent (gcloud handles page tokens itself; --page-size caps 500):
#   gcloud dataplex entries search 'system=bigquery' \
#       --project=example-project --scope=projects/example-project \
#       --semantic-search --page-size=50
