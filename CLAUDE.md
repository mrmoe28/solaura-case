# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the Solaura Case Files repository containing two main components:
1. **Enphase Energy Dashboard Crawler** - Python-based web scraping tools for extracting customer data from Enphase Energy dashboards
2. **Processor Web Application** - Next.js web app for processing and managing contact data with file generation capabilities

## Development Commands

### Python Crawler Environment

```bash
# Initial setup
chmod +x setup_crawler.sh
./setup_crawler.sh

# Activate virtual environment
source venv_crawler/bin/activate

# Test installation
python test_crawler.py

# Run crawlers
python enphase_crawler.py           # Basic crawler
python enphase_simple_crawler.py    # Simplified version
python enphase_advanced_crawler.py  # Full-featured crawler (recommended)

# Data processing
./scripts/run_split.sh              # Split contacts by filter criteria
```

### Next.js Web Application

```bash
cd processor-web

# Development
npm run dev         # Start development server
npm run build       # Build for production
npm run start       # Start production server
npm run lint        # Run ESLint

# Install dependencies
npm install
```

## Architecture Overview

### Crawler Components

The crawler system uses a layered architecture:

- **Core Crawler Classes**: `EnphaseAdvancedCrawler`, `EnphaseCrawler`, `EnphaseSimpleCrawler`
  - Built with Playwright for browser automation
  - Pydantic models for data validation (`CustomerData`)
  - Multiple extraction methods: DOM parsing, JavaScript execution, API monitoring, network interception

- **Data Pipeline**:
  - Input: Enphase Energy dashboard URLs
  - Processing: Multi-method data extraction with validation
  - Output: JSON, CSV, Excel formats with timestamped files

- **Network Monitoring**: Captures API calls and responses for debugging and enhanced data extraction

### Web Application Architecture

The processor web app follows Next.js 14 App Router patterns:

- **Core Processing Logic** (`lib/processor.ts`):
  - `PersonData` interface for standardized contact data
  - Name parsing with proper title case and suffix handling
  - Address normalization with US state abbreviations
  - File generation: PDF, vCard, address labels, README files

- **Data Flow**:
  - Input: CSV upload via drag-and-drop (react-dropzone)
  - Processing: Row-by-row contact data extraction and validation
  - Output: Multi-format file packages (PDF, JSON, vCard, etc.)

## Key File Locations

### Configuration
- `config/names_filter.txt` - Name inclusion filters
- `config/exclude_names.txt` - Name exclusion filters
- `requirements_crawler.txt` - Python dependencies
- `processor-web/package.json` - Node.js dependencies

### Data Processing
- `scripts/split_people.py` - Contact filtering and organization
- `processor-web/lib/processor.ts` - Core data processing logic

### Outputs
- `output/` - Crawler results and processed data
- `output/selected_people/` - Individual contact packages

## Dependencies and Technologies

### Python Stack
- **Playwright**: Browser automation and network monitoring
- **Pydantic**: Data validation and serialization
- **Pandas**: Data manipulation and Excel export
- **BeautifulSoup4**: HTML parsing fallback

### JavaScript/TypeScript Stack
- **Next.js 14**: React framework with App Router
- **jsPDF**: PDF generation
- **PapaParse**: CSV parsing
- **Tailwind CSS**: Styling
- **React Dropzone**: File upload interface

## Data Models

### CustomerData (Python)
```python
class CustomerData(BaseModel):
    name: str
    email: str  # Validated for @ symbol
    address: str
    system_id: str  # Cannot be empty
    system_size: str
    equipment: List[str]
    installation_date: Optional[str]
    status: Optional[str]
    last_updated: str
    raw_data: Optional[Dict[str, Any]]
```

### PersonData (TypeScript)
```typescript
interface PersonData {
  full_name: string;
  name: { first: string; middle: string; last: string; suffix: string; };
  company: string;
  email: string;
  phone: string;
  system_id: string;
  address: { street: string; city: string; state: string; postal_code: string; country: string; };
  source: { csv_path: string; row_number: number; raw: any; };
}
```

## Testing

```bash
# Test crawler functionality
python test_crawler.py

# Test web application
cd processor-web
npm run lint
```

## Common Workflows

### Crawler Data Extraction
1. Run setup script to install dependencies and browsers
2. Activate virtual environment
3. Choose appropriate crawler based on complexity needs
4. Manual authentication when prompted
5. Review output files in timestamped directories

### Contact Data Processing
1. Start web application development server
2. Upload CSV file with contact data
3. Configure name filters if needed
4. Generate individual contact packages
5. Download ZIP archive with all files

## Browser and Network Handling

The crawler system includes sophisticated browser automation:
- Automatic browser installation via Playwright
- Network request/response interception for API data
- Manual authentication detection and handling
- Headless and headed browser modes
- Configurable timeouts and retry logic