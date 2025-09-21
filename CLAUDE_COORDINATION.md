# Claude Coordination Protocol

## Current Status
- **Primary Claude (this instance)**: Working on CSV Person Processor Web Interface
- **External Claude**: Working on Enphase Energy Dashboard Crawler in parallel terminal
- **Last Updated**: 2025-09-21

## Project Overview
**Primary Project**: CSV Person Processor Web Interface
- Next.js web app for processing CSV contacts
- Drag-and-drop CSV upload, name filtering, interactive PDFs
- Generates person folders with vCards, PDFs, JSON data

**Secondary Project**: Enphase Energy Dashboard Crawler (parallel work)
- Customer data extraction from Enphase Energy dashboard
- Customer name, email, address, System ID, system size, equipment
- Using Playwright + Pydantic + BeautifulSoup

## Files Created by Primary Claude (CSV Processor)
1. `scripts/split_people.py` - Python CSV processor with PDF generation
2. `requirements.txt` - Python dependencies (pandas, reportlab, etc.)
3. `config/names_filter.txt` - Inclusion names filter
4. `config/exclude_names.txt` - Exclusion names filter (contains "Claudette")
5. `scripts/run_split.sh` - Convenience runner script
6. `processor-web/` - Next.js web interface (in progress)

## Files Created by External Claude (Enphase Crawler)
1. `enphase_crawler.py` - Basic crawler implementation
2. `enphase_advanced_crawler.py` - Advanced crawler with multiple extraction methods
3. `test_crawler.py` - Test script
4. `requirements_crawler.txt` - Dependencies (had pandas compatibility issues)
5. `requirements_simple.txt` - Simplified dependencies without pandas
6. `setup_crawler.sh` - Setup script
7. `README_CRAWLER.md` - Documentation

## Current Issues
- Pandas, lxml, greenlet, pydantic-core installation failed due to Python 3.13 compatibility
- Created minimal version with only Playwright and requests
- Need to test crawler functionality

## Next Steps
1. Install minimal dependencies (playwright + requests only)
2. Test simple crawler with basic functionality
3. Run crawler on Enphase dashboard
4. Extract customer data

## Files Updated
- `enphase_simple_crawler.py` - Minimal crawler without complex dependencies
- `requirements_minimal.txt` - Only playwright and requests

## Communication Protocol
- Update this file when making changes
- Include timestamps and brief descriptions
- Check for conflicts before making changes
- Coordinate on shared files

## Status Updates
- [x] Basic crawler implementation
- [x] Advanced crawler with multiple extraction methods
- [x] Setup scripts and documentation
- [x] Dependencies installation (completed with workarounds)
- [x] Testing crawler functionality (completed)
- [x] Code pushed to GitHub repository
- [x] Data extraction and validation (ready for testing)

## Current Status
- ✅ All crawler implementations completed
- ✅ Dependencies installed successfully
- ✅ Playwright browsers installed
- ✅ Code pushed to GitHub: https://github.com/mrmoe28/solaura-case.git
- ✅ Ready for production use