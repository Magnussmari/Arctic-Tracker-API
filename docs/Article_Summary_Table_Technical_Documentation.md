# Article Summary Table Technical Documentation

<table_documentation>

<overview>
The `article_summary_table` is a master aggregation table that serves as the foundation for scientific analysis of Arctic wildlife trade patterns and conservation implications. This pre-computed table consolidates complex data from multiple sources to provide a comprehensive view of each Arctic species' trade history, conservation status, and geographic patterns. It is designed to power research visualizations, statistical analyses, and policy recommendations regarding the international trade of Arctic species under CITES regulations.

**Purpose**: To provide researchers, policymakers, and conservationists with a single, authoritative source for understanding the complete trade and conservation profile of Arctic species without requiring complex multi-table joins or real-time calculations.

**Data Refresh**: Updated weekly via automated ETL pipeline
**Last Update**: Tracked in `last_updated` column for each record
**Primary Key**: `id` (UUID)
**Foreign Key**: `species_id` references `species.id`
</overview>

<columns>

<column name="id">
<description>Unique identifier for each summary record</description>
<data_type>uuid</data_type>
<calculation>System-generated UUID</calculation>
<source>Generated during record creation</source>
<example>ae4cda1c-4e2d-4600-a7d1-26097065f3f0</example>
<notes>Immutable primary key</notes>
</column>

<column name="species_id">
<description>Reference to the species being summarized</description>
<data_type>uuid</data_type>
<calculation>Direct reference</calculation>
<source>species.id</source>
<example>01648df8-41bf-4fc2-97ec-563565d7a6e4 (Orcinus orca)</example>
<notes>Foreign key constraint ensures referential integrity</notes>
</column>

<column name="trade_records_count">
<description>Total number of CITES trade records for this species across all years</description>
<data_type>integer</data_type>
<calculation>COUNT(*) of matching records in cites_trade_records</calculation>
<source>cites_trade_records table</source>
<example>951 (indicates 951 separate trade transactions recorded)</example>
<notes>Includes all trade types, purposes, and origins</notes>
</column>

<column name="total_quantity">
<description>Cumulative quantity of specimens traded, standardized to whole organism equivalents where possible</description>
<data_type>numeric(12,2)</data_type>
<calculation>SUM(quantity) with unit standardization applied</calculation>
<source>cites_trade_records.quantity</source>
<example>17674.63 (could represent individuals, kg, or other units depending on specimen type)</example>
<notes>Mixed units are preserved; interpretation requires checking specimen types</notes>
</column>

<column name="most_recorded_trade_use">
<description>The most frequent CITES purpose code across all trade records</description>
<data_type>text</data_type>
<calculation>MODE() of purpose codes, weighted by record count</calculation>
<source>cites_trade_records.purpose</source>
<example>S (Scientific), T (Commercial), B (Breeding), P (Personal), H (Hunting trophy)</example>
<notes>CITES standard purpose codes; ties broken by most recent usage</notes>
</column>

<column name="trade_use_percentage">
<description>Percentage of trade records attributed to the most common purpose</description>
<data_type>numeric(5,2)</data_type>
<calculation>(COUNT of most_recorded_trade_use / trade_records_count) * 100</calculation>
<source>Derived from cites_trade_records.purpose</source>
<example>54.89 (means 54.89% of all trade records were for scientific purposes)</example>
<notes>Based on record count, not quantity; rounded to 2 decimal places</notes>
</column>

<column name="wild_origin_count">
<description>Number of trade records involving specimens taken from the wild</description>
<data_type>integer</data_type>
<calculation>COUNT(*) WHERE source IN ('W', 'X', 'R')</calculation>
<source>cites_trade_records.source</source>
<example>762 (wild-sourced specimen records)</example>
<notes>W=Wild, X=Unknown wild, R=Ranched; excludes captive-bred</notes>
</column>

<column name="pre_convention_count">
<description>Number of trade records for specimens acquired before CITES listing</description>
<data_type>integer</data_type>
<calculation>COUNT(*) WHERE source = 'O'</calculation>
<source>cites_trade_records.source</source>
<example>51 (pre-Convention specimens)</example>
<notes>O=Pre-Convention; important for antique trade analysis</notes>
</column>

<column name="period_start_year">
<description>First year with recorded CITES trade data for this species</description>
<data_type>integer</data_type>
<calculation>MIN(year) from trade records</calculation>
<source>cites_trade_records.year</source>
<example>1980 (earliest trade record)</example>
<notes>Null if no trade records exist</notes>
</column>

<column name="period_end_year">
<description>Most recent year with recorded CITES trade data</description>
<data_type>integer</data_type>
<calculation>MAX(year) from trade records</calculation>
<source>cites_trade_records.year</source>
<example>2023 (latest trade record)</example>
<notes>Updated annually as new CITES data becomes available</notes>
</column>

<column name="last_recorded_quantity">
<description>Quantity traded in the most recent year of activity</description>
<data_type>numeric</data_type>
<calculation>SUM(quantity) WHERE year = period_end_year</calculation>
<source>cites_trade_records.quantity</source>
<example>192 (specimens traded in 2023)</example>
<notes>Useful for assessing current trade levels</notes>
</column>

<column name="last_recorded_year">
<description>The most recent year with any trade activity</description>
<data_type>integer</data_type>
<calculation>MAX(year) WHERE quantity > 0</calculation>
<source>cites_trade_records.year</source>
<example>2023</example>
<notes>Same as period_end_year in most cases</notes>
</column>

<column name="trade_trend">
<description>Statistical trend in trade volume over the most recent 10-year period</description>
<data_type>text</data_type>
<calculation>Linear regression slope analysis with significance testing</calculation>
<source>Derived from annual trade quantities</source>
<example>"stable", "increasing", "decreasing"</example>
<notes>P-value threshold 0.05; "stable" if non-significant</notes>
</column>

<column name="cites_suspensions_count">
<description>Number of active CITES trade suspensions affecting this species</description>
<data_type>integer</data_type>
<calculation>COUNT(*) of active suspensions</calculation>
<source>cites_trade_suspensions table</source>
<example>0 (no current suspensions)</example>
<notes>Only counts currently active suspensions</notes>
</column>

<column name="cites_suspension_states">
<description>Array of country codes with active CITES trade suspensions</description>
<data_type>text[]</data_type>
<calculation>ARRAY_AGG(country_code) WHERE suspension active</calculation>
<source>cites_trade_suspensions.country</source>
<example>[] (empty array) or ["MG", "TZ"] (Madagascar, Tanzania)</example>
<notes>ISO 3166-1 alpha-2 country codes</notes>
</column>

<column name="iucn_status_current">
<description>Current IUCN Red List conservation status</description>
<data_type>text</data_type>
<calculation>Most recent assessment status</calculation>
<source>iucn_assessments.red_list_category</source>
<example>DD (Data Deficient), LC (Least Concern), NT (Near Threatened), VU (Vulnerable)</example>
<notes>Uses standard IUCN categories; null if never assessed</notes>
</column>

<column name="cites_status_current">
<description>Current CITES Appendix listing</description>
<data_type>text</data_type>
<calculation>Current effective listing</calculation>
<source>cites_listings.appendix</source>
<example>I (most restrictive), II (regulated trade), III (cooperation needed)</example>
<notes>Roman numerals per CITES convention</notes>
</column>

<column name="cms_status_current">
<description>Current CMS (Convention on Migratory Species) Appendix listing</description>
<data_type>text</data_type>
<calculation>Current effective CMS listing</calculation>
<source>cms_listings.appendix</source>
<example>I (endangered), II (conservation agreements needed), null (not listed)</example>
<notes>Relevant for migratory Arctic species</notes>
</column>

<column name="iucn_status_change">
<description>Type of change in IUCN status over assessment history</description>
<data_type>text</data_type>
<calculation>Comparison of first vs current assessment</calculation>
<source>Historical iucn_assessments analysis</source>
<example>"no_change", "new_listing", "uplisted", "downlisted"</example>
<notes>Tracks conservation trajectory; "new_listing" for first assessment</notes>
</column>

<column name="cites_status_change">
<description>Type of change in CITES listing over time</description>
<data_type>text</data_type>
<calculation>Comparison of initial vs current listing</calculation>
<source>Historical cites_listings analysis</source>
<example>"new_listing", "no_change", "uplisted", "downlisted"</example>
<notes>"new_listing" indicates species added to CITES after 1975</notes>
</column>

<column name="cms_status_change">
<description>Type of change in CMS listing status</description>
<data_type>text</data_type>
<calculation>Comparison of initial vs current CMS listing</calculation>
<source>Historical cms_listings analysis</source>
<example>"new_listing", "no_change", null (never listed)</example>
<notes>Null for species not covered by CMS</notes>
</column>

<column name="top_arctic_exporter">
<description>Arctic country with highest trade volume by record count</description>
<data_type>text</data_type>
<calculation>MODE(exporter) WHERE exporter IN Arctic countries</calculation>
<source>cites_trade_records.exporter</source>
<example>GL (Greenland), CA (Canada), RU (Russia), US (Alaska), NO (Norway)</example>
<notes>ISO country codes; Arctic countries predefined list</notes>
</column>

<column name="top_arctic_exporter_percentage">
<description>Percentage of total trade records from the top Arctic exporter</description>
<data_type>numeric(5,2)</data_type>
<calculation>(Arctic exporter record count / total records) * 100</calculation>
<source>Derived from trade records analysis</source>
<example>25.66 (means 25.66% of all trade records from Greenland)</example>
<notes>Based on record count, not quantity</notes>
</column>

<column name="top_global_exporter">
<description>Country with highest trade volume globally</description>
<data_type>text</data_type>
<calculation>MODE(exporter) across all records</calculation>
<source>cites_trade_records.exporter</source>
<example>CA (Canada), NL (Netherlands), US (United States)</example>
<notes>May differ from Arctic exporter if non-Arctic trade dominates</notes>
</column>

<column name="top_global_exporter_percentage">
<description>Percentage of total trade records from the top global exporter</description>
<data_type>numeric(5,2)</data_type>
<calculation>(Top exporter record count / total records) * 100</calculation>
<source>Derived from trade records analysis</source>
<example>75.44 (means 75.44% of all trade from Canada)</example>
<notes>Indicates trade concentration; high values suggest limited sources</notes>
</column>

<column name="last_updated">
<description>Timestamp of most recent data refresh for this record</description>
<data_type>timestamp with time zone</data_type>
<calculation>System timestamp at ETL completion</calculation>
<source>ETL process metadata</source>
<example>2025-07-31T14:54:27.689608+00:00</example>
<notes>UTC timezone; used for data freshness validation</notes>
</column>

<column name="created_at">
<description>Initial creation timestamp of this summary record</description>
<data_type>timestamp with time zone</data_type>
<calculation>System timestamp at record creation</calculation>
<source>Database trigger</source>
<example>2025-07-31T14:26:45.465669+00:00</example>
<notes>Immutable; tracks when species first added to summary</notes>
</column>

</columns>

<methodologies>

<methodology name="trade_trend_calculation">
<formula>
Linear regression: quantity = β₀ + β₁(year) + ε
where β₁ slope determines trend direction
</formula>
<steps>
1. Extract annual trade quantities for most recent 10 years
2. Apply linear regression to (year, quantity) pairs
3. Calculate slope coefficient (β₁) and p-value
4. Classify trend:
   - "increasing" if β₁ > 0 and p < 0.05
   - "decreasing" if β₁ < 0 and p < 0.05
   - "stable" if p ≥ 0.05 (non-significant)
</steps>
<edge_cases>
- Less than 3 years of data: return "insufficient_data"
- All quantities zero: return "no_trade"
- Single year spike: use median absolute deviation filter
</edge_cases>
</methodology>

<methodology name="quantity_standardization">
<formula>
Standardized_quantity = raw_quantity * conversion_factor
Conversion factors vary by specimen_type and unit
</formula>
<steps>
1. Identify specimen type from trade record
2. Apply standardization rules:
   - Live specimens (LIV): count as is
   - Skins (SKI): multiply by 1
   - Meat (MEA): convert kg to estimated individuals
   - Parts (BOD, SKU): aggregate to whole organism equivalents
3. Sum standardized quantities
</steps>
<edge_cases>
- Unknown units: preserve raw quantity
- Mixed specimen types: maintain separate tallies
- Scientific samples: minimal quantity (0.01)
</edge_cases>
</methodology>

<methodology name="exporter_ranking">
<formula>
Exporter_percentage = (exporter_record_count / total_records) * 100
Rank by percentage descending
</formula>
<steps>
1. Group trade records by exporter country code
2. Count records per exporter (not quantity)
3. Calculate percentage of total for each
4. For Arctic: filter by predefined Arctic countries list
5. Select top exporter by percentage
</steps>
<edge_cases>
- Tie breaking: most recent year of trade wins
- Re-exports: use original source country if available
- Unknown exporter: exclude from calculations
</edge_cases>
</methodology>

<methodology name="conservation_status_change_detection">
<formula>
Compare first_known_status with current_status
Map transitions to categories
</formula>
<steps>
1. Query historical assessment/listing data
2. Identify earliest and most recent statuses
3. Apply change categories:
   - "new_listing": no prior status exists
   - "uplisted": moved to more threatened category
   - "downlisted": moved to less threatened category
   - "no_change": same category maintained
4. Handle status systems separately (IUCN, CITES, CMS)
</steps>
<edge_cases>
- Multiple assessments same year: use most recent
- Gap in assessments: compare endpoints only
- Regional vs global assessments: prioritize global
</edge_cases>
</methodology>

</methodologies>

<sql_examples>

<query purpose="Generate trade trend analysis for a species">
```sql
WITH annual_trade AS (
  SELECT 
    year,
    SUM(quantity) as annual_quantity
  FROM cites_trade_records
  WHERE species_id = '01648df8-41bf-4fc2-97ec-563565d7a6e4'
    AND year >= EXTRACT(YEAR FROM CURRENT_DATE) - 10
  GROUP BY year
  ORDER BY year
),
regression_calc AS (
  SELECT 
    regr_slope(annual_quantity, year) as slope,
    regr_r2(annual_quantity, year) as r_squared,
    COUNT(*) as data_points
  FROM annual_trade
)
SELECT 
  CASE 
    WHEN data_points < 3 THEN 'insufficient_data'
    WHEN slope > 0 AND r_squared > 0.3 THEN 'increasing'
    WHEN slope < 0 AND r_squared > 0.3 THEN 'decreasing'
    ELSE 'stable'
  END as trade_trend
FROM regression_calc;
```
</query>

<query purpose="Calculate trade purpose distribution">
```sql
SELECT 
  purpose,
  COUNT(*) as record_count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM cites_trade_records
WHERE species_id = '01648df8-41bf-4fc2-97ec-563565d7a6e4'
GROUP BY purpose
ORDER BY record_count DESC;
```
</query>

<query purpose="Identify top exporters with Arctic filtering">
```sql
WITH exporter_stats AS (
  SELECT 
    exporter,
    COUNT(*) as export_count,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as percentage
  FROM cites_trade_records
  WHERE species_id = '01648df8-41bf-4fc2-97ec-563565d7a6e4'
  GROUP BY exporter
),
arctic_countries AS (
  SELECT * FROM (VALUES ('CA'), ('GL'), ('US'), ('RU'), ('NO'), ('IS'), ('FI'), ('SE')) AS t(code)
)
SELECT 
  e.exporter as top_arctic_exporter,
  ROUND(e.percentage, 2) as top_arctic_exporter_percentage
FROM exporter_stats e
JOIN arctic_countries a ON e.exporter = a.code
ORDER BY e.percentage DESC
LIMIT 1;
```
</query>

<query purpose="Track conservation status changes over time">
```sql
WITH status_history AS (
  SELECT 
    species_id,
    red_list_category,
    assessment_date,
    ROW_NUMBER() OVER (PARTITION BY species_id ORDER BY assessment_date) as rn,
    ROW_NUMBER() OVER (PARTITION BY species_id ORDER BY assessment_date DESC) as rn_desc
  FROM iucn_assessments
  WHERE species_id = '01648df8-41bf-4fc2-97ec-563565d7a6e4'
)
SELECT 
  first.red_list_category as first_status,
  latest.red_list_category as current_status,
  CASE
    WHEN first.red_list_category IS NULL THEN 'new_listing'
    WHEN first.red_list_category = latest.red_list_category THEN 'no_change'
    WHEN latest.red_list_category IN ('CR', 'EN') AND first.red_list_category NOT IN ('CR', 'EN') THEN 'uplisted'
    WHEN first.red_list_category IN ('CR', 'EN') AND latest.red_list_category NOT IN ('CR', 'EN') THEN 'downlisted'
    ELSE 'changed'
  END as status_change
FROM status_history first
JOIN status_history latest ON first.species_id = latest.species_id
WHERE first.rn = 1 AND latest.rn_desc = 1;
```
</query>

<query purpose="Complete summary table refresh for a species">
```sql
INSERT INTO article_summary_table (
  species_id,
  trade_records_count,
  total_quantity,
  most_recorded_trade_use,
  trade_use_percentage,
  wild_origin_count,
  pre_convention_count,
  period_start_year,
  period_end_year,
  last_recorded_quantity,
  last_recorded_year,
  trade_trend,
  cites_suspensions_count,
  cites_suspension_states,
  iucn_status_current,
  cites_status_current,
  cms_status_current,
  iucn_status_change,
  cites_status_change,
  cms_status_change,
  top_arctic_exporter,
  top_arctic_exporter_percentage,
  top_global_exporter,
  top_global_exporter_percentage,
  last_updated
)
SELECT 
  s.id as species_id,
  -- Trade metrics
  COUNT(DISTINCT t.id) as trade_records_count,
  COALESCE(SUM(t.quantity), 0) as total_quantity,
  MODE() WITHIN GROUP (ORDER BY t.purpose) as most_recorded_trade_use,
  -- [Additional complex calculations as shown above]
  -- ...
  CURRENT_TIMESTAMP as last_updated
FROM species s
LEFT JOIN cites_trade_records t ON s.id = t.species_id
LEFT JOIN iucn_assessments ia ON s.id = ia.species_id
LEFT JOIN cites_listings cl ON s.id = cl.species_id
LEFT JOIN cms_listings cm ON s.id = cm.species_id
WHERE s.id = '01648df8-41bf-4fc2-97ec-563565d7a6e4'
GROUP BY s.id
ON CONFLICT (species_id) 
DO UPDATE SET 
  trade_records_count = EXCLUDED.trade_records_count,
  -- ... all other fields
  last_updated = EXCLUDED.last_updated;
```
</query>

</sql_examples>

<data_quality_notes>

## Known Limitations

1. **Quantity Standardization**: Different specimen types use different units (individuals, kg, m³, etc.). The total_quantity field aggregates these without perfect standardization, requiring careful interpretation.

2. **Trade Trend Analysis**: Based on 10-year window which may miss longer-term patterns. Seasonal variations not accounted for in annual aggregation.

3. **Geographic Coverage**: "Arctic exporter" classification based on political boundaries, not species range. Some Arctic species traded from non-Arctic range states.

4. **Temporal Gaps**: CITES trade data may have reporting delays of 1-2 years. Recent years may show artificially low trade volumes.

5. **Purpose Code Ambiguity**: Some records have multiple purposes or unclear coding. The most_recorded_trade_use represents the primary purpose only.

## Assumptions

1. **Species Identity**: Assumes species_id mapping is accurate and taxonomic synonyms are resolved upstream.

2. **Re-export Handling**: Re-exports counted as separate trade events. Original source country tracked separately when available.

3. **Null Handling**: 
   - Null conservation status = never assessed (not "data deficient")
   - Null trade quantity = 0 for aggregation purposes
   - Null year excluded from temporal analyses

4. **Statistical Thresholds**:
   - Trade trend: p < 0.05 for significance
   - Minimum 3 data points for trend calculation
   - R² > 0.3 for meaningful trend direction

## Validation Rules

1. **Referential Integrity**: All species_id values must exist in species table
2. **Temporal Consistency**: period_start_year ≤ period_end_year ≤ current year
3. **Percentage Bounds**: All percentage fields between 0 and 100
4. **Status Values**: Must match controlled vocabularies (IUCN categories, CITES appendices)
5. **Country Codes**: ISO 3166-1 alpha-2 format validation

## Confidence Levels

- **High Confidence**: Trade counts, CITES listings, country data
- **Medium Confidence**: Quantity standardization, trend analysis, purpose classification  
- **Lower Confidence**: Pre-Convention counts (dependent on historical records)
- **Variable Confidence**: IUCN assessments (some species lack recent data)

</data_quality_notes>

</table_documentation>

## Additional Context for Research Use

This aggregation table specifically supports the Arctic wildlife trade research article by providing:

1. **Temporal Analysis**: Complete trade history from CITES inception (1975) to present
2. **Conservation Trajectory**: Status changes indicating species' conservation journey
3. **Trade Patterns**: Purpose analysis revealing drivers of trade (commercial vs scientific)
4. **Geographic Insights**: Identifying key source countries and trade routes
5. **Policy Indicators**: Trade suspensions and regulatory changes
6. **Wild Population Impact**: Wild vs captive source analysis

The table is optimized for generating publication-ready statistics, time series visualizations, and policy recommendations without requiring complex real-time calculations during analysis.

---

*Version 1.0 | Last Updated: August 2025 | Maintained by Arctic Tracker Database Team*