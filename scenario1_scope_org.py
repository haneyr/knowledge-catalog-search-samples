"""Scenario 1 cookbook: organization-wide (open-ended) search.

Omitting scope, or setting it to an organization, searches everything the
caller can see. Note: order_by is not supported on the current search stack.
"""

from google.cloud import dataplex_v1

with dataplex_v1.CatalogServiceClient() as client:
    request = dataplex_v1.SearchEntriesRequest(
        name="projects/example-project/locations/global",
        # Search across the whole organization instead of one project.
        # Replace ORG_ID with your organization's ID (gcloud organizations list).
        # If scope is omitted, it defaults to the organization that contains
        # the project named above.
        scope="organizations/ORG_ID",
        query="thelook",
        semantic_search=True,
    )
    for result in client.search_entries(request=request):
        print(result.dataplex_entry.name)

# Expected output: entries from every project in the organization that the
# caller can read, including copies of thelook_ecommerce in other projects.
#
# CLI equivalent:
#   gcloud dataplex entries search 'thelook' --project=example-project \
#       --scope=organizations/ORG_ID --semantic-search
