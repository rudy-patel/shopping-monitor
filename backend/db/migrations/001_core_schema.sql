CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- profiles  (Pattern A; PK = auth.users.id)
CREATE TABLE public.profiles (
    user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_currency text NOT NULL DEFAULT 'CAD'
        CHECK (display_currency IN ('CAD','USD','EUR','GBP')),
    default_threshold_pct int NOT NULL DEFAULT 20
        CHECK (default_threshold_pct BETWEEN 1 AND 95),
    notifications_enabled boolean NOT NULL DEFAULT true,
    email_digest_enabled boolean NOT NULL DEFAULT true,
    theme text NOT NULL DEFAULT 'light'
        CHECK (theme IN ('light','dark')),
    revisit_prompts_enabled boolean NOT NULL DEFAULT true,
    revisit_on_sale_enabled boolean NOT NULL DEFAULT true,
    revisit_stale_enabled boolean NOT NULL DEFAULT true,
    revisit_stale_days int NOT NULL DEFAULT 30
        CHECK (revisit_stale_days BETWEEN 7 AND 365),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TRIGGER profiles_set_updated_at BEFORE UPDATE ON public.profiles
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY profiles_select_own ON public.profiles FOR SELECT
    USING (auth.uid() = user_id);
CREATE POLICY profiles_insert_own ON public.profiles FOR INSERT
    WITH CHECK (auth.uid() = user_id);
CREATE POLICY profiles_update_own ON public.profiles FOR UPDATE
    USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY profiles_delete_own ON public.profiles FOR DELETE
    USING (auth.uid() = user_id);

-- products  (Pattern A; FK auth.users CASCADE)
CREATE TABLE public.products (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title text NOT NULL,
    brand text,
    image_url text,
    category text NOT NULL
        CHECK (category IN ('clothing','shoes','home','tech','other')),
    status text NOT NULL DEFAULT 'active'
        CHECK (status IN ('active','needs_input','archived')),
    notification_threshold_pct int
        CHECK (notification_threshold_pct IS NULL
               OR notification_threshold_pct BETWEEN 1 AND 95),
    notifications_enabled boolean NOT NULL DEFAULT true,
    discovery_status text NOT NULL DEFAULT 'pending'
        CHECK (discovery_status IN ('pending','running','complete','failed')),
    category_source text NOT NULL
        CHECK (category_source IN ('manual','llm','heuristic','default_other')),
    last_refresh_at timestamptz,
    last_user_interaction_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX products_user_status_idx ON public.products(user_id, status);
CREATE INDEX products_user_id_idx ON public.products(user_id);
CREATE TRIGGER products_set_updated_at BEFORE UPDATE ON public.products
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();
ALTER TABLE public.products ENABLE ROW LEVEL SECURITY;
CREATE POLICY products_select_own ON public.products FOR SELECT
    USING (auth.uid() = user_id);
CREATE POLICY products_insert_own ON public.products FOR INSERT
    WITH CHECK (auth.uid() = user_id);
CREATE POLICY products_update_own ON public.products FOR UPDATE
    USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY products_delete_own ON public.products FOR DELETE
    USING (auth.uid() = user_id);

-- product_listings  (Pattern A via products.user_id join)
CREATE TABLE public.product_listings (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id uuid NOT NULL
        REFERENCES public.products(id) ON DELETE CASCADE,
    retailer_slug text NOT NULL,
    url text NOT NULL,
    variant_attributes jsonb NOT NULL DEFAULT '{}'::jsonb,
    available_variants jsonb,
    scrape_snapshot jsonb,
    is_primary boolean NOT NULL DEFAULT false,
    match_confidence numeric(4,3)
        CHECK (match_confidence IS NULL
               OR (match_confidence >= 0 AND match_confidence <= 1)),
    review_status text NOT NULL
        CHECK (review_status IN ('auto_added','needs_review','accepted','rejected')),
    last_known_price_cents int,
    is_in_stock boolean,
    last_scraped_at timestamptz,
    scrape_status text
        CHECK (scrape_status IS NULL
               OR scrape_status IN ('ok','failing','blocked')),
    scrape_failure_count int NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX product_listings_product_id_idx ON public.product_listings(product_id);
CREATE TRIGGER product_listings_set_updated_at BEFORE UPDATE ON public.product_listings
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();
ALTER TABLE public.product_listings ENABLE ROW LEVEL SECURITY;
CREATE POLICY product_listings_select_own ON public.product_listings FOR SELECT
    USING (EXISTS (SELECT 1 FROM public.products p
                    WHERE p.id = product_listings.product_id
                      AND p.user_id = auth.uid()));
CREATE POLICY product_listings_insert_own ON public.product_listings FOR INSERT
    WITH CHECK (EXISTS (SELECT 1 FROM public.products p
                         WHERE p.id = product_listings.product_id
                           AND p.user_id = auth.uid()));
CREATE POLICY product_listings_update_own ON public.product_listings FOR UPDATE
    USING (EXISTS (SELECT 1 FROM public.products p
                    WHERE p.id = product_listings.product_id
                      AND p.user_id = auth.uid()))
    WITH CHECK (EXISTS (SELECT 1 FROM public.products p
                         WHERE p.id = product_listings.product_id
                           AND p.user_id = auth.uid()));
CREATE POLICY product_listings_delete_own ON public.product_listings FOR DELETE
    USING (EXISTS (SELECT 1 FROM public.products p
                    WHERE p.id = product_listings.product_id
                      AND p.user_id = auth.uid()));

-- price_history  (Pattern A via two-step join)
CREATE TABLE public.price_history (
    id bigserial PRIMARY KEY,
    listing_id uuid NOT NULL
        REFERENCES public.product_listings(id) ON DELETE CASCADE,
    price_cents int NOT NULL,
    is_in_stock boolean,
    observed_at timestamptz NOT NULL DEFAULT now(),
    source text NOT NULL CHECK (source IN ('scheduled','manual'))
);
CREATE INDEX price_history_listing_id_idx ON public.price_history(listing_id);
CREATE INDEX price_history_observed_at_idx ON public.price_history(observed_at);
ALTER TABLE public.price_history ENABLE ROW LEVEL SECURITY;
CREATE POLICY price_history_select_own ON public.price_history FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM public.product_listings pl
        JOIN public.products p ON p.id = pl.product_id
        WHERE pl.id = price_history.listing_id
          AND p.user_id = auth.uid()));
CREATE POLICY price_history_insert_own ON public.price_history FOR INSERT
    WITH CHECK (EXISTS (
        SELECT 1 FROM public.product_listings pl
        JOIN public.products p ON p.id = pl.product_id
        WHERE pl.id = price_history.listing_id
          AND p.user_id = auth.uid()));
CREATE POLICY price_history_update_own ON public.price_history FOR UPDATE
    USING (EXISTS (
        SELECT 1 FROM public.product_listings pl
        JOIN public.products p ON p.id = pl.product_id
        WHERE pl.id = price_history.listing_id
          AND p.user_id = auth.uid()))
    WITH CHECK (EXISTS (
        SELECT 1 FROM public.product_listings pl
        JOIN public.products p ON p.id = pl.product_id
        WHERE pl.id = price_history.listing_id
          AND p.user_id = auth.uid()));
CREATE POLICY price_history_delete_own ON public.price_history FOR DELETE
    USING (EXISTS (
        SELECT 1 FROM public.product_listings pl
        JOIN public.products p ON p.id = pl.product_id
        WHERE pl.id = price_history.listing_id
          AND p.user_id = auth.uid()));

-- notifications  (Pattern A)
CREATE TABLE public.notifications (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    product_id uuid REFERENCES public.products(id) ON DELETE CASCADE,
    listing_id uuid REFERENCES public.product_listings(id) ON DELETE CASCADE,
    type text NOT NULL CHECK (type IN (
        'price_drop','back_in_stock','discovery_complete',
        'needs_input','scrape_failing','revisit_on_sale','revisit_stale')),
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    is_read boolean NOT NULL DEFAULT false,
    email_sent_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX notifications_user_created_idx
    ON public.notifications(user_id, created_at DESC);
CREATE INDEX notifications_created_at_idx
    ON public.notifications(created_at);
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;
CREATE POLICY notifications_select_own ON public.notifications FOR SELECT
    USING (auth.uid() = user_id);
CREATE POLICY notifications_insert_own ON public.notifications FOR INSERT
    WITH CHECK (auth.uid() = user_id);
CREATE POLICY notifications_update_own ON public.notifications FOR UPDATE
    USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY notifications_delete_own ON public.notifications FOR DELETE
    USING (auth.uid() = user_id);

-- fx_rates_cache  (Pattern B — service-role only)
CREATE TABLE public.fx_rates_cache (
    pair text PRIMARY KEY,
    rate numeric NOT NULL,
    fetched_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.fx_rates_cache ENABLE ROW LEVEL SECURITY;
-- Intentionally no CREATE POLICY statements; service role bypasses RLS,
-- and authenticated/anon clients get no access by design.
