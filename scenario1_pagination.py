"""Scenario 1 cookbook: pagination.

Predicate-only queries can return results beyond the ~100 limit that applies
to natural-language and free-text queries. A query is predicate-only when it
is built from predicates alone (system=, parent:, aspect:) with no free text.
"""

from google.cloud import dataplex_v1

with dataplex_v1.CatalogServiceClient() as client:
    request = dataplex_v1.SearchEntriesRequest(
        name="projects/example-project/locations/global",
        scope="projects/example-project",
        # A predicate-only query: every BigQuery table in the project.
        query="system=bigquery type=table",
        semantic_search=True,
        page_size=50,  # max 1000
    )
    # The pager fetches subsequent pages transparently as you iterate.
    count = 0
    for result in client.search_entries(request=request):
        count += 1
    print(f"Total BigQuery tables in project: {count}")

# Expected output (the four tutorial tables):
#
# Total BigQuery tables in project: 4
#
# CLI equivalent (gcloud handles page tokens automatically; use --limit to
# bound total results):
#   gcloud dataplex entries search 'system=bigquery type=table' \
#       --project=example-project --scope=projects/example-project \
#       --semantic-search --page-size=50
