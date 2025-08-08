# Illegal Trade Database Migration Plan

## Overview

Plan to integrate illegal wildlife trade seizure data into the Arctic Tracker database while maintaining best practices for database architecture and referential integrity.

## Database Architecture Design

### New Tables Structure

#### 1. `illegal_trade_seizures` (Main Table)
Primary table for seizure records with foreign key to species table.

```sql
CREATE TABLE illegal_trade_seizures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    species_id UUID NOT NULL REFERENCES species(id),
    
    -- Source Information
    source_database VARCHAR(20) NOT NULL, -- 'TRAFFIC', 'LEMIS', 'CITES'
    original_record_id VARCHAR(100), -- ID from source database if available
    
    -- Seizure Details
    seizure_date DATE, -- If available from future data
    seizure_year INTEGER, -- Currently only have year info
    seizure_location VARCHAR(100), -- Country/region if available
    
    -- Product Information
    product_type_id UUID REFERENCES illegal_trade_products(id),
    product_category VARCHAR(50), -- 'dead/raw', 'live', 'processed/derived'
    quantity NUMERIC,
    unit VARCHAR(50),
    
    -- Taxonomic Information (denormalized for search)
    reported_taxon_name VARCHAR(255), -- Original name in seizure record
    gbif_id VARCHAR(50), -- GBIF taxonomic ID
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    data_source VARCHAR(255) DEFAULT 'Stringham et al. 2021',
    
    -- Indexes
    INDEX idx_species_id (species_id),
    INDEX idx_product_type (product_type_id),
    INDEX idx_year (seizure_year),
    INDEX idx_source (source_database)
);
```

#### 2. `illegal_trade_products` (Lookup Table)
Normalized product types with hierarchical categorization.

```sql
CREATE TABLE illegal_trade_products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_code VARCHAR(20) UNIQUE NOT NULL, -- e.g., 'u_id_055'
    product_name VARCHAR(100) NOT NULL, -- e.g., 'ivory product'
    product_category VARCHAR(50), -- 'ivory carvings/products'
    main_category VARCHAR(50), -- 'processed/derived'
    is_high_value BOOLEAN DEFAULT FALSE,
    
    -- Search optimization
    search_terms TEXT[], -- Array of search keywords
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### 3. `species_illegal_trade_summary` (Materialized View)
Pre-aggregated summary for performance.

```sql
CREATE MATERIALIZED VIEW species_illegal_trade_summary AS
SELECT 
    s.id as species_id,
    s.scientific_name,
    s.common_name,
    COUNT(DISTINCT its.id) as total_seizures,
    COUNT(DISTINCT its.product_type_id) as product_variety,
    ARRAY_AGG(DISTINCT itp.product_name) as product_types,
    ARRAY_AGG(DISTINCT its.source_database) as data_sources,
    MAX(its.seizure_year) as latest_seizure_year,
    MIN(its.seizure_year) as earliest_seizure_year,
    
    -- Risk scoring components
    CASE 
        WHEN COUNT(its.id) > 100 THEN 'CRITICAL'
        WHEN COUNT(its.id) > 50 THEN 'HIGH'
        WHEN COUNT(its.id) > 10 THEN 'MODERATE'
        ELSE 'LOW'
    END as seizure_risk_level,
    
    -- Conservation concern flags
    CASE 
        WHEN s.cites_appendix = 'I' AND COUNT(its.id) > 0 THEN TRUE
        ELSE FALSE
    END as appendix_i_violation,
    
    CASE 
        WHEN ia.status IN ('EN', 'CR', 'VU') AND COUNT(its.id) > 0 THEN TRUE
        ELSE FALSE
    END as threatened_species_trade

FROM species s
LEFT JOIN illegal_trade_seizures its ON s.id = its.species_id
LEFT JOIN illegal_trade_products itp ON its.product_type_id = itp.id
LEFT JOIN iucn_assessments ia ON s.id = ia.species_id AND ia.is_latest = TRUE
GROUP BY s.id, s.scientific_name, s.common_name, s.cites_appendix, ia.status;

-- Refresh strategy
CREATE INDEX idx_summary_species ON species_illegal_trade_summary(species_id);
CREATE INDEX idx_summary_risk ON species_illegal_trade_summary(seizure_risk_level);
```

#### 4. `illegal_trade_risk_scores` (Computed Table)
Advanced risk metrics combining legal and illegal trade data.

```sql
CREATE TABLE illegal_trade_risk_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    species_id UUID NOT NULL REFERENCES species(id),
    
    -- Trade volumes
    legal_trade_volume INTEGER, -- From CITES trade records
    illegal_seizure_count INTEGER, -- From seizures
    illegal_to_legal_ratio NUMERIC(5,2),
    
    -- Risk components (0-100 scale)
    volume_risk_score INTEGER, -- Based on seizure frequency
    conservation_risk_score INTEGER, -- Based on IUCN/CITES status
    product_risk_score INTEGER, -- Based on high-value products
    trend_risk_score INTEGER, -- Based on increasing/decreasing trends
    
    -- Composite score
    overall_risk_score INTEGER, -- Weighted average
    risk_category VARCHAR(20), -- 'CRITICAL', 'HIGH', 'MODERATE', 'LOW'
    
    -- Metadata
    last_calculated TIMESTAMPTZ DEFAULT NOW(),
    calculation_notes TEXT,
    
    UNIQUE(species_id)
);
```

## Data Migration Strategy

### Phase 1: Schema Creation (1 hour)
1. Create lookup table `illegal_trade_products`
2. Populate with unique product types from analysis
3. Create main `illegal_trade_seizures` table
4. Add foreign key constraints

### Phase 2: Data Loading (2-3 hours)
1. Load product types (92 unique types identified)
2. Transform and load 919 seizure records
3. Map all species_ids correctly
4. Handle taxonomic variations

### Phase 3: Summary Generation (1 hour)
1. Create materialized view for summaries
2. Calculate initial risk scores
3. Generate illegal-to-legal trade ratios
4. Create performance indexes

### Phase 4: Integration (2 hours)
1. Update species table with illegal trade flags
2. Create API endpoints for illegal trade data
3. Add triggers for automatic updates
4. Create audit trails

## Key Design Decisions

### 1. Separate Tables vs. Extended CITES Table
**Decision**: Separate tables for illegal trade
**Rationale**: 
- Different data sources and quality
- Different temporal granularity
- Maintains clean separation of legal vs illegal
- Allows independent updates

### 2. Product Normalization
**Decision**: Normalized product lookup table
**Rationale**:
- 92 product types with hierarchical categories
- Enables consistent analysis
- Supports search optimization
- Reduces redundancy

### 3. Species Mapping Strategy
**Decision**: Store both original names and species_id
**Rationale**:
- Preserves data provenance
- Handles taxonomic changes
- Enables fuzzy matching
- Maintains referential integrity

### 4. Risk Scoring
**Decision**: Separate computed risk table
**Rationale**:
- Complex calculations updated periodically
- Combines multiple data sources
- Enables trend analysis
- Performance optimization

## Implementation Checklist

### Pre-Migration
- [ ] Backup current database
- [ ] Review species mapping accuracy
- [ ] Validate all 36 species have correct IDs
- [ ] Create staging environment

### Migration Scripts Needed
1. `create_illegal_trade_schema.sql` - DDL for all tables
2. `load_illegal_products.py` - Product type loader
3. `load_illegal_seizures.py` - Main data loader
4. `calculate_risk_scores.py` - Risk calculation
5. `validate_illegal_trade.py` - Data validation

### Post-Migration
- [ ] Validate record counts (919 seizures)
- [ ] Check foreign key integrity
- [ ] Test query performance
- [ ] Update API documentation
- [ ] Create monitoring dashboards

## API Endpoints (Future)

```
GET /api/species/{id}/illegal-trade
GET /api/illegal-trade/high-risk-species
GET /api/illegal-trade/products
GET /api/illegal-trade/trends
POST /api/illegal-trade/calculate-risk
```

## Performance Considerations

1. **Indexes**: On species_id, year, product_type, risk scores
2. **Materialized Views**: For summary statistics
3. **Partitioning**: Consider by year if data grows
4. **Caching**: Risk scores updated daily/weekly

## Security & Compliance

1. **Data Sensitivity**: Some seizure data may be sensitive
2. **Access Control**: Role-based access to enforcement data
3. **Audit Trail**: Track all updates to seizure records
4. **Data Retention**: Follow enforcement agency guidelines

## Maintenance Plan

### Regular Updates
- Weekly: Refresh materialized views
- Monthly: Recalculate risk scores
- Quarterly: Review product categorization
- Annually: Full data validation

### Monitoring
- Alert on new Appendix I violations
- Track risk score changes
- Monitor high-value product trades
- Report unusual patterns

## Success Metrics

1. **Data Completeness**: 100% of seizures mapped to species
2. **Query Performance**: <100ms for species summaries
3. **Risk Accuracy**: Validated against expert assessment
4. **Integration**: Seamless with existing CITES data

## Timeline Estimate

- **Day 1**: Schema creation and setup (3 hours)
- **Day 2**: Data migration and validation (4 hours)
- **Day 3**: Integration and testing (3 hours)
- **Total**: 10-12 hours

---

**Created**: July 28, 2025  
**Purpose**: Integrate illegal wildlife trade data  
**Next Review**: Before implementation