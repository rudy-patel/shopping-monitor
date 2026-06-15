-- Per-user manual ordering on the category-grouped dashboard (null = fall back to created_at).
ALTER TABLE public.products
    ADD COLUMN dashboard_sort_order integer;

CREATE INDEX products_user_dashboard_sort_idx
    ON public.products (user_id, category, dashboard_sort_order);
