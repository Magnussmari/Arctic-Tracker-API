

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


CREATE EXTENSION IF NOT EXISTS "pgsodium";






COMMENT ON SCHEMA "public" IS 'standard public schema';



CREATE EXTENSION IF NOT EXISTS "pg_graphql" WITH SCHEMA "graphql";






CREATE EXTENSION IF NOT EXISTS "pg_stat_statements" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "pgcrypto" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "pgjwt" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "supabase_vault" WITH SCHEMA "vault";






CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA "extensions";






CREATE OR REPLACE FUNCTION "public"."get_conservation_status_changes_for_arctic_species"() RETURNS TABLE("scientific_name" "text", "status" "text", "listing_year" integer, "pre_listing_trend" "text", "post_listing_trend" "text", "change_direction" "text")
    LANGUAGE "sql"
    AS $$
  WITH 
  -- Get the first CITES listing year for each species
  first_listings AS (
    SELECT 
      species_id,
      MIN(EXTRACT(YEAR FROM listing_date::date)) AS first_listing_year
    FROM 
      cites_listings
    GROUP BY 
      species_id
  ),
  
  -- Get IUCN assessments before and after CITES listing
  assessments_with_listing AS (
    SELECT 
      s.id AS species_id,
      s.scientific_name,
      ia.status,
      ia.year_published,
      fl.first_listing_year,
      CASE 
        WHEN ia.year_published < fl.first_listing_year THEN 'pre-listing'
        WHEN ia.year_published >= fl.first_listing_year THEN 'post-listing'
      END AS assessment_period
    FROM 
      species s
    JOIN 
      iucn_assessments ia ON s.id = ia.species_id
    JOIN 
      first_listings fl ON s.id = fl.species_id
    WHERE 
      -- Filter for Arctic species (same condition as the previous function)
      s.id IN (
        SELECT id FROM species 
        WHERE 
          scientific_name LIKE 'Ursus maritimus' OR  -- Polar Bear
          scientific_name LIKE 'Monodon monoceros' OR  -- Narwhal
          scientific_name LIKE 'Odobenus rosmarus' OR  -- Walrus
          (genus = 'Rangifer' AND species_name = 'tarandus') OR
          family = 'Falconidae'
      )
  ),
  
  -- Get the most recent assessment before listing
  pre_listing_assessments AS (
    SELECT 
      species_id,
      scientific_name,
      status,
      year_published,
      first_listing_year,
      ROW_NUMBER() OVER (PARTITION BY species_id ORDER BY year_published DESC) AS rn
    FROM 
      assessments_with_listing
    WHERE 
      assessment_period = 'pre-listing'
  ),
  
  -- Get the most recent assessment after listing
  post_listing_assessments AS (
    SELECT 
      species_id,
      scientific_name,
      status,
      year_published,
      first_listing_year,
      ROW_NUMBER() OVER (PARTITION BY species_id ORDER BY year_published DESC) AS rn
    FROM 
      assessments_with_listing
    WHERE 
      assessment_period = 'post-listing'
  ),
  
  -- Combine pre and post assessments
  combined_assessments AS (
    SELECT 
      pre.species_id,
      pre.scientific_name,
      pre.status AS pre_status,
      pre.year_published AS pre_year,
      post.status AS post_status,
      post.year_published AS post_year,
      pre.first_listing_year
    FROM 
      pre_listing_assessments pre
    LEFT JOIN 
      post_listing_assessments post ON pre.species_id = post.species_id AND post.rn = 1
    WHERE 
      pre.rn = 1
    
    UNION
    
    SELECT 
      post.species_id,
      post.scientific_name,
      pre.status AS pre_status,
      pre.year_published AS pre_year,
      post.status AS post_status,
      post.year_published AS post_year,
      post.first_listing_year
    FROM 
      post_listing_assessments post
    LEFT JOIN 
      pre_listing_assessments pre ON post.species_id = pre.species_id AND pre.rn = 1
    WHERE 
      post.rn = 1
      AND NOT EXISTS (
        SELECT 1 FROM pre_listing_assessments pre2 
        WHERE pre2.species_id = post.species_id AND pre2.rn = 1
      )
  )
  
  -- Return the final result
  SELECT 
    scientific_name,
    COALESCE(post_status, pre_status) AS status,
    first_listing_year AS listing_year,
    CASE WHEN pre_year IS NOT NULL THEN (first_listing_year - pre_year) || ' years before listing' ELSE NULL END AS pre_listing_trend,
    CASE WHEN post_year IS NOT NULL THEN (post_year - first_listing_year) || ' years after listing' ELSE NULL END AS post_listing_trend,
    CASE 
      -- Compare IUCN status values - this is simplified and would need to be adapted to your actual IUCN status encoding
      -- Assuming status values like CR, EN, VU, NT, LC where CR is most threatened
      WHEN pre_status IS NULL OR post_status IS NULL THEN NULL
      WHEN (
        (pre_status = 'CR' AND post_status IN ('EN', 'VU', 'NT', 'LC')) OR
        (pre_status = 'EN' AND post_status IN ('VU', 'NT', 'LC')) OR
        (pre_status = 'VU' AND post_status IN ('NT', 'LC')) OR
        (pre_status = 'NT' AND post_status = 'LC')
      ) THEN 'improved'
      WHEN (
        (pre_status = 'LC' AND post_status IN ('NT', 'VU', 'EN', 'CR')) OR
        (pre_status = 'NT' AND post_status IN ('VU', 'EN', 'CR')) OR
        (pre_status = 'VU' AND post_status IN ('EN', 'CR')) OR
        (pre_status = 'EN' AND post_status = 'CR')
      ) THEN 'declined'
      WHEN pre_status = post_status THEN 'stable'
      ELSE NULL
    END AS change_direction
  FROM 
    combined_assessments
  ORDER BY 
    scientific_name;
$$;


ALTER FUNCTION "public"."get_conservation_status_changes_for_arctic_species"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_trade_volume_trend_by_year_for_arctic_species"() RETURNS TABLE("year" integer, "count" bigint)
    LANGUAGE "sql"
    AS $$
  SELECT 
    ctr.year, 
    COUNT(*) as count
  FROM 
    cites_trade_records ctr
  JOIN 
    species s ON ctr.species_id = s.id
  WHERE 
    -- Filter for Arctic species - adjust this condition based on your data model
    -- This example assumes you have an Arctic designation in your species table
    -- or you can use taxonomic classification to identify Arctic species
    s.id IN (
      SELECT id FROM species 
      WHERE 
        -- Example conditions - modify based on your actual data
        -- Species known to be Arctic
        scientific_name LIKE 'Ursus maritimus' OR  -- Polar Bear
        scientific_name LIKE 'Monodon monoceros' OR  -- Narwhal
        scientific_name LIKE 'Odobenus rosmarus' OR  -- Walrus
        -- Add other Arctic species scientific names
        -- Or use a taxonomic or geographic filter if available
        (genus = 'Rangifer' AND species_name = 'tarandus') OR  -- Reindeer/Caribou
        family = 'Falconidae'  -- Falcons (many Arctic species)
    )
  GROUP BY 
    ctr.year
  ORDER BY 
    ctr.year ASC;
$$;


ALTER FUNCTION "public"."get_trade_volume_trend_by_year_for_arctic_species"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."handle_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."handle_updated_at"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."list_public_tables"() RETURNS TABLE("table_name" "text")
    LANGUAGE "plpgsql"
    AS $$
BEGIN
  RETURN QUERY
  SELECT c.relname::text FROM pg_catalog.pg_class c
  LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
  WHERE c.relkind = 'r' -- 'r' indicates a relation (table)
    AND n.nspname = 'public' -- Filter for the public schema
  ORDER BY c.relname;
END;
$$;


ALTER FUNCTION "public"."list_public_tables"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_updated_at_column"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_updated_at_column"() OWNER TO "postgres";

SET default_tablespace = '';

SET default_table_access_method = "heap";


CREATE TABLE IF NOT EXISTS "public"."catch_records" (
    "id" bigint NOT NULL,
    "species_id" "uuid",
    "country" "text",
    "year" integer NOT NULL,
    "area" "text",
    "catch_total" integer,
    "quota" integer,
    "source" "text" DEFAULT 'NAMMCO'::"text",
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."catch_records" OWNER TO "postgres";


ALTER TABLE "public"."catch_records" ALTER COLUMN "id" ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME "public"."catch_records_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);



CREATE TABLE IF NOT EXISTS "public"."cites_listings" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "species_id" "uuid" NOT NULL,
    "appendix" "text" NOT NULL,
    "listing_date" "date" NOT NULL,
    "notes" "text",
    "is_current" boolean DEFAULT false
);


ALTER TABLE "public"."cites_listings" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."cites_trade_records" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "species_id" "uuid" NOT NULL,
    "record_id" "text",
    "year" integer NOT NULL,
    "appendix" "text" NOT NULL,
    "taxon" "text" NOT NULL,
    "class" "text",
    "order_name" "text",
    "family" "text",
    "genus" "text",
    "term" "text" NOT NULL,
    "quantity" numeric(10,2),
    "unit" "text",
    "importer" "text",
    "exporter" "text",
    "origin" "text",
    "purpose" "text",
    "source" "text",
    "reporter_type" "text",
    "import_permit" "text",
    "export_permit" "text",
    "origin_permit" "text"
);


ALTER TABLE "public"."cites_trade_records" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."common_names" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "species_id" "uuid" NOT NULL,
    "name" "text" NOT NULL,
    "language" "text" NOT NULL,
    "is_main" boolean DEFAULT false
);


ALTER TABLE "public"."common_names" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."conservation_measures" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "species_id" "uuid" NOT NULL,
    "measure_type" "text" NOT NULL,
    "measure_code" "text" NOT NULL,
    "status" "text",
    "implementing_organizations" "text"[],
    "start_date" "date",
    "end_date" "date",
    "description" "text",
    "effectiveness" "text",
    "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE "public"."conservation_measures" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."distribution_ranges" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "species_id" "uuid" NOT NULL,
    "region" "text" NOT NULL,
    "presence_code" "text" NOT NULL,
    "origin_code" "text" NOT NULL,
    "seasonal_code" "text",
    "geojson" "jsonb",
    "notes" "text",
    "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE "public"."distribution_ranges" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."families" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "family_name" character varying(255) NOT NULL,
    "order_name" character varying(255),
    "class" character varying(255),
    "description" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."families" OWNER TO "postgres";


COMMENT ON TABLE "public"."families" IS 'Normalized table containing unique taxonomic families';



COMMENT ON COLUMN "public"."families"."family_name" IS 'The scientific name of the taxonomic family';



COMMENT ON COLUMN "public"."families"."order_name" IS 'The taxonomic order this family belongs to';



COMMENT ON COLUMN "public"."families"."class" IS 'The taxonomic class this family belongs to';



COMMENT ON COLUMN "public"."families"."description" IS 'Optional description of the family';



CREATE TABLE IF NOT EXISTS "public"."species" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "scientific_name" "text" NOT NULL,
    "common_name" "text" NOT NULL,
    "kingdom" "text" NOT NULL,
    "phylum" "text" NOT NULL,
    "class" "text" NOT NULL,
    "order_name" "text" NOT NULL,
    "family" "text" NOT NULL,
    "genus" "text" NOT NULL,
    "species_name" "text" NOT NULL,
    "authority" "text",
    "sis_id" integer,
    "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    "inaturalist_id" integer,
    "default_image_url" "text",
    "description" "text",
    "habitat_description" "text",
    "population_trend" "text",
    "population_size" "text",
    "generation_length" numeric(5,2),
    "movement_patterns" "text",
    "use_and_trade" "text",
    "threats_overview" "text",
    "conservation_overview" "text",
    "family_id" "uuid"
);


ALTER TABLE "public"."species" OWNER TO "postgres";


COMMENT ON COLUMN "public"."species"."family_id" IS 'Foreign key reference to the families table';



CREATE OR REPLACE VIEW "public"."family_species_count" AS
 SELECT "f"."family_name",
    "f"."order_name",
    "f"."class",
    "count"("s"."id") AS "species_count",
    "f"."created_at" AS "family_created_at"
   FROM ("public"."families" "f"
     LEFT JOIN "public"."species" "s" ON (("f"."id" = "s"."family_id")))
  GROUP BY "f"."id", "f"."family_name", "f"."order_name", "f"."class", "f"."created_at"
  ORDER BY ("count"("s"."id")) DESC, "f"."family_name";


ALTER TABLE "public"."family_species_count" OWNER TO "postgres";


COMMENT ON VIEW "public"."family_species_count" IS 'Summary view showing species count per family';



CREATE TABLE IF NOT EXISTS "public"."iucn_assessments" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "species_id" "uuid" NOT NULL,
    "year_published" integer NOT NULL,
    "is_latest" boolean DEFAULT false,
    "possibly_extinct" boolean DEFAULT false,
    "possibly_extinct_in_wild" boolean DEFAULT false,
    "status" "text",
    "url" "text",
    "assessment_id" integer,
    "scope_code" "text",
    "scope_description" "text"
);


ALTER TABLE "public"."iucn_assessments" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."profiles" (
    "id" "uuid" NOT NULL,
    "email" "text",
    "role" "text",
    "full_name" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."profiles" OWNER TO "postgres";


COMMENT ON TABLE "public"."profiles" IS 'Stores user profile information, extending auth.users. Includes roles for access control.';



COMMENT ON COLUMN "public"."profiles"."id" IS 'User ID from auth.users. Primary key and foreign key linking to auth.users.';



COMMENT ON COLUMN "public"."profiles"."email" IS 'User''s email address. Should be unique.';



COMMENT ON COLUMN "public"."profiles"."role" IS 'User role, e.g., ''admin'', ''editor'', used for authorization.';



COMMENT ON COLUMN "public"."profiles"."full_name" IS 'User''s full name.';



COMMENT ON COLUMN "public"."profiles"."created_at" IS 'Timestamp of when the profile was created.';



COMMENT ON COLUMN "public"."profiles"."updated_at" IS 'Timestamp of when the profile was last updated.';



CREATE TABLE IF NOT EXISTS "public"."species_threats" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "species_id" "uuid" NOT NULL,
    "threat_type" "text" NOT NULL,
    "threat_code" "text" NOT NULL,
    "severity" "text",
    "scope" "text",
    "timing" "text",
    "description" "text",
    "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE "public"."species_threats" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."species_trade_summary" (
    "species_id" "uuid" NOT NULL,
    "last_updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "total_trade_records" integer,
    "overall_min_year" integer,
    "overall_max_year" integer,
    "overall_total_quantity" numeric,
    "distinct_years" "jsonb",
    "distinct_terms" "jsonb",
    "distinct_importers" "jsonb",
    "distinct_exporters" "jsonb",
    "annual_summaries" "jsonb"
);


ALTER TABLE "public"."species_trade_summary" OWNER TO "postgres";


CREATE OR REPLACE VIEW "public"."species_with_family" AS
 SELECT "s"."id",
    "s"."scientific_name",
    "s"."common_name",
    "s"."kingdom",
    "s"."phylum",
    "s"."class",
    "s"."order_name",
    "s"."family",
    "s"."genus",
    "s"."species_name",
    "s"."authority",
    "s"."sis_id",
    "s"."created_at",
    "s"."inaturalist_id",
    "s"."default_image_url",
    "s"."description",
    "s"."habitat_description",
    "s"."population_trend",
    "s"."population_size",
    "s"."generation_length",
    "s"."movement_patterns",
    "s"."use_and_trade",
    "s"."threats_overview",
    "s"."conservation_overview",
    "s"."family_id",
    "f"."family_name" AS "family_name_normalized",
    "f"."order_name" AS "family_order",
    "f"."class" AS "family_class",
    "f"."description" AS "family_description"
   FROM ("public"."species" "s"
     LEFT JOIN "public"."families" "f" ON (("s"."family_id" = "f"."id")));


ALTER TABLE "public"."species_with_family" OWNER TO "postgres";


COMMENT ON VIEW "public"."species_with_family" IS 'Backward-compatible view showing species with denormalized family information';



CREATE OR REPLACE VIEW "public"."species_with_status_view" AS
 SELECT "s"."id",
    "s"."scientific_name",
    "s"."common_name",
    "s"."kingdom",
    "s"."phylum",
    "s"."class",
    "s"."order_name",
    "s"."family",
    "s"."genus",
    "s"."species_name",
    "s"."authority",
    "s"."sis_id",
    "s"."created_at",
    "s"."inaturalist_id",
    "s"."default_image_url",
    "s"."description",
    "s"."habitat_description",
    "s"."population_trend",
    "s"."population_size",
    "s"."generation_length",
    "s"."movement_patterns",
    "s"."use_and_trade",
    "s"."threats_overview",
    "s"."conservation_overview",
    "latest_iucn"."status" AS "latest_iucn_status",
    "latest_iucn"."year_published" AS "latest_iucn_year",
    "latest_iucn"."is_latest" AS "has_iucn_assessment",
    "current_cites"."appendix" AS "current_cites_appendix",
    "current_cites"."listing_date" AS "current_cites_date",
    "current_cites"."notes" AS "current_cites_notes",
    "current_cites"."is_current" AS "has_cites_listing",
    "primary_cn"."name" AS "primary_common_name"
   FROM ((("public"."species" "s"
     LEFT JOIN "public"."iucn_assessments" "latest_iucn" ON ((("s"."id" = "latest_iucn"."species_id") AND ("latest_iucn"."is_latest" = true))))
     LEFT JOIN "public"."cites_listings" "current_cites" ON ((("s"."id" = "current_cites"."species_id") AND ("current_cites"."is_current" = true))))
     LEFT JOIN LATERAL ( SELECT "cn"."name"
           FROM "public"."common_names" "cn"
          WHERE ("cn"."species_id" = "s"."id")
          ORDER BY "cn"."name"
         LIMIT 1) "primary_cn" ON (true))
  ORDER BY "s"."scientific_name";


ALTER TABLE "public"."species_with_status_view" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."subpopulations" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "species_id" "uuid" NOT NULL,
    "scientific_name" "text" NOT NULL,
    "subpopulation_name" "text" NOT NULL,
    "sis_id" integer,
    "authority" "text"
);


ALTER TABLE "public"."subpopulations" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."timeline_events" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "species_id" "uuid" NOT NULL,
    "event_date" "date" NOT NULL,
    "year" integer NOT NULL,
    "event_type" "text" NOT NULL,
    "title" "text" NOT NULL,
    "description" "text",
    "status" "text",
    "source_type" "text" NOT NULL,
    "source_id" "uuid"
);


ALTER TABLE "public"."timeline_events" OWNER TO "postgres";


ALTER TABLE ONLY "public"."catch_records"
    ADD CONSTRAINT "catch_records_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."cites_listings"
    ADD CONSTRAINT "cites_listings_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."cites_trade_records"
    ADD CONSTRAINT "cites_trade_records_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."common_names"
    ADD CONSTRAINT "common_names_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."conservation_measures"
    ADD CONSTRAINT "conservation_measures_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."distribution_ranges"
    ADD CONSTRAINT "distribution_ranges_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."families"
    ADD CONSTRAINT "families_family_name_key" UNIQUE ("family_name");



ALTER TABLE ONLY "public"."families"
    ADD CONSTRAINT "families_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."iucn_assessments"
    ADD CONSTRAINT "iucn_assessments_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."profiles"
    ADD CONSTRAINT "profiles_email_key" UNIQUE ("email");



ALTER TABLE ONLY "public"."profiles"
    ADD CONSTRAINT "profiles_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."species"
    ADD CONSTRAINT "species_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."species_threats"
    ADD CONSTRAINT "species_threats_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."species_trade_summary"
    ADD CONSTRAINT "species_trade_summary_pkey" PRIMARY KEY ("species_id");



ALTER TABLE ONLY "public"."subpopulations"
    ADD CONSTRAINT "subpopulations_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."timeline_events"
    ADD CONSTRAINT "timeline_events_pkey" PRIMARY KEY ("id");



CREATE INDEX "idx_catch_records_species_year" ON "public"."catch_records" USING "btree" ("species_id", "year");



CREATE INDEX "idx_cites_trade_species" ON "public"."cites_trade_records" USING "btree" ("species_id");



CREATE INDEX "idx_cites_trade_year" ON "public"."cites_trade_records" USING "btree" ("year");



CREATE INDEX "idx_distribution_species" ON "public"."distribution_ranges" USING "btree" ("species_id");



CREATE INDEX "idx_families_family_name" ON "public"."families" USING "btree" ("family_name");



CREATE INDEX "idx_families_order_name" ON "public"."families" USING "btree" ("order_name");



CREATE INDEX "idx_iucn_assessments_species" ON "public"."iucn_assessments" USING "btree" ("species_id");



CREATE INDEX "idx_iucn_assessments_year" ON "public"."iucn_assessments" USING "btree" ("year_published");



CREATE INDEX "idx_measures_species" ON "public"."conservation_measures" USING "btree" ("species_id");



CREATE INDEX "idx_species_family_id" ON "public"."species" USING "btree" ("family_id");



CREATE INDEX "idx_species_scientific_name" ON "public"."species" USING "btree" ("scientific_name");



CREATE INDEX "idx_threats_species" ON "public"."species_threats" USING "btree" ("species_id");



CREATE INDEX "idx_timeline_events_date" ON "public"."timeline_events" USING "btree" ("event_date");



CREATE INDEX "idx_timeline_events_species" ON "public"."timeline_events" USING "btree" ("species_id");



CREATE INDEX "idx_timeline_events_type" ON "public"."timeline_events" USING "btree" ("event_type");



CREATE OR REPLACE TRIGGER "on_profiles_updated" BEFORE UPDATE ON "public"."profiles" FOR EACH ROW EXECUTE FUNCTION "public"."handle_updated_at"();



CREATE OR REPLACE TRIGGER "update_families_updated_at" BEFORE UPDATE ON "public"."families" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



ALTER TABLE ONLY "public"."catch_records"
    ADD CONSTRAINT "catch_records_species_id_fkey" FOREIGN KEY ("species_id") REFERENCES "public"."species"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."cites_listings"
    ADD CONSTRAINT "cites_listings_species_id_fkey" FOREIGN KEY ("species_id") REFERENCES "public"."species"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."cites_trade_records"
    ADD CONSTRAINT "cites_trade_records_species_id_fkey" FOREIGN KEY ("species_id") REFERENCES "public"."species"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."common_names"
    ADD CONSTRAINT "common_names_species_id_fkey" FOREIGN KEY ("species_id") REFERENCES "public"."species"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."conservation_measures"
    ADD CONSTRAINT "conservation_measures_species_id_fkey" FOREIGN KEY ("species_id") REFERENCES "public"."species"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."distribution_ranges"
    ADD CONSTRAINT "distribution_ranges_species_id_fkey" FOREIGN KEY ("species_id") REFERENCES "public"."species"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."species"
    ADD CONSTRAINT "fk_species_family" FOREIGN KEY ("family_id") REFERENCES "public"."families"("id");



ALTER TABLE ONLY "public"."iucn_assessments"
    ADD CONSTRAINT "iucn_assessments_species_id_fkey" FOREIGN KEY ("species_id") REFERENCES "public"."species"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."profiles"
    ADD CONSTRAINT "profiles_id_fkey" FOREIGN KEY ("id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."species_threats"
    ADD CONSTRAINT "species_threats_species_id_fkey" FOREIGN KEY ("species_id") REFERENCES "public"."species"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."species_trade_summary"
    ADD CONSTRAINT "species_trade_summary_species_id_fkey" FOREIGN KEY ("species_id") REFERENCES "public"."species"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."subpopulations"
    ADD CONSTRAINT "subpopulations_species_id_fkey" FOREIGN KEY ("species_id") REFERENCES "public"."species"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."timeline_events"
    ADD CONSTRAINT "timeline_events_species_id_fkey" FOREIGN KEY ("species_id") REFERENCES "public"."species"("id") ON DELETE CASCADE;



CREATE POLICY "Allow individual user read access to their own profile" ON "public"."profiles" FOR SELECT USING (("auth"."uid"() = "id"));



CREATE POLICY "Allow individual user to update their own profile" ON "public"."profiles" FOR UPDATE USING (("auth"."uid"() = "id")) WITH CHECK (("auth"."uid"() = "id"));



CREATE POLICY "Enable insert for service_role" ON "public"."species_trade_summary" FOR INSERT WITH CHECK (("auth"."role"() = 'service_role'::"text"));



CREATE POLICY "Enable read access for all users" ON "public"."species_trade_summary" FOR SELECT USING (true);



CREATE POLICY "Enable update for service_role" ON "public"."species_trade_summary" FOR UPDATE USING (("auth"."role"() = 'service_role'::"text"));



ALTER TABLE "public"."profiles" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."species_trade_summary" ENABLE ROW LEVEL SECURITY;




ALTER PUBLICATION "supabase_realtime" OWNER TO "postgres";


GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";




















































































































































































GRANT ALL ON FUNCTION "public"."get_conservation_status_changes_for_arctic_species"() TO "anon";
GRANT ALL ON FUNCTION "public"."get_conservation_status_changes_for_arctic_species"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_conservation_status_changes_for_arctic_species"() TO "service_role";



GRANT ALL ON FUNCTION "public"."get_trade_volume_trend_by_year_for_arctic_species"() TO "anon";
GRANT ALL ON FUNCTION "public"."get_trade_volume_trend_by_year_for_arctic_species"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_trade_volume_trend_by_year_for_arctic_species"() TO "service_role";



GRANT ALL ON FUNCTION "public"."handle_updated_at"() TO "anon";
GRANT ALL ON FUNCTION "public"."handle_updated_at"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."handle_updated_at"() TO "service_role";



GRANT ALL ON FUNCTION "public"."list_public_tables"() TO "anon";
GRANT ALL ON FUNCTION "public"."list_public_tables"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."list_public_tables"() TO "service_role";



GRANT ALL ON FUNCTION "public"."update_updated_at_column"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_updated_at_column"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_updated_at_column"() TO "service_role";



























GRANT ALL ON TABLE "public"."catch_records" TO "anon";
GRANT ALL ON TABLE "public"."catch_records" TO "authenticated";
GRANT ALL ON TABLE "public"."catch_records" TO "service_role";



GRANT ALL ON SEQUENCE "public"."catch_records_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."catch_records_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."catch_records_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."cites_listings" TO "anon";
GRANT ALL ON TABLE "public"."cites_listings" TO "authenticated";
GRANT ALL ON TABLE "public"."cites_listings" TO "service_role";



GRANT ALL ON TABLE "public"."cites_trade_records" TO "anon";
GRANT ALL ON TABLE "public"."cites_trade_records" TO "authenticated";
GRANT ALL ON TABLE "public"."cites_trade_records" TO "service_role";



GRANT ALL ON TABLE "public"."common_names" TO "anon";
GRANT ALL ON TABLE "public"."common_names" TO "authenticated";
GRANT ALL ON TABLE "public"."common_names" TO "service_role";



GRANT ALL ON TABLE "public"."conservation_measures" TO "anon";
GRANT ALL ON TABLE "public"."conservation_measures" TO "authenticated";
GRANT ALL ON TABLE "public"."conservation_measures" TO "service_role";



GRANT ALL ON TABLE "public"."distribution_ranges" TO "anon";
GRANT ALL ON TABLE "public"."distribution_ranges" TO "authenticated";
GRANT ALL ON TABLE "public"."distribution_ranges" TO "service_role";



GRANT ALL ON TABLE "public"."families" TO "anon";
GRANT ALL ON TABLE "public"."families" TO "authenticated";
GRANT ALL ON TABLE "public"."families" TO "service_role";



GRANT ALL ON TABLE "public"."species" TO "anon";
GRANT ALL ON TABLE "public"."species" TO "authenticated";
GRANT ALL ON TABLE "public"."species" TO "service_role";



GRANT ALL ON TABLE "public"."family_species_count" TO "anon";
GRANT ALL ON TABLE "public"."family_species_count" TO "authenticated";
GRANT ALL ON TABLE "public"."family_species_count" TO "service_role";



GRANT ALL ON TABLE "public"."iucn_assessments" TO "anon";
GRANT ALL ON TABLE "public"."iucn_assessments" TO "authenticated";
GRANT ALL ON TABLE "public"."iucn_assessments" TO "service_role";



GRANT ALL ON TABLE "public"."profiles" TO "anon";
GRANT ALL ON TABLE "public"."profiles" TO "authenticated";
GRANT ALL ON TABLE "public"."profiles" TO "service_role";



GRANT ALL ON TABLE "public"."species_threats" TO "anon";
GRANT ALL ON TABLE "public"."species_threats" TO "authenticated";
GRANT ALL ON TABLE "public"."species_threats" TO "service_role";



GRANT ALL ON TABLE "public"."species_trade_summary" TO "anon";
GRANT ALL ON TABLE "public"."species_trade_summary" TO "authenticated";
GRANT ALL ON TABLE "public"."species_trade_summary" TO "service_role";



GRANT ALL ON TABLE "public"."species_with_family" TO "anon";
GRANT ALL ON TABLE "public"."species_with_family" TO "authenticated";
GRANT ALL ON TABLE "public"."species_with_family" TO "service_role";



GRANT ALL ON TABLE "public"."species_with_status_view" TO "anon";
GRANT ALL ON TABLE "public"."species_with_status_view" TO "authenticated";
GRANT ALL ON TABLE "public"."species_with_status_view" TO "service_role";



GRANT ALL ON TABLE "public"."subpopulations" TO "anon";
GRANT ALL ON TABLE "public"."subpopulations" TO "authenticated";
GRANT ALL ON TABLE "public"."subpopulations" TO "service_role";



GRANT ALL ON TABLE "public"."timeline_events" TO "anon";
GRANT ALL ON TABLE "public"."timeline_events" TO "authenticated";
GRANT ALL ON TABLE "public"."timeline_events" TO "service_role";









ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES  TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES  TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES  TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES  TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS  TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS  TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS  TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS  TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES  TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES  TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES  TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES  TO "service_role";






























RESET ALL;
