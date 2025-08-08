# Frontend Species Profile Display Guide

**Date**: June 11, 2025  
**Purpose**: Complete guide for displaying enhanced species profiles in the Arctic Tracker frontend

---

## 🎯 Overview

This guide provides comprehensive instructions for displaying the new enhanced species profiles with references, conservation data, and catch records in the Arctic Tracker frontend.

## 📊 Available Data Structure

### Enhanced Species Data
Each species now has access to:
- **Basic Information**: Scientific name, common name, taxonomy
- **Detailed Descriptions**: Physical characteristics, habitat, behavior
- **Conservation Data**: Population trends, threats, conservation measures
- **Scientific References**: Peer-reviewed citations with DOI links
- **Catch Records**: NAMMCO data with quotas and trends
- **Management Areas**: Geographic distribution and management units

## 🏗️ Frontend Architecture

### 1. Species Detail Page Layout

```jsx
// Main Species Detail Component
const SpeciesDetailPage = ({ speciesId }) => {
  return (
    <div className="species-detail-container">
      <SpeciesHeader species={species} />
      <SpeciesNavigation activeTab={activeTab} />
      
      <div className="species-content">
        {activeTab === 'overview' && <OverviewTab species={species} />}
        {activeTab === 'conservation' && <ConservationTab species={species} />}
        {activeTab === 'catch-data' && <CatchDataTab species={species} />}
        {activeTab === 'references' && <ReferencesTab species={species} />}
        {activeTab === 'distribution' && <DistributionTab species={species} />}
      </div>
    </div>
  );
};
```

### 2. Data Fetching Strategy

```javascript
// Enhanced species data query
const fetchSpeciesProfile = async (speciesId) => {
  const { data, error } = await supabase
    .from('species')
    .select(`
      *,
      conservation_profiles (
        id,
        profile_type,
        content,
        created_at,
        profile_references (
          reference_id,
          references (
            title,
            authors,
            journal,
            year,
            doi,
            url,
            reference_type
          )
        )
      ),
      catch_records (
        id,
        year,
        catch_total,
        quota_amount,
        country:country_id (
          country_name
        ),
        management_area:management_area_id (
          area_name,
          area_type
        )
      ),
      iucn_assessments (
        year_published,
        status,
        is_latest
      ),
      cites_listings (
        appendix,
        listing_date,
        is_current
      )
    `)
    .eq('id', speciesId)
    .single();

  return data;
};
```

## 📱 Component Specifications

### 1. Species Header Component

```jsx
const SpeciesHeader = ({ species }) => {
  const latestIUCN = species.iucn_assessments?.find(a => a.is_latest);
  const currentCITES = species.cites_listings?.find(l => l.is_current);

  return (
    <div className="species-header">
      <div className="species-title">
        <h1 className="common-name">{species.common_name}</h1>
        <h2 className="scientific-name">{species.scientific_name}</h2>
        <p className="authority">{species.authority}</p>
      </div>
      
      <div className="species-status">
        {latestIUCN && (
          <StatusBadge 
            type="iucn" 
            status={latestIUCN.status}
            year={latestIUCN.year_published}
          />
        )}
        {currentCITES && (
          <StatusBadge 
            type="cites" 
            appendix={currentCITES.appendix}
            date={currentCITES.listing_date}
          />
        )}
      </div>
      
      <div className="species-image">
        {species.default_image_url && (
          <img src={species.default_image_url} alt={species.common_name} />
        )}
      </div>
    </div>
  );
};
```

### 2. Overview Tab Component

```jsx
const OverviewTab = ({ species }) => {
  return (
    <div className="overview-tab">
      <div className="overview-grid">
        
        {/* Physical Description */}
        <Section title="Description" icon="🔬">
          <div className="description-content">
            {species.description && (
              <FormattedText text={species.description} />
            )}
          </div>
        </Section>

        {/* Habitat */}
        <Section title="Habitat" icon="🌍">
          <div className="habitat-content">
            {species.habitat_description && (
              <FormattedText text={species.habitat_description} />
            )}
          </div>
        </Section>

        {/* Quick Facts */}
        <Section title="Quick Facts" icon="📊">
          <div className="quick-facts">
            <FactItem 
              label="Population Size" 
              value={species.population_size || 'Unknown'} 
            />
            <FactItem 
              label="Population Trend" 
              value={species.population_trend || 'Unknown'} 
            />
            <FactItem 
              label="Generation Length" 
              value={species.generation_length ? `${species.generation_length} years` : 'Unknown'} 
            />
            <FactItem 
              label="Family" 
              value={species.family} 
            />
            <FactItem 
              label="Order" 
              value={species.order_name} 
            />
          </div>
        </Section>

        {/* Movement Patterns */}
        {species.movement_patterns && (
          <Section title="Movement Patterns" icon="🗺️">
            <FormattedText text={species.movement_patterns} />
          </Section>
        )}

      </div>
    </div>
  );
};
```

### 3. Conservation Tab Component

```jsx
const ConservationTab = ({ species }) => {
  const conservationProfile = species.conservation_profiles?.[0];

  return (
    <div className="conservation-tab">
      
      {/* Threats Overview */}
      <Section title="Threats Overview" icon="⚠️" priority="high">
        <div className="threats-content">
          {species.threats_overview && (
            <FormattedText text={species.threats_overview} />
          )}
        </div>
      </Section>

      {/* Conservation Overview */}
      <Section title="Conservation Measures" icon="🛡️" priority="medium">
        <div className="conservation-content">
          {species.conservation_overview && (
            <FormattedText text={species.conservation_overview} />
          )}
        </div>
      </Section>

      {/* Use and Trade */}
      <Section title="Use and Trade" icon="🏪">
        <div className="trade-content">
          {species.use_and_trade && (
            <FormattedText text={species.use_and_trade} />
          )}
        </div>
      </Section>

      {/* Subpopulations */}
      {conservationProfile?.content?.subpopulations && (
        <Section title="Subpopulations" icon="👥">
          <FormattedText text={conservationProfile.content.subpopulations} />
        </Section>
      )}

      {/* Distribution Range */}
      {conservationProfile?.content?.distribution_range && (
        <Section title="Distribution Range" icon="🌐">
          <FormattedText text={conservationProfile.content.distribution_range} />
        </Section>
      )}

    </div>
  );
};
```

### 4. Catch Data Tab Component

```jsx
const CatchDataTab = ({ species }) => {
  const [selectedCountry, setSelectedCountry] = useState('all');
  const [selectedYearRange, setSelectedYearRange] = useState([1990, 2025]);

  const catchRecords = species.catch_records || [];
  const filteredRecords = useMemo(() => {
    return catchRecords.filter(record => {
      const countryMatch = selectedCountry === 'all' || 
        record.country?.country_name === selectedCountry;
      const yearMatch = record.year >= selectedYearRange[0] && 
        record.year <= selectedYearRange[1];
      return countryMatch && yearMatch;
    });
  }, [catchRecords, selectedCountry, selectedYearRange]);

  return (
    <div className="catch-data-tab">
      
      {/* Filters */}
      <div className="catch-filters">
        <CountryFilter 
          countries={getUniqueCountries(catchRecords)}
          selected={selectedCountry}
          onChange={setSelectedCountry}
        />
        <YearRangeSlider 
          range={selectedYearRange}
          onChange={setSelectedYearRange}
          min={getMinYear(catchRecords)}
          max={getMaxYear(catchRecords)}
        />
      </div>

      {/* Summary Statistics */}
      <div className="catch-summary">
        <StatCard 
          title="Total Records" 
          value={filteredRecords.length}
          icon="📊"
        />
        <StatCard 
          title="Total Catch" 
          value={getTotalCatch(filteredRecords)}
          icon="🎣"
        />
        <StatCard 
          title="Countries" 
          value={getUniqueCountries(filteredRecords).length}
          icon="🌍"
        />
        <StatCard 
          title="Year Range" 
          value={`${getMinYear(filteredRecords)}-${getMaxYear(filteredRecords)}`}
          icon="📅"
        />
      </div>

      {/* Catch Trends Chart */}
      <Section title="Catch Trends Over Time" icon="📈">
        <CatchTrendsChart data={filteredRecords} />
      </Section>

      {/* Catch by Country Chart */}
      <Section title="Catch by Country" icon="🌍">
        <CatchByCountryChart data={filteredRecords} />
      </Section>

      {/* Quota vs Catch Analysis */}
      <Section title="Quota vs Actual Catch" icon="⚖️">
        <QuotaAnalysisChart data={filteredRecords} />
      </Section>

      {/* Detailed Records Table */}
      <Section title="Detailed Records" icon="📋">
        <CatchRecordsTable data={filteredRecords} />
      </Section>

    </div>
  );
};
```

### 5. References Tab Component

```jsx
const ReferencesTab = ({ species }) => {
  const references = species.conservation_profiles?.[0]?.profile_references?.map(
    pr => pr.references
  ) || [];

  const [sortBy, setSortBy] = useState('year');
  const [filterBy, setFilterBy] = useState('all');

  const sortedReferences = useMemo(() => {
    return [...references].sort((a, b) => {
      switch (sortBy) {
        case 'year':
          return (b.year || 0) - (a.year || 0);
        case 'title':
          return a.title.localeCompare(b.title);
        case 'journal':
          return (a.journal || '').localeCompare(b.journal || '');
        default:
          return 0;
      }
    });
  }, [references, sortBy]);

  return (
    <div className="references-tab">
      
      {/* Reference Controls */}
      <div className="reference-controls">
        <div className="sort-controls">
          <label>Sort by:</label>
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
            <option value="year">Year (newest first)</option>
            <option value="title">Title (A-Z)</option>
            <option value="journal">Journal (A-Z)</option>
          </select>
        </div>
        
        <div className="filter-controls">
          <label>Filter by type:</label>
          <select value={filterBy} onChange={(e) => setFilterBy(e.target.value)}>
            <option value="all">All Types</option>
            <option value="journal">Journal Articles</option>
            <option value="book">Books</option>
            <option value="report">Reports</option>
          </select>
        </div>
      </div>

      {/* References List */}
      <div className="references-list">
        {sortedReferences.map((ref, index) => (
          <ReferenceCard key={index} reference={ref} />
        ))}
      </div>

      {/* Citation Export */}
      <div className="citation-export">
        <button onClick={() => exportCitations(sortedReferences, 'bibtex')}>
          Export as BibTeX
        </button>
        <button onClick={() => exportCitations(sortedReferences, 'ris')}>
          Export as RIS
        </button>
      </div>

    </div>
  );
};
```

### 6. Reference Card Component

```jsx
const ReferenceCard = ({ reference }) => {
  return (
    <div className="reference-card">
      <div className="reference-header">
        <h3 className="reference-title">{reference.title}</h3>
        <span className="reference-year">{reference.year}</span>
      </div>
      
      <div className="reference-authors">
        {reference.authors?.join(', ')}
      </div>
      
      {reference.journal && (
        <div className="reference-journal">
          <em>{reference.journal}</em>
          {reference.volume && `, ${reference.volume}`}
          {reference.issue && `(${reference.issue})`}
          {reference.pages && `, ${reference.pages}`}
        </div>
      )}
      
      <div className="reference-links">
        {reference.doi && (
          <a 
            href={`https://doi.org/${reference.doi}`} 
            target="_blank" 
            rel="noopener noreferrer"
            className="doi-link"
          >
            DOI: {reference.doi}
          </a>
        )}
        {reference.url && (
          <a 
            href={reference.url} 
            target="_blank" 
            rel="noopener noreferrer"
            className="external-link"
          >
            View Article
          </a>
        )}
      </div>
      
      <div className="reference-type">
        <span className={`type-badge type-${reference.reference_type}`}>
          {reference.reference_type}
        </span>
      </div>
    </div>
  );
};
```

## 📊 Data Visualization Components

### 1. Catch Trends Chart

```jsx
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';

const CatchTrendsChart = ({ data }) => {
  const chartData = useMemo(() => {
    const yearlyData = data.reduce((acc, record) => {
      const year = record.year;
      if (!acc[year]) {
        acc[year] = { year, catch_total: 0, quota_amount: 0, records: 0 };
      }
      acc[year].catch_total += record.catch_total || 0;
      acc[year].quota_amount += record.quota_amount || 0;
      acc[year].records += 1;
      return acc;
    }, {});
    
    return Object.values(yearlyData).sort((a, b) => a.year - b.year);
  }, [data]);

  return (
    <div className="catch-trends-chart">
      <LineChart width={800} height={400} data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="year" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Line 
          type="monotone" 
          dataKey="catch_total" 
          stroke="#8884d8" 
          name="Total Catch"
        />
        <Line 
          type="monotone" 
          dataKey="quota_amount" 
          stroke="#82ca9d" 
          name="Quota Amount"
        />
      </LineChart>
    </div>
  );
};
```

### 2. Catch by Country Chart

```jsx
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';

const CatchByCountryChart = ({ data }) => {
  const chartData = useMemo(() => {
    const countryData = data.reduce((acc, record) => {
      const country = record.country?.country_name || 'Unknown';
      if (!acc[country]) {
        acc[country] = { country, total_catch: 0, records: 0 };
      }
      acc[country].total_catch += record.catch_total || 0;
      acc[country].records += 1;
      return acc;
    }, {});
    
    return Object.values(countryData).sort((a, b) => b.total_catch - a.total_catch);
  }, [data]);

  return (
    <div className="catch-by-country-chart">
      <BarChart width={800} height={400} data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="country" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Bar dataKey="total_catch" fill="#8884d8" name="Total Catch" />
      </BarChart>
    </div>
  );
};
```

## 🎨 Styling Guidelines

### 1. CSS Variables

```css
:root {
  /* Species Profile Colors */
  --species-primary: #2563eb;
  --species-secondary: #64748b;
  --species-accent: #059669;
  --species-warning: #dc2626;
  --species-info: #0891b2;
  
  /* Status Colors */
  --status-critical: #dc2626;
  --status-endangered: #ea580c;
  --status-vulnerable: #ca8a04;
  --status-near-threatened: #65a30d;
  --status-least-concern: #059669;
  
  /* Layout */
  --species-header-height: 200px;
  --species-nav-height: 60px;
  --species-content-padding: 2rem;
}
```

### 2. Component Styles

```css
.species-detail-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 1rem;
}

.species-header {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 2rem;
  padding: 2rem;
  background: linear-gradient(135deg, var(--species-primary), var(--species-secondary));
  color: white;
  border-radius: 12px;
  margin-bottom: 2rem;
}

.species-title h1 {
  font-size: 2.5rem;
  font-weight: 700;
  margin: 0 0 0.5rem 0;
}

.species-title h2 {
  font-size: 1.5rem;
  font-style: italic;
  font-weight: 400;
  margin: 0 0 0.25rem 0;
  opacity: 0.9;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 0.875rem;
  font-weight: 600;
  text-transform: uppercase;
}

.status-badge.iucn {
  background: var(--status-critical);
}

.status-badge.cites {
  background: var(--species-accent);
}

.section {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.25rem;
  font-weight: 600;
  margin-bottom: 1rem;
  color: var(--species-primary);
}

.reference-card {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1rem;
  transition: box-shadow 0.2s;
}

.reference-card:hover {
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}
```

## 📱 Responsive Design

### Mobile Optimization

```css
@media (max-width: 768px) {
  .species-header {
    grid-template-columns: 1fr;
    text-align: center;
  }
  
  .overview-grid {
    grid-template-columns: 1fr;
  }
  
  .catch-filters {
    flex-direction: column;
    gap: 1rem;
  }
  
  .catch-trends-chart,
  .catch-by-country-chart {
    width: 100%;
    overflow-x: auto;
  }
}
```

## 🔧 Utility Functions

### Text Formatting

```javascript
// Format text with citations and line breaks
const FormattedText = ({ text }) => {
  if (!text) return null;
  
  // Convert line breaks to paragraphs
  const paragraphs = text.split('\n\n').filter(p => p.trim());
  
  return (
    <div className="formatted-text">
      {paragraphs.map((paragraph, index) => (
        <p key={index} className="text-paragraph">
          {formatCitations(paragraph)}
        </p>
      ))}
    </div>
  );
};

// Format in-text citations
const formatCitations = (text) => {
  return text.replace(
    /\(([^)]+),\s*(\d{4})\)/g,
    '<span class="citation">($1, $2)</span>'
  );
};
```

### Data Processing

```javascript
// Get unique countries from catch records
const getUniqueCountries = (records) => {
  const countries = records
    .map(r => r.country?.country_name)
    .filter(Boolean);
  return [...new Set(countries)].sort();
};

// Calculate total catch
const getTotalCatch = (records) => {
  return records.reduce((sum, record) => sum + (record.catch_total || 0), 0);
};

// Get year range
const getMinYear = (records) => {
  return Math.min(...records.map(r => r.year));
};

const getMaxYear = (records) => {
  return Math.max(...records.map(r => r.year));
};
```

## 🚀 Implementation Checklist

### Phase 1: Basic Display
- [ ] Species header with status badges
- [ ] Overview tab with basic information
- [ ] Navigation between tabs
- [ ] Responsive layout

### Phase 2: Enhanced Features
- [ ] Conservation tab with threats and measures
- [ ] References tab with citation formatting
- [ ] Catch data visualization
- [ ] Search and filtering

### Phase 3: Advanced Features
- [ ] Interactive charts and graphs
- [ ] Citation export functionality
- [ ] Print-friendly layouts
- [ ] Accessibility improvements

### Phase 4: Integration
- [ ] Link to existing NAMMCO catch data
- [ ] Connect with IUCN and CITES data
- [ ] Cross-reference between species
- [ ] Admin interface for profile management

---

**Ready for Implementation**: This guide provides everything needed to display the enhanced species profiles in a user-friendly, comprehensive interface that showcases all the rich data now available in the Arctic Tracker database.
