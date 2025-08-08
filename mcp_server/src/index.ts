#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from '@modelcontextprotocol/sdk/types.js';
import { createClient, SupabaseClient } from '@supabase/supabase-js';
import { config } from 'dotenv';
import { z } from 'zod';

// Load environment variables
config();

// Validation schemas
const SpeciesQuerySchema = z.object({
  table: z.string(),
  filters: z.record(z.string(), z.any()).optional(),
  limit: z.number().min(1).max(1000).optional(),
  offset: z.number().min(0).optional(),
});

const CitesTradeQuerySchema = z.object({
  species_id: z.string().uuid().optional(),
  year: z.number().optional(),
  importer: z.string().optional(),
  exporter: z.string().optional(),
  purpose: z.string().optional(),
  source: z.string().optional(),
  limit: z.number().min(1).max(1000).optional(),
});

const ConservationStatusSchema = z.object({
  species_id: z.string().uuid().optional(),
  assessment_type: z.enum(['IUCN', 'CITES']).optional(),
  status: z.string().optional(),
});

const SpeciesSearchSchema = z.object({
  query: z.string().min(1),
  search_type: z.enum(['scientific_name', 'common_name', 'family', 'all']).optional(),
  limit: z.number().min(1).max(100).optional(),
});

const ArcticRegionSchema = z.object({
  region: z.enum(['arctic_ocean', 'canadian_arctic', 'greenland', 'svalbard', 'siberian_arctic', 'all']).optional(),
  include_subpopulations: z.boolean().optional(),
});

class ArcticTrackerMCPServer {
  private server: Server;
  private supabase: SupabaseClient;

  constructor() {
    this.server = new Server(
      {
        name: 'arctic-tracker-mcp-server',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    // Initialize Supabase client
    const supabaseUrl = process.env.SUPABASE_URL;
    const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_ANON_KEY;

    if (!supabaseUrl || !supabaseKey) {
      throw new Error('Missing required environment variables: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY');
    }

    this.supabase = createClient(supabaseUrl, supabaseKey);

    this.setupToolHandlers();
  }

  private setupToolHandlers() {
    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: 'list_arctic_species',
            description: 'List Arctic species with optional filtering by taxonomic groups, conservation status, or region',
            inputSchema: {
              type: 'object',
              properties: {
                class: { type: 'string', description: 'Taxonomic class (e.g., MAMMALIA, AVES)' },
                family: { type: 'string', description: 'Taxonomic family' },
                conservation_status: { type: 'string', description: 'IUCN or CITES status' },
                region: { type: 'string', description: 'Arctic region' },
                limit: { type: 'number', minimum: 1, maximum: 100, description: 'Maximum results to return' },
              },
            },
          },
          {
            name: 'search_species',
            description: 'Search for species by scientific name, common name, or family',
            inputSchema: {
              type: 'object',
              properties: {
                query: { type: 'string', description: 'Search query' },
                search_type: { 
                  type: 'string', 
                  enum: ['scientific_name', 'common_name', 'family', 'all'],
                  description: 'Type of search to perform' 
                },
                limit: { type: 'number', minimum: 1, maximum: 100, description: 'Maximum results' },
              },
              required: ['query'],
            },
          },
          {
            name: 'get_cites_trade_data',
            description: 'Query CITES trade records with filtering options',
            inputSchema: {
              type: 'object',
              properties: {
                species_id: { type: 'string', description: 'Species UUID' },
                year: { type: 'number', description: 'Trade year' },
                importer: { type: 'string', description: 'Importing country' },
                exporter: { type: 'string', description: 'Exporting country' },
                purpose: { type: 'string', description: 'Trade purpose code' },
                source: { type: 'string', description: 'Source code' },
                limit: { type: 'number', minimum: 1, maximum: 1000, description: 'Maximum results' },
              },
            },
          },
          {
            name: 'get_conservation_status',
            description: 'Get conservation status information (IUCN Red List, CITES listings)',
            inputSchema: {
              type: 'object',
              properties: {
                species_id: { type: 'string', description: 'Species UUID' },
                assessment_type: { 
                  type: 'string', 
                  enum: ['IUCN', 'CITES'],
                  description: 'Type of assessment' 
                },
                status: { type: 'string', description: 'Conservation status' },
              },
            },
          },
          {
            name: 'get_species_threats',
            description: 'Get threat information for species',
            inputSchema: {
              type: 'object',
              properties: {
                species_id: { type: 'string', description: 'Species UUID' },
                threat_category: { type: 'string', description: 'IUCN threat category' },
                limit: { type: 'number', minimum: 1, maximum: 100, description: 'Maximum results' },
              },
            },
          },
          {
            name: 'get_distribution_data',
            description: 'Get species distribution and range information',
            inputSchema: {
              type: 'object',
              properties: {
                species_id: { type: 'string', description: 'Species UUID' },
                region: { 
                  type: 'string',
                  enum: ['arctic_ocean', 'canadian_arctic', 'greenland', 'svalbard', 'siberian_arctic', 'all'],
                  description: 'Arctic region filter' 
                },
                include_subpopulations: { type: 'boolean', description: 'Include subpopulation data' },
              },
            },
          },
          {
            name: 'get_trade_summary',
            description: 'Get pre-aggregated trade summary data for quick analysis',
            inputSchema: {
              type: 'object',
              properties: {
                species_id: { type: 'string', description: 'Species UUID' },
                year_range: { 
                  type: 'object',
                  properties: {
                    start_year: { type: 'number' },
                    end_year: { type: 'number' },
                  },
                  description: 'Year range for summary' 
                },
                summary_type: { 
                  type: 'string',
                  enum: ['annual', 'country', 'purpose', 'source'],
                  description: 'Type of summary aggregation' 
                },
                limit: { type: 'number', minimum: 1, maximum: 100, description: 'Maximum results' },
              },
            },
          },
          {
            name: 'query_database',
            description: 'Generic database query tool for any table in the Arctic Tracker database',
            inputSchema: {
              type: 'object',
              properties: {
                table: { 
                  type: 'string',
                  enum: [
                    'species', 'cites_trade_records', 'cites_listings', 'iucn_assessments',
                    'species_threats', 'distribution_ranges', 'subpopulations', 'common_names',
                    'conservation_measures', 'timeline_events', 'catch_records', 'species_trade_summary',
                    'families', 'cms_listings', 'cms_assessments', 'cites_trade_suspensions', 
                    'article_summary_table'
                  ],
                  description: 'Database table to query' 
                },
                filters: { 
                  type: 'object',
                  description: 'Filter criteria as key-value pairs' 
                },
                limit: { type: 'number', minimum: 1, maximum: 1000, description: 'Maximum results' },
                offset: { type: 'number', minimum: 0, description: 'Offset for pagination' },
              },
              required: ['table'],
            },
          },
        ] as Tool[],
      };
    });

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          case 'list_arctic_species':
            return await this.listArcticSpecies(args);
          case 'search_species':
            return await this.searchSpecies(args);
          case 'get_cites_trade_data':
            return await this.getCitesTradeData(args);
          case 'get_conservation_status':
            return await this.getConservationStatus(args);
          case 'get_species_threats':
            return await this.getSpeciesThreats(args);
          case 'get_distribution_data':
            return await this.getDistributionData(args);
          case 'get_trade_summary':
            return await this.getTradeSummary(args);
          case 'query_database':
            return await this.queryDatabase(args);
          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      } catch (error) {
        return {
          content: [
            {
              type: 'text',
              text: `Error executing ${name}: ${error instanceof Error ? error.message : String(error)}`,
            },
          ],
          isError: true,
        };
      }
    });
  }

  private async listArcticSpecies(args: any) {
    let query = this.supabase
      .from('species')
      .select(`
        *,
        families(family_name, order_name),
        iucn_assessments(red_list_category, assessment_date),
        cites_listings(appendix, listing_date)
      `);

    if (args.class) {
      query = query.eq('class', args.class);
    }
    if (args.family) {
      query = query.eq('family', args.family);
    }
    if (args.limit) {
      query = query.limit(args.limit);
    } else {
      query = query.limit(50);
    }

    const { data, error } = await query;

    if (error) {
      throw error;
    }

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({
            species_count: data?.length || 0,
            species: data,
          }, null, 2),
        },
      ],
    };
  }

  private async searchSpecies(args: any) {
    const validated = SpeciesSearchSchema.parse(args);
    let query = this.supabase.from('species').select('*');

    switch (validated.search_type || 'all') {
      case 'scientific_name':
        query = query.ilike('scientific_name', `%${validated.query}%`);
        break;
      case 'common_name':
        query = query.ilike('common_name', `%${validated.query}%`);
        break;
      case 'family':
        query = query.ilike('family', `%${validated.query}%`);
        break;
      case 'all':
      default:
        query = query.or(`scientific_name.ilike.%${validated.query}%,common_name.ilike.%${validated.query}%,family.ilike.%${validated.query}%`);
        break;
    }

    query = query.limit(validated.limit || 20);

    const { data, error } = await query;

    if (error) {
      throw error;
    }

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({
            search_query: validated.query,
            search_type: validated.search_type || 'all',
            results_count: data?.length || 0,
            species: data,
          }, null, 2),
        },
      ],
    };
  }

  private async getCitesTradeData(args: any) {
    const validated = CitesTradeQuerySchema.parse(args);
    let query = this.supabase
      .from('cites_trade_records')
      .select(`
        *,
        species(scientific_name, common_name, class, family)
      `);

    if (validated.species_id) {
      query = query.eq('species_id', validated.species_id);
    }
    if (validated.year) {
      query = query.eq('year', validated.year);
    }
    if (validated.importer) {
      query = query.eq('importer', validated.importer);
    }
    if (validated.exporter) {
      query = query.eq('exporter', validated.exporter);
    }
    if (validated.purpose) {
      query = query.eq('purpose', validated.purpose);
    }
    if (validated.source) {
      query = query.eq('source', validated.source);
    }

    query = query.limit(validated.limit || 100);

    const { data, error } = await query;

    if (error) {
      throw error;
    }

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({
            trade_records_count: data?.length || 0,
            filters_applied: validated,
            trade_records: data,
          }, null, 2),
        },
      ],
    };
  }

  private async getConservationStatus(args: any) {
    const validated = ConservationStatusSchema.parse(args);
    
    if (validated.assessment_type === 'IUCN' || !validated.assessment_type) {
      let iucnQuery = this.supabase
        .from('iucn_assessments')
        .select(`
          *,
          species(scientific_name, common_name, class, family)
        `);

      if (validated.species_id) {
        iucnQuery = iucnQuery.eq('species_id', validated.species_id);
      }
      if (validated.status) {
        iucnQuery = iucnQuery.eq('red_list_category', validated.status);
      }

      const { data: iucnData, error: iucnError } = await iucnQuery;

      if (iucnError) {
        throw iucnError;
      }

      if (validated.assessment_type === 'IUCN') {
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify({
                assessment_type: 'IUCN',
                assessments_count: iucnData?.length || 0,
                assessments: iucnData,
              }, null, 2),
            },
          ],
        };
      }
    }

    if (validated.assessment_type === 'CITES' || !validated.assessment_type) {
      let citesQuery = this.supabase
        .from('cites_listings')
        .select(`
          *,
          species(scientific_name, common_name, class, family)
        `);

      if (validated.species_id) {
        citesQuery = citesQuery.eq('species_id', validated.species_id);
      }
      if (validated.status) {
        citesQuery = citesQuery.eq('appendix', validated.status);
      }

      const { data: citesData, error: citesError } = await citesQuery;

      if (citesError) {
        throw citesError;
      }

      if (validated.assessment_type === 'CITES') {
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify({
                assessment_type: 'CITES',
                listings_count: citesData?.length || 0,
                listings: citesData,
              }, null, 2),
            },
          ],
        };
      }
    }

    // If no specific type requested, return both
    const [iucnResult, citesResult] = await Promise.all([
      this.supabase.from('iucn_assessments')
        .select(`*, species(scientific_name, common_name, class, family)`)
        .eq('species_id', validated.species_id || ''),
      this.supabase.from('cites_listings')
        .select(`*, species(scientific_name, common_name, class, family)`)
        .eq('species_id', validated.species_id || ''),
    ]);

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({
            species_id: validated.species_id,
            iucn_assessments: iucnResult.data,
            cites_listings: citesResult.data,
          }, null, 2),
        },
      ],
    };
  }

  private async getSpeciesThreats(args: any) {
    let query = this.supabase
      .from('species_threats')
      .select(`
        *,
        species(scientific_name, common_name, class, family)
      `);

    if (args.species_id) {
      query = query.eq('species_id', args.species_id);
    }
    if (args.threat_category) {
      query = query.eq('threat_category', args.threat_category);
    }

    query = query.limit(args.limit || 50);

    const { data, error } = await query;

    if (error) {
      throw error;
    }

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({
            threats_count: data?.length || 0,
            threats: data,
          }, null, 2),
        },
      ],
    };
  }

  private async getDistributionData(args: any) {
    const validated = ArcticRegionSchema.parse(args);
    let query = this.supabase
      .from('distribution_ranges')
      .select(`
        *,
        species(scientific_name, common_name, class, family)
      `);

    if (args.species_id) {
      query = query.eq('species_id', args.species_id);
    }

    if (validated.region && validated.region !== 'all') {
      query = query.ilike('region_name', `%${validated.region}%`);
    }

    const { data, error } = await query;

    if (error) {
      throw error;
    }

    let result: any = {
      distribution_count: data?.length || 0,
      distribution_data: data,
    };

    // If subpopulations are requested, fetch them too
    if (validated.include_subpopulations && args.species_id) {
      const { data: subpopData, error: subpopError } = await this.supabase
        .from('subpopulations')
        .select('*')
        .eq('species_id', args.species_id);

      if (!subpopError) {
        result.subpopulations = subpopData;
      }
    }

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify(result, null, 2),
        },
      ],
    };
  }

  private async getTradeSummary(args: any) {
    let query = this.supabase
      .from('species_trade_summary')
      .select(`
        *,
        species(scientific_name, common_name, class, family)
      `);

    if (args.species_id) {
      query = query.eq('species_id', args.species_id);
    }

    if (args.year_range) {
      if (args.year_range.start_year) {
        query = query.gte('year', args.year_range.start_year);
      }
      if (args.year_range.end_year) {
        query = query.lte('year', args.year_range.end_year);
      }
    }

    query = query.limit(args.limit || 100);

    const { data, error } = await query;

    if (error) {
      throw error;
    }

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({
            summary_type: args.summary_type || 'general',
            summary_count: data?.length || 0,
            trade_summaries: data,
          }, null, 2),
        },
      ],
    };
  }

  private async queryDatabase(args: any) {
    const validated = SpeciesQuerySchema.parse(args);
    let query = this.supabase.from(validated.table).select('*');

    if (validated.filters) {
      Object.entries(validated.filters).forEach(([key, value]) => {
        query = query.eq(key, value);
      });
    }

    if (validated.limit) {
      query = query.limit(validated.limit);
    } else {
      query = query.limit(100);
    }

    if (validated.offset) {
      query = query.range(validated.offset, validated.offset + (validated.limit || 100) - 1);
    }

    const { data, error } = await query;

    if (error) {
      throw error;
    }

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({
            table: validated.table,
            filters_applied: validated.filters,
            record_count: data?.length || 0,
            records: data,
          }, null, 2),
        },
      ],
    };
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('Arctic Tracker MCP Server running on stdio');
  }
}

const server = new ArcticTrackerMCPServer();
server.run().catch(console.error);
