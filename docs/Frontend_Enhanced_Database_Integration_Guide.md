# Frontend Enhanced Database Integration Guide

**Date**: June 11, 2025  
**Purpose**: Complete guide for integrating enhanced Arctic Tracker database features in the frontend

---

## 🎯 Overview

This guide covers how to use the newly enhanced Arctic Tracker database features in your frontend application, including enhanced species profiles, country references, and new database views.

## 🗄️ Enhanced Database Structure

### New Tables & Views Available

#### **Core Tables (Enhanced)**
- `species` - Enhanced with detailed conservation profiles
- `countries` - Now includes Arctic Council and NAMMCO membership
- `conservation_profiles` - New comprehensive species profiles
- `references` - Scientific citations with DOI links
- `profile_references` - Links profiles to citations

#### **New Database Views (Ready to Use)**
- `v_catch_records_with_countries` - Catch data with country names
- `v_country_statistics` - Country summary statistics
- `v_cites_trade_with_countries` - Trade data with resolved country names

---

## 🚀 Frontend Integration Patterns

### 1. Enhanced Species Detail Pages

#### **Complete Species Data Query**
```javascript
// Fetch complete species profile with all related data
const fetchEnhancedSpeciesProfile = async (speciesId) => {
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
            reference_type,
            full_citation
          )
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

#### **Species Profile Component**
```jsx
const EnhancedSpeciesProfile = ({ speciesId }) => {
  const [species, setSpecies] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadSpecies = async () => {
      const data = await fetchEnhancedSpeciesProfile(speciesId);
      setSpecies(data);
      setLoading(false);
    };
    loadSpecies();
  }, [speciesId]);

  if (loading) return <LoadingSpinner />;

  const profile = species.conservation_profiles?.[0];
  const references = profile?.profile_references?.map(pr => pr.references) || [];

  return (
    <div className="enhanced-species-profile">
      {/* Species Header with Status Badges */}
      <SpeciesHeader species={species} />
      
      {/* Tabbed Content */}
      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="conservation">Conservation</TabsTrigger>
          <TabsTrigger value="catch-data">Catch Data</TabsTrigger>
          <TabsTrigger value="references">References ({references.length})</TabsTrigger>
        </TabsList>
        
        <TabsContent value="overview">
          <OverviewTab species={species} />
        </TabsContent>
        
        <TabsContent value="conservation">
          <ConservationTab species={species} profile={profile} />
        </TabsContent>
        
        <TabsContent value="catch-data">
          <CatchDataTab speciesId={speciesId} />
        </TabsContent>
        
        <TabsContent value="references">
          <ReferencesTab references={references} />
        </TabsContent>
      </Tabs>
    </div>
  );
};
```

### 2. Country-Enhanced Catch Data

#### **Using the New Catch Records View**
```javascript
// Fetch catch data with country information using the new view
const fetchCatchDataWithCountries = async (filters = {}) => {
  let query = supabase
    .from('v_catch_records_with_countries')
    .select('*');

  // Apply filters
  if (filters.speciesId) {
    query = query.eq('species_id', filters.speciesId);
  }
  
  if (filters.countryId) {
    query = query.eq('country_id', filters.countryId);
  }
  
  if (filters.arcticCouncilOnly) {
    query = query.eq('arctic_council', true);
  }
  
  if (filters.nammcoOnly) {
    query = query.eq('nammco_member', true);
  }
  
  if (filters.yearRange) {
    query = query
      .gte('year', filters.yearRange[0])
      .lte('year', filters.yearRange[1]);
  }

  const { data, error } = await query
    .order('year', { ascending: false })
    .limit(filters.limit || 100);

  return data;
};
```

#### **Enhanced Catch Data Component**
```jsx
const EnhancedCatchDataTable = ({ speciesId }) => {
  const [catchData, setCatchData] = useState([]);
  const [filters, setFilters] = useState({
    speciesId,
    arcticCouncilOnly: false,
    nammcoOnly: false,
    yearRange: [2000, 2025]
  });

  useEffect(() => {
    const loadCatchData = async () => {
      const data = await fetchCatchDataWithCountries(filters);
      setCatchData(data);
    };
    loadCatchData();
  }, [filters]);

  return (
    <div className="enhanced-catch-data">
      {/* Filters */}
      <div className="catch-filters">
        <label>
          <input
            type="checkbox"
            checked={filters.arcticCouncilOnly}
            onChange={(e) => setFilters({
              ...filters,
              arcticCouncilOnly: e.target.checked
            })}
          />
          Arctic Council Countries Only
        </label>
        
        <label>
          <input
            type="checkbox"
            checked={filters.nammcoOnly}
            onChange={(e) => setFilters({
              ...filters,
              nammcoOnly: e.target.checked
            })}
          />
          NAMMCO Members Only
        </label>
      </div>

      {/* Data Table */}
      <table className="catch-data-table">
        <thead>
          <tr>
            <th>Year</th>
            <th>Country</th>
            <th>Governance</th>
            <th>Catch Total</th>
            <th>Quota</th>
            <th>Data Source</th>
          </tr>
        </thead>
        <tbody>
          {catchData.map((record) => (
            <tr key={record.id}>
              <td>{record.year}</td>
              <td>
                <CountryFlag code={record.country_code} />
                {record.country_name}
              </td>
              <td>
                <GovernanceBadges 
                  arcticCouncil={record.arctic_council}
                  nammco={record.nammco_member}
                />
              </td>
              <td>{record.catch_total || 'N/A'}</td>
              <td>{record.quota_amount || 'N/A'}</td>
              <td>{record.data_source}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
```

### 3. Country Statistics Dashboard

#### **Using Country Statistics View**
```javascript
// Fetch country statistics using the new view
const fetchCountryStatistics = async () => {
  const { data, error } = await supabase
    .from('v_country_statistics')
    .select('*')
    .order('total_catch_records', { ascending: false });

  return data;
};
```

#### **Country Statistics Component**
```jsx
const CountryStatisticsDashboard = () => {
  const [countries, setCountries] = useState([]);
  const [selectedType, setSelectedType] = useState('all');

  useEffect(() => {
    const loadCountries = async () => {
      const data = await fetchCountryStatistics();
      setCountries(data);
    };
    loadCountries();
  }, []);

  const filteredCountries = countries.filter(country => {
    switch (selectedType) {
      case 'arctic-council':
        return country.arctic_council;
      case 'nammco':
        return country.nammco_member;
      case 'both':
        return country.arctic_council && country.nammco_member;
      default:
        return true;
    }
  });

  return (
    <div className="country-statistics-dashboard">
      <div className="dashboard-header">
        <h2>Country Statistics</h2>
        <select 
          value={selectedType} 
          onChange={(e) => setSelectedType(e.target.value)}
        >
          <option value="all">All Countries</option>
          <option value="arctic-council">Arctic Council</option>
          <option value="nammco">NAMMCO Members</option>
          <option value="both">Both AC & NAMMCO</option>
        </select>
      </div>

      <div className="countries-grid">
        {filteredCountries.map((country) => (
          <CountryStatCard key={country.id} country={country} />
        ))}
      </div>
    </div>
  );
};

const CountryStatCard = ({ country }) => (
  <div className="country-stat-card">
    <div className="country-header">
      <CountryFlag code={country.country_code} />
      <h3>{country.country_name}</h3>
      <GovernanceBadges 
        arcticCouncil={country.arctic_council}
        nammco={country.nammco_member}
      />
    </div>
    
    <div className="country-stats">
      <StatItem 
        label="Catch Records" 
        value={country.total_catch_records}
        icon="🎣"
      />
      <StatItem 
        label="Total Catch" 
        value={country.total_catch}
        icon="📊"
      />
      <StatItem 
        label="Species" 
        value={country.species_with_catch_data}
        icon="🐋"
      />
      <StatItem 
        label="Trade Records" 
        value={country.total_trade_records}
        icon="📦"
      />
    </div>
  </div>
);
```

### 4. Enhanced Species Search & Filtering

#### **Advanced Species Search**
```javascript
// Enhanced species search with conservation status
const searchSpeciesAdvanced = async (searchParams) => {
  let query = supabase
    .from('species')
    .select(`
      id,
      scientific_name,
      common_name,
      family,
      conservation_profiles (
        id,
        profile_type
      ),
      iucn_assessments (
        status,
        is_latest
      ),
      cites_listings (
        appendix,
        is_current
      )
    `);

  // Text search
  if (searchParams.query) {
    query = query.or(`
      scientific_name.ilike.%${searchParams.query}%,
      common_name.ilike.%${searchParams.query}%
    `);
  }

  // Filter by family
  if (searchParams.family) {
    query = query.eq('family', searchParams.family);
  }

  // Filter by conservation status
  if (searchParams.iucnStatus) {
    query = query.eq('iucn_assessments.status', searchParams.iucnStatus);
  }

  // Filter by CITES appendix
  if (searchParams.citesAppendix) {
    query = query.eq('cites_listings.appendix', searchParams.citesAppendix);
  }

  // Filter by profile availability
  if (searchParams.hasProfile) {
    query = query.not('conservation_profiles', 'is', null);
  }

  const { data, error } = await query.limit(50);
  return data;
};
```

### 5. References Management

#### **Scientific References Component**
```jsx
const ScientificReferences = ({ references }) => {
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

  const filteredReferences = sortedReferences.filter(ref => {
    if (filterBy === 'all') return true;
    return ref.reference_type === filterBy;
  });

  return (
    <div className="scientific-references">
      <div className="references-controls">
        <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
          <option value="year">Sort by Year</option>
          <option value="title">Sort by Title</option>
          <option value="journal">Sort by Journal</option>
        </select>
        
        <select value={filterBy} onChange={(e) => setFilterBy(e.target.value)}>
          <option value="all">All Types</option>
          <option value="journal">Journal Articles</option>
          <option value="book">Books</option>
          <option value="report">Reports</option>
        </select>
      </div>

      <div className="references-list">
        {filteredReferences.map((ref, index) => (
          <ReferenceCard key={index} reference={ref} />
        ))}
      </div>

      <div className="references-actions">
        <button onClick={() => exportReferences(filteredReferences, 'bibtex')}>
          Export BibTeX
        </button>
        <button onClick={() => exportReferences(filteredReferences, 'ris')}>
          Export RIS
        </button>
      </div>
    </div>
  );
};

const ReferenceCard = ({ reference }) => (
  <div className="reference-card">
    <div className="reference-header">
      <h4>{reference.title}</h4>
      <span className="reference-year">{reference.year}</span>
    </div>
    
    <div className="reference-authors">
      {Array.isArray(reference.authors) 
        ? reference.authors.join(', ')
        : reference.authors
      }
    </div>
    
    {reference.journal && (
      <div className="reference-journal">
        <em>{reference.journal}</em>
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
    
    <span className={`reference-type type-${reference.reference_type}`}>
      {reference.reference_type}
    </span>
  </div>
);
```

---

## 🎨 UI Components Library

### Governance Badges Component
```jsx
const GovernanceBadges = ({ arcticCouncil, nammco }) => (
  <div className="governance-badges">
    {arcticCouncil && (
      <span className="badge arctic-council">
        🌍 Arctic Council
      </span>
    )}
    {nammco && (
      <span className="badge nammco">
        🐋 NAMMCO
      </span>
    )}
  </div>
);
```

### Country Flag Component
```jsx
const CountryFlag = ({ code, size = 'sm' }) => {
  if (!code) return null;
  
  return (
    <img 
      src={`https://flagcdn.com/${size}/${code.toLowerCase()}.png`}
      alt={`${code} flag`}
      className={`country-flag flag-${size}`}
      width={size === 'sm' ? 16 : 24}
      height={size === 'sm' ? 12 : 18}
    />
  );
};
```

### Conservation Status Badge
```jsx
const ConservationStatusBadge = ({ status, type = 'iucn' }) => {
  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'critically endangered': return 'status-critical';
      case 'endangered': return 'status-endangered';
      case 'vulnerable': return 'status-vulnerable';
      case 'near threatened': return 'status-near-threatened';
      case 'least concern': return 'status-least-concern';
      default: return 'status-unknown';
    }
  };

  return (
    <span className={`status-badge ${getStatusColor(status)} ${type}`}>
      {type.toUpperCase()}: {status}
    </span>
  );
};
```

---

## 📊 Data Visualization Examples

### Catch Data by Country Chart
```jsx
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';

const CatchByCountryChart = ({ data }) => {
  const chartData = useMemo(() => {
    const countryData = data.reduce((acc, record) => {
      const country = record.country_name || 'Unknown';
      if (!acc[country]) {
        acc[country] = { 
          country, 
          total_catch: 0, 
          arctic_council: record.arctic_council,
          nammco_member: record.nammco_member
        };
      }
      acc[country].total_catch += record.catch_total || 0;
      return acc;
    }, {});
    
    return Object.values(countryData)
      .sort((a, b) => b.total_catch - a.total_catch)
      .slice(0, 10);
  }, [data]);

  return (
    <BarChart width={800} height={400} data={chartData}>
      <CartesianGrid strokeDasharray="3 3" />
      <XAxis dataKey="country" />
      <YAxis />
      <Tooltip 
        content={({ active, payload, label }) => {
          if (active && payload && payload.length) {
            const data = payload[0].payload;
            return (
              <div className="chart-tooltip">
                <p>{label}</p>
                <p>Total Catch: {payload[0].value}</p>
                <GovernanceBadges 
                  arcticCouncil={data.arctic_council}
                  nammco={data.nammco_member}
                />
              </div>
            );
          }
          return null;
        }}
      />
      <Legend />
      <Bar dataKey="total_catch" fill="#8884d8" name="Total Catch" />
    </BarChart>
  );
};
```

---

## 🔧 Utility Functions

### Export Functions
```javascript
// Export references in different formats
export const exportReferences = (references, format) => {
  switch (format) {
    case 'bibtex':
      return exportBibTeX(references);
    case 'ris':
      return exportRIS(references);
    case 'csv':
      return exportCSV(references);
    default:
      throw new Error(`Unsupported format: ${format}`);
  }
};

const exportBibTeX = (references) => {
  const bibtex = references.map(ref => {
    const key = `${ref.authors?.[0]?.split(',')[0] || 'unknown'}${ref.year}`;
    return `@article{${key},
  title={${ref.title}},
  author={${Array.isArray(ref.authors) ? ref.authors.join(' and ') : ref.authors}},
  journal={${ref.journal || ''}},
  year={${ref.year || ''}},
  doi={${ref.doi || ''}}
}`;
  }).join('\n\n');
  
  downloadFile(bibtex, 'references.bib', 'text/plain');
};

const downloadFile = (content, filename, mimeType) => {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};
```

### Data Processing Utilities
```javascript
// Process catch data for visualizations
export const processCatchDataForCharts = (data) => {
  return {
    byYear: groupByYear(data),
    byCountry: groupByCountry(data),
    bySpecies: groupBySpecies(data),
    trends: calculateTrends(data)
  };
};

const groupByYear = (data) => {
  return data.reduce((acc, record) => {
    const year = record.year;
    if (!acc[year]) {
      acc[year] = { year, total_catch: 0, records: 0 };
    }
    acc[year].total_catch += record.catch_total || 0;
    acc[year].records += 1;
    return acc;
  }, {});
};

const groupByCountry = (data) => {
  return data.reduce((acc, record) => {
    const country = record.country_name || 'Unknown';
    if (!acc[country]) {
      acc[country] = { 
        country, 
        total_catch: 0, 
        records: 0,
        arctic_council: record.arctic_council,
        nammco_member: record.nammco_member
      };
    }
    acc[country].total_catch += record.catch_total || 0;
    acc[country].records += 1;
    return acc;
  }, {});
};
```

---

## 🚀 Implementation Checklist

### Phase 1: Basic Integration
- [ ] Update species detail pages to use enhanced data
- [ ] Implement country-enhanced catch data tables
- [ ] Add governance badges (Arctic Council, NAMMCO)
- [ ] Create basic references display

### Phase 2: Advanced Features
- [ ] Implement country statistics dashboard
- [ ] Add advanced search with conservation filters
- [ ] Create data visualization charts
- [ ] Add reference export functionality

### Phase 3: Optimization
- [ ] Add caching for frequently accessed data
- [ ] Implement pagination for large datasets
- [ ] Add real-time updates for new data
- [ ] Optimize queries for performance

### Phase 4: User Experience
- [ ] Add loading states and error handling
- [ ] Implement responsive design
- [ ] Add accessibility features
- [ ] Create user preferences for data display

---

**Ready for Implementation**: This guide provides comprehensive patterns for integrating all enhanced Arctic Tracker database features into your frontend application, with complete code examples and best practices.
