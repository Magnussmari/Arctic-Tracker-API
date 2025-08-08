-- Fix CMS Listings Table Schema - Precise Version
-- Based on investigation, the table exists with different columns than expected

-- Current columns that exist:
-- id, species_id, appendix, listing_date (as date), notes, is_current, created_at, updated_at

-- Need to add these missing columns:
ALTER TABLE "public"."cms_listings" 
ADD COLUMN IF NOT EXISTS "agreement" text,
ADD COLUMN IF NOT EXISTS "listed_under" text,
ADD COLUMN IF NOT EXISTS "native_distribution" text[],
ADD COLUMN IF NOT EXISTS "distribution_codes" text[],
ADD COLUMN IF NOT EXISTS "introduced_distribution" text[],
ADD COLUMN IF NOT EXISTS "extinct_distribution" text[],
ADD COLUMN IF NOT EXISTS "distribution_uncertain" text[];

-- Note: listing_date exists but as DATE type, our script expects TEXT
-- We need to change it to TEXT to match the expected format
ALTER TABLE "public"."cms_listings" 
ALTER COLUMN "listing_date" TYPE text USING listing_date::text;

-- Drop the is_current column as it's not in our data model
ALTER TABLE "public"."cms_listings" 
DROP COLUMN IF EXISTS "is_current";

-- Add comments for documentation
COMMENT ON TABLE "public"."cms_listings" IS 'Stores CMS (Convention on the Conservation of Migratory Species) appendix listings for Arctic species';
COMMENT ON COLUMN "public"."cms_listings"."species_id" IS 'Foreign key reference to the species table';
COMMENT ON COLUMN "public"."cms_listings"."appendix" IS 'CMS Appendix listing (I, II, or I/II)';
COMMENT ON COLUMN "public"."cms_listings"."agreement" IS 'Agreement name (usually CMS)';
COMMENT ON COLUMN "public"."cms_listings"."listed_under" IS 'Scientific name as listed in CMS';
COMMENT ON COLUMN "public"."cms_listings"."listing_date" IS 'Date when species was listed';
COMMENT ON COLUMN "public"."cms_listings"."notes" IS 'Additional notes about the listing';
COMMENT ON COLUMN "public"."cms_listings"."native_distribution" IS 'Array of countries where species is native';
COMMENT ON COLUMN "public"."cms_listings"."distribution_codes" IS 'Array of ISO country codes for distribution';
COMMENT ON COLUMN "public"."cms_listings"."introduced_distribution" IS 'Array of countries where species was introduced';
COMMENT ON COLUMN "public"."cms_listings"."extinct_distribution" IS 'Array of countries where species is extinct';
COMMENT ON COLUMN "public"."cms_listings"."distribution_uncertain" IS 'Array of countries with uncertain distribution';

-- Create indexes if they don't exist
CREATE INDEX IF NOT EXISTS "idx_cms_listings_species_id" ON "public"."cms_listings"("species_id");
CREATE INDEX IF NOT EXISTS "idx_cms_listings_appendix" ON "public"."cms_listings"("appendix");

-- Create the view
CREATE OR REPLACE VIEW "public"."species_cms_listings" AS
SELECT 
    s.id AS species_id,
    s.scientific_name,
    s.common_name,
    s.class,
    s.order_name,
    s.family,
    c.appendix AS cms_appendix,
    c.listing_date AS cms_listing_date,
    c.native_distribution,
    c.distribution_codes,
    array_length(c.native_distribution, 1) AS native_country_count,
    c.notes AS cms_notes
FROM 
    "public"."species" s
    LEFT JOIN "public"."cms_listings" c ON s.id = c.species_id
ORDER BY 
    s.scientific_name;

COMMENT ON VIEW "public"."species_cms_listings" IS 'View combining species information with their CMS listings';

-- Grant permissions
GRANT SELECT ON "public"."cms_listings" TO anon, authenticated;
GRANT ALL ON "public"."cms_listings" TO service_role;
GRANT SELECT ON "public"."species_cms_listings" TO anon, authenticated;

-- Enable RLS if not already enabled
ALTER TABLE "public"."cms_listings" ENABLE ROW LEVEL SECURITY;

-- Create RLS policies if they don't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'cms_listings' 
        AND policyname = 'Allow public read access to CMS listings'
    ) THEN
        CREATE POLICY "Allow public read access to CMS listings" 
            ON "public"."cms_listings" 
            FOR SELECT 
            TO public 
            USING (true);
    END IF;
END $$;

-- Verify the final schema
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' 
AND table_name = 'cms_listings'
ORDER BY ordinal_position;