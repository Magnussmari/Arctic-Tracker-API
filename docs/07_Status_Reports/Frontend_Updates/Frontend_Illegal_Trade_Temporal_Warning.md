# Frontend Warning: Illegal Trade Data Has No Dates

**Critical Information for UI Development**

## The Issue
The illegal trade dataset (919 seizure records) contains **NO temporal information**:
- No seizure dates
- No years
- No time periods

All `seizure_date` and `seizure_year` fields are NULL in the database.

## UI Components to Avoid

### ❌ DO NOT IMPLEMENT:
- Date filters for illegal trade
- Trend charts over time
- "Recent seizures" sections
- Year comparisons
- Timeline visualizations
- "Last updated" for illegal data

### ✅ SAFE TO IMPLEMENT:
- Total seizure counts
- Species rankings by volume
- Product type breakdowns
- Geographic distribution (if available)
- CITES violation alerts
- Risk levels based on volume

## Example Component Updates

```javascript
// BAD - Don't do this
const IllegalTradeTrends = () => {
  return <LineChart data={seizuresByYear} />; // NO YEAR DATA!
};

// GOOD - Do this instead
const IllegalTradeVolume = () => {
  return (
    <div>
      <h3>Illegal Trade Impact</h3>
      <p className="text-muted">
        Based on compiled enforcement records
      </p>
      <BarChart data={seizuresBySpecies} />
    </div>
  );
};
```

## Required Disclaimers

Add to any illegal trade display:
```html
<small>
  Seizure data compiled from enforcement databases. 
  Temporal information not available.
</small>
```

## API Response Example

```json
{
  "illegal_trade": {
    "total_seizures": 195,
    "product_types": ["tusks", "carvings", "skins"],
    "seizure_date": null,  // Always null
    "seizure_year": null   // Always null
  }
}
```

Remember: The data shows **what** was seized, not **when**.