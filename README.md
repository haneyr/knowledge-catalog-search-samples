# Search Knowledge Catalog programmatically

Most of what you do with a catalog starts with a query from code. The scripts in this directory search Knowledge Catalog (formerly Dataplex Universal Catalog) with the Python client library and chain the calls that most metadata workflows reduce to: find entries, fetch their payloads, and hand the result to whatever acts on it — an audit loop, a pipeline, or an agent answering questions in plain language.

Each script is self-contained. Imports and client setup repeat in every file, so you can run one on its own or paste it into a notebook cell without hunting for context defined somewhere above. Every script runs against the same sample dataset, and each ends with a comment block showing the output you should see.

## How it works

Three API methods do the work:

1. `searchEntries` finds catalog entries that match a query. Natural language queries return up to about 100 results; queries built from predicates alone (such as `system=`, `parent:`, and `aspect:`) have no result cap and can be paged through completely.
2. `lookupEntry` retrieves everything the catalog holds on a single entry: every aspect attached to it, entry-level or column-level. `searchEntries` returns the same `Entry` shape, and its schema includes the aspects map, but the request offers no view parameter to ask for payloads and the map comes back empty. A workflow that filters on aspect field values therefore chains search with lookup and filters client side.
3. `lookupContext` serves the model rather than the caller. One call covers up to 10 entries and returns a pre-formatted package of the metadata most relevant to working with them and the resources they connect to, including schemas and possible join paths, in YAML, JSON, or XML trimmed to a character budget you set. Use it to ground an agent; use `lookupEntry` when you need every field on one specific entry.

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

Indexing is not instant. Freshly copied tables take a few minutes to appear in semantic search results, and newly attached aspects take a few minutes to match `aspect:` predicates. A search that returns nothing right after setup usually means wait and retry, not broken.

## Scenario 0: Search the catalog

`scenario0_search_semantic.py` is the minimal complete example: one `search_entries` call with a natural language query, scoped to your project. `scenario0_search_keyword.py` is the same call with a keyword query. Both set `semantic_search=True` because the flag picks the search stack rather than the query style; setting it to `False` routes queries to the legacy stack, kept around for older integrations.

Two variations follow. `scenario0_scope_org.py` drops the project scope and searches everything in the organization you can read — use project scope when you know where the data lives. `scenario0_pagination.py` pages through results; only predicate-only queries page past the first ~100.

Each scenario 0 script ends with its CLI counterpart. The command is `gcloud dataplex entries search`, the `--semantic-search` flag maps to `semantic_search=True`, and `--scope` takes the same values as the API field.

One behavior surprises people parsing results: entry names come back with the project number, not the project ID. The lookup methods accept these names as they are, so pass them through unchanged.

## Scenario 1: Enumerate assets with a predicate-only query

`scenario1_inventory_sweep.py` lists every BigQuery table under `thelook_ecommerce` that carries the `pii` aspect, using only predicates:

```
system=bigquery parent:thelook_ecommerce aspect:PROJECT_ID.global.pii
```

The script prints the first result in full so you can see the exact structure of a `SearchEntriesResult`, then iterates the rest. Use the full `PROJECT_ID.LOCATION.ASPECT_TYPE_ID` path in `aspect:` predicates; short forms like `aspect:pii` are not matched on the current search stack, and the query returns nothing rather than failing.

## Scenario 2: Audit column-level metadata with search and lookup

`scenario2_pii_audit.py` answers a question your security team eventually asks: which tables contain PII, in which columns, and which of those are unmasked? It searches for entries carrying the `pii` aspect, calls `lookup_entry` on each result to retrieve the aspect payloads that search results leave empty, and filters client side. Against the sample data it reports four unmasked columns: `users.email`, `users.first_name`, `users.last_name`, and `users.street_address`.

Field-value matching in `aspect:` predicates (for example, `aspect:PROJECT_ID.global.pii.pii_type=EMAIL`) is not supported on the current search stack and degrades to free-text matching, which returns unrelated entries instead of an error. Filter on aspect field values in your own code after lookup, as this script does.

## Scenario 3: Ground an agent in your catalog

`scenario3_agent/` defines a minimal [Agent Development Kit](https://google.github.io/adk-docs/) agent with two tools: `search_catalog`, which runs a semantic search and returns the top entry names, and `get_context`, which retrieves LLM-ready metadata for those entries with `lookup_context`. Ask it "Which tables and columns do I need to compute revenue by product category?" and it searches, reads the retrieved context, and answers with real names like `products.category` — or tells you what metadata is missing when the context can't support an answer.

Run it from this directory:

```bash
export GOOGLE_GENAI_USE_VERTEXAI=1
export GOOGLE_CLOUD_PROJECT=PROJECT_ID
export GOOGLE_CLOUD_LOCATION=us-central1
adk run scenario3_agent
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
