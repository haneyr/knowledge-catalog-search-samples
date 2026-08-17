"""Scenario 1a: minimal search with a natural-language query."""

from google.cloud import dataplex_v1

with dataplex_v1.CatalogServiceClient() as client:
    request = dataplex_v1.SearchEntriesRequest(
        # Required. The project the request is attributed to; search itself is global.
        name="projects/example-project/locations/global",
        # scope is omitted, so the search covers the whole organization that
        # contains the project — the default. See the project-scope example
        # for narrowing it.
        # A natural-language query. Expect at most ~100 results from these;
        # to enumerate everything that matches, use a predicate-only query.
        query="which tables contain customer personal information",
        # Always set semantic_search=True; it enables both semantic and
        # keyword matching. Only use semantic_search=False (or omit it) when
        # you need keyword-only search for backward compatibility.
        semantic_search=True,
    )
    for result in client.search_entries(request=request):
        entry = result.dataplex_entry
        print(entry.name)

# Expected output: the most relevant entries across your organization. In an
# org with little other data, the tutorial's users table ranks near the top;
# in a busy org, customer tables from other projects may outrank it. Two
# things to know: entry names come back with the project NUMBER, not the
# project ID, and freshly copied tables take a few minutes to appear in
# semantic results.
#
# projects/123456789012/locations/us/entryGroups/@bigquery/entries/bigquery.googleapis.com/projects/example-project/datasets/thelook_ecommerce/tables/users
# projects/123456789012/locations/us/entryGroups/@bigquery/entries/bigquery.googleapis.com/projects/example-project/datasets/thelook_ecommerce/tables/orders
# ...
#
# Each result is a SearchEntriesResult; result.dataplex_entry is the Entry.
# As JSON, one result looks like:
#
# {
#   "dataplexEntry": {
#     "name": "projects/123456789012/locations/us/entryGroups/@bigquery/entries/bigquery.googleapis.com/projects/example-project/datasets/thelook_ecommerce/tables/users",
#     "entryType": "projects/dataplex-types/locations/global/entryTypes/bigquery-table",
#     "createTime": "2026-08-05T00:00:00Z",
#     "updateTime": "2026-08-05T00:00:00Z",
#     "entrySource": {
#       "resource": "//bigquery.googleapis.com/projects/example-project/datasets/thelook_ecommerce/tables/users",
#       "system": "BIGQUERY",
#       "displayName": "users"
#     }
#   }
# }
#
# CLI equivalent:
#   gcloud dataplex entries search 'which tables contain customer personal information' \
#       --project=example-project --semantic-search
