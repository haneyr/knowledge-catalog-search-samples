"""Scenario 1: predicate-only search, then parse the outputs.

Lists every BigQuery table under thelook_ecommerce that carries the pii
aspect. The aspect filter is what makes this a catalog search rather than a
dressed-up `bq ls`.

A predicate-only query is built from predicates alone (system=, parent:,
aspect:, and so on) without any free text. These queries have no result cap,
so you can enumerate every match; natural-language queries top out around
100 results.
"""

import json

from google.cloud import dataplex_v1

with dataplex_v1.CatalogServiceClient() as client:
    request = dataplex_v1.SearchEntriesRequest(
        name="projects/example-project/locations/global",
        scope="projects/example-project",
        # Predicates only: entry system, parent dataset, and aspect existence.
        # aspect: matches against <project>.<location>.<aspect_type_id>.
        query="system=bigquery parent:thelook_ecommerce aspect:example-project.global.pii",
        semantic_search=True,
        page_size=100,
    )

    results = list(client.search_entries(request=request))
    print(f"Matched {len(results)} entries\n")

    # Print the first result in full to show the response structure,
    # then names only for the rest.
    if results:
        first = dataplex_v1.SearchEntriesResult.to_dict(results[0])
        print(json.dumps(first, indent=2, default=str)[:1500])
    for result in results[1:]:
        print(result.dataplex_entry.name)

# Note: newly attached aspects take a few minutes to reach the search index.
# If this returns 0 entries right after running the setup script, wait and
# retry. The aspect: predicate needs the full <project>.<location>.<id> path
# on the current stack; the short form (aspect:pii) is not matched.
#
# Expected output: only the users table matches, because that is the only
# entry the setup script attached the pii aspect to.
#
# Matched 1 entries
#
# {
#   "dataplex_entry": {
#     "name": "projects/example-project/locations/us/entryGroups/@bigquery/entries/bigquery.googleapis.com/projects/example-project/datasets/thelook_ecommerce/tables/users",
#     "entry_type": "projects/dataplex-types/locations/global/entryTypes/bigquery-table",
#     "entry_source": {
#       "resource": "//bigquery.googleapis.com/projects/example-project/datasets/thelook_ecommerce/tables/users",
#       "system": "BIGQUERY",
#       "display_name": "users"
#     }
#   }
# }
#
# Note: search results do NOT include the column-level aspect payloads.
# Scenario 2 shows how to retrieve them with lookup_entry.
