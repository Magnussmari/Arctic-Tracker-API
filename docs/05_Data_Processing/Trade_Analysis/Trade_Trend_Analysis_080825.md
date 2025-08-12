I'll query the Arctic Tracker database to understand how the trade trend is calculated for the Article Summary Table.Let me search for more specific information about how the trade trend calculation is done:Now let me query for decreasing trends to compare:Based on my analysis of the Arctic Tracker's Article Summary Table data, here's my review of how the trade trend is calculated:

## Review of Trade Trend Calculation Methodology

### Current Understanding from Data Analysis

Looking at the data patterns, I can identify several key insights about the trade trend calculation:

1. **Time Period Coverage**: The calculation appears to consider the full historical period (period_start_year to period_end_year), which can span from 1975 to 2023/2024.

2. **Classification Categories**: Three distinct trends are identified:
   - **"increasing"** 
   - **"stable"**
   - **"decreasing"**

3. **Observable Patterns**:

   **For "increasing" trends:**
   - Often associated with higher recent trade quantities
   - Many show consistent or growing activity through 2023
   - Examples: Species with last_recorded_quantity of 192,242 (2023) or 2,991 (2023)

   **For "decreasing" trends:**
   - Often show lower recent quantities compared to historical peaks
   - Some haven't been traded recently (e.g., last year 2019 or 2022)
   - Examples: Species with last_recorded_quantity of 1 (2023) or 6 (2022)

### Critical Issues Requiring Documentation

**1. Methodology Ambiguity**
The exact statistical method used is not clear from the data alone. Possible approaches could include:
- Linear regression on annual trade volumes
- Moving average comparisons
- Percentage change over specific time windows
- Mann-Kendall trend test for non-parametric time series

**2. Time Window Considerations**
- Is the trend calculated over the entire period or a recent subset?
- How are data gaps handled (years with no trade)?
- Is there a minimum data requirement for trend calculation?

**3. Quantity vs. Frequency**
- Does the trend consider total_quantity, trade_records_count, or both?
- How are outlier years weighted?

### Recommendations for Documentation Improvement

1. **Add Methodology Details**:
   ```sql
   -- Example documentation needed:
   -- Trade trend calculation uses [specific statistical method]
   -- over the most recent [X] years of data
   -- Thresholds: 
   --   Increasing: slope > +X% per year
   --   Stable: slope between -X% and +X% per year  
   --   Decreasing: slope < -X% per year
   ```

2. **Include Confidence Metrics**:
   - Add a `trend_confidence` field (high/medium/low)
   - Add `trend_p_value` or similar statistical significance measure
   - Document minimum data requirements

3. **Clarify Edge Cases**:
   - Species with sporadic trade (gaps in years)
   - Species with very low trade volumes
   - Recent vs. historical trade patterns weighting

4. **Provide Calculation Examples**:
   Show step-by-step calculation for one species in each category

### Suggested Documentation Addition

```markdown
### trade_trend Calculation Methodology

**Field**: `trade_trend`
**Type**: VARCHAR
**Values**: 'increasing', 'stable', 'decreasing'

**Calculation Method**: 
[TO BE DOCUMENTED - Current implementation unclear]

**Recommended Documentation**:
- Statistical test used (e.g., linear regression, Mann-Kendall)
- Time window (full period vs recent X years)
- Data requirements (minimum years, handling gaps)
- Thresholds for classification
- Whether based on quantity, record count, or composite
- Handling of outliers and zero-trade years

**Example Calculation**:
For species X with trade from 1980-2023:
1. Extract annual trade quantities
2. [Statistical method steps]
3. Classification based on [threshold criteria]
```

This lack of clear documentation on the trade trend calculation is a significant gap that should be addressed before the article publication, as it's a key metric for understanding Arctic species trade dynamics.