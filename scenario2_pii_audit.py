"""Scenario 2: search, then iterate with lookup_entry.

PII audit: find every table that has PII, say which columns, and flag which
are unmasked. Search finds the entries; lookup_entry retrieves the aspect
payloads, which search results don't carry.
"""

from google.cloud import dataplex_v1

PROJECT_ID = "example-project"
PII_ASPECT_TYPE = f"projects/{PROJECT_ID}/locations/global/aspectTypes/pii"

with dataplex_v1.CatalogServiceClient() as client:
    # Step 1: find candidate entries by aspect existence. This matches
    # column-attached aspects; use the full <project>.<location>.<id> path.
    # Field-value matching (aspect:...pii_type=EMAIL) is not supported on the
    # current stack; it silently degrades to free-text matching. Filter on
    # field values client-side instead (step 3).
    search_request = dataplex_v1.SearchEntriesRequest(
        name=f"projects/{PROJECT_ID}/locations/global",
        scope=f"projects/{PROJECT_ID}",
        query=f"aspect:{PROJECT_ID}.global.pii",
        semantic_search=True,
        page_size=100,
    )
    candidates = [r.dataplex_entry.name for r in client.search_entries(request=search_request)]
    print(f"Candidate entries: {len(candidates)}\n")

    # Step 2: look up each entry and read its aspect payloads.
    findings = []
    for entry_name in candidates:
        entry = client.lookup_entry(
            request=dataplex_v1.LookupEntryRequest(
                name=f"projects/{PROJECT_ID}/locations/us",
                entry=entry_name,
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

    # Step 3: post-filter client-side. Field-value matching in search does not
    # apply to column-attached aspects, so filtering happens here.
    unmasked = [f for f in findings if not f["masked"]]
    print(f"{len(unmasked)} unmasked PII columns:")
    for f in unmasked:
        print(f"  {f['table']}.{f['column']}  ({f['pii_type']})")

# Expected output:
#
# Candidate entries: 1
#
# 4 unmasked PII columns:
#   users.email  (EMAIL)
#   users.first_name  (NAME)
#   users.last_name  (NAME)
#   users.street_address  (ADDRESS)
#
# One aspect entry as JSON, for reference:
#
# "example-project.global.pii@Schema.email": {
#   "aspectType": "projects/example-project/locations/global/aspectTypes/pii",
#   "path": "Schema.email",
#   "data": { "pii_type": "EMAIL", "masked": false }
# }
