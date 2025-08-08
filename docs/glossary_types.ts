// TypeScript Type Definitions for Glossary Feature
// Arctic Tracker Frontend

export interface GlossaryTerm {
  id: string;
  term: string;
  acronym: string | null;
  definition: string;
  category: GlossaryCategory;
  subcategory: string | null;
  examples: string | null;
  related_terms: string[] | null;
  priority: number;
  display_contexts: DisplayContext[] | null;
  created_at: string;
  updated_at: string;
}

export type GlossaryCategory = 
  | 'Conservation' 
  | 'Trade' 
  | 'Taxonomy' 
  | 'Data' 
  | 'Geography';

export type DisplayContext = 
  | 'species_card'
  | 'trade_tab'
  | 'filters'
  | 'conservation_tab'
  | 'timeline'
  | 'charts'
  | 'species_detail'
  | 'search'
  | 'catch_tab'
  | 'about'
  | 'catch_data';

export interface GlossarySearchResult {
  id: string;
  term: string;
  acronym: string | null;
  definition: string;
  category: GlossaryCategory;
  rank: number; // Search relevance score
}

export interface GlossaryByCategory {
  category: GlossaryCategory;
  subcategory: string | null;
  term_count: number;
  terms: GlossaryTermSummary[];
}

export interface GlossaryTermSummary {
  id: string;
  term: string;
  acronym: string | null;
  definition: string;
  priority: number;
}

// Helper functions for glossary
export const GlossaryHelpers = {
  // Get category icon
  getCategoryIcon: (category: GlossaryCategory): string => {
    const icons: Record<GlossaryCategory, string> = {
      'Conservation': '🌍',
      'Trade': '📦',
      'Taxonomy': '🔬',
      'Data': '📊',
      'Geography': '🗺️'
    };
    return icons[category] || '📖';
  },

  // Get category color (Tailwind classes)
  getCategoryColor: (category: GlossaryCategory): string => {
    const colors: Record<GlossaryCategory, string> = {
      'Conservation': 'bg-green-100 text-green-800',
      'Trade': 'bg-blue-100 text-blue-800',
      'Taxonomy': 'bg-purple-100 text-purple-800',
      'Data': 'bg-yellow-100 text-yellow-800',
      'Geography': 'bg-gray-100 text-gray-800'
    };
    return colors[category] || 'bg-gray-100 text-gray-800';
  },

  // Format term with acronym
  formatTermWithAcronym: (term: GlossaryTerm): string => {
    if (term.acronym) {
      return `${term.term} (${term.acronym})`;
    }
    return term.term;
  },

  // Check if term should show tooltip in context
  shouldShowTooltip: (term: GlossaryTerm, context: DisplayContext): boolean => {
    if (!term.display_contexts || term.display_contexts.length === 0) {
      return false;
    }
    return term.display_contexts.includes(context) && term.priority > 0;
  },

  // Group terms alphabetically
  groupTermsAlphabetically: (terms: GlossaryTerm[]): Record<string, GlossaryTerm[]> => {
    return terms.reduce((acc, term) => {
      const firstLetter = term.term[0].toUpperCase();
      if (!acc[firstLetter]) {
        acc[firstLetter] = [];
      }
      acc[firstLetter].push(term);
      return acc;
    }, {} as Record<string, GlossaryTerm[]>);
  }
};

// Supabase query builders
export const GlossaryQueries = {
  // Get all terms
  getAllTerms: () => ({
    table: 'glossary_terms',
    select: '*',
    order: [
      { column: 'category', ascending: true },
      { column: 'term', ascending: true }
    ]
  }),

  // Get terms by category
  getByCategory: (category: GlossaryCategory) => ({
    table: 'glossary_terms',
    select: '*',
    filter: { category },
    order: [
      { column: 'priority', ascending: false },
      { column: 'term', ascending: true }
    ]
  }),

  // Get contextual terms for tooltips
  getContextualTerms: (context: DisplayContext) => ({
    table: 'glossary_contextual_terms',
    select: '*',
    filter: { display_contexts: { contains: [context] } },
    order: { column: 'priority', ascending: false }
  }),

  // Search terms
  searchTerms: (query: string) => ({
    rpc: 'search_glossary_terms',
    params: { search_query: query }
  }),

  // Get related terms
  getRelatedTerms: (termId: string) => ({
    rpc: 'get_related_glossary_terms',
    params: { term_id: termId }
  })
};

// Priority terms that should always show tooltips
export const PRIORITY_TERMS = [
  'CITES',
  'IUCN',
  'CMS',
  'Appendix I',
  'Appendix II',
  'Appendix III',
  'Endangered',
  'Critically Endangered',
  'Vulnerable',
  'Scientific name',
  'Wild',
  'Commercial'
];

// Term patterns for auto-detection
export const TERM_PATTERNS = {
  // IUCN Status codes
  iucnStatus: /\b(LC|NT|VU|EN|CR|EW|EX)\b/g,
  
  // Trade purpose codes
  purposeCodes: /\b[BEGHKLMNPQSTZ]\b(?=\s*-|\s*:|\s*\))/g,
  
  // Source codes
  sourceCodes: /\b[WRDACFIOUX]\b(?=\s*-|\s*:|\s*\))/g,
  
  // Conservation organizations
  organizations: /\b(CITES|IUCN|NAMMCO|CMS)\b/g,
  
  // Appendix references
  appendices: /\bAppendix\s+(I{1,3}|[123])\b/gi
};

// Tooltip configuration
export interface TooltipConfig {
  delay: number;
  hideDelay: number;
  maxWidth: number;
  placement: 'top' | 'bottom' | 'left' | 'right' | 'auto';
  interactive: boolean;
  arrow: boolean;
  theme: 'light' | 'dark' | 'light-border';
}

export const DEFAULT_TOOLTIP_CONFIG: TooltipConfig = {
  delay: 300,
  hideDelay: 100,
  maxWidth: 300,
  placement: 'top',
  interactive: true,
  arrow: true,
  theme: 'light-border'
};

// Analytics events
export interface GlossaryAnalyticsEvent {
  termId: string;
  term: string;
  category: GlossaryCategory;
  context: DisplayContext | 'glossary_page' | 'search';
  action: 'view' | 'search' | 'click' | 'hover';
  timestamp: Date;
}

// Component props
export interface GlossaryTooltipProps {
  term: string;
  children: React.ReactNode;
  context?: DisplayContext;
  className?: string;
  tooltipConfig?: Partial<TooltipConfig>;
}

export interface GlossaryPageProps {
  initialCategory?: GlossaryCategory;
  initialSearch?: string;
  embedded?: boolean; // For embedding in other pages
}

export interface GlossaryCardProps {
  term: GlossaryTerm;
  showRelated?: boolean;
  compact?: boolean;
  onTermClick?: (term: GlossaryTerm) => void;
}