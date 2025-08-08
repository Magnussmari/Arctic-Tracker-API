#!/usr/bin/env node

import { createClient } from '@supabase/supabase-js';
import { config } from 'dotenv';

// Load environment variables
config();

async function testConnection() {
  console.log('🧊 Testing Arctic Tracker MCP Server Connection...\n');

  // Check environment variables
  const supabaseUrl = process.env.SUPABASE_URL;
  const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_ANON_KEY;

  if (!supabaseUrl || !supabaseKey) {
    console.error('❌ Missing environment variables:');
    console.error('   SUPABASE_URL:', supabaseUrl ? '✅ Set' : '❌ Missing');
    console.error('   SUPABASE_SERVICE_ROLE_KEY:', process.env.SUPABASE_SERVICE_ROLE_KEY ? '✅ Set' : '❌ Missing');
    console.error('   SUPABASE_ANON_KEY:', process.env.SUPABASE_ANON_KEY ? '✅ Set' : '❌ Missing');
    console.error('\nPlease configure your .env file with Supabase credentials.');
    process.exit(1);
  }

  console.log('✅ Environment variables configured');

  // Create Supabase client
  const supabase = createClient(supabaseUrl, supabaseKey);

  try {
    // Test basic connection
    console.log('🔍 Testing database connection...');
    const { data, error } = await supabase.from('species').select('id').limit(1);
    
    if (error) {
      console.error('❌ Database connection failed:', error.message);
      process.exit(1);
    }

    console.log('✅ Database connection successful');

    // Test each main table
    const tables = [
      'species',
      'cites_trade_records', 
      'cites_listings',
      'iucn_assessments',
      'species_threats',
      'distribution_ranges',
      'common_names',
      'families'
    ];

    console.log('\n📊 Testing table access...');
    for (const table of tables) {
      try {
        const { data, error } = await supabase.from(table).select('*').limit(1);
        if (error) {
          console.log(`❌ ${table}: ${error.message}`);
        } else {
          console.log(`✅ ${table}: ${data?.length || 0} records accessible`);
        }
      } catch (err) {
        console.log(`❌ ${table}: ${err instanceof Error ? err.message : 'Unknown error'}`);
      }
    }

    // Test a simple species query
    console.log('\n🔍 Testing species query...');
    const { data: speciesData, error: speciesError } = await supabase
      .from('species')
      .select('scientific_name, common_name, class, family')
      .limit(3);

    if (speciesError) {
      console.error('❌ Species query failed:', speciesError.message);
    } else {
      console.log('✅ Species query successful:');
      speciesData?.forEach((species, index) => {
        console.log(`   ${index + 1}. ${species.scientific_name} (${species.common_name})`);
      });
    }

    console.log('\n🎉 Arctic Tracker MCP Server is ready to use!');
    console.log('\nYou can now:');
    console.log('1. Start the server: npm run dev');
    console.log('2. Add it to your MCP client configuration');
    console.log('3. Use the Arctic Tracker tools in your AI assistant');

  } catch (error) {
    console.error('❌ Test failed:', error instanceof Error ? error.message : 'Unknown error');
    process.exit(1);
  }
}

testConnection();
