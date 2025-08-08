# Supabase MCP Server Guide for Arctic Tracker API

This guide documents how to use the Supabase MCP server for database analysis and management in the Arctic Tracker API project.

## Available Tools

The Supabase MCP server provides two main tools for database interaction:

### 1. `list_tables`
Lists all tables in the public schema of the Supabase database.

**Usage:**
```json
{
  "server_name": "supabase",
  "tool_name": "list_tables",
  "arguments": {}
}
```

### 2. `query_table`
Query rows from a specified table with optional filters and limit.

**Parameters:**
- `table` (required): Table name to query
- `filters` (optional): Equality filters as key-value pairs
- `limit` (optional): Maximum number of rows to return (1-1000)

**Usage Examples:**
```json
{
  "server_name": "supabase",
  "tool_name": "query_table",
  "arguments": {
    "table": "species",
    "limit": 10
  }
}
```

```json
{
  "server_name": "supabase",
  "tool_name": "query_table",
  "arguments": {
    "table": "species",
    "filters": {
      "class": "MAMMALIA"
    },
    "limit": 50
  }
}
```

## Database Schema Analysis

### Current Tables
Based on our analysis, the Arctic Tracker database contains:

1. **catch_records** - Fishing/hunting catch data
2. **cites_listings** - CITES conservation status listings
3. **cites_trade_records** - International trade records
4. **common_names** - Species common names in different languages
5. **conservation_measures** - Conservation actions and measures
6. **distribution_ranges** - Geographic distribution data
7. **iucn_assessments** - IUCN Red List assessments
8. **profiles** - User/researcher profiles
9. **species** - Core species taxonomic data
10. **species_threats** - Threat assessments for species
11. **species_trade_summary** - Aggregated trade data
12. **subpopulations** - Species subpopulation data
13. **timeline_events** - Historical events and milestones

### Species Table Structure
The `species` table contains the following key fields:
- `id` (UUID) - Primary key
- `scientific_name` - Binomial nomenclature
- `common_name` - Primary common name
- `kingdom`, `phylum`, `class`, `order_name` - Taxonomic hierarchy
- `family` - **Target for normalization**
- `genus`, `species_name` - Lower taxonomic levels
- `authority` - Taxonomic authority
- `sis_id` - Species Information Service ID
- Various descriptive fields (habitat, threats, etc.)

## Family Normalization Analysis

### Current State
The `family` field in the species table stores family names as text strings, leading to:
- Data redundancy
- Potential inconsistencies
- Limited ability to store family-level metadata
- Inefficient queries for family-based analysis

### Identified Families
Through database analysis, we identified these taxonomic families:

**Marine Mammals:**
- BALAENOPTERIDAE (rorqual whales)
- BALAENIDAE (right whales)
- MONODONTIDAE (beluga, narwhal)
- DELPHINIDAE (dolphins)
- PHOCOENIDAE (porpoises)
- PHYSETERIDAE (sperm whales)
- ZIPHIIDAE (beaked whales)

**Terrestrial Mammals:**
- URSIDAE (bears)
- FELIDAE (cats)
- MUSTELIDAE (otters, weasels)
- ODOBENIDAE (walrus)

**Birds:**
- FALCONIDAE (falcons)
- ACCIPITRIDAE (hawks, eagles)
- STRIGIDAE (owls)
- GRUIDAE (cranes)
- SCOLOPACIDAE (sandpipers)
- ANATIDAE (ducks, geese)
- DIOMEDEIDAE (albatrosses)

**Fish:**
- LAMNIDAE (mackerel sharks)
- CETORHINIDAE (basking sharks)
- ALOPIIDAE (thresher sharks)
- ACIPENSERIDAE (sturgeons)

**Plants:**
- CRASSULACEAE (stonecrops)

## Database Analysis Workflows

### 1. Exploring Table Structure
```bash
# List all tables
use_mcp_tool supabase list_tables

# Get sample data from species table
use_mcp_tool supabase query_table species limit=5

# Get all unique families
use_mcp_tool supabase query_table species limit=100
```

### 2. Family Distribution Analysis
```bash
# Query species by class to understand taxonomic distribution
use_mcp_tool supabase query_table species filters={"class":"MAMMALIA"} limit=50
use_mcp_tool supabase query_table species filters={"class":"AVES"} limit=50
use_mcp_tool supabase query_table species filters={"class":"CHONDRICHTHYES"} limit=20
```

### 3. Data Quality Assessment
```bash
# Check for species without family information
use_mcp_tool supabase query_table species filters={"family":null} limit=10

# Sample different families
use_mcp_tool supabase query_table species filters={"family":"BALAENOPTERIDAE"} limit=10
```

## Migration Strategy

### Phase 1: Analysis (Completed)
- ✅ Identified all existing families using MCP queries
- ✅ Analyzed taxonomic hierarchy consistency
- ✅ Created comprehensive migration script

### Phase 2: Implementation
The `migration/family_normalization.sql` script provides:

1. **families table creation** with proper constraints
2. **Data migration** from existing species.family field
3. **Foreign key relationships** between species and families
4. **Backward compatibility** through views
5. **Performance optimization** with indexes
6. **Data validation** queries

### Phase 3: Verification
Post-migration verification using MCP tools:

```bash
# Verify families table was created
use_mcp_tool supabase list_tables

# Check family distribution
use_mcp_tool supabase query_table families limit=20

# Verify species-family relationships
use_mcp_tool supabase query_table species limit=10
```

## Troubleshooting

### Common Migration Issues

#### Duplicate Key Error (23505)
**Error:** `duplicate key value violates unique constraint "families_family_name_key"`

**Cause:** This occurs when trying to insert a family that already exists in the families table, typically when:
- The migration script has been partially run before
- Some family data already exists in the database
- The script is being re-run without proper cleanup

**Solution:** The migration script has been updated to use `ON CONFLICT DO NOTHING` clause:
```sql
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
```

**Verification:** Use MCP tools to check existing families:
```bash
use_mcp_tool supabase query_table families limit=50
```

#### Missing Family References
**Issue:** Species records not properly linked to families after migration

**Diagnosis:** Check for unlinked species:
```sql
SELECT COUNT(*) as total_species, 
       COUNT(family_id) as species_with_family_id,
       COUNT(*) - COUNT(family_id) as missing_family_id
FROM species;
```

**Solution:** Re-run the family linking step:
```sql
UPDATE species 
SET family_id = f.id
FROM families f
WHERE species.family = f.family_name
    AND species.family_id IS NULL;
```

#### Case Sensitivity Issues
**Issue:** Family names with different capitalization not matching

**Diagnosis:** Look for case mismatches:
```sql
SELECT DISTINCT s.family, f.family_name
FROM species s 
LEFT JOIN families f ON UPPER(s.family) = UPPER(f.family_name)
WHERE s.family_id IS NULL AND s.family IS NOT NULL;
```

**Solution:** Normalize case during migration or update family names to match.

## Best Practices

### 1. Data Exploration
- Always start with `list_tables` to understand schema
- Use small limits (5-10) for initial data exploration
- Gradually increase limits for comprehensive analysis

### 2. Query Optimization
- Use filters to narrow down large datasets
- Leverage the 1000 row limit effectively
- Combine multiple queries for complete analysis

### 3. Migration Safety
- Test queries on small datasets first
- Use the provided verification queries
- Maintain backward compatibility with views
- Always backup data before running migrations
- Use transactions to ensure atomicity

### 4. Error Handling
- Use `IF NOT EXISTS` clauses for table creation
- Use `ON CONFLICT` clauses for data insertion
- Include comprehensive verification queries
- Plan for rollback scenarios

## Limitations

### Current MCP Server Limitations
- **Read-only access**: Cannot execute DDL/DML statements
- **No transaction support**: Cannot run migration scripts directly
- **Limited filtering**: Only equality filters supported
- **No joins**: Cannot perform complex relational queries

### Workarounds
- Use multiple queries to simulate joins
- Export data for complex analysis
- Run migration scripts through other tools (psql, Supabase dashboard)
- Use views for complex query patterns

## Future Enhancements

### Potential MCP Server Improvements
1. **Write capabilities** for data modification
2. **Complex filtering** (LIKE, IN, range queries)
3. **Join support** for relational queries
4. **Transaction support** for safe migrations
5. **Schema introspection** for detailed table structure

### Database Improvements
1. **Complete normalization** of all taxonomic levels
2. **Audit trails** for data changes
3. **Data validation** constraints
4. **Performance monitoring** for query optimization

## Conclusion

The Supabase MCP server provides valuable read-only access to the Arctic Tracker database, enabling comprehensive analysis and migration planning. While it has limitations for direct data modification, it's excellent for:

- Database exploration and documentation
- Data quality assessment
- Migration planning and verification
- Ongoing monitoring and analysis

The family normalization analysis demonstrates how MCP tools can effectively support database modernization efforts in scientific data management systems. The updated migration script with proper error handling ensures safe execution even when run multiple times or on databases with existing family data.
