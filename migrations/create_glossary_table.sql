-- Create Glossary Table for Arctic Tracker
-- This table stores all terms and definitions for the glossary feature

-- Create the glossary table
CREATE TABLE IF NOT EXISTS "public"."glossary_terms" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "term" "text" NOT NULL,
    "acronym" "text",
    "definition" "text" NOT NULL,
    "category" "text" NOT NULL,
    "subcategory" "text",
    "examples" "text",
    "related_terms" "text"[],
    "priority" integer DEFAULT 0,
    "display_contexts" "text"[],
    "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "glossary_terms_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "glossary_terms_term_unique" UNIQUE ("term")
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS "idx_glossary_terms_category" ON "public"."glossary_terms"("category");
CREATE INDEX IF NOT EXISTS "idx_glossary_terms_term" ON "public"."glossary_terms"("term");
CREATE INDEX IF NOT EXISTS "idx_glossary_terms_acronym" ON "public"."glossary_terms"("acronym");
CREATE INDEX IF NOT EXISTS "idx_glossary_terms_priority" ON "public"."glossary_terms"("priority" DESC);

-- Full text search index for term and definition
CREATE INDEX IF NOT EXISTS "idx_glossary_terms_search" ON "public"."glossary_terms" 
USING gin(to_tsvector('english', term || ' ' || COALESCE(acronym, '') || ' ' || definition));

-- Add comments for documentation
COMMENT ON TABLE "public"."glossary_terms" IS 'Stores glossary terms and definitions for the Arctic Tracker education feature';
COMMENT ON COLUMN "public"."glossary_terms"."term" IS 'The term or phrase being defined';
COMMENT ON COLUMN "public"."glossary_terms"."acronym" IS 'Acronym if applicable (e.g., CITES, IUCN)';
COMMENT ON COLUMN "public"."glossary_terms"."definition" IS 'Full definition of the term';
COMMENT ON COLUMN "public"."glossary_terms"."category" IS 'Main category: Conservation, Trade, Taxonomy, Geography, Data';
COMMENT ON COLUMN "public"."glossary_terms"."subcategory" IS 'Optional subcategory for more specific grouping';
COMMENT ON COLUMN "public"."glossary_terms"."examples" IS 'Usage examples or additional context';
COMMENT ON COLUMN "public"."glossary_terms"."related_terms" IS 'Array of related glossary terms';
COMMENT ON COLUMN "public"."glossary_terms"."priority" IS 'Display priority (higher = more important)';
COMMENT ON COLUMN "public"."glossary_terms"."display_contexts" IS 'Where this term should be highlighted (species_card, trade_tab, filters, etc.)';

-- Create a view for easy category grouping
CREATE OR REPLACE VIEW "public"."glossary_by_category" AS
SELECT 
    category,
    subcategory,
    COUNT(*) as term_count,
    array_agg(
        json_build_object(
            'id', id,
            'term', term,
            'acronym', acronym,
            'definition', definition,
            'priority', priority
        ) ORDER BY priority DESC, term ASC
    ) as terms
FROM 
    "public"."glossary_terms"
GROUP BY 
    category, subcategory
ORDER BY 
    category, subcategory;

COMMENT ON VIEW "public"."glossary_by_category" IS 'View showing glossary terms grouped by category';

-- Create a view for contextual help (terms that should show tooltips)
CREATE OR REPLACE VIEW "public"."glossary_contextual_terms" AS
SELECT 
    id,
    term,
    acronym,
    definition,
    category,
    display_contexts,
    priority
FROM 
    "public"."glossary_terms"
WHERE 
    array_length(display_contexts, 1) > 0
    AND priority > 0
ORDER BY 
    priority DESC, term;

COMMENT ON VIEW "public"."glossary_contextual_terms" IS 'Terms that should display contextual help tooltips in various UI contexts';

-- Grant appropriate permissions
GRANT SELECT ON "public"."glossary_terms" TO anon, authenticated;
GRANT ALL ON "public"."glossary_terms" TO service_role;
GRANT SELECT ON "public"."glossary_by_category" TO anon, authenticated;
GRANT SELECT ON "public"."glossary_contextual_terms" TO anon, authenticated;

-- Create RLS policies
ALTER TABLE "public"."glossary_terms" ENABLE ROW LEVEL SECURITY;

-- Allow everyone to read glossary terms
CREATE POLICY "Allow public read access to glossary terms" 
    ON "public"."glossary_terms" 
    FOR SELECT 
    TO public 
    USING (true);

-- Only authenticated users with appropriate roles can modify
CREATE POLICY "Allow editors to manage glossary terms" 
    ON "public"."glossary_terms" 
    FOR ALL 
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

-- Function to search glossary terms
CREATE OR REPLACE FUNCTION "public"."search_glossary_terms"(search_query text)
RETURNS TABLE(
    id uuid,
    term text,
    acronym text,
    definition text,
    category text,
    rank real
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        g.id,
        g.term,
        g.acronym,
        g.definition,
        g.category,
        ts_rank(
            to_tsvector('english', g.term || ' ' || COALESCE(g.acronym, '') || ' ' || g.definition),
            plainto_tsquery('english', search_query)
        ) as rank
    FROM glossary_terms g
    WHERE 
        to_tsvector('english', g.term || ' ' || COALESCE(g.acronym, '') || ' ' || g.definition) 
        @@ plainto_tsquery('english', search_query)
    ORDER BY rank DESC, g.priority DESC
    LIMIT 20;
END;
$$;

COMMENT ON FUNCTION "public"."search_glossary_terms" IS 'Full text search function for glossary terms';

-- Function to get related terms
CREATE OR REPLACE FUNCTION "public"."get_related_glossary_terms"(term_id uuid)
RETURNS TABLE(
    id uuid,
    term text,
    acronym text,
    definition text,
    category text
)
LANGUAGE plpgsql
AS $$
DECLARE
    related_term_names text[];
BEGIN
    -- Get the related terms array for the given term
    SELECT related_terms INTO related_term_names
    FROM glossary_terms
    WHERE id = term_id;
    
    -- Return the full details of related terms
    RETURN QUERY
    SELECT 
        g.id,
        g.term,
        g.acronym,
        g.definition,
        g.category
    FROM glossary_terms g
    WHERE g.term = ANY(related_term_names)
    ORDER BY g.priority DESC, g.term;
END;
$$;

COMMENT ON FUNCTION "public"."get_related_glossary_terms" IS 'Get full details of related glossary terms';