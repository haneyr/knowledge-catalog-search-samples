"""Scenario 0b: the same minimal search with a keyword query.

The query style changes; the flag does not. Keep semantic_search=True for
natural-language and keyword queries alike; it selects the current search
stack. Setting it to False routes the query to the legacy stack and exists
only to keep older integrations working.
"""

from google.cloud import dataplex_v1

with dataplex_v1.CatalogServiceClient() as client:
    request = dataplex_v1.SearchEntriesRequest(
        name="projects/example-project/locations/global",
        scope="projects/example-project",
        # Keyword query: free text plus predicates. name: matches the entry
        # name, system= filters to BigQuery entries.
        query="users system=bigquery",
        semantic_search=True,
        page_size=5,
    )
    for result in client.search_entries(request=request):
        entry = result.dataplex_entry
        print(f"{entry.entry_source.display_name}: {entry.name}")

# Expected output:
#
# users: projects/example-project/locations/us/entryGroups/@bigquery/entries/bigquery.googleapis.com/projects/example-project/datasets/thelook_ecommerce/tables/users
