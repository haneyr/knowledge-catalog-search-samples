"""Scenario 1: enumerate assets with a predicate-only search, then audit them.

PII audit: list every BigQuery table under thelook_ecommerce that carries the
pii aspect, show the structure of a search result, then report which columns
hold unmasked PII. Search finds the entries; lookup_entry retrieves the
aspect payloads, which search results leave empty.

A predicate-only query is built from predicates alone (system=, parent:,
aspect:, and so on) without any free text, so it can return results beyond
the ~100 limit that applies to natural-language and free-text queries.
"""

import json

from google.cloud import dataplex_v1

PROJECT_ID = "example-project"
PII_ASPECT_TYPE = f"projects/{PROJECT_ID}/locations/global/aspectTypes/pii"

with dataplex_v1.CatalogServiceClient() as client:
    # Step 1: find candidate entries with a predicate-only search. The aspect
    # filter is what makes this a catalog search rather than a BigQuery
    # listing. Aspect existence matches column-attached aspects; use the full
    # <project>.<location>.<id> path. Field-value matching
    # (aspect:...pii_type=EMAIL) is not supported on the current stack; it
    # silently degrades to free-text matching. Filter on field values
    # client-side instead (step 3).
    search_request = dataplex_v1.SearchEntriesRequest(
        name=f"projects/{PROJECT_ID}/locations/global",
        scope=f"projects/{PROJECT_ID}",
        query=f"system=bigquery parent:thelook_ecommerce aspect:{PROJECT_ID}.global.pii",
        semantic_search=True,
        page_size=100,
    )
    results = list(client.search_entries(request=search_request))
    print(f"Matched {len(results)} entries\n")

    # Print the first result in full to show the response structure.
    if results:
        first = dataplex_v1.SearchEntriesResult.to_dict(results[0])
        print(json.dumps(first, indent=2, default=str)[:1500])

    # Step 2: look up each entry and read its aspect payloads.
    findings = []
    for result in results:
        entry = client.lookup_entry(
            request=dataplex_v1.LookupEntryRequest(
                name=f"projects/{PROJECT_ID}/locations/us",
                entry=result.dataplex_entry.name,
                # CUSTOM view + aspect_types returns only the aspects we care about.
                view=dataplex_v1.EntryView.CUSTOM,
                aspect_types=[PII_ASPECT_TYPE],
            )
        )
        # Aspect keys look like: example-project.global.pii@Schema.email
        # aspect.path carries the column: Schema.email
        # aspect.data is dict-like; read fields with [] or .get()
        for key, aspect in entry.aspects.items():
            findings.append(
                {
                    "table": entry.entry_source.display_name,
                    "column": aspect.path.removeprefix("Schema."),
                    "pii_type": aspect.data["pii_type"],
                    "masked": aspect.data.get("masked", False),
                }
            )

    # Step 3: filter client-side on the aspect field values.
    unmasked = [f for f in findings if not f["masked"]]
    print(f"\n{len(unmasked)} unmasked PII columns:")
    for f in unmasked:
        print(f"  {f['table']}.{f['column']}  ({f['pii_type']})")

# Note: newly attached aspects take a few minutes to reach the search index.
# If the search matches 0 entries right after running the setup script, wait
# and retry.
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
#     },
#     "aspects": {}
#   }
# }
#
# 4 unmasked PII columns:
#   users.email  (EMAIL)
#   users.first_name  (NAME)
#   users.last_name  (NAME)
#   users.street_address  (ADDRESS)
#
# The aspects map on search results comes back empty, and the request has no
# view parameter to ask for payloads; that is why step 2 calls lookup_entry.
