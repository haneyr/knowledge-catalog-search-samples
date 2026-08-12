"""Scenario 0a: minimal search with a natural-language query."""

from google.cloud import dataplex_v1

with dataplex_v1.CatalogServiceClient() as client:
    request = dataplex_v1.SearchEntriesRequest(
        # Required. The project the request is attributed to; search itself is global.
        name="projects/example-project/locations/global",
        # Limit the search to this project. Omit scope to search the whole
        # organization; see the org-scope example.
        scope="projects/example-project",
        # A natural-language query. Expect at most ~100 results from these;
        # to enumerate everything that matches, use a predicate-only query.
        query="which tables contain customer personal information",
        # semantic_search selects which search stack runs the query. Keep it
        # True for natural-language and keyword queries alike; False routes to
        # the legacy stack and exists only for older integrations.
        semantic_search=True,
        page_size=5,
    )
    for result in client.search_entries(request=request):
        entry = result.dataplex_entry
        print(entry.name)

# Expected output (entry names depend on your project; with the tutorial
# dataset in place, the users table ranks first). Two things to know:
# entry names come back with the project NUMBER, not the project ID, and
# freshly copied tables take a few minutes to appear in semantic results.
#
# projects/example-project/locations/us/entryGroups/@bigquery/entries/bigquery.googleapis.com/projects/example-project/datasets/thelook_ecommerce/tables/users
# projects/example-project/locations/us/entryGroups/@bigquery/entries/bigquery.googleapis.com/projects/example-project/datasets/thelook_ecommerce/tables/orders
# ...
#
# Each result is a SearchEntriesResult; result.dataplex_entry is the Entry.
# As JSON, one result looks like:
#
# {
#   "dataplexEntry": {
#     "name": "projects/example-project/locations/us/entryGroups/@bigquery/entries/bigquery.googleapis.com/projects/example-project/datasets/thelook_ecommerce/tables/users",
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
#       --project=example-project --scope=projects/example-project \
#       --semantic-search --limit=5
