-- Arctic Tracker Database Schema Updates for NAMMCO Data Import
-- Run this before importing CSV data

-- ORDER OF OPERATIONS: countries -> management_areas -> catch_records columns -> data insert -> views.

-- 1. Create countries table first
CREATE TABLE IF NOT EXISTS countries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    country_name VARCHAR(100) UNIQUE NOT NULL,
    country_code VARCHAR(3),
    nammco_member BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 2. Create management_areas table (references countries)
CREATE TABLE IF NOT EXISTS management_areas (
    id SERIAL PRIMARY KEY,
    area_name VARCHAR(200) NOT NULL,
    country_id UUID REFERENCES countries(id),
    area_type VARCHAR(50),
    parent_area_id INTEGER REFERENCES management_areas(id),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(area_name, country_id)
);

-- 3. Add new columns to catch_records (after referenced tables exist)
ALTER TABLE catch_records 
ADD COLUMN IF NOT EXISTS country_id UUID REFERENCES countries(id),
ADD COLUMN IF NOT EXISTS management_area_id INTEGER REFERENCES management_areas(id),
ADD COLUMN IF NOT EXISTS data_source VARCHAR(50) DEFAULT 'NAMMCO',
ADD COLUMN IF NOT EXISTS quota_amount INTEGER,
ADD COLUMN IF NOT EXISTS quota_notes TEXT,
ADD COLUMN IF NOT EXISTS notes TEXT,
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();

-- 4. Insert NAMMCO member countries
INSERT INTO countries (country_name, nammco_member) VALUES
('Greenland', TRUE),
('Norway', TRUE),
('Iceland', TRUE),
('Faroe Islands', TRUE)
ON CONFLICT (country_name) DO UPDATE SET nammco_member = EXCLUDED.nammco_member;

-- 5. Create views (using scientific_name for species)
DROP VIEW IF EXISTS nammco_catch_summary;
CREATE OR REPLACE VIEW nammco_catch_summary AS
SELECT 
    s.scientific_name as species_name,
    c.country_name,
    ma.area_name,
    cr.year,
    cr.catch_total,
    cr.quota_amount,
    cr.quota_notes
FROM catch_records cr
JOIN species s ON cr.species_id = s.id
JOIN countries c ON cr.country_id = c.id
LEFT JOIN management_areas ma ON cr.management_area_id = ma.id
WHERE cr.data_source = 'NAMMCO'
ORDER BY s.scientific_name, c.country_name, cr.year;

DROP VIEW IF EXISTS nammco_species_totals;
CREATE OR REPLACE VIEW nammco_species_totals AS
SELECT 
    s.scientific_name as species_name,
    c.country_name,
    COUNT(*) as record_count,
    SUM(cr.catch_total) as total_catch,
    MIN(cr.year) as earliest_year,
    MAX(cr.year) as latest_year
FROM catch_records cr
JOIN species s ON cr.species_id = s.id
JOIN countries c ON cr.country_id = c.id
WHERE cr.data_source = 'NAMMCO'
GROUP BY s.scientific_name, c.country_name
ORDER BY total_catch DESC;

-- 6. Update existing country data if country column exists and is populated
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'catch_records' AND column_name = 'country'
    ) THEN
        -- Update country_id based on existing country names
        UPDATE catch_records SET country_id = c.id 
        FROM countries c 
        WHERE catch_records.country = c.country_name
        AND catch_records.country_id IS NULL;
    END IF;
END $$;

-- 7. Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_catch_records_species_year ON catch_records(species_id, year);
CREATE INDEX IF NOT EXISTS idx_catch_records_country_year ON catch_records(country_id, year);
CREATE INDEX IF NOT EXISTS idx_catch_records_country_id ON catch_records(country_id);
CREATE INDEX IF NOT EXISTS idx_catch_records_area_id ON catch_records(management_area_id);
CREATE INDEX IF NOT EXISTS idx_catch_records_data_source ON catch_records(data_source);
CREATE INDEX IF NOT EXISTS idx_management_areas_country ON management_areas(country_id);
CREATE INDEX IF NOT EXISTS idx_management_areas_name ON management_areas(area_name);

-- 8. Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_catch_records_updated_at 
    BEFORE UPDATE ON catch_records 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- 9. Grant permissions (adjust as needed for your user)
-- GRANT SELECT, INSERT, UPDATE ON catch_records TO your_app_user;
-- GRANT SELECT, INSERT, UPDATE ON countries TO your_app_user;
-- GRANT SELECT, INSERT, UPDATE ON management_areas TO your_app_user;
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO your_app_user;

COMMENT ON TABLE countries IS 'Countries involved in NAMMCO marine mammal catch reporting';
COMMENT ON TABLE management_areas IS 'Management areas/zones/regions for marine mammal populations';
COMMENT ON COLUMN catch_records.data_source IS 'Source of the catch data (NAMMCO, etc.)';
COMMENT ON COLUMN catch_records.quota_amount IS 'Catch quota amount if applicable';
COMMENT ON COLUMN catch_records.quota_notes IS 'Notes about quota status (No quota, etc.)';

-- Success message
SELECT 'Arctic Tracker database schema updated for NAMMCO data import' AS status;
