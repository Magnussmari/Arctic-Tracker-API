-- Create missing tables for enhanced species profiles
-- Run this in Supabase SQL Editor

-- Create references table (matching actual schema)
CREATE TABLE IF NOT EXISTS public.references (
  id uuid not null default extensions.uuid_generate_v4 (),
  source_id text not null,
  authors text null,
  year integer null,
  title text null,
  journal text null,
  doi text null,
  full_citation text not null,
  created_at timestamp with time zone null default CURRENT_TIMESTAMP,
  updated_at timestamp with time zone null default CURRENT_TIMESTAMP,
  constraint references_pkey primary key (id),
  constraint references_source_id_key unique (source_id)
) TABLESPACE pg_default;

-- Create conservation_measures table (matching actual schema)
CREATE TABLE IF NOT EXISTS public.conservation_measures (
  id uuid not null default extensions.uuid_generate_v4 (),
  species_id uuid not null,
  measure_type text not null,
  measure_code text not null,
  status text null,
  implementing_organizations text[] null,
  start_date date null,
  end_date date null,
  description text null,
  effectiveness text null,
  created_at timestamp with time zone null default CURRENT_TIMESTAMP,
  constraint conservation_measures_pkey primary key (id),
  constraint conservation_measures_species_id_fkey foreign KEY (species_id) references species (id) on delete CASCADE
) TABLESPACE pg_default;

-- Create conservation_profiles table (for comprehensive profiles)
CREATE TABLE IF NOT EXISTS public.conservation_profiles (
    id UUID DEFAULT extensions.uuid_generate_v4() PRIMARY KEY,
    species_id UUID NOT NULL REFERENCES species(id) ON DELETE CASCADE,
    profile_type TEXT DEFAULT 'comprehensive',
    content JSONB, -- Store profile content as JSON
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create profile_references junction table
CREATE TABLE IF NOT EXISTS public.profile_references (
    id UUID DEFAULT extensions.uuid_generate_v4() PRIMARY KEY,
    profile_id UUID NOT NULL REFERENCES conservation_profiles(id) ON DELETE CASCADE,
    reference_id UUID NOT NULL REFERENCES "references"(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(profile_id, reference_id)
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_references_source_id ON public."references" USING btree (source_id) TABLESPACE pg_default;
CREATE INDEX IF NOT EXISTS idx_references_year ON public."references" USING btree (year) TABLESPACE pg_default;
CREATE INDEX IF NOT EXISTS idx_references_authors ON public."references" USING btree (authors) TABLESPACE pg_default;
CREATE INDEX IF NOT EXISTS idx_measures_species ON public.conservation_measures USING btree (species_id) TABLESPACE pg_default;
CREATE INDEX IF NOT EXISTS idx_conservation_profiles_species_id ON conservation_profiles(species_id);
CREATE INDEX IF NOT EXISTS idx_profile_references_profile_id ON profile_references(profile_id);
CREATE INDEX IF NOT EXISTS idx_profile_references_reference_id ON profile_references(reference_id);

-- Add triggers for updated_at (PostgreSQL doesn't support IF NOT EXISTS for triggers)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_references_updated_at') THEN
        CREATE TRIGGER update_references_updated_at 
        BEFORE UPDATE ON "references" 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- Add comments
COMMENT ON TABLE "references" IS 'Scientific references and citations';
COMMENT ON TABLE conservation_measures IS 'Conservation measures and actions for species';
COMMENT ON TABLE conservation_profiles IS 'Comprehensive species conservation profiles';
COMMENT ON TABLE profile_references IS 'Links conservation profiles to their references';

COMMENT ON COLUMN "references".source_id IS 'Unique identifier for the reference source';
COMMENT ON COLUMN "references".authors IS 'Authors as comma-separated text';
COMMENT ON COLUMN "references".doi IS 'Digital Object Identifier';
COMMENT ON COLUMN conservation_profiles.content IS 'JSON content with subpopulations, distribution, etc.';
