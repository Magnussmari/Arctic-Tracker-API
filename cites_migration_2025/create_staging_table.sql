-- Create Staging Table for CITES Migration
-- Arctic Tracker - CITES v2025.1 Migration
-- 
-- This creates a staging table identical to cites_trade_records
-- for safe data loading and validation before the final migration.

-- Drop staging table if it exists
DROP TABLE IF EXISTS cites_trade_records_staging;

-- Create staging table with identical structure to production
CREATE TABLE cites_trade_records_staging (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    species_id UUID NOT NULL,
    
    -- Trade Information
    year INTEGER NOT NULL,
    appendix VARCHAR(10),
    taxon TEXT NOT NULL,
    class VARCHAR(50),
    order_name VARCHAR(50),
    family VARCHAR(50),
    genus VARCHAR(50),
    
    -- Trade Details
    importer VARCHAR(100),
    exporter VARCHAR(100),
    origin VARCHAR(100),
    importer_reported_quantity NUMERIC,
    exporter_reported_quantity NUMERIC,
    term VARCHAR(50),
    unit VARCHAR(50),
    purpose VARCHAR(10),
    source VARCHAR(10),
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    data_source VARCHAR(100) DEFAULT 'CITES v2025.1',
    
    -- Constraints
    CONSTRAINT fk_staging_species FOREIGN KEY (species_id) REFERENCES species(id),
    CONSTRAINT chk_staging_year CHECK (year BETWEEN 1900 AND 2030),
    CONSTRAINT chk_staging_appendix CHECK (appendix IN ('I', 'II', 'III', 'N'))
);

-- Create indexes for performance during staging operations
CREATE INDEX idx_staging_species_id ON cites_trade_records_staging(species_id);
CREATE INDEX idx_staging_year ON cites_trade_records_staging(year);
CREATE INDEX idx_staging_appendix ON cites_trade_records_staging(appendix);
CREATE INDEX idx_staging_taxon ON cites_trade_records_staging(taxon);
CREATE INDEX idx_staging_importer ON cites_trade_records_staging(importer);
CREATE INDEX idx_staging_exporter ON cites_trade_records_staging(exporter);

-- Add comments for documentation
COMMENT ON TABLE cites_trade_records_staging IS 'Staging table for CITES v2025.1 migration - temporary table for data validation';
COMMENT ON COLUMN cites_trade_records_staging.species_id IS 'Foreign key to Arctic species in species table';
COMMENT ON COLUMN cites_trade_records_staging.data_source IS 'Set to CITES v2025.1 for new migration data';

-- Create staging summary view for validation
CREATE OR REPLACE VIEW cites_staging_summary AS
SELECT 
    COUNT(*) as total_records,
    COUNT(DISTINCT species_id) as unique_species,
    MIN(year) as earliest_year,
    MAX(year) as latest_year,
    COUNT(*) FILTER (WHERE appendix = 'I') as appendix_i_count,
    COUNT(*) FILTER (WHERE appendix = 'II') as appendix_ii_count,
    COUNT(*) FILTER (WHERE appendix = 'III') as appendix_iii_count,
    COUNT(DISTINCT importer) as unique_importers,
    COUNT(DISTINCT exporter) as unique_exporters,
    SUM(CASE WHEN importer_reported_quantity IS NOT NULL THEN importer_reported_quantity ELSE 0 END) as total_importer_quantity,
    SUM(CASE WHEN exporter_reported_quantity IS NOT NULL THEN exporter_reported_quantity ELSE 0 END) as total_exporter_quantity
FROM cites_trade_records_staging;

COMMENT ON VIEW cites_staging_summary IS 'Summary statistics for staging table validation';

-- Grant appropriate permissions
-- GRANT SELECT, INSERT, UPDATE, DELETE ON cites_trade_records_staging TO migration_role;
-- GRANT SELECT ON cites_staging_summary TO migration_role;