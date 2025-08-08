-- Add Arctic Council column to countries table
-- Run this in Supabase SQL Editor

-- Add the arctic_council column
ALTER TABLE countries ADD COLUMN IF NOT EXISTS arctic_council BOOLEAN DEFAULT FALSE;

-- Update existing countries with Arctic Council status
-- Arctic Council Members (8 countries)
UPDATE countries SET arctic_council = TRUE, country_code = 'IS' WHERE country_name = 'Iceland';
UPDATE countries SET arctic_council = TRUE, country_code = 'NO' WHERE country_name = 'Norway';
UPDATE countries SET arctic_council = FALSE WHERE country_name = 'Greenland';
UPDATE countries SET arctic_council = FALSE WHERE country_name = 'Faroe Islands';

-- Insert missing Arctic Council members
INSERT INTO countries (country_name, country_code, nammco_member, arctic_council) VALUES
('Canada', 'CA', FALSE, TRUE),
('Denmark', 'DK', FALSE, TRUE),
('Finland', 'FI', FALSE, TRUE),
('Russia', 'RU', FALSE, TRUE),
('Sweden', 'SE', FALSE, TRUE),
('United States', 'US', FALSE, TRUE)
ON CONFLICT (country_name) DO UPDATE SET
    country_code = EXCLUDED.country_code,
    arctic_council = EXCLUDED.arctic_council;

-- Add some additional important countries for species range coverage
INSERT INTO countries (country_name, country_code, nammco_member, arctic_council) VALUES
('Japan', 'JP', FALSE, FALSE),
('United Kingdom', 'GB', FALSE, FALSE),
('Germany', 'DE', FALSE, FALSE),
('France', 'FR', FALSE, FALSE),
('Spain', 'ES', FALSE, FALSE),
('Netherlands', 'NL', FALSE, FALSE),
('Australia', 'AU', FALSE, FALSE),
('New Zealand', 'NZ', FALSE, FALSE),
('South Korea', 'KR', FALSE, FALSE),
('China', 'CN', FALSE, FALSE)
ON CONFLICT (country_name) DO NOTHING;

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_countries_arctic_council ON countries(arctic_council);

-- Verify the results
SELECT 
    country_name, 
    country_code, 
    nammco_member, 
    arctic_council,
    CASE 
        WHEN arctic_council AND nammco_member THEN 'Arctic Council + NAMMCO'
        WHEN arctic_council THEN 'Arctic Council'
        WHEN nammco_member THEN 'NAMMCO'
        ELSE 'Other'
    END as membership_status
FROM countries 
ORDER BY arctic_council DESC, nammco_member DESC, country_name;
