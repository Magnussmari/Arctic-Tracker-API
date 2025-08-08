-- Family Normalization Migration
-- This script normalizes the family data from the species table into a separate families table
-- and updates the species table to reference families by ID instead of storing family names directly

BEGIN;

-- Step 1: Create the families table
CREATE TABLE IF NOT EXISTS families (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    family_name VARCHAR(255) NOT NULL UNIQUE,
    order_name VARCHAR(255),
    class VARCHAR(255),
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Step 2: Create an index on family_name for better performance
CREATE INDEX IF NOT EXISTS idx_families_family_name ON families(family_name);
CREATE INDEX IF NOT EXISTS idx_families_order_name ON families(order_name);

-- Step 3: Insert unique families from the species table
-- Use INSERT ... ON CONFLICT DO NOTHING to handle duplicates gracefully
INSERT INTO families (family_name, order_name, class)
SELECT DISTINCT 
    s.family as family_name,
    s.order_name,
    s.class
FROM species s 
WHERE s.family IS NOT NULL 
    AND s.family != ''
ORDER BY s.family
ON CONFLICT (family_name) DO NOTHING;

-- Step 4: Add family_id column to species table
ALTER TABLE species ADD COLUMN IF NOT EXISTS family_id UUID;

-- Step 5: Create foreign key constraint
-- PostgreSQL doesn't support IF NOT EXISTS with ADD CONSTRAINT, so we use DO block
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_species_family' 
        AND table_name = 'species'
    ) THEN
        ALTER TABLE species ADD CONSTRAINT fk_species_family 
            FOREIGN KEY (family_id) REFERENCES families(id);
    END IF;
END $$;

-- Step 6: Update species table to reference families by ID
UPDATE species 
SET family_id = f.id
FROM families f
WHERE species.family = f.family_name
    AND species.family_id IS NULL;

-- Step 7: Create index on family_id for better join performance
CREATE INDEX IF NOT EXISTS idx_species_family_id ON species(family_id);

-- Step 8: Add updated_at trigger for families table
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- PostgreSQL doesn't support IF NOT EXISTS with CREATE TRIGGER, so we use DO block
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.triggers 
        WHERE trigger_name = 'update_families_updated_at' 
        AND event_object_table = 'families'
    ) THEN
        CREATE TRIGGER update_families_updated_at 
            BEFORE UPDATE ON families 
            FOR EACH ROW 
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- Step 9: Create a view that maintains backward compatibility
CREATE OR REPLACE VIEW species_with_family AS
SELECT 
    s.*,
    f.family_name as family_name_normalized,
    f.order_name as family_order,
    f.class as family_class,
    f.description as family_description
FROM species s
LEFT JOIN families f ON s.family_id = f.id;

-- Step 10: Verify the normalization
-- This query shows the family distribution after normalization
CREATE OR REPLACE VIEW family_species_count AS
SELECT 
    f.family_name,
    f.order_name,
    f.class,
    COUNT(s.id) as species_count,
    f.created_at as family_created_at
FROM families f
LEFT JOIN species s ON f.id = s.family_id
GROUP BY f.id, f.family_name, f.order_name, f.class, f.created_at
ORDER BY species_count DESC, f.family_name;

-- Step 11: Add comments for documentation
COMMENT ON TABLE families IS 'Normalized table containing unique taxonomic families';
COMMENT ON COLUMN families.family_name IS 'The scientific name of the taxonomic family';
COMMENT ON COLUMN families.order_name IS 'The taxonomic order this family belongs to';
COMMENT ON COLUMN families.class IS 'The taxonomic class this family belongs to';
COMMENT ON COLUMN families.description IS 'Optional description of the family';

COMMENT ON COLUMN species.family_id IS 'Foreign key reference to the families table';
COMMENT ON VIEW species_with_family IS 'Backward-compatible view showing species with denormalized family information';
COMMENT ON VIEW family_species_count IS 'Summary view showing species count per family';

-- Step 12: Grant appropriate permissions (adjust as needed for your setup)
-- GRANT SELECT ON families TO authenticated;
-- GRANT SELECT ON species_with_family TO authenticated;
-- GRANT SELECT ON family_species_count TO authenticated;

COMMIT;

-- Post-migration verification queries:
-- 
-- 1. Check family normalization results:
-- SELECT * FROM family_species_count ORDER BY species_count DESC;
--
-- 2. Verify all species have family_id assigned:
-- SELECT COUNT(*) as total_species, 
--        COUNT(family_id) as species_with_family_id,
--        COUNT(*) - COUNT(family_id) as missing_family_id
-- FROM species;
--
-- 3. Check for any orphaned family references:
-- SELECT s.scientific_name, s.family, s.family_id 
-- FROM species s 
-- LEFT JOIN families f ON s.family_id = f.id 
-- WHERE s.family_id IS NOT NULL AND f.id IS NULL;
--
-- 4. Compare original family names with normalized ones:
-- SELECT s.scientific_name, s.family as original_family, f.family_name as normalized_family
-- FROM species s 
-- LEFT JOIN families f ON s.family_id = f.id 
-- WHERE s.family != f.family_name OR (s.family IS NULL) != (f.family_name IS NULL);
