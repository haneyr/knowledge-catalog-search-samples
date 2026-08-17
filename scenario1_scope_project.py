"""Scenario 1 cookbook: project-scoped search.

The previous examples omit scope and search the whole organization, the
default. Setting scope narrows the search to one project; project-scoped
searches execute faster. Note: order_by is not supported on the current
search stack.
"""

from google.cloud import dataplex_v1

with dataplex_v1.CatalogServiceClient() as client:
    request = dataplex_v1.SearchEntriesRequest(
        name="projects/example-project/locations/global",
        # Narrow the search to this project.
        scope="projects/example-project",
        query="thelook",
        semantic_search=True,
    )
    for result in client.search_entries(request=request):
        print(result.dataplex_entry.name)

# An alternative that keeps the org-wide scope: narrow within the query
# using the projectid: predicate, e.g. "thelook projectid:example-project".

# Expected output: only entries from this project — the thelook_ecommerce
# dataset entry and its four tables.

# CLI equivalent:
#   gcloud dataplex entries search 'thelook' --project=example-project \
#       --scope=projects/example-project --semantic-search
