// TypeScript Type Definitions for CMS Integration
// For use in Arctic Tracker Frontend

export interface CMSListing {
  id: string;
  species_id: string;
  appendix: 'I' | 'II' | 'I/II';
  agreement: string;
  listed_under: string;
  listing_date: string;
  notes: string | null;
  native_distribution: string[];
  distribution_codes: string[];
  introduced_distribution: string[];
  extinct_distribution: string[];
  distribution_uncertain: string[];
  created_at: string;
  updated_at: string;
}

export interface SpeciesWithCMS extends Species {
  cms_listings?: CMSListing;
}

export interface SpeciesCMSView {
  species_id: string;
  scientific_name: string;
  common_name: string;
  class: string;
  order_name: string;
  family: string;
  cms_appendix: 'I' | 'II' | 'I/II' | null;
  cms_listing_date: string | null;
  native_distribution: string[] | null;
  distribution_codes: string[] | null;
  native_country_count: number | null;
  cms_notes: string | null;
}

// Helper type for conservation status display
export interface ConservationStatus {
  cites?: {
    appendix: string;
    listing_date: string;
    is_current: boolean;
  };
  cms?: {
    appendix: 'I' | 'II' | 'I/II';
    listing_date: string;
    country_count: number;
  };
  iucn?: {
    status: string;
    year_published: number;
    trend: string;
  };
}

// Distribution data structure
export interface DistributionData {
  native: {
    countries: string[];
    iso_codes: string[];
  };
  introduced: {
    countries: string[];
    iso_codes: string[];
  };
  extinct: {
    countries: string[];
    iso_codes: string[];
  };
  uncertain: {
    countries: string[];
    iso_codes: string[];
  };
}

// Filter options for species list
export interface CMSFilterOptions {
  includeAppendixI: boolean;
  includeAppendixII: boolean;
  includeAppendixBoth: boolean;
  includeNotListed: boolean;
  minCountries?: number;
  maxCountries?: number;
}

// Summary statistics
export interface CMSStatistics {
  totalListedSpecies: number;
  appendixI: number;
  appendixII: number;
  appendixBoth: number;
  notListed: number;
  byClass: {
    [className: string]: {
      total: number;
      appendixI: number;
      appendixII: number;
      appendixBoth: number;
    };
  };
}

// Supabase query helpers
export const CMS_QUERIES = {
  // Get CMS listing for a specific species
  getSpeciesCMS: (speciesId: string) => ({
    table: 'cms_listings',
    select: '*',
    filter: { species_id: speciesId },
    single: true
  }),

  // Get all species with CMS listings
  getAllCMSSpecies: () => ({
    table: 'species_cms_listings',
    select: '*',
    filter: { cms_appendix: { not: { is: null } } },
    order: { column: 'scientific_name', ascending: true }
  }),

  // Get species by appendix
  getSpeciesByAppendix: (appendix: 'I' | 'II' | 'I/II') => ({
    table: 'cms_listings',
    select: `
      *,
      species (
        id,
        scientific_name,
        common_name,
        class,
        order_name,
        family,
        default_image_url
      )
    `,
    filter: { appendix },
    order: { column: 'species.scientific_name', ascending: true }
  }),

  // Get distribution summary
  getDistributionSummary: () => ({
    table: 'cms_listings',
    select: `
      species_id,
      appendix,
      array_length(native_distribution, 1) as country_count,
      species (scientific_name, common_name)
    `,
    order: { column: 'country_count', ascending: false }
  })
};

// Utility functions
export const CMSUtils = {
  // Get badge color based on appendix
  getAppendixColor: (appendix: 'I' | 'II' | 'I/II'): string => {
    switch (appendix) {
      case 'I': return '#D32F2F'; // Red
      case 'II': return '#F57C00'; // Orange
      case 'I/II': return '#7B1FA2'; // Purple
      default: return '#757575'; // Gray
    }
  },

  // Get appendix description
  getAppendixDescription: (appendix: 'I' | 'II' | 'I/II'): string => {
    switch (appendix) {
      case 'I': 
        return 'Endangered migratory species requiring strict protection';
      case 'II': 
        return 'Migratory species that would benefit from international cooperation';
      case 'I/II': 
        return 'Listed in both appendices for comprehensive protection';
      default: 
        return 'Not listed in CMS';
    }
  },

  // Format distribution for display
  formatDistribution: (distribution: string[]): string => {
    if (!distribution || distribution.length === 0) return 'No data';
    if (distribution.length <= 3) return distribution.join(', ');
    return `${distribution.slice(0, 3).join(', ')} and ${distribution.length - 3} more`;
  },

  // Check if species needs urgent conservation
  isHighPriority: (listing: CMSListing): boolean => {
    return listing.appendix === 'I' || 
           listing.extinct_distribution.length > 0 ||
           listing.native_distribution.length < 5;
  }
};