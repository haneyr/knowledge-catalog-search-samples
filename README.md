# Search Knowledge Catalog programmatically

Most of what you do with a catalog starts with a query from code. The scripts in this directory search Knowledge Catalog (formerly Dataplex Universal Catalog) with the Python client library, then chain search with entry lookup and context retrieval — ending with an agent grounded in the catalog.

Each script is self-contained: imports, client setup, and inline values. Run one alone or paste it into a notebook cell. All scripts use the same sample dataset, and each ends with a comment block showing the output to expect.

## How it works

Three API methods do the work:

1. `searchEntries` finds catalog entries that match a query. Natural language queries return up to about 100 results; queries built from predicates alone (such as `system=`, `parent:`, and `aspect:`) have no result cap and can be paged through completely.
2. `lookupEntry` retrieves a single entry with its aspects, entry-level and column-level; the `view` field on the request selects which aspects, and even the widest view returns at most 100. Search results never carry aspect data: the aspects map on a search result arrives empty, and `SearchEntriesRequest` has no view field to fill it. A search can tell you `users` carries the `pii` aspect; which columns, and whether they're masked, requires `lookupEntry`. Workflows that filter on aspect fields chain the two calls and filter client side.
3. `lookupContext` returns prompt-ready metadata for up to 10 entries and the resources they connect to — schemas, join paths — as YAML, JSON, or XML sized by the `context_budget` option. Use it to ground an agent; use `lookupEntry` to read one entry in full.

One regionality rule spans all three: search is a global service, so its requests name `locations/global`, while entries live in regional data planes — the lookup calls target the asset's storage region (`locations/us` for this tutorial's dataset).

## Before you begin

You need four IAM roles on the project:

- Dataplex Catalog Editor (`roles/dataplex.catalogEditor`) — create the aspect type and attach aspects
- Dataplex Catalog Viewer (`roles/dataplex.catalogViewer`) — search, look up entries, and retrieve context
- BigQuery Data Editor (`roles/bigquery.dataEditor`) and BigQuery Job User (`roles/bigquery.jobUser`) — create the sample dataset
- Vertex AI User (`roles/aiplatform.user`) — run the agent example

Enable the APIs, set up Application Default Credentials, and install the client libraries:

```bash
gcloud services enable bigquery.googleapis.com dataplex.googleapis.com aiplatform.googleapis.com
gcloud auth application-default login
pip install -r requirements.txt
```

## Set up the sample dataset

The examples run against a copy of the theLook eCommerce public dataset. You copy four tables into your own project because Knowledge Catalog indexes what your project owns, and because you can't attach aspects to `bigquery-public-data`. The source lives in the US multi-region, so the target dataset must too.

```bash
bq mk --dataset --location=US PROJECT_ID:thelook_ecommerce

bq cp bigquery-public-data:thelook_ecommerce.users        PROJECT_ID:thelook_ecommerce.users
bq cp bigquery-public-data:thelook_ecommerce.orders       PROJECT_ID:thelook_ecommerce.orders
bq cp bigquery-public-data:thelook_ecommerce.order_items  PROJECT_ID:thelook_ecommerce.order_items
bq cp bigquery-public-data:thelook_ecommerce.products     PROJECT_ID:thelook_ecommerce.products
```

Replace `PROJECT_ID` in the commands above with your project ID. The scripts use `example-project` as their placeholder; replace it the same way before running them.

Then create the `pii` aspect type and attach it to the columns of the `users` table:

```bash
python3 setup_pii_aspect.py
```

The aspect type has two fields: `pii_type`, an enum classifying the kind of PII, and `masked`, a boolean recording whether the column is masked downstream. The setup script tags seven columns of `users`, four of them unmasked, so the audit in scenario 2 returns a subset instead of everything it scanned. The script is safe to re-run.

Indexing is not instant. Freshly copied tables take a few minutes to appear in semantic search results, and newly attached aspects take a few minutes to match `aspect:` predicates. If a search returns nothing right after setup, wait a few minutes and retry.

## Scenario 1: Search the catalog

`scenario1_search_semantic.py` is the minimal complete example: one `search_entries` call with a natural language query. `scenario1_search_keyword.py` is the same call with a keyword query. Both omit `scope`, so they search the whole organization that contains the project — the default. Always set `semantic_search=True`; it enables both semantic and keyword matching. Only use `semantic_search=False` (or omit the flag) when you need keyword-only search for backward compatibility.

Two variations follow. `scenario1_scope_project.py` sets `scope` to narrow the search to one project; project-scoped searches execute faster. `scenario1_pagination.py` pages through results; predicate-only queries can return results beyond the ~100 limit.

Each scenario 1 script ends with its CLI counterpart. The command is `gcloud dataplex entries search`, the `--semantic-search` flag maps to `semantic_search=True`, and `--scope` takes the same values as the API field.

One behavior surprises people parsing results: entry names come back with the project number, not the project ID. The lookup methods accept these names as they are, so pass them through unchanged.

## Scenario 2: Retrieve and audit assets with search and lookup

Which tables contain PII, in which columns, and which are unmasked? `scenario2_pii_audit.py` starts with a predicate-only search for every BigQuery table under `thelook_ecommerce` that carries the `pii` aspect:

```
system=bigquery parent:thelook_ecommerce aspect:PROJECT_ID.global.pii
```

The script prints the first result in full to show the `SearchEntriesResult` structure, then calls `lookup_entry` on each result for the aspect payloads and filters client side. The sample data yields four unmasked columns: `users.email`, `users.first_name`, `users.last_name`, and `users.street_address`.

Two predicate rules apply. Use the full `PROJECT_ID.LOCATION.ASPECT_TYPE_ID` path (short forms like `aspect:pii` return nothing on the current search stack). And don't rely on field-value matching (`aspect:...pii_type=EMAIL`) — it degrades to free-text matching and returns unrelated entries. Filter on field values after lookup, as the script does.

The lookups run sequentially, which is fine for a tutorial dataset. A production scan over hundreds of tables should issue them concurrently — `concurrent.futures.ThreadPoolExecutor` or `CatalogServiceAsyncClient`.

## Scenario 3: Ground an agent in your catalog

`scenario3_agent/` defines a minimal [Agent Development Kit](https://google.github.io/adk-docs/) agent with two tools: `search_catalog`, which runs a semantic search and returns the top entry names, and `get_context`, which retrieves LLM-ready metadata for those entries with `lookup_context`. Ask it "Which tables and columns do I need to compute revenue by product category?" and it answers with real names like `products.category`, or says what metadata is missing.

Run it from this directory:

```bash
export GOOGLE_GENAI_USE_VERTEXAI=1
export GOOGLE_CLOUD_PROJECT=PROJECT_ID
export GOOGLE_CLOUD_LOCATION=us-central1
adk run scenario3_agent
```

`GOOGLE_CLOUD_LOCATION` here is the Vertex AI inference region and is unrelated to the Dataplex metadata region — the agent's `lookup_context` call still targets `locations/us`, where the tutorial dataset lives. Passing resources from different regions in one `lookup_context` call fails with a location mismatch error.

## Run the tests

The suite fakes only the API client; requests and responses use the real proto types, so proto-handling mistakes fail in tests the same way they fail live. No GCP project is needed.

```bash
pip install -r requirements-dev.txt
python -m pytest tests/
```

## Clean up

Delete the resources you created:

```bash
bq rm -r -f PROJECT_ID:thelook_ecommerce
gcloud dataplex aspect-types delete pii --location=global --project=PROJECT_ID
```

## What's next

- [Search syntax for Knowledge Catalog](https://docs.cloud.google.com/dataplex/docs/search-syntax)
- [Retrieve context for data assets](https://docs.cloud.google.com/dataplex/docs/retrieve-data-context)
- [Manage aspects and enrich metadata](https://docs.cloud.google.com/dataplex/docs/enrich-entries-metadata)
- [Build an agent to discover your data](https://docs.cloud.google.com/dataplex/docs/use-discovery-agent)
