# Frontend References Tab Implementation Guide

## Overview
This guide provides implementation details for a dedicated "References" tab that displays scientific citations with proper academic formatting, enhancing the credibility and scholarly value of the Arctic Tracker application.

## Database Schema

### References Table Structure
```sql
references (
  id: UUID (Primary Key)
  source_id: TEXT (Unique identifier)
  authors: TEXT (Comma-separated authors)
  year: INTEGER (Publication year)
  title: TEXT (Article/paper title)
  journal: TEXT (Journal name)
  doi: TEXT (Digital Object Identifier)
  full_citation: TEXT (Complete formatted citation)
  created_at: TIMESTAMPTZ
  updated_at: TIMESTAMPTZ
)
```

### Profile References Junction Table
```sql
profile_references (
  id: UUID (Primary Key)
  profile_id: UUID (Foreign Key to conservation_profiles)
  reference_id: UUID (Foreign Key to references)
  created_at: TIMESTAMPTZ
)
```

## Frontend Implementation

### 1. References Tab Component

```jsx
// components/species/ReferencesTab.jsx
import React, { useState, useEffect } from 'react';
import { ExternalLinkIcon, DocumentTextIcon, AcademicCapIcon } from '@heroicons/react/outline';

const ReferencesTab = ({ speciesId }) => {
  const [references, setReferences] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState('year'); // year, authors, title
  const [sortOrder, setSortOrder] = useState('desc');

  useEffect(() => {
    fetchReferences();
  }, [speciesId, sortBy, sortOrder]);

  const fetchReferences = async () => {
    try {
      setLoading(true);
      
      // First get the conservation profile for this species
      const { data: profiles, error: profileError } = await supabase
        .from('conservation_profiles')
        .select('id')
        .eq('species_id', speciesId);

      if (profileError) throw profileError;
      
      if (!profiles || profiles.length === 0) {
        setReferences([]);
        return;
      }

      const profileId = profiles[0].id;

      // Then get references linked to this profile
      const { data: profileRefs, error: refsError } = await supabase
        .from('profile_references')
        .select(`
          references (
            id,
            source_id,
            authors,
            year,
            title,
            journal,
            doi,
            full_citation
          )
        `)
        .eq('profile_id', profileId);

      if (refsError) throw refsError;

      // Extract and sort references
      const referencesData = profileRefs
        .map(pr => pr.references)
        .filter(ref => ref !== null)
        .sort((a, b) => {
          const aVal = a[sortBy];
          const bVal = b[sortBy];
          
          if (sortOrder === 'asc') {
            return aVal > bVal ? 1 : -1;
          } else {
            return aVal < bVal ? 1 : -1;
          }
        });

      setReferences(referencesData);
    } catch (error) {
      console.error('Error fetching references:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatAuthors = (authorsString) => {
    if (!authorsString) return 'Unknown Authors';
    
    const authors = authorsString.split(',').map(a => a.trim());
    
    if (authors.length === 1) return authors[0];
    if (authors.length === 2) return `${authors[0]} & ${authors[1]}`;
    if (authors.length > 2) {
      return `${authors[0]} et al.`;
    }
    
    return authorsString;
  };

  const handleDOIClick = (doi) => {
    if (doi) {
      window.open(`https://doi.org/${doi}`, '_blank');
    }
  };

  const exportReferences = () => {
    const citationText = references
      .map(ref => ref.full_citation)
      .join('\n\n');
    
    const blob = new Blob([citationText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${speciesId}_references.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600">Loading references...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <AcademicCapIcon className="h-6 w-6 text-blue-600" />
          <h3 className="text-lg font-semibold text-gray-900">
            Scientific References ({references.length})
          </h3>
        </div>
        
        <div className="flex items-center space-x-4">
          {/* Sort Controls */}
          <div className="flex items-center space-x-2">
            <label className="text-sm text-gray-600">Sort by:</label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="text-sm border border-gray-300 rounded px-2 py-1"
            >
              <option value="year">Year</option>
              <option value="authors">Authors</option>
              <option value="title">Title</option>
            </select>
            <button
              onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
              className="text-sm text-blue-600 hover:text-blue-800"
            >
              {sortOrder === 'asc' ? '↑' : '↓'}
            </button>
          </div>
          
          {/* Export Button */}
          <button
            onClick={exportReferences}
            className="flex items-center space-x-1 px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            <DocumentTextIcon className="h-4 w-4" />
            <span>Export</span>
          </button>
        </div>
      </div>

      {/* References List */}
      {references.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <AcademicCapIcon className="h-12 w-12 mx-auto mb-4 text-gray-300" />
          <p>No references available for this species.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {references.map((reference, index) => (
            <ReferenceCard 
              key={reference.id} 
              reference={reference} 
              index={index + 1}
              onDOIClick={handleDOIClick}
            />
          ))}
        </div>
      )}
    </div>
  );
};

const ReferenceCard = ({ reference, index, onDOIClick }) => {
  const { authors, year, title, journal, doi, full_citation } = reference;

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start space-x-3">
        {/* Reference Number */}
        <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
          <span className="text-sm font-semibold text-blue-600">{index}</span>
        </div>
        
        {/* Reference Content */}
        <div className="flex-1 space-y-2">
          {/* Formatted Citation */}
          <div className="text-gray-900">
            <span className="font-medium">{formatAuthors(authors)}</span>
            {year && <span className="text-gray-600"> ({year})</span>}
            {title && <span className="italic">. {title}</span>}
            {journal && <span className="text-gray-700">. <em>{journal}</em></span>}
          </div>
          
          {/* Full Citation (if different from formatted) */}
          {full_citation && (
            <div className="text-sm text-gray-600 bg-gray-50 p-2 rounded">
              <strong>Full Citation:</strong> {full_citation}
            </div>
          )}
          
          {/* DOI Link */}
          {doi && (
            <div className="flex items-center space-x-2">
              <button
                onClick={() => onDOIClick(doi)}
                className="flex items-center space-x-1 text-sm text-blue-600 hover:text-blue-800"
              >
                <ExternalLinkIcon className="h-4 w-4" />
                <span>DOI: {doi}</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ReferencesTab;
```

### 2. Integration with Species Profile Tabs

```jsx
// components/species/SpeciesProfileTabs.jsx
import ReferencesTab from './ReferencesTab';

const SpeciesProfileTabs = ({ species }) => {
  const [activeTab, setActiveTab] = useState('overview');

  const tabs = [
    { id: 'overview', name: 'Overview', icon: InformationCircleIcon },
    { id: 'conservation', name: 'Conservation', icon: ShieldCheckIcon },
    { id: 'trade', name: 'Trade Data', icon: TrendingUpIcon },
    { id: 'catches', name: 'Catch Records', icon: LocationMarkerIcon },
    { id: 'references', name: 'References', icon: AcademicCapIcon }, // New tab
  ];

  return (
    <div className="space-y-6">
      {/* Tab Navigation */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              } whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm flex items-center space-x-2`}
            >
              <tab.icon className="h-5 w-5" />
              <span>{tab.name}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="mt-6">
        {activeTab === 'overview' && <OverviewTab species={species} />}
        {activeTab === 'conservation' && <ConservationTab species={species} />}
        {activeTab === 'trade' && <TradeDataTab species={species} />}
        {activeTab === 'catches' && <CatchRecordsTab species={species} />}
        {activeTab === 'references' && <ReferencesTab speciesId={species.id} />}
      </div>
    </div>
  );
};
```

### 3. Reference Management Utilities

```javascript
// utils/referenceUtils.js

export const formatCitation = (reference) => {
  const { authors, year, title, journal, doi } = reference;
  
  let citation = '';
  
  if (authors) {
    citation += authors;
  }
  
  if (year) {
    citation += ` (${year})`;
  }
  
  if (title) {
    citation += `. ${title}`;
  }
  
  if (journal) {
    citation += `. <em>${journal}</em>`;
  }
  
  if (doi) {
    citation += `. DOI: ${doi}`;
  }
  
  return citation;
};

export const exportReferencesToBibTeX = (references) => {
  return references.map(ref => {
    const { source_id, authors, year, title, journal, doi } = ref;
    
    return `@article{${source_id},
  author = {${authors}},
  title = {${title}},
  journal = {${journal}},
  year = {${year}},
  doi = {${doi}}
}`;
  }).join('\n\n');
};

export const validateDOI = (doi) => {
  const doiRegex = /^10\.\d{4,}\/[-._;()\/:a-zA-Z0-9]+$/;
  return doiRegex.test(doi);
};
```

### 4. API Endpoints

```javascript
// api/references.js

// Get references for a species
export const getSpeciesReferences = async (speciesId) => {
  const { data, error } = await supabase
    .from('profile_references')
    .select(`
      reference_id,
      references (
        id,
        source_id,
        authors,
        year,
        title,
        journal,
        doi,
        full_citation,
        created_at
      )
    `)
    .eq('profile_id', speciesId)
    .order('references.year', { ascending: false });

  if (error) throw error;
  return data.map(pr => pr.references).filter(ref => ref !== null);
};

// Search references
export const searchReferences = async (query) => {
  const { data, error } = await supabase
    .from('references')
    .select('*')
    .or(`title.ilike.%${query}%,authors.ilike.%${query}%,journal.ilike.%${query}%`)
    .order('year', { ascending: false });

  if (error) throw error;
  return data;
};
```

## Academic Standards

### Citation Formats Supported
- **APA Style**: Author, A. A. (Year). Title of article. *Journal Name*, Volume(Issue), pages.
- **MLA Style**: Author, First. "Title of Article." *Journal Name*, vol. #, no. #, Year, pp. ##-##.
- **Chicago Style**: Author, First Last. "Title of Article." *Journal Name* Volume, no. Issue (Year): pages.

### Features for Academic Rigor
1. **DOI Links**: Direct links to original publications
2. **Export Options**: Plain text, BibTeX, RIS formats
3. **Citation Validation**: Ensures proper formatting
4. **Sorting & Filtering**: By year, author, journal
5. **Reference Counting**: Shows total number of sources
6. **Full Citation Display**: Complete bibliographic information

## Implementation Checklist

- [ ] Create ReferencesTab component
- [ ] Integrate with species profile tabs
- [ ] Implement reference fetching logic
- [ ] Add sorting and filtering functionality
- [ ] Create export functionality
- [ ] Style with proper academic formatting
- [ ] Add DOI validation and linking
- [ ] Test with real reference data
- [ ] Add loading states and error handling
- [ ] Implement responsive design

This References tab will significantly enhance the academic credibility of the Arctic Tracker application by providing properly formatted, searchable, and exportable scientific citations.
