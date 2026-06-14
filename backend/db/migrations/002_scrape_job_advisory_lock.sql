-- T3.5: Postgres advisory lock helpers for scheduled scrape-all job.
-- Fixed int8 key — parity with SCRAPE_ALL_ADVISORY_LOCK_KEY in scrape_job_service.py.

CREATE OR REPLACE FUNCTION public.try_acquire_scrape_all_lock()
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  RETURN pg_try_advisory_lock(8675309);
END;
$$;

CREATE OR REPLACE FUNCTION public.release_scrape_all_lock()
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  RETURN pg_advisory_unlock(8675309);
END;
$$;
