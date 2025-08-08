-- Create CMS (Convention on the Conservation of Migratory Species) listings table
-- This table stores CMS appendix listings for Arctic species

-- Create the cms_listings table
CREATE TABLE IF NOT EXISTS "public"."cms_listings" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "species_id" "uuid" NOT NULL,
    "appendix" "text" NOT NULL,
    "agreement" "text",
    "listed_under" "text",
    "listing_date" "text",
    "notes" "text",
    "native_distribution" "text"[],
    "distribution_codes" "text"[],
    "introduced_distribution" "text"[],
    "extinct_distribution" "text"[],
    "distribution_uncertain" "text"[],
    "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "cms_listings_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "cms_listings_species_id_fkey" FOREIGN KEY ("species_id") 
        REFERENCES "public"."species"("id") ON DELETE CASCADE
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS "idx_cms_listings_species_id" ON "public"."cms_listings"("species_id");
CREATE INDEX IF NOT EXISTS "idx_cms_listings_appendix" ON "public"."cms_listings"("appendix");

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

-- Create a view to easily query CMS listings with species information
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

-- Grant appropriate permissions
GRANT SELECT ON "public"."cms_listings" TO anon, authenticated;
GRANT ALL ON "public"."cms_listings" TO service_role;
GRANT SELECT ON "public"."species_cms_listings" TO anon, authenticated;

-- Create RLS policies
ALTER TABLE "public"."cms_listings" ENABLE ROW LEVEL SECURITY;

-- Allow everyone to read CMS listings
CREATE POLICY "Allow public read access to CMS listings" 
    ON "public"."cms_listings" 
    FOR SELECT 
    TO public 
    USING (true);

-- Only authenticated users with appropriate roles can modify
CREATE POLICY "Allow authenticated users to insert CMS listings" 
    ON "public"."cms_listings" 
    FOR INSERT 
    TO authenticated 
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM "public"."profiles" 
            WHERE id = auth.uid() 
            AND role IN ('admin', 'editor')
        )
    );

CREATE POLICY "Allow authenticated users to update CMS listings" 
    ON "public"."cms_listings" 
    FOR UPDATE 
    TO authenticated 
    USING (
        EXISTS (
            SELECT 1 FROM "public"."profiles" 
            WHERE id = auth.uid() 
            AND role IN ('admin', 'editor')
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM "public"."profiles" 
            WHERE id = auth.uid() 
            AND role IN ('admin', 'editor')
        )
    );

CREATE POLICY "Allow authenticated users to delete CMS listings" 
    ON "public"."cms_listings" 
    FOR DELETE 
    TO authenticated 
    USING (
        EXISTS (
            SELECT 1 FROM "public"."profiles" 
            WHERE id = auth.uid() 
            AND role = 'admin'
        )
    );