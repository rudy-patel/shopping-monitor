-- T8.x: global search cache for the search-based product add flow.
-- Backend-only table (Pattern B) — keyed by SHA-256 of normalized query.
-- Cache is intentionally global (not per-user); product search queries are not PII.
-- Service-role inserts/reads only; no authenticated/anon policies.

CREATE TABLE public.search_cache (
    query_hash text PRIMARY KEY,
    query text NOT NULL,
    result_payload jsonb NOT NULL,
    fetched_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX search_cache_fetched_at_idx
    ON public.search_cache (fetched_at DESC);

ALTER TABLE public.search_cache ENABLE ROW LEVEL SECURITY;
-- Pattern B: no policies — service-role bypasses RLS; no other roles can read.
