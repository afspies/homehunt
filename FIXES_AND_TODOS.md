# HomeHunt - Fixes and Short-Term TODOs

## 🚨 Critical Fixes Needed

### Missing Property Fields in Data Model
**Priority: HIGH**

The export system expects these fields that are currently missing from PropertyListing:

```python
# Location fields
'latitude': Optional[float]
'longitude': Optional[float] 
'postcode': Optional[str]  # Currently exists but may need extraction improvements

# Property features
'parking': Optional[bool]
'garden': Optional[bool]
'balcony': Optional[bool]
'pets_allowed': Optional[bool]

# Rental details
'let_type': Optional[LetType]  # e.g., long_term, short_term, student
'is_active': bool = True  # Track if property is still available
```

### Required Implementation Steps:

1. **Update PropertyListing Model** (`homehunt/core/models.py`)
   - Add missing fields with proper types and validation
   - Add database migration if needed

2. **Update Scrapers** (`homehunt/scrapers/`)
   - **Rightmove**: Extract parking, garden, balcony, pets from features/description
   - **Zoopla**: Extract same fields from property details
   - **Both**: Improve postcode extraction from address/location data
   - **Both**: Add geocoding for latitude/longitude (integrate with TravelTime or Google Geocoding)

3. **Update Database Schema** (`homehunt/core/db.py`)
   - Add new columns to property table
   - Create migration script for existing data

4. **Fix Export Service** (`homehunt/exports/service.py`)
   - Currently commented out to avoid errors
   - Re-enable once fields are available

## 🧪 Comprehensive Testing Suite

### Phase 1: Basic Functionality Tests
```bash
# Test authentication and connection
python -m homehunt test-sheets

# Test database status
python -m homehunt stats
python -m homehunt export-status

# Test export templates
python -m homehunt export-templates
```

### Phase 2: Search and Data Collection Tests
```bash
# Test basic search functionality
python -m homehunt search "London" --max-price 2000 --max-results 5
python -m homehunt search "Manchester" --type flat --min-beds 2 --max-results 5
python -m homehunt search "Brighton" --portals rightmove --max-results 3

# Test different search parameters
python -m homehunt search "Edinburgh" --furnished furnished --parking --garden
python -m homehunt search "Birmingham" --radius 2.0 --min-price 1000 --max-price 2500

# Verify data in database
python -m homehunt list --limit 10
python -m homehunt stats
```

### Phase 3: Export Functionality Tests
```bash
# Test CSV exports
python -m homehunt export-csv --output test_basic.csv
python -m homehunt export-csv --output test_filtered.csv --include title,price,bedrooms,area
python -m homehunt export-csv --output rightmove_only.csv --portal rightmove
python -m homehunt export-csv --output budget_props.csv --min-price 1000 --max-price 2500

# Test JSON exports
python -m homehunt export-json --output test_basic.json
python -m homehunt export-json --output test_detailed.json --exclude description,features

# Test Google Sheets exports
python -m homehunt export-sheets --sheet-name "HomeHunt Test 1" --share your-email@gmail.com
python -m homehunt export-sheets --sheet-name "Filtered Properties" --include title,price,bedrooms,area --share your-email@gmail.com
python -m homehunt export-sheets --sheet-name "Rightmove Only" --portal rightmove --clear --share your-email@gmail.com
```

### Phase 4: Advanced Feature Tests
```bash
# Test commute analysis (if TravelTime API configured)
python -m homehunt commute "Canary Wharf" --max-time 30 --transport public_transport
python -m homehunt commute "King's Cross" --transport cycling --max-time 20

# Test configuration-driven searches
python -m homehunt init-config --output test-config.yaml
# Edit the config file, then:
python -m homehunt run-config test-config.yaml --dry-run
python -m homehunt run-config test-config.yaml

# Test export with commute data
python -m homehunt export-csv --output commute_analysis.csv --include title,price,bedrooms,commute_public_transport,commute_cycling
```

### Phase 5: Integration and Stress Tests
```bash
# Test larger data volumes
python -m homehunt search "London" --max-results 50
python -m homehunt search "Manchester" --max-results 30

# Test multiple portal searches
python -m homehunt search "Bristol" --portals all --max-results 20

# Test database cleanup
python -m homehunt cleanup --days 1 --yes

# Test configuration management
python -m homehunt list-configs
python -m homehunt show-config test-config.yaml

# Stress test exports
python -m homehunt export-csv --output large_export.csv
python -m homehunt export-sheets --sheet-name "Large Dataset" --share your-email@gmail.com
```

### Phase 6: Error Handling and Edge Cases
```bash
# Test with invalid inputs
python -m homehunt search "NonexistentPlace12345" --max-results 5
python -m homehunt export-csv --output /invalid/path/test.csv
python -m homehunt export-sheets --sheet-name "Test" --include nonexistent_field

# Test empty database scenarios
python -m homehunt cleanup --days 0 --yes  # Clear all data
python -m homehunt export-csv --output empty_test.csv
python -m homehunt export-sheets --sheet-name "Empty Test" --share your-email@gmail.com

# Test network issues (disconnect internet briefly)
# python -m homehunt search "London" --max-results 5
```

## 🔄 Data Quality Improvements

### Scraping Enhancements Needed:

1. **Property Features Extraction**
   - Improve parsing of bullet points and feature lists
   - Extract parking info from descriptions ("parking space", "garage", "resident parking")
   - Extract garden info ("garden", "outdoor space", "patio", "balcony")
   - Extract pet policy ("pets allowed", "no pets", "pets considered")

2. **Location Data Enhancement**
   - Implement geocoding for latitude/longitude coordinates
   - Improve postcode extraction and validation
   - Add distance calculations to transport hubs

3. **Price Data Normalization** 
   - Ensure price_numeric is consistently populated
   - Handle different price formats (weekly, monthly, annual)
   - Track price changes over time

4. **Data Validation**
   - Add validation for extracted bedrooms/bathrooms numbers
   - Validate property types against known values
   - Check for duplicate listings across portals

## 🚀 Performance Optimizations

### Database Improvements:
- Add indexes on frequently queried fields (price, bedrooms, area, portal)
- Implement property deduplication at database level
- Add data archiving for old/inactive properties

### Scraping Optimizations:
- Implement incremental scraping (only scrape new/changed properties)
- Add caching for expensive operations
- Improve rate limiting to maximize scraping speed

## 📊 Export System Enhancements

### Google Sheets Features:
- Add conditional formatting for price ranges
- Create charts and summary statistics
- Implement real-time data refresh
- Add property comparison sheets

### Additional Export Formats:
- Excel (.xlsx) with multiple sheets
- PDF reports with property summaries
- Real estate-specific formats (REAXML, etc.)

## 🔍 Monitoring and Alerting

### Health Checks:
- Monitor scraping success rates
- Track API rate limits and usage
- Alert on database growth/storage issues
- Monitor export success rates

### Data Quality Metrics:
- Track completeness of property data fields
- Monitor for scraping failures by portal
- Alert on unusual price patterns or outliers

## 🎯 Quick Wins (Easy Implementations)

1. **Add is_active field tracking** - Mark properties as inactive when they disappear from search results
2. **Improve postcode extraction** - Better regex patterns for UK postcodes
3. **Add property age tracking** - Days since first seen, last price change
4. **Export formatting improvements** - Better column names, data formatting
5. **CLI usability** - Better progress indicators, more helpful error messages

## 📋 Testing Checklist

- [ ] All Phase 1 tests pass
- [ ] All Phase 2 tests collect data successfully  
- [ ] All Phase 3 exports work correctly
- [ ] Phase 4 advanced features function properly
- [ ] Phase 5 stress tests complete without errors
- [ ] Phase 6 error cases are handled gracefully
- [ ] Google Sheets are properly formatted and shared
- [ ] CSV/JSON files contain expected data
- [ ] Database statistics are accurate
- [ ] Configuration system works end-to-end

## 🎉 Success Criteria

**Phase 5B Export Integration is considered complete when:**
- ✅ All export formats work reliably
- ✅ Google Sheets integration is fully functional
- ✅ Export templates provide useful defaults
- ✅ CLI commands are intuitive and well-documented
- ✅ Error handling is comprehensive and helpful
- ✅ Performance is acceptable for typical use cases
- ✅ Data quality meets user expectations for property search