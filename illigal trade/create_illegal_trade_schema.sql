-- Illegal Trade Database Schema
-- Arctic Tracker Database Extension for Wildlife Crime Data
-- Created: July 30, 2025

-- =============================================================================
-- 1. PRODUCT TYPES LOOKUP TABLE
-- =============================================================================

CREATE TABLE illegal_trade_products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_code VARCHAR(20) UNIQUE NOT NULL, -- e.g., 'u_id_055'
    product_name VARCHAR(100) NOT NULL, -- e.g., 'ivory product'
    product_category VARCHAR(50), -- e.g., 'ivory carvings/products'
    main_category VARCHAR(50), -- 'processed/derived', 'dead/raw', 'live'
    is_high_value BOOLEAN DEFAULT FALSE,
    
    -- Search optimization
    search_terms TEXT[], -- Array of search keywords
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for performance
CREATE INDEX idx_illegal_products_code ON illegal_trade_products(product_code);
CREATE INDEX idx_illegal_products_category ON illegal_trade_products(main_category);

-- =============================================================================
-- 2. MAIN SEIZURES TABLE
-- =============================================================================

CREATE TABLE illegal_trade_seizures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    species_id UUID NOT NULL,
    
    -- Source Information
    source_database VARCHAR(20) NOT NULL, -- 'TRAFFIC', 'LEMIS', 'CITES', 'WTP'
    original_record_id VARCHAR(100), -- ID from source database if available
    
    -- Seizure Details
    seizure_date DATE, -- If available from future data
    seizure_year INTEGER, -- Currently only have year info
    seizure_location VARCHAR(100), -- Country/region if available
    
    -- Product Information
    product_type_id UUID,
    product_category VARCHAR(50), -- 'dead/raw', 'live', 'processed/derived'
    quantity NUMERIC,
    unit VARCHAR(50),
    
    -- Taxonomic Information (denormalized for search)
    reported_taxon_name VARCHAR(255), -- Original name in seizure record
    gbif_id VARCHAR(50), -- GBIF taxonomic ID
    db_taxa_name_clean VARCHAR(255), -- Cleaned taxonomic name
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    data_source VARCHAR(255) DEFAULT 'Stringham et al. 2021',
    
    -- Foreign key constraints
    CONSTRAINT fk_seizures_species FOREIGN KEY (species_id) REFERENCES species(id),
    CONSTRAINT fk_seizures_product FOREIGN KEY (product_type_id) REFERENCES illegal_trade_products(id)
);

-- Performance indexes
CREATE INDEX idx_seizures_species_id ON illegal_trade_seizures(species_id);
CREATE INDEX idx_seizures_product_type ON illegal_trade_seizures(product_type_id);
CREATE INDEX idx_seizures_year ON illegal_trade_seizures(seizure_year);
CREATE INDEX idx_seizures_source ON illegal_trade_seizures(source_database);
CREATE INDEX idx_seizures_category ON illegal_trade_seizures(product_category);

-- =============================================================================
-- 3. RISK SCORES TABLE
-- =============================================================================

CREATE TABLE illegal_trade_risk_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    species_id UUID NOT NULL,
    
    -- Trade volumes
    legal_trade_volume INTEGER, -- From CITES trade records
    illegal_seizure_count INTEGER, -- From seizures
    illegal_to_legal_ratio NUMERIC(5,2),
    
    -- Risk components (0-100 scale)
    volume_risk_score INTEGER DEFAULT 0, -- Based on seizure frequency
    conservation_risk_score INTEGER DEFAULT 0, -- Based on IUCN/CITES status
    product_risk_score INTEGER DEFAULT 0, -- Based on high-value products
    trend_risk_score INTEGER DEFAULT 0, -- Based on increasing/decreasing trends
    
    -- Composite score
    overall_risk_score INTEGER DEFAULT 0, -- Weighted average
    risk_category VARCHAR(20) DEFAULT 'LOW', -- 'CRITICAL', 'HIGH', 'MODERATE', 'LOW'
    
    -- Metadata
    last_calculated TIMESTAMPTZ DEFAULT NOW(),
    calculation_notes TEXT,
    
    -- Foreign key and unique constraint
    CONSTRAINT fk_risk_species FOREIGN KEY (species_id) REFERENCES species(id),
    CONSTRAINT uq_risk_per_species UNIQUE(species_id)
);

-- Index for risk queries
CREATE INDEX idx_risk_species ON illegal_trade_risk_scores(species_id);
CREATE INDEX idx_risk_category ON illegal_trade_risk_scores(risk_category);
CREATE INDEX idx_risk_score ON illegal_trade_risk_scores(overall_risk_score);

-- =============================================================================
-- 4. SUMMARY MATERIALIZED VIEW
-- =============================================================================

CREATE MATERIALIZED VIEW species_illegal_trade_summary AS
SELECT 
    s.id as species_id,
    s.scientific_name,
    s.common_name,
    s.cites_appendix,
    
    -- Seizure statistics
    COUNT(DISTINCT its.id) as total_seizures,
    COUNT(DISTINCT its.product_type_id) as product_variety,
    ARRAY_AGG(DISTINCT itp.product_name ORDER BY itp.product_name) FILTER (WHERE itp.product_name IS NOT NULL) as product_types,
    ARRAY_AGG(DISTINCT its.source_database ORDER BY its.source_database) as data_sources,
    
    -- Temporal data
    MAX(its.seizure_year) as latest_seizure_year,
    MIN(its.seizure_year) as earliest_seizure_year,
    
    -- Risk classification
    CASE 
        WHEN COUNT(its.id) > 100 THEN 'CRITICAL'
        WHEN COUNT(its.id) > 50 THEN 'HIGH'
        WHEN COUNT(its.id) > 10 THEN 'MODERATE'
        WHEN COUNT(its.id) > 0 THEN 'LOW'
        ELSE 'NONE'
    END as seizure_risk_level,
    
    -- Conservation concern flags
    CASE 
        WHEN s.cites_appendix = 'I' AND COUNT(its.id) > 0 THEN TRUE
        ELSE FALSE
    END as appendix_i_violation,
    
    CASE 
        WHEN ia.status IN ('EN', 'CR', 'VU') AND COUNT(its.id) > 0 THEN TRUE
        ELSE FALSE
    END as threatened_species_trade,
    
    -- Last updated
    NOW() as summary_updated_at

FROM species s
LEFT JOIN illegal_trade_seizures its ON s.id = its.species_id
LEFT JOIN illegal_trade_products itp ON its.product_type_id = itp.id
LEFT JOIN iucn_assessments ia ON s.id = ia.species_id AND ia.is_latest = TRUE
GROUP BY s.id, s.scientific_name, s.common_name, s.cites_appendix, ia.status;

-- Indexes for materialized view
CREATE INDEX idx_summary_species_id ON species_illegal_trade_summary(species_id);
CREATE INDEX idx_summary_risk_level ON species_illegal_trade_summary(seizure_risk_level);
CREATE INDEX idx_summary_appendix_violation ON species_illegal_trade_summary(appendix_i_violation);
CREATE INDEX idx_summary_threatened_trade ON species_illegal_trade_summary(threatened_species_trade);

-- =============================================================================
-- 5. TRIGGERS FOR DATA CONSISTENCY
-- =============================================================================

-- Update timestamp trigger for products
CREATE OR REPLACE FUNCTION update_illegal_products_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trigger_update_illegal_products_timestamp
    BEFORE UPDATE ON illegal_trade_products
    FOR EACH ROW
    EXECUTE FUNCTION update_illegal_products_timestamp();

-- Update timestamp trigger for seizures
CREATE OR REPLACE FUNCTION update_illegal_seizures_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trigger_update_illegal_seizures_timestamp
    BEFORE UPDATE ON illegal_trade_seizures
    FOR EACH ROW
    EXECUTE FUNCTION update_illegal_seizures_timestamp();

-- =============================================================================
-- 6. REFRESH FUNCTION FOR MATERIALIZED VIEW
-- =============================================================================

CREATE OR REPLACE FUNCTION refresh_illegal_trade_summary()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY species_illegal_trade_summary;
END;
$$ language 'plpgsql';

-- =============================================================================
-- 7. COMMENTS FOR DOCUMENTATION
-- =============================================================================

COMMENT ON TABLE illegal_trade_products IS 'Lookup table for standardized product types found in illegal wildlife trade';
COMMENT ON TABLE illegal_trade_seizures IS 'Main table storing wildlife crime seizure records mapped to Arctic species';
COMMENT ON TABLE illegal_trade_risk_scores IS 'Computed risk scores combining legal and illegal trade indicators';
COMMENT ON MATERIALIZED VIEW species_illegal_trade_summary IS 'Pre-computed summary statistics for species illegal trade activity';

COMMENT ON COLUMN illegal_trade_seizures.species_id IS 'Foreign key to species table - Arctic species involved in seizure';
COMMENT ON COLUMN illegal_trade_seizures.source_database IS 'Original data source: WTP (Wildlife Trade Portal), TRAFFIC, LEMIS, etc.';
COMMENT ON COLUMN illegal_trade_seizures.reported_taxon_name IS 'Original taxonomic name as reported in seizure record';
COMMENT ON COLUMN illegal_trade_seizures.gbif_id IS 'GBIF taxonomic identifier for reported taxon';

-- =============================================================================
-- 8. INITIAL DATA VALIDATION CONSTRAINTS
-- =============================================================================

-- Ensure risk scores are within valid ranges
ALTER TABLE illegal_trade_risk_scores 
    ADD CONSTRAINT chk_volume_risk_range CHECK (volume_risk_score >= 0 AND volume_risk_score <= 100);
ALTER TABLE illegal_trade_risk_scores 
    ADD CONSTRAINT chk_conservation_risk_range CHECK (conservation_risk_score >= 0 AND conservation_risk_score <= 100);
ALTER TABLE illegal_trade_risk_scores 
    ADD CONSTRAINT chk_product_risk_range CHECK (product_risk_score >= 0 AND product_risk_score <= 100);
ALTER TABLE illegal_trade_risk_scores 
    ADD CONSTRAINT chk_trend_risk_range CHECK (trend_risk_score >= 0 AND trend_risk_score <= 100);
ALTER TABLE illegal_trade_risk_scores 
    ADD CONSTRAINT chk_overall_risk_range CHECK (overall_risk_score >= 0 AND overall_risk_score <= 100);

-- Ensure valid risk categories
ALTER TABLE illegal_trade_risk_scores 
    ADD CONSTRAINT chk_risk_category CHECK (risk_category IN ('CRITICAL', 'HIGH', 'MODERATE', 'LOW'));

-- Ensure valid product categories
ALTER TABLE illegal_trade_seizures 
    ADD CONSTRAINT chk_product_category CHECK (product_category IN ('dead/raw', 'live', 'processed/derived'));

-- =============================================================================
-- SCHEMA CREATION COMPLETE
-- =============================================================================

-- Grant permissions (adjust as needed)
-- GRANT SELECT ON illegal_trade_products TO readonly_role;
-- GRANT SELECT ON illegal_trade_seizures TO readonly_role;
-- GRANT SELECT ON species_illegal_trade_summary TO readonly_role;
-- GRANT SELECT ON illegal_trade_risk_scores TO readonly_role;