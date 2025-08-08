# Frontend CMS Implementation Guide

## Quick Start Guide for Frontend Developers

### 🎯 What's New
The article_summary_table now includes comprehensive CMS (Convention on Migratory Species) data with 10 new fields that provide conservation insights equal to CITES coverage.

### 📊 New Fields Reference

```typescript
// Add to your existing ArticleSummaryTable interface
interface CMSFields {
  // Temporal Data
  cms_listing_date: string | null;        // "**II** 08/02/2015"
  cms_listing_years: number | null;       // Years since listing
  
  // Metadata
  cms_agreement_type: string | null;      // Usually "CMS"
  cms_listing_notes: string | null;       // Important notes
  
  // Geographic Distribution
  cms_native_countries_count: number;     // Count of range states
  cms_distribution_codes: string[];       // ISO country codes
  cms_introduced_countries_count: number; // Where introduced
  cms_extinct_countries_count: number;    // Where extinct
  
  // Conservation Assessment  
  cms_conservation_priority: string | null; // "High" | "Medium"
  
  // Future Fields (currently null)
  cms_population_trend: string | null;
  has_cms_action_plan: boolean;
}
```

### 🛠️ Implementation Examples

#### 1. Basic Status Display
```tsx
function CMSStatusBadge({ species }: { species: ArticleSummaryTable }) {
  if (!species.cms_status_current) {
    return <Badge variant="outline">No CMS listing</Badge>;
  }
  
  return (
    <div className="flex items-center gap-2">
      <Badge variant={species.cms_status_current === 'I' ? 'destructive' : 'warning'}>
        CMS {species.cms_status_current}
      </Badge>
      {species.cms_listing_years && (
        <span className="text-sm text-muted-foreground">
          {species.cms_listing_years} years
        </span>
      )}
    </div>
  );
}
```

#### 2. Conservation Timeline
```tsx
function ConservationTimeline({ species }: { species: ArticleSummaryTable }) {
  const events = [];
  
  // Parse CMS date
  if (species.cms_listing_date) {
    const dateMatch = species.cms_listing_date.match(/(\d{2})\/(\d{2})\/(\d{4})/);
    if (dateMatch) {
      const [_, day, month, year] = dateMatch;
      events.push({
        date: new Date(`${year}-${month}-${day}`),
        type: 'CMS',
        appendix: species.cms_status_current,
        description: `Listed in CMS Appendix ${species.cms_status_current}`
      });
    }
  }
  
  // Add CITES events if available
  // Add IUCN assessments if available
  
  return (
    <Timeline>
      {events.sort((a, b) => a.date - b.date).map(event => (
        <TimelineItem key={event.type} date={event.date}>
          {event.description}
        </TimelineItem>
      ))}
    </Timeline>
  );
}
```

#### 3. Geographic Distribution Map
```tsx
function DistributionMap({ species }: { species: ArticleSummaryTable }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Geographic Distribution</CardTitle>
        <CardDescription>
          {species.cms_native_countries_count} range countries
        </CardDescription>
      </CardHeader>
      <CardContent>
        <WorldMap
          data={species.cms_distribution_codes.map(code => ({
            country: code,
            status: 'native'
          }))}
        />
        <div className="mt-4 grid grid-cols-3 gap-4 text-sm">
          <div>
            <span className="font-medium">Native:</span> {species.cms_native_countries_count}
          </div>
          <div>
            <span className="font-medium">Introduced:</span> {species.cms_introduced_countries_count}
          </div>
          <div>
            <span className="font-medium">Extinct:</span> {species.cms_extinct_countries_count}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

#### 4. Multi-Convention Dashboard
```tsx
function ConservationDashboard({ species }: { species: ArticleSummaryTable }) {
  const riskLevel = calculateRiskLevel(species);
  
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {/* IUCN Card */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">IUCN Red List</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{species.iucn_status_current || 'NE'}</div>
          <p className="text-xs text-muted-foreground">
            {getIUCNDescription(species.iucn_status_current)}
          </p>
        </CardContent>
      </Card>
      
      {/* CITES Card */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">CITES</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {species.cites_status_current ? `Appendix ${species.cites_status_current}` : 'Not listed'}
          </div>
          <p className="text-xs text-muted-foreground">
            {species.trade_records_count} trade records • {species.trade_trend} trend
          </p>
        </CardContent>
      </Card>
      
      {/* CMS Card */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">CMS</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {species.cms_status_current ? `Appendix ${species.cms_status_current}` : 'Not listed'}
          </div>
          <p className="text-xs text-muted-foreground">
            {species.cms_listing_years ? `${species.cms_listing_years} years` : 'Not protected'} • 
            {species.cms_conservation_priority || 'No priority'}
          </p>
        </CardContent>
      </Card>
      
      {/* Risk Assessment */}
      <Card className="md:col-span-3">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            Conservation Risk
            <Badge variant={riskLevel.variant}>{riskLevel.emoji} {riskLevel.label}</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Progress value={riskLevel.score * 10} className="h-2" />
        </CardContent>
      </Card>
    </div>
  );
}
```

### 📈 Utility Functions

```typescript
// Extract date from CMS listing format
export function parseCMSListingDate(dateString: string | null): Date | null {
  if (!dateString) return null;
  const match = dateString.match(/(\d{2})\/(\d{2})\/(\d{4})/);
  if (!match) return null;
  const [_, day, month, year] = match;
  return new Date(`${year}-${month}-${day}`);
}

// Get appendix from listing date string
export function extractCMSAppendix(dateString: string | null): string | null {
  if (!dateString) return null;
  const match = dateString.match(/\*\*([IVX]+)\*\*/);
  return match ? match[1] : null;
}

// Calculate comprehensive risk score
export function calculateRiskLevel(species: ArticleSummaryTable) {
  let score = 0;
  
  // IUCN scoring
  const iucnScores: Record<string, number> = {
    'CR': 3, 'EN': 2.5, 'VU': 2, 'NT': 1, 'LC': 0, 'DD': 0.5
  };
  score += iucnScores[species.iucn_status_current || 'NE'] || 0;
  
  // CITES scoring
  if (species.cites_status_current === 'I') score += 2;
  else if (species.cites_status_current === 'II') score += 1;
  else if (species.cites_status_current === 'III') score += 0.5;
  
  // CMS scoring
  if (species.cms_status_current === 'I') score += 2;
  else if (species.cms_status_current === 'II') score += 1;
  
  // Trade trend
  if (species.trade_trend === 'increasing') score += 1;
  
  // Limited distribution
  if (species.cms_native_countries_count > 0 && species.cms_native_countries_count < 5) {
    score += 1;
  }
  
  return {
    score,
    label: score >= 6 ? 'Critical' : score >= 4 ? 'High' : score >= 2 ? 'Medium' : 'Low',
    emoji: score >= 6 ? '🔴' : score >= 4 ? '🟠' : score >= 2 ? '🟡' : '🟢',
    variant: score >= 6 ? 'destructive' : score >= 4 ? 'warning' : score >= 2 ? 'secondary' : 'success'
  };
}

// Format distribution summary
export function getDistributionSummary(species: ArticleSummaryTable): string {
  const parts = [];
  
  if (species.cms_native_countries_count > 0) {
    parts.push(`${species.cms_native_countries_count} native countries`);
  }
  
  if (species.cms_introduced_countries_count > 0) {
    parts.push(`${species.cms_introduced_countries_count} introduced`);
  }
  
  if (species.cms_extinct_countries_count > 0) {
    parts.push(`${species.cms_extinct_countries_count} extinct`);
  }
  
  return parts.join(', ') || 'No distribution data';
}
```

### 🎨 UI Component Ideas

1. **Protection Badge Stack**
   ```tsx
   <div className="flex gap-1">
     {species.iucn_status_current && <IUCNBadge status={species.iucn_status_current} />}
     {species.cites_status_current && <CITESBadge appendix={species.cites_status_current} />}
     {species.cms_status_current && <CMSBadge appendix={species.cms_status_current} />}
   </div>
   ```

2. **Conservation Score Card**
   ```tsx
   <MetricCard
     title="Conservation Priority"
     value={species.cms_conservation_priority || 'Not assessed'}
     trend={species.cms_listing_years ? `Protected for ${species.cms_listing_years} years` : undefined}
     icon={<Shield className="h-4 w-4" />}
   />
   ```

3. **Distribution Tooltip**
   ```tsx
   <TooltipProvider>
     <Tooltip>
       <TooltipTrigger>
         <Badge variant="outline">
           {species.cms_native_countries_count} countries
         </Badge>
       </TooltipTrigger>
       <TooltipContent>
         <p className="font-semibold">Range States:</p>
         <p className="text-sm">{species.cms_distribution_codes.join(', ')}</p>
       </TooltipContent>
     </Tooltip>
   </TooltipProvider>
   ```

### 🔍 Filtering & Sorting

```typescript
// Filter species by CMS status
const cmsProtectedSpecies = species.filter(s => s.cms_status_current !== null);

// Sort by conservation priority
const prioritizedSpecies = species.sort((a, b) => {
  const priorityOrder = { 'High': 0, 'Medium': 1, null: 2 };
  return priorityOrder[a.cms_conservation_priority] - priorityOrder[b.cms_conservation_priority];
});

// Find species with longest protection
const veteranSpecies = species
  .filter(s => s.cms_listing_years !== null)
  .sort((a, b) => (b.cms_listing_years || 0) - (a.cms_listing_years || 0));

// Multi-convention protected species
const multiProtected = species.filter(s => 
  s.cites_status_current !== null && 
  s.cms_status_current !== null
);
```

### 📱 Mobile Considerations

```tsx
// Responsive convention display
<div className="grid grid-cols-2 md:grid-cols-4 gap-2">
  <StatusCard title="IUCN" value={species.iucn_status_current} />
  <StatusCard title="CITES" value={species.cites_status_current} />
  <StatusCard title="CMS" value={species.cms_status_current} />
  <StatusCard 
    title="Range" 
    value={`${species.cms_native_countries_count} countries`} 
  />
</div>
```

### 🚀 Performance Tips

1. **Memoize calculations**: Risk scores and date parsing should be memoized
2. **Lazy load maps**: Distribution maps should load on demand
3. **Virtualize lists**: Use virtual scrolling for species lists with CMS data
4. **Cache parsed dates**: Store parsed CMS dates to avoid repeated regex

### 📋 Testing Checklist

- [ ] Handle null CMS values gracefully
- [ ] Parse CMS dates correctly (DD/MM/YYYY format)
- [ ] Display conservation priority appropriately
- [ ] Show distribution data when available
- [ ] Calculate risk scores accurately
- [ ] Responsive design for all components
- [ ] Accessibility for status badges and tooltips

### 🎯 Quick Implementation Priority

1. **Phase 1**: Basic CMS status display
2. **Phase 2**: Conservation timeline
3. **Phase 3**: Geographic distribution
4. **Phase 4**: Risk assessment dashboard
5. **Phase 5**: Advanced filtering and analytics

---

Need help? Check the comprehensive report at `/docs/CMS_Article_Summary_Enhancement_Report.md` for detailed field descriptions and data examples.