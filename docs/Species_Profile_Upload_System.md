# Species Profile Upload System Documentation

**Last Updated**: July 10, 2025  
**Status**: Production Ready ✅

## Overview

The Species Profile Upload System automates the process of enhancing Arctic Tracker's species database with AI-generated research profiles. The system intelligently processes JSON files containing conservation data and updates the species table with comprehensive information.

## System Architecture

### File Structure
```
species_data/scite/
├── processed/              # Standardized JSON files (43 files)
│   ├── Scientific_name.json    # Research data files (8 files)
│   └── Scientific_name.json    # Empty templates (35 files)
├── prompts/species/        # Species-specific research prompts (42 files)
└── raw/                   # Raw Scite AI output
```

### Core Scripts

1. **`core/standardize_species_json_files.py`**
   - Renames files to consistent `Scientific_name.json` format
   - Creates empty templates for unresearched species
   - Ensures complete coverage of all 42 Arctic species

2. **`core/upload_species_profiles.py`**
   - Intelligently detects files with research data vs. empty templates
   - Prevents duplicate uploads
   - Updates species table with enhanced conservation data
   - Comprehensive logging and error tracking

## File Detection Algorithm

The system distinguishes between research data and empty templates using:

### Empty Template Detection
- Files containing `"Empty template - awaiting research data"` in metadata
- JSON structure with empty taxonomic fields
- Missing substantial content (descriptions < 100 characters)

### Research Data Detection  
- Files with `species_data` containing substantial descriptions
- Habitat descriptions over 50 characters
- Conservation profiles with scientific content

## Database Integration

### Species Table Enhancement
The upload system populates the following fields in the existing `species` table:

| Field | Source | Description |
|-------|--------|-------------|
| `description` | `species_data.description` | Comprehensive species overview |
| `habitat_description` | `species_data.habitat_description` | Habitat and distribution details |
| `population_size` | `species_data.population_size` | Current population estimates |
| `population_trend` | `species_data.population_trend` | Population trajectory analysis |
| `generation_length` | `species_data.generation_length` | Reproductive cycle duration |
| `movement_patterns` | `species_data.movement_patterns` | Migration and seasonal movements |
| `use_and_trade` | `species_data.use_and_trade` | Commercial and subsistence use |
| `threats_overview` | `species_data.threats_overview` | Primary conservation threats |
| `conservation_overview` | `species_data.conservation_overview` | Conservation measures and status |

## Usage Instructions

### 1. File Standardization
```bash
# Rename files and create empty templates
python core/standardize_species_json_files.py
```

**Output**: All 42 species will have standardized JSON files with consistent naming.

### 2. Data Validation (Dry Run)
```bash
# Test upload without making changes
python core/upload_species_profiles.py --dry-run
```

**Benefits**: 
- Validates file structure
- Identifies files with research data
- Checks for potential upload issues
- No database changes

### 3. Live Upload
```bash
# Upload species with research data
python core/upload_species_profiles.py
```

**Process**:
- Skips empty templates automatically
- Avoids duplicate uploads
- Updates species table with enhanced data
- Creates detailed logs

### 4. Monitor Results
```bash
# View detailed upload logs
tail -f logs/species_upload_*.log
```

## Upload Results Summary

### July 2025 Upload Statistics
- **Total Files Processed**: 43
- **Empty Templates Skipped**: 35 (83%)
- **Research Data Files**: 8 (17%)
- **Already Uploaded**: 4 (duplicates avoided)
- **New Uploads**: 4 species enhanced
- **Success Rate**: 100%

### Successfully Enhanced Species

1. **Asio flammeus** (Short-eared Owl)
   - Enhanced habitat descriptions
   - Population trend analysis
   - Threat assessments

2. **Balaena mysticetus** (Bowhead Whale)
   - Comprehensive population data
   - Arctic-specific habitat information
   - Traditional use documentation

3. **Hyperoodon ampullatus** (Northern Bottlenose Whale)
   - Deep-water habitat preferences
   - Migration pattern details
   - Conservation status updates

4. **Antigone canadensis** (Sandhill Crane)
   - Breeding range information
   - Population trend analysis
   - Migration corridor data

## Error Handling & Prevention

### Duplication Prevention
- Checks existing conservation profiles before upload
- Uses species scientific names for unique identification
- Tracks processed species within session

### Data Validation
- Verifies JSON structure integrity
- Ensures required fields are present
- Validates scientific names against database

### Error Recovery
- Continues processing if individual files fail
- Detailed error logging with specific issues
- Graceful handling of database connection issues

## File Management Best Practices

### Naming Convention
- **Format**: `Scientific_name.json`
- **Examples**: 
  - `Ursus_maritimus.json` (Polar Bear)
  - `Monodon_monoceros.json` (Narwhal)
  - `Balaena_mysticetus.json` (Bowhead Whale)

### File Categories
1. **Research Data Files** (8 files)
   - Contain AI-generated conservation profiles
   - Ready for database upload
   - Include scientific citations and references

2. **Empty Templates** (35 files)
   - Placeholder files for future research
   - Standardized JSON structure
   - Clearly marked as templates

## Integration with AI Workflow

The upload system is part of the larger AI-powered species research workflow:

1. **Species Prompt Generation** → Research questions for each species
2. **Scite AI Research** → Evidence-based content with citations
3. **Gemini 2.5 Pro Structuring** → JSON formatting
4. **Upload System** → Database integration ✅
5. **Frontend Display** → User interface presentation

## Monitoring & Maintenance

### Log Analysis
```bash
# View successful uploads
grep "Successfully uploaded" logs/species_upload_*.log

# Check for errors
grep "Failed to upload" logs/species_upload_*.log

# Monitor file processing
grep "Processing:" logs/species_upload_*.log
```

### Regular Maintenance
- **Weekly**: Review upload logs for any issues
- **Monthly**: Validate data consistency in frontend
- **Quarterly**: Update empty templates with new research

## Future Enhancements

### Planned Improvements
1. **Automated Citations** - Direct reference table population
2. **Batch Processing** - Multiple file upload with progress tracking
3. **Data Versioning** - Track profile update history
4. **Quality Metrics** - Content completeness scoring

### Scalability Considerations
- Support for additional species beyond the current 42
- Multi-language profile support
- Enhanced validation rules
- Performance optimization for large datasets

## Troubleshooting

### Common Issues

**Issue**: "Species not found in database"
**Solution**: Verify scientific name spelling matches database exactly

**Issue**: "Empty template detected"
**Solution**: Ensure JSON contains substantial research content

**Issue**: "Already uploaded"
**Solution**: Normal behavior - system prevents duplicates automatically

### Support Contacts
- **Development Team**: Arctic Tracker API Team
- **Documentation**: `/docs/AI_Workflow_Species_Profile_Generation.md`
- **Database Issues**: Supabase dashboard monitoring

---

## Success Metrics

✅ **100% Coverage**: All 42 Arctic species have JSON files  
✅ **Zero Errors**: All uploads completed successfully  
✅ **Duplication Prevention**: No duplicate entries created  
✅ **Data Quality**: Enhanced species information now available in frontend  

The Species Profile Upload System successfully bridges AI research with database integration, providing a robust foundation for Arctic species conservation data management.