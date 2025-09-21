# Enphase Energy Dashboard Crawler

A comprehensive web crawler built with Playwright and Pydantic to extract customer data from the Enphase Energy manager dashboard.

## Features

- **Multiple Extraction Methods**: Uses page elements, JavaScript variables, API responses, and script tags
- **Data Validation**: Pydantic models ensure data integrity
- **Multiple Output Formats**: JSON, CSV, and Excel export
- **Network Monitoring**: Captures API calls and network requests
- **Authentication Handling**: Manual login support with automatic detection
- **Error Handling**: Robust error handling and logging

## Data Extracted

- Customer name
- Email address
- Physical address
- System ID number
- System size (kW)
- Equipment list
- Installation date
- System status
- Raw data for debugging

## Installation

1. **Run the setup script:**
   ```bash
   chmod +x setup_crawler.sh
   ./setup_crawler.sh
   ```

2. **Activate the virtual environment:**
   ```bash
   source venv_crawler/bin/activate
   ```

3. **Test the installation:**
   ```bash
   python test_crawler.py
   ```

## Usage

### Basic Usage

```bash
# Activate virtual environment
source venv_crawler/bin/activate

# Run the basic crawler
python enphase_crawler.py

# Run the advanced crawler (recommended)
python enphase_advanced_crawler.py
```

### Advanced Usage

```python
from enphase_advanced_crawler import EnphaseAdvancedCrawler
import asyncio

async def custom_crawl():
    crawler = EnphaseAdvancedCrawler(headless=False)
    await crawler.run("https://enlighten.enphaseenergy.com/manager/dashboard/systems")

asyncio.run(custom_crawl())
```

## How It Works

1. **Browser Launch**: Starts a Chromium browser with network interception
2. **Navigation**: Navigates to the Enphase dashboard
3. **Authentication**: Detects login requirement and waits for manual authentication
4. **Data Extraction**: Uses multiple methods to extract customer data:
   - Page element analysis
   - JavaScript variable extraction
   - API response monitoring
   - Script tag parsing
5. **Data Validation**: Validates data using Pydantic models
6. **Export**: Saves data in multiple formats (JSON, CSV, Excel)

## Output Files

The crawler creates timestamped files in the `output/` directory:

- `enphase_customers_YYYYMMDD_HHMMSS.json` - Raw data in JSON format
- `enphase_customers_YYYYMMDD_HHMMSS.csv` - Data in CSV format
- `enphase_customers_YYYYMMDD_HHMMSS.xlsx` - Data in Excel format
- `network_requests_YYYYMMDD_HHMMSS.json` - Network requests for debugging

## Configuration

### Headless Mode
```python
crawler = EnphaseAdvancedCrawler(headless=True)  # Run without browser window
```

### Custom Timeout
```python
crawler = EnphaseAdvancedCrawler(timeout=60000)  # 60 second timeout
```

### Custom Output Directory
```python
await crawler.save_data("custom_output_dir")
```

## Troubleshooting

### Common Issues

1. **Login Required**: The crawler will detect login requirements and wait for manual authentication
2. **No Data Found**: Check the network requests file to see what API calls were made
3. **Browser Issues**: Ensure Playwright browsers are installed: `playwright install chromium`
4. **Permission Errors**: Make sure the output directory is writable

### Debug Mode

Enable debug mode by setting `headless=False` to see the browser window and debug issues.

### Network Analysis

Check the `network_requests_*.json` file to see all API calls made during crawling. This helps identify the correct endpoints for data extraction.

## Data Structure

```json
{
  "name": "John Doe",
  "email": "john.doe@example.com",
  "address": "123 Main St, City, State 12345",
  "system_id": "SYSTEM_12345",
  "system_size": "5.2 kW",
  "equipment": ["Enphase IQ7+ Microinverters", "Solar Panels"],
  "installation_date": "2023-01-15",
  "status": "Active",
  "last_updated": "2024-01-15T10:30:00",
  "raw_data": {...}
}
```

## Requirements

- Python 3.8+
- Playwright
- Pydantic
- Pandas
- BeautifulSoup4
- Requests

## Legal Notice

This crawler is for educational and authorized use only. Ensure you have permission to access and extract data from the Enphase Energy dashboard. Always comply with the website's terms of service and applicable laws.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review the network requests file for debugging
3. Ensure all dependencies are properly installed
4. Verify you have access to the Enphase Energy dashboard