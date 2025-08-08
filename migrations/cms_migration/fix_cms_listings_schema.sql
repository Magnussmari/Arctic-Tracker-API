-- Fix CMS Listings Table Schema
-- This script updates the existing cms_listings table to match the required schema

-- First, check if we need to add missing columns
-- The table exists but is missing several columns including 'agreement'

-- Add missing columns to cms_listings table
ALTER TABLE "public"."cms_listings" 
ADD COLUMN IF NOT EXISTS "agreement" text,
ADD COLUMN IF NOT EXISTS "listed_under" text,
ADD COLUMN IF NOT EXISTS "listing_date" text,
ADD COLUMN IF NOT EXISTS "notes" text,
ADD COLUMN IF NOT EXISTS "native_distribution" text[],
ADD COLUMN IF NOT EXISTS "distribution_codes" text[],
ADD COLUMN IF NOT EXISTS "introduced_distribution" text[],
ADD COLUMN IF NOT EXISTS "extinct_distribution" text[],
ADD COLUMN IF NOT EXISTS "distribution_uncertain" text[],
ADD COLUMN IF NOT EXISTS "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP;

-- Add comments for the new columns
COMMENT ON COLUMN "public"."cms_listings"."agreement" IS 'Agreement name (usually CMS)';
COMMENT ON COLUMN "public"."cms_listings"."listed_under" IS 'Scientific name as listed in CMS';
COMMENT ON COLUMN "public"."cms_listings"."listing_date" IS 'Date when species was listed';
COMMENT ON COLUMN "public"."cms_listings"."notes" IS 'Additional notes about the listing';
COMMENT ON COLUMN "public"."cms_listings"."native_distribution" IS 'Array of countries where species is native';
COMMENT ON COLUMN "public"."cms_listings"."distribution_codes" IS 'Array of ISO country codes for distribution';
COMMENT ON COLUMN "public"."cms_listings"."introduced_distribution" IS 'Array of countries where species was introduced';
COMMENT ON COLUMN "public"."cms_listings"."extinct_distribution" IS 'Array of countries where species is extinct';
COMMENT ON COLUMN "public"."cms_listings"."distribution_uncertain" IS 'Array of countries with uncertain distribution';

-- Create the view if it doesn't exist
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

-- Grant permissions if not already granted
GRANT SELECT ON "public"."species_cms_listings" TO anon, authenticated;

-- Verify the schema is now correct
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' 
AND table_name = 'cms_listings'
ORDER BY ordinal_position;