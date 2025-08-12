# Arctic Tracker API - Deployment Guide

This guide covers deploying the Arctic Tracker API for production use.

## Architecture Overview

Arctic Tracker uses a serverless architecture:
- **Database**: Supabase (PostgreSQL)
- **API**: Supabase auto-generated REST/GraphQL
- **Data Processing**: Python scripts (run on-demand or scheduled)
- **File Storage**: Supabase Storage (for images/documents)

## Prerequisites

- Supabase Pro account (for production)
- Python environment for data processing
- Domain name (optional, for custom domain)
- SSL certificate (handled by Supabase)

## Production Deployment Steps

### 1. Supabase Project Setup

#### Create Production Project
1. Log in to [Supabase Dashboard](https://supabase.com/dashboard)
2. Create new project:
   - Project name: `arctic-tracker-prod`
   - Database password: Generate strong password
   - Region: Choose closest to users
   - Pricing plan: Pro (recommended for production)

#### Configure Project Settings
1. Go to Settings → General
2. Set project name and support email
3. Enable email confirmations if using auth

### 2. Database Deployment

#### Initial Schema Setup
1. Go to SQL Editor in Supabase Dashboard
2. Run migrations in order:

```sql
-- 1. Main schema (db_architechture_june25.sql)
-- 2. CMS tables (migrations/create_cms_listings_table.sql)
-- 3. Glossary tables (migrations/create_glossary_table.sql)
-- 4. Initial data (migrations/insert_glossary_data.sql)
```

#### Configure Connection Pooling
1. Go to Settings → Database
2. Enable connection pooling
3. Pool mode: Transaction
4. Pool size: 15 (adjust based on load)

### 3. Security Configuration

#### API Keys
1. Go to Settings → API
2. Note the following keys:
   - `anon` key: For public frontend access
   - `service_role` key: Keep secure, only for backend

#### Row Level Security
Verify RLS is enabled:
```sql
-- Check RLS status
SELECT schemaname, tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public';
```

#### Environment Variables
Store production credentials securely:
```bash
# Production .env
SUPABASE_URL=https://your-prod-project.supabase.co
SUPABASE_ANON_KEY=your-prod-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-prod-service-key
ENVIRONMENT=production
```

### 4. Data Loading

#### Prepare Production Data
1. Test all scripts in staging first
2. Create backups before major operations
3. Use transaction blocks for critical updates

#### Load Initial Data
```bash
# From a secure environment with production credentials
cd /path/to/Arctic-Tracker-API

# Load CMS data
python core/load_cms_data_to_db.py

# Verify data integrity
python core/verify_cms_data.py

# Generate trade summaries
python core/generate_trade_summaries.py
```

### 5. Performance Optimization

#### Database Indexes
Verify all indexes are created:
```sql
SELECT schemaname, tablename, indexname 
FROM pg_indexes 
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
```

#### Enable Query Performance Monitoring
1. Go to Reports → Query Performance
2. Monitor slow queries
3. Add indexes as needed

#### Configure Caching
In Supabase Dashboard:
1. Settings → API
2. Enable HTTP caching headers
3. Set appropriate cache durations

### 6. Monitoring Setup

#### Database Metrics
- Enable pg_stat_statements
- Monitor connection count
- Track query performance
- Set up alerts for anomalies

#### API Monitoring
- Use Supabase Dashboard metrics
- Monitor request rates
- Track error rates
- Set up uptime monitoring

### 7. Backup Configuration

#### Automated Backups
Supabase Pro includes:
- Daily backups (7 days retention)
- Point-in-time recovery

#### Manual Backup Script
```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump $DATABASE_URL > backups/arctic_tracker_$DATE.sql
gzip backups/arctic_tracker_$DATE.sql
```

### 8. Scheduled Jobs

#### Option 1: GitHub Actions
```yaml
name: Daily Data Update
on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM daily
jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
      - name: Update IUCN Data
        env:
          SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_KEY }}
        run: |
          pip install -r requirements.txt
          python core/rebuild_iucn_assessments.py
```

#### Option 2: Cron Jobs
On a dedicated server:
```cron
# Update trade summaries weekly
0 3 * * 0 cd /app && python core/generate_trade_summaries.py

# Check data integrity daily
0 4 * * * cd /app && python validation/validate_before_load.py
```

### 9. Frontend Deployment

#### Update Frontend Configuration
```javascript
// production.env
VITE_SUPABASE_URL=https://your-prod-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-prod-anon-key
```

#### CORS Configuration
In Supabase Dashboard:
1. Authentication → URL Configuration
2. Add allowed domains
3. Save changes

### 10. Custom Domain (Optional)

#### Setup Custom API Domain
1. Go to Settings → Custom Domains
2. Add domain: `api.arctictracker.org`
3. Update DNS records as instructed
4. Wait for SSL certificate

## Production Checklist

### Pre-Deployment
- [ ] All tests passing
- [ ] Data validation complete
- [ ] Staging environment tested
- [ ] Backup procedures documented
- [ ] Rollback plan prepared

### Security
- [ ] RLS policies active
- [ ] API keys rotated
- [ ] Service role key secured
- [ ] HTTPS enforced
- [ ] CORS configured

### Performance
- [ ] Indexes optimized
- [ ] Query performance acceptable
- [ ] Connection pooling enabled
- [ ] Caching configured
- [ ] Rate limiting set

### Monitoring
- [ ] Alerts configured
- [ ] Logging enabled
- [ ] Metrics dashboard created
- [ ] Uptime monitoring active
- [ ] Error tracking setup

### Documentation
- [ ] API documentation current
- [ ] Runbooks created
- [ ] Contact list updated
- [ ] Recovery procedures documented

## Maintenance Procedures

### Regular Tasks
1. **Daily**: Check monitoring dashboards
2. **Weekly**: Review slow query logs
3. **Monthly**: Update dependencies
4. **Quarterly**: Security audit

### Update Procedures
```bash
# 1. Test in staging
git checkout staging
# Make changes and test

# 2. Deploy to production
git checkout main
git merge staging
# Run deployment scripts

# 3. Verify deployment
python validation/post_deployment_check.py
```

## Troubleshooting

### Common Issues

#### High Database Load
1. Check slow queries
2. Add missing indexes
3. Increase connection pool
4. Scale Supabase plan

#### API Rate Limiting
1. Implement caching
2. Batch requests
3. Use connection pooling
4. Consider CDN

#### Data Sync Issues
1. Check cron logs
2. Verify credentials
3. Test scripts manually
4. Check disk space

## Rollback Procedures

### Database Rollback
```sql
-- Point-in-time recovery
-- Contact Supabase support for assistance
```

### Application Rollback
```bash
# Revert to previous version
git checkout <previous-tag>
# Redeploy
```

## Support Contacts

- **Supabase Support**: support@supabase.com
- **Development Team**: [Contact List]
- **On-Call Schedule**: [Link to schedule]

## Appendix

### Useful Commands

```bash
# Check database size
psql $DATABASE_URL -c "SELECT pg_database_size('postgres');"

# List largest tables
psql $DATABASE_URL -c "
SELECT schemaname, tablename, 
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"

# Export specific table
pg_dump $DATABASE_URL -t species --data-only > species_backup.sql
```

### Performance Queries

```sql
-- Find missing indexes
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE schemaname = 'public'
AND n_distinct > 100
AND correlation < 0.1
ORDER BY n_distinct DESC;

-- Check cache hit ratio
SELECT 
  sum(heap_blks_read) as heap_read,
  sum(heap_blks_hit)  as heap_hit,
  sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) as ratio
FROM pg_statio_user_tables;
```

---

Remember: Always test in staging before deploying to production!