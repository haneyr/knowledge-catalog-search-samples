# Search Knowledge Catalog programmatically

This tutorial shows you how to search Knowledge Catalog (formerly Dataplex Universal Catalog) with the Python client library, and how to chain search with entry lookup and context retrieval to build data discovery workflows, including an AI agent grounded in your catalog.

Each script in this directory is self-contained: it includes its own imports and client initialization, uses inline resource names, and can be run on its own or pasted into a notebook cell. The scripts build on each other in order, and all of them run against the same sample dataset so results are reproducible.

## Use cases

- **Find data assets by meaning, not just name:** search the catalog with natural language queries.
- **Enumerate assets with predicate queries:** run unbounded, SQL-like sweeps over the catalog, such as listing every table in a dataset that carries a given aspect.
- **Audit metadata at the column level:** find every column tagged as containing personally identifiable information (PII) and check its masking status.
- **Ground an AI agent in your data estate:** answer natural language questions about your data with responses that cite real tables and columns.

## How it works

The scripts demonstrate three Knowledge Catalog API methods and the patterns for chaining them:

1. `searchEntries` finds catalog entries that match a query. Natural language queries return up to about 100 results; queries built only from predicates (such as `system=`, `parent:`, and `aspect:`) are unbounded and can be paged through completely.
2. `lookupEntry` retrieves a single entry with its full aspect payloads. Search results don't include column-level aspects, so workflows that filter on aspect field values chain search with lookup and filter client side.
3. `lookupContext` returns a pre-formatted, LLM-ready bundle of metadata for up to 10 entries at a time, including schemas and possible join paths. This is the method to use when passing catalog context to a model or an agent.

## Before you begin

### Required roles

To run these scripts, ask your administrator to grant you the following IAM roles on your project:

- Dataplex Catalog Editor (`roles/dataplex.catalogEditor`) — create the aspect type and attach aspects
- Dataplex Catalog Viewer (`roles/dataplex.catalogViewer`) — search, look up entries, and retrieve context
- BigQuery Data Editor (`roles/bigquery.dataEditor`) and BigQuery Job User (`roles/bigquery.jobUser`) — create the sample dataset
- Vertex AI User (`roles/aiplatform.user`) — run the agent example

### Enable the APIs

```bash
gcloud services enable bigquery.googleapis.com dataplex.googleapis.com aiplatform.googleapis.com
```

### Set up authentication and dependencies

```bash
gcloud auth application-default login
pip install -r requirements.txt
```

## Set up the sample dataset

The examples run against a copy of the theLook eCommerce public dataset. Copy four tables into your own project so that Knowledge Catalog indexes them and you can attach metadata to them. The source dataset lives in the US multi-region, so the target dataset must too.

```bash
bq mk --dataset --location=US PROJECT_ID:thelook_ecommerce

bq cp bigquery-public-data:thelook_ecommerce.users        PROJECT_ID:thelook_ecommerce.users
bq cp bigquery-public-data:thelook_ecommerce.orders       PROJECT_ID:thelook_ecommerce.orders
bq cp bigquery-public-data:thelook_ecommerce.order_items  PROJECT_ID:thelook_ecommerce.order_items
bq cp bigquery-public-data:thelook_ecommerce.products     PROJECT_ID:thelook_ecommerce.products
```

Replace `PROJECT_ID` in the commands above with your project ID. The scripts use `example-project` as their placeholder; replace it with your project ID before running them.

Then create the `pii` aspect type and attach it to the columns of the `users` table:

```bash
python3 setup_pii_aspect.py
```

The aspect type has two fields: `pii_type`, an enum classifying the kind of PII, and `masked`, a boolean recording whether the column is masked downstream. The setup script attaches it to seven columns of `users` with a mix of masked and unmasked values, which gives the audit example in scenario 2 a meaningful result. The script is safe to re-run.

**Note:** BigQuery metadata is ingested into Knowledge Catalog automatically, but indexing is not instant. Freshly copied tables take a few minutes to appear in semantic search results, and newly attached aspects take a few minutes to match `aspect:` predicates. If a search returns nothing right after setup, wait and retry.

## Scenario 0: Search the catalog

`scenario0_search_semantic.py` is the minimal complete example: one `search_entries` call with a natural language query, scoped to your project. `scenario0_search_keyword.py` is the same call with a keyword query. Both set `semantic_search=True`: the flag selects the current search stack for both query styles, and `semantic_search=False` exists for backward compatibility only.

Two variations round out the basics:

- `scenario0_scope_org.py` searches organization-wide instead of within one project. Use project scope when you know where the data lives.
- `scenario0_pagination.py` pages through results. Pagination past the first ~100 results works only for predicate-only queries.

**Note:** search results return entry names containing the project number rather than the project ID. The lookup methods accept these names as they are.

## Scenario 1: Enumerate assets with a predicate-only query

`scenario1_inventory_sweep.py` lists every BigQuery table under `thelook_ecommerce` that carries the `pii` aspect, using only predicates:

```
system=bigquery parent:thelook_ecommerce aspect:PROJECT_ID.global.pii
```

The script prints the first result in full so you can see the exact structure of a `SearchEntriesResult`, then iterates the rest. Use the full `PROJECT_ID.LOCATION.ASPECT_TYPE_ID` path in `aspect:` predicates; short forms are not matched on the current search stack.

## Scenario 2: Audit column-level metadata with search and lookup

`scenario2_pii_audit.py` answers the question "which tables contain PII, in which columns, and which of those are unmasked?" It searches for entries carrying the `pii` aspect, calls `lookup_entry` on each result to retrieve the column-level aspect payloads that search results don't expose, and filters client side on the aspect's field values.

Field-value matching in `aspect:` predicates (for example, `aspect:PROJECT_ID.global.pii.pii_type=EMAIL`) is not supported on the current search stack and degrades to free-text matching. Filter on aspect field values in your own code after lookup, as this script does.

## Scenario 3: Ground an agent in your catalog

`scenario3_agent/` defines a minimal [Agent Development Kit](https://google.github.io/adk-docs/) agent with two tools: `search_catalog`, which runs a semantic search and returns the top entry names, and `get_context`, which retrieves LLM-ready metadata for those entries with `lookup_context`. The agent turns a question like "Which tables and columns do I need to compute revenue by product category?" into a search, grounds itself in the retrieved context, and answers citing real table and column names.

Run it from this directory:

```bash
export GOOGLE_GENAI_USE_VERTEXAI=1
export GOOGLE_CLOUD_PROJECT=PROJECT_ID
export GOOGLE_CLOUD_LOCATION=us-central1
adk run scenario3_agent
```

## Clean up

To avoid incurring charges, delete the resources you created:

```bash
bq rm -r -f PROJECT_ID:thelook_ecommerce
gcloud dataplex aspect-types delete pii --location=global --project=PROJECT_ID
```

## What's next

- [Search syntax for Knowledge Catalog](https://docs.cloud.google.com/dataplex/docs/search-syntax)
- [Retrieve context for data assets](https://docs.cloud.google.com/dataplex/docs/retrieve-data-context)
- [Manage aspects and enrich metadata](https://docs.cloud.google.com/dataplex/docs/enrich-entries-metadata)
- [Build an agent to discover your data](https://docs.cloud.google.com/dataplex/docs/use-discovery-agent)
