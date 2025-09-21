#!/usr/bin/env python3
"""
Advanced Enphase Energy Dashboard Crawler
Enhanced version with API detection and multiple extraction methods
"""

import asyncio
import json
import csv
import time
import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pathlib import Path

from playwright.async_api import async_playwright, Page, Browser, Route, Request, Response
from pydantic import BaseModel, Field, validator
import pandas as pd


class CustomerData(BaseModel):
    """Pydantic model for customer data validation"""
    name: str = Field(..., description="Customer name")
    email: str = Field(..., description="Customer email address")
    address: str = Field(..., description="Customer address")
    system_id: str = Field(..., description="System ID number")
    system_size: str = Field(..., description="System size in kW")
    equipment: List[str] = Field(default_factory=list, description="List of equipment")
    installation_date: Optional[str] = Field(None, description="Installation date")
    status: Optional[str] = Field(None, description="System status")
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Raw extracted data")
    
    @validator('email')
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email format')
        return v
    
    @validator('system_id')
    def validate_system_id(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('System ID cannot be empty')
        return v.strip()


class EnphaseAdvancedCrawler:
    """Advanced crawler with API detection and multiple extraction methods"""
    
    def __init__(self, headless: bool = False, timeout: int = 30000):
        self.headless = headless
        self.timeout = timeout
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.customer_data: List[CustomerData] = []
        self.api_responses: List[Dict[str, Any]] = []
        self.network_requests: List[Dict[str, Any]] = []
        
    async def start_browser(self):
        """Initialize Playwright browser with network interception"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-web-security']
        )
        
        # Create context with network interception
        context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            extra_http_headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        )
        
        self.page = await context.new_page()
        
        # Set up network request interception
        await self.page.route("**/*", self.handle_route)
        
    async def handle_route(self, route: Route):
        """Handle network requests to capture API calls"""
        request = route.request
        
        # Log all requests
        self.network_requests.append({
            'url': request.url,
            'method': request.method,
            'headers': dict(request.headers),
            'timestamp': datetime.now().isoformat()
        })
        
        # Look for API calls that might contain customer data
        if any(keyword in request.url.lower() for keyword in ['api', 'customer', 'system', 'enlighten', 'data']):
            print(f"🔍 API Request detected: {request.method} {request.url}")
            
        # Continue with the request
        await route.continue_()
        
    async def close_browser(self):
        """Close browser and cleanup"""
        if self.browser:
            await self.browser.close()
            
    async def navigate_to_dashboard(self, url: str = "https://enlighten.enphaseenergy.com/manager/dashboard/systems"):
        """Navigate to the Enphase dashboard with enhanced error handling"""
        print(f"🌐 Navigating to: {url}")
        
        try:
            response = await self.page.goto(url, wait_until="networkidle", timeout=self.timeout)
            print(f"✅ Page loaded with status: {response.status}")
            
            # Wait for page to stabilize
            await self.page.wait_for_timeout(3000)
            
            # Check for login requirement
            login_selectors = [
                'input[type="email"]',
                'input[type="password"]',
                '[data-testid*="login"]',
                '[class*="login"]',
                'form[action*="login"]'
            ]
            
            login_found = False
            for selector in login_selectors:
                if await self.page.locator(selector).count() > 0:
                    login_found = True
                    break
                    
            if login_found:
                print("🔐 Login required - please authenticate manually")
                await self.handle_authentication()
            else:
                print("✅ Dashboard accessible without login")
                
        except Exception as e:
            print(f"❌ Navigation error: {e}")
            raise
            
    async def handle_authentication(self):
        """Enhanced authentication handling"""
        print("Please log in manually in the browser window...")
        print("The crawler will automatically detect when you're logged in.")
        
        # Wait for login completion by monitoring URL changes or specific elements
        max_wait_time = 300  # 5 minutes
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            current_url = self.page.url
            if 'dashboard' in current_url.lower() or 'systems' in current_url.lower():
                print("✅ Login detected - proceeding with data extraction")
                break
                
            # Check for dashboard elements
            dashboard_selectors = [
                '[data-testid*="system"]',
                '.system-card',
                '.dashboard',
                '[class*="system"]'
            ]
            
            for selector in dashboard_selectors:
                if await self.page.locator(selector).count() > 0:
                    print("✅ Dashboard elements detected - proceeding with data extraction")
                    break
            else:
                await self.page.wait_for_timeout(2000)
                continue
            break
        else:
            print("⏰ Login timeout - proceeding anyway")
            
        await self.page.wait_for_timeout(3000)
        
    async def extract_customer_data(self):
        """Enhanced data extraction with multiple methods"""
        print("🔍 Starting comprehensive data extraction...")
        
        # Method 1: Try to extract from API responses
        await self.extract_from_api_responses()
        
        # Method 2: Extract from page elements
        await self.extract_from_page_elements()
        
        # Method 3: Extract from JavaScript variables
        await self.extract_from_js_variables()
        
        # Method 4: Look for data in script tags
        await self.extract_from_script_tags()
        
        print(f"📊 Total customers extracted: {len(self.customer_data)}")
        
    async def extract_from_api_responses(self):
        """Extract data from captured API responses"""
        print("🔍 Extracting from API responses...")
        
        # This would require intercepting responses, which is more complex
        # For now, we'll implement a simpler approach
        
    async def extract_from_page_elements(self):
        """Extract data from visible page elements"""
        print("🔍 Extracting from page elements...")
        
        # Wait for data to load
        try:
            await self.page.wait_for_selector('body', timeout=10000)
        except:
            pass
            
        # Get all text content
        page_text = await self.page.text_content('body')
        if not page_text:
            print("⚠️  No text content found on page")
            return
            
        # Look for customer data patterns
        customers = await self.find_customer_patterns(page_text)
        
        for i, customer_data in enumerate(customers):
            try:
                customer = CustomerData(
                    name=customer_data.get('name', f"Customer {i+1}"),
                    email=customer_data.get('email', "N/A"),
                    address=customer_data.get('address', "N/A"),
                    system_id=customer_data.get('system_id', f"SYSTEM_{i+1}"),
                    system_size=customer_data.get('system_size', "N/A"),
                    equipment=customer_data.get('equipment', []),
                    raw_data=customer_data
                )
                self.customer_data.append(customer)
                print(f"✅ Extracted customer {i+1}: {customer.name}")
            except Exception as e:
                print(f"❌ Error creating customer {i+1}: {e}")
                
    async def find_customer_patterns(self, text: str) -> List[Dict[str, Any]]:
        """Find customer data patterns in text"""
        customers = []
        
        # Split text into lines for analysis
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Look for email patterns
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        
        # Look for system ID patterns
        system_id_pattern = r'(?:system|id|#)\s*:?\s*([A-Za-z0-9-]+)'
        system_ids = re.findall(system_id_pattern, text, re.IGNORECASE)
        
        # Look for kW patterns
        kw_pattern = r'(\d+(?:\.\d+)?)\s*kW'
        kw_values = re.findall(kw_pattern, text, re.IGNORECASE)
        
        # Look for address patterns
        address_pattern = r'\d+\s+[A-Za-z0-9\s,.-]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd)'
        addresses = re.findall(address_pattern, text, re.IGNORECASE)
        
        # Create customer records
        max_customers = max(len(emails), len(system_ids), len(kw_values), len(addresses), 1)
        
        for i in range(max_customers):
            customer = {
                'name': f"Customer {i+1}",
                'email': emails[i] if i < len(emails) else "N/A",
                'address': addresses[i] if i < len(addresses) else "N/A",
                'system_id': system_ids[i] if i < len(system_ids) else f"SYSTEM_{i+1}",
                'system_size': f"{kw_values[i]} kW" if i < len(kw_values) else "N/A",
                'equipment': []
            }
            customers.append(customer)
            
        return customers
        
    async def extract_from_js_variables(self):
        """Extract data from JavaScript variables"""
        print("🔍 Extracting from JavaScript variables...")
        
        try:
            # Look for common variable names that might contain customer data
            js_variables = [
                'window.customerData',
                'window.systemData',
                'window.dashboardData',
                'window.appData',
                'window.userData'
            ]
            
            for var_name in js_variables:
                try:
                    value = await self.page.evaluate(f"() => {var_name}")
                    if value:
                        print(f"Found JS variable: {var_name}")
                        # Process the variable data
                        await self.process_js_data(var_name, value)
                except:
                    continue
                    
        except Exception as e:
            print(f"Error extracting JS variables: {e}")
            
    async def process_js_data(self, var_name: str, data: Any):
        """Process JavaScript variable data"""
        if isinstance(data, dict):
            # Look for customer data in the dictionary
            if 'customers' in data or 'systems' in data:
                customers_data = data.get('customers', data.get('systems', []))
                if isinstance(customers_data, list):
                    for customer_data in customers_data:
                        try:
                            customer = CustomerData(
                                name=customer_data.get('name', 'Unknown'),
                                email=customer_data.get('email', 'N/A'),
                                address=customer_data.get('address', 'N/A'),
                                system_id=customer_data.get('id', customer_data.get('system_id', 'N/A')),
                                system_size=customer_data.get('size', customer_data.get('system_size', 'N/A')),
                                equipment=customer_data.get('equipment', []),
                                raw_data=customer_data
                            )
                            self.customer_data.append(customer)
                            print(f"✅ Extracted from JS: {customer.name}")
                        except Exception as e:
                            print(f"❌ Error processing JS customer data: {e}")
                            
    async def extract_from_script_tags(self):
        """Extract data from script tags"""
        print("🔍 Extracting from script tags...")
        
        try:
            scripts = await self.page.locator('script').all()
            for i, script in enumerate(scripts):
                content = await script.text_content()
                if content and any(keyword in content.lower() for keyword in ['customer', 'system', 'data', 'api']):
                    print(f"Found relevant script {i+1}")
                    # Try to extract JSON data from script
                    await self.extract_json_from_script(content)
                    
        except Exception as e:
            print(f"Error extracting from script tags: {e}")
            
    async def extract_json_from_script(self, script_content: str):
        """Extract JSON data from script content"""
        try:
            # Look for JSON patterns
            json_patterns = [
                r'var\s+\w+\s*=\s*({.*?});',
                r'window\.\w+\s*=\s*({.*?});',
                r'const\s+\w+\s*=\s*({.*?});',
                r'let\s+\w+\s*=\s*({.*?});'
            ]
            
            for pattern in json_patterns:
                matches = re.findall(pattern, script_content, re.DOTALL)
                for match in matches:
                    try:
                        data = json.loads(match)
                        if isinstance(data, dict) and any(key in data for key in ['customers', 'systems', 'data']):
                            print("Found JSON data in script")
                            await self.process_js_data('script_data', data)
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            print(f"Error extracting JSON from script: {e}")
            
    async def save_data(self, output_dir: str = "output"):
        """Save extracted data to various formats"""
        if not self.customer_data:
            print("⚠️  No data to save")
            return
            
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save as JSON
        json_file = output_path / f"enphase_customers_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump([customer.dict() for customer in self.customer_data], f, indent=2)
        print(f"✅ Data saved to JSON: {json_file}")
        
        # Save as CSV
        csv_file = output_path / f"enphase_customers_{timestamp}.csv"
        df = pd.DataFrame([customer.dict() for customer in self.customer_data])
        df.to_csv(csv_file, index=False)
        print(f"✅ Data saved to CSV: {csv_file}")
        
        # Save as Excel
        excel_file = output_path / f"enphase_customers_{timestamp}.xlsx"
        df.to_excel(excel_file, index=False)
        print(f"✅ Data saved to Excel: {excel_file}")
        
        # Save network requests for debugging
        network_file = output_path / f"network_requests_{timestamp}.json"
        with open(network_file, 'w') as f:
            json.dump(self.network_requests, f, indent=2)
        print(f"✅ Network requests saved to: {network_file}")
        
        print(f"\n📊 Summary: Extracted {len(self.customer_data)} customer records")
        
    async def run(self, url: str = "https://enlighten.enphaseenergy.com/manager/dashboard/systems"):
        """Main crawler execution method"""
        try:
            print("🚀 Starting Advanced Enphase Energy Dashboard Crawler")
            print("=" * 60)
            
            await self.start_browser()
            await self.navigate_to_dashboard(url)
            await self.extract_customer_data()
            await self.save_data()
            
            print("\n✅ Advanced crawling completed successfully!")
            
        except Exception as e:
            print(f"❌ Crawler error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.close_browser()


async def main():
    """Main function to run the advanced crawler"""
    crawler = EnphaseAdvancedCrawler(headless=False)
    await crawler.run()


if __name__ == "__main__":
    asyncio.run(main())