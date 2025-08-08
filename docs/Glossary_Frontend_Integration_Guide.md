# Glossary Feature - Frontend Integration Guide

**Date**: July 10, 2025  
**For**: Arctic Tracker Frontend Development Team  
**New Feature**: Interactive Glossary System

## 🎯 Executive Summary

I've created a comprehensive glossary system for Arctic Tracker that will help users understand conservation terminology. The database is ready with 80+ terms covering conservation organizations, trade terminology, taxonomy, and more. This guide will help you implement an intuitive glossary feature across the application.

## 📊 Database Overview

### New Table: `glossary_terms`

```sql
CREATE TABLE glossary_terms (
    id UUID PRIMARY KEY,
    term TEXT NOT NULL,           -- The term being defined
    acronym TEXT,                 -- Optional acronym (e.g., CITES)
    definition TEXT NOT NULL,     -- Full definition
    category TEXT NOT NULL,       -- Main category
    subcategory TEXT,            -- Optional subcategory
    examples TEXT,               -- Usage examples
    related_terms TEXT[],        -- Array of related terms
    priority INTEGER,            -- Display priority (0-10)
    display_contexts TEXT[],     -- Where to show tooltips
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Helper Views

1. **`glossary_by_category`** - Terms grouped by category
2. **`glossary_contextual_terms`** - Terms that should show tooltips

### Search Function

```sql
-- Full-text search for glossary
SELECT * FROM search_glossary_terms('CITES trade');
```

## 📈 Data Summary

**Total Terms**: 80+

### By Category:
- **Conservation**: 20 terms (CITES, IUCN, CMS, Red List statuses)
- **Trade**: 34 terms (specimen types, purpose codes, source codes)
- **Taxonomy**: 9 terms (Kingdom through Species)
- **Data**: 8 terms (analysis and metrics)
- **Geography**: 5 terms (range states, parties, Arctic region)

### Priority Terms (Must Have Tooltips):
- CITES, IUCN, CMS (priority: 10)
- Red List Categories (LC, VU, EN, CR)
- Appendix I, II, III
- Scientific name, Common name

## 🚀 Quick Start Implementation

### 1. Basic Glossary Queries

```javascript
// Get all terms for glossary page
const getAllTerms = async () => {
  const { data, error } = await supabase
    .from('glossary_terms')
    .select('*')
    .order('category')
    .order('term');
  
  return data;
};

// Get terms by category
const getTermsByCategory = async (category) => {
  const { data, error } = await supabase
    .from('glossary_terms')
    .select('*')
    .eq('category', category)
    .order('priority', { ascending: false })
    .order('term');
  
  return data;
};

// Get terms that need tooltips for a specific context
const getContextualTerms = async (context) => {
  const { data, error } = await supabase
    .from('glossary_contextual_terms')
    .select('*')
    .contains('display_contexts', [context]);
  
  return data;
};

// Search glossary
const searchGlossary = async (query) => {
  const { data, error } = await supabase
    .rpc('search_glossary_terms', { search_query: query });
  
  return data;
};
```

### 2. Tooltip Component

```jsx
import { useState, useEffect } from 'react';
import { Tooltip } from '@/components/ui/tooltip';

const GlossaryTooltip = ({ term, children, context = 'general' }) => {
  const [definition, setDefinition] = useState(null);
  
  useEffect(() => {
    // Check if this term should show tooltip in this context
    fetchTermDefinition(term, context).then(setDefinition);
  }, [term, context]);
  
  if (!definition) return children;
  
  return (
    <Tooltip
      content={
        <div className="max-w-xs p-3">
          <div className="font-semibold mb-1">
            {definition.term} {definition.acronym && `(${definition.acronym})`}
          </div>
          <div className="text-sm">{definition.definition}</div>
          {definition.related_terms?.length > 0 && (
            <div className="text-xs mt-2 text-gray-500">
              Related: {definition.related_terms.join(', ')}
            </div>
          )}
        </div>
      }
    >
      <span className="underline decoration-dotted cursor-help">
        {children}
      </span>
    </Tooltip>
  );
};
```

### 3. Glossary Page Component

```jsx
const GlossaryPage = () => {
  const [terms, setTerms] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  
  const categories = [
    { value: 'all', label: 'All Terms', icon: '📚' },
    { value: 'Conservation', label: 'Conservation', icon: '🌍' },
    { value: 'Trade', label: 'Trade', icon: '📦' },
    { value: 'Taxonomy', label: 'Taxonomy', icon: '🔬' },
    { value: 'Data', label: 'Data & Analysis', icon: '📊' },
    { value: 'Geography', label: 'Geography', icon: '🗺️' }
  ];
  
  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6">Arctic Tracker Glossary</h1>
      
      {/* Search Bar */}
      <div className="mb-6">
        <input
          type="text"
          placeholder="Search terms..."
          className="w-full max-w-md px-4 py-2 border rounded-lg"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>
      
      {/* Category Filters */}
      <div className="flex gap-2 mb-8 flex-wrap">
        {categories.map(cat => (
          <button
            key={cat.value}
            onClick={() => setSelectedCategory(cat.value)}
            className={`px-4 py-2 rounded-lg flex items-center gap-2 ${
              selectedCategory === cat.value 
                ? 'bg-blue-500 text-white' 
                : 'bg-gray-100 hover:bg-gray-200'
            }`}
          >
            <span>{cat.icon}</span>
            <span>{cat.label}</span>
          </button>
        ))}
      </div>
      
      {/* Terms Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {filteredTerms.map(term => (
          <GlossaryCard key={term.id} term={term} />
        ))}
      </div>
    </div>
  );
};
```

## 🎨 UI/UX Implementation Guide

### 1. Where to Add Glossary Features

#### Main Navigation
- Add "Glossary" link between "Community" and "About"
- Icon: 📖 or info icon
- Mobile: Include in hamburger menu

#### Species Cards
Add tooltips for:
- Conservation status (LC, VU, EN, CR)
- CITES Appendix (I, II, III)
- CMS Appendix (I, II)
- Family name

#### Trade Tab
Add tooltips for:
- All specimen types
- Purpose codes (when showing single letters)
- Source codes
- "Importer/Exporter" headers

#### Filters
Add (?) icons next to:
- Conservation status options
- CITES Appendix options
- Taxonomic filters

### 2. Tooltip Behavior

```jsx
// Tooltip configuration
const TOOLTIP_CONFIG = {
  delay: 300,                    // Show after 300ms hover
  hideDelay: 100,               // Hide quickly
  maxWidth: 300,                // Maximum tooltip width
  placement: 'top',             // Default placement
  interactive: true,            // Allow hovering over tooltip
  arrow: true,                  // Show arrow pointer
  theme: 'light-border'         // Light theme with border
};
```

### 3. First-Time User Experience

```jsx
const FirstTimeGlossaryTour = () => {
  const steps = [
    {
      target: '.conservation-status',
      content: 'Hover over any underlined term to see its definition',
      placement: 'bottom'
    },
    {
      target: '.glossary-nav-link',
      content: 'Visit our full glossary to explore all terms',
      placement: 'bottom'
    },
    {
      target: '.cites-badge',
      content: 'CITES badges show international trade protection status',
      placement: 'top'
    }
  ];
  
  return <Tour steps={steps} />;
};
```

## 📱 Mobile Considerations

### Mobile Glossary Access
```jsx
// Mobile-optimized glossary modal
const MobileGlossary = () => {
  return (
    <Sheet>
      <SheetTrigger>
        <Button variant="ghost" size="icon">
          <BookIcon />
        </Button>
      </SheetTrigger>
      <SheetContent side="bottom" className="h-[80vh]">
        <div className="overflow-y-auto">
          {/* Alphabet jump navigation */}
          <div className="sticky top-0 bg-white p-2 flex gap-1 flex-wrap">
            {alphabet.map(letter => (
              <button
                key={letter}
                onClick={() => scrollToLetter(letter)}
                className="w-8 h-8 text-sm"
              >
                {letter}
              </button>
            ))}
          </div>
          
          {/* Terms list */}
          <div className="p-4">
            {groupedTerms.map(group => (
              <div key={group.letter} id={`letter-${group.letter}`}>
                <h3 className="font-bold text-lg mb-2">{group.letter}</h3>
                {group.terms.map(term => (
                  <MobileTermCard key={term.id} term={term} />
                ))}
              </div>
            ))}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
};
```

## 🔍 Search Integration

### Global Search Enhancement
```javascript
// Include glossary in global search
const globalSearch = async (query) => {
  const [species, glossary] = await Promise.all([
    searchSpecies(query),
    searchGlossary(query)
  ]);
  
  return {
    species: species.data,
    glossary: glossary.data,
    // Show glossary results first if exact match
    priority: glossary.data?.[0]?.rank > 0.8 ? 'glossary' : 'species'
  };
};
```

## 📊 Analytics Tracking

Track glossary usage to improve content:

```javascript
// Track tooltip views
const trackGlossaryView = (termId, context) => {
  analytics.track('Glossary Term Viewed', {
    termId,
    context,
    timestamp: new Date()
  });
};

// Track glossary page usage
const trackGlossarySearch = (query, resultsCount) => {
  analytics.track('Glossary Search', {
    query,
    resultsCount,
    timestamp: new Date()
  });
};
```

## 🚦 Implementation Phases

### Phase 1: Core Features (Week 1)
- [ ] Create glossary page with all terms
- [ ] Add navigation link
- [ ] Implement basic search
- [ ] Add category filtering

### Phase 2: Contextual Help (Week 2)
- [ ] Add tooltips to species cards (conservation status)
- [ ] Add tooltips to trade tab
- [ ] Create tooltip component with proper styling
- [ ] Mobile tap-to-reveal functionality

### Phase 3: Enhanced Features (Week 3)
- [ ] First-time user tour
- [ ] Global search integration
- [ ] Related terms navigation
- [ ] Print/download glossary option

## 🎯 Key Terms to Prioritize

### Must Have Tooltips Everywhere:
1. **CITES** - Show on every species card
2. **LC, NT, VU, EN, CR** - IUCN statuses
3. **Appendix I, II, III** - Trade protection levels
4. **Scientific name** - Explain binomial nomenclature

### Trade Tab Essentials:
- All single-letter codes (W, C, T, etc.)
- "Specimens" vs "Live" distinction
- "Commercial" vs other purposes

## 🔗 Related Resources

- **Database Schema**: `/migrations/create_glossary_table.sql`
- **Sample Data**: `/migrations/insert_glossary_data.sql`
- **Original Glossary**: `/glossary_of_terms.md`

## 💡 Pro Tips

1. **Performance**: Cache glossary terms in context to avoid repeated queries
2. **Accessibility**: Ensure tooltips work with keyboard navigation
3. **SEO**: Include glossary terms in meta descriptions for better search
4. **Localization**: Structure ready for future multi-language support

---

The glossary system is ready to make Arctic Tracker more educational and user-friendly. With 80+ terms already loaded, users will have instant access to clear definitions of conservation terminology. Let's make complex conservation data accessible to everyone! 🌍