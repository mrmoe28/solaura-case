#!/usr/bin/env python3
"""
Enphase Energy Dashboard Crawler
Crawls customer data from the Enphase Energy manager dashboard
"""

import asyncio
import json
import csv
import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from playwright.async_api import async_playwright, Page, Browser
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


class EnphaseCrawler:
    """Main crawler class for Enphase Energy dashboard"""
    
    def __init__(self, headless: bool = False, timeout: int = 30000):
        self.headless = headless
        self.timeout = timeout
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.customer_data: List[CustomerData] = []
        
    async def start_browser(self):
        """Initialize Playwright browser and page"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        self.page = await self.browser.new_page()
        
        # Set viewport and user agent
        await self.page.set_viewport_size({"width": 1920, "height": 1080})
        await self.page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
    async def close_browser(self):
        """Close browser and cleanup"""
        if self.browser:
            await self.browser.close()
            
    async def navigate_to_dashboard(self, url: str = "https://enlighten.enphaseenergy.com/manager/dashboard/systems"):
        """Navigate to the Enphase dashboard"""
        print(f"Navigating to: {url}")
        await self.page.goto(url, wait_until="networkidle", timeout=self.timeout)
        
        # Wait for page to load
        await self.page.wait_for_timeout(3000)
        
        # Check if we need to login
        if await self.page.locator('input[type="email"], input[type="password"]').count() > 0:
            print("🔐 Login required - please authenticate manually")
            await self.handle_authentication()
        else:
            print("✅ Dashboard loaded successfully")
            
    async def handle_authentication(self):
        """Handle authentication process"""
        print("Please log in manually in the browser window...")
        print("Press Enter in the terminal when you're logged in and ready to continue...")
        
        # Wait for user to complete login
        input("Press Enter after completing login...")
        
        # Wait for dashboard to load after login
        await self.page.wait_for_timeout(5000)
        
    async def extract_customer_data(self):
        """Extract customer data from the dashboard"""
        print("🔍 Extracting customer data...")
        
        try:
            # Wait for data to load
            await self.page.wait_for_selector('[data-testid*="system"], .system-card, .customer-card', timeout=10000)
            
            # Look for different possible selectors for customer data
            selectors_to_try = [
                '[data-testid*="system"]',
                '.system-card',
                '.customer-card',
                '.system-item',
                '.customer-item',
                '[class*="system"]',
                '[class*="customer"]'
            ]
            
            customer_elements = []
            for selector in selectors_to_try:
                elements = await self.page.locator(selector).all()
                if elements:
                    customer_elements = elements
                    print(f"Found {len(elements)} elements using selector: {selector}")
                    break
                    
            if not customer_elements:
                print("⚠️  No customer elements found. Let's examine the page structure...")
                await self.analyze_page_structure()
                return
                
            # Extract data from each customer element
            for i, element in enumerate(customer_elements):
                try:
                    customer_data = await self.extract_single_customer(element, i)
                    if customer_data:
                        self.customer_data.append(customer_data)
                        print(f"✅ Extracted data for customer {i+1}: {customer_data.name}")
                except Exception as e:
                    print(f"❌ Error extracting customer {i+1}: {e}")
                    continue
                    
        except Exception as e:
            print(f"❌ Error during data extraction: {e}")
            await self.analyze_page_structure()
            
    async def extract_single_customer(self, element, index: int) -> Optional[CustomerData]:
        """Extract data from a single customer element"""
        try:
            # Try to extract text content
            text_content = await element.text_content()
            if not text_content or len(text_content.strip()) < 10:
                return None
                
            # Look for specific data patterns
            name = await self.extract_field(element, ['name', 'customer', 'owner'], text_content)
            email = await self.extract_field(element, ['email', 'mail'], text_content)
            address = await self.extract_field(element, ['address', 'location'], text_content)
            system_id = await self.extract_field(element, ['system', 'id', 'number'], text_content)
            system_size = await self.extract_field(element, ['size', 'kw', 'kilowatt'], text_content)
            
            # Extract equipment information
            equipment = await self.extract_equipment(element, text_content)
            
            # Create customer data object
            customer = CustomerData(
                name=name or f"Customer {index + 1}",
                email=email or "N/A",
                address=address or "N/A",
                system_id=system_id or f"SYSTEM_{index + 1}",
                system_size=system_size or "N/A",
                equipment=equipment
            )
            
            return customer
            
        except Exception as e:
            print(f"Error extracting customer {index + 1}: {e}")
            return None
            
    async def extract_field(self, element, field_names: List[str], text_content: str) -> Optional[str]:
        """Extract a specific field from customer element"""
        for field_name in field_names:
            # Try to find the field in the text content
            lines = text_content.split('\n')
            for line in lines:
                line_lower = line.lower()
                if field_name.lower() in line_lower:
                    # Extract the value after the field name
                    parts = line.split(':', 1)
                    if len(parts) > 1:
                        return parts[1].strip()
                    # Try to extract from the same line
                    words = line.split()
                    for i, word in enumerate(words):
                        if field_name.lower() in word.lower() and i + 1 < len(words):
                            return words[i + 1].strip()
        return None
        
    async def extract_equipment(self, element, text_content: str) -> List[str]:
        """Extract equipment information"""
        equipment = []
        equipment_keywords = ['inverter', 'panel', 'battery', 'microinverter', 'optimizer', 'monitor']
        
        for keyword in equipment_keywords:
            if keyword.lower() in text_content.lower():
                # Try to extract the full equipment name
                lines = text_content.split('\n')
                for line in lines:
                    if keyword.lower() in line.lower():
                        equipment.append(line.strip())
                        
        return equipment
        
    async def analyze_page_structure(self):
        """Analyze the page structure to understand the layout"""
        print("🔍 Analyzing page structure...")
        
        # Get all elements with text content
        elements = await self.page.locator('*').all()
        print(f"Total elements on page: {len(elements)}")
        
        # Look for common data patterns
        text_content = await self.page.text_content('body')
        print(f"Page text length: {len(text_content)} characters")
        
        # Look for JSON data in script tags
        scripts = await self.page.locator('script').all()
        for i, script in enumerate(scripts):
            content = await script.text_content()
            if content and ('customer' in content.lower() or 'system' in content.lower()):
                print(f"Script {i} contains relevant data:")
                print(content[:500] + "..." if len(content) > 500 else content)
                
        # Look for API calls in network tab
        print("\n🔍 Checking for API endpoints...")
        # This would require intercepting network requests
        
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
        
        print(f"\n📊 Summary: Extracted {len(self.customer_data)} customer records")
        
    async def run(self, url: str = "https://enlighten.enphaseenergy.com/manager/dashboard/systems"):
        """Main crawler execution method"""
        try:
            print("🚀 Starting Enphase Energy Dashboard Crawler")
            print("=" * 50)
            
            await self.start_browser()
            await self.navigate_to_dashboard(url)
            await self.extract_customer_data()
            await self.save_data()
            
            print("\n✅ Crawling completed successfully!")
            
        except Exception as e:
            print(f"❌ Crawler error: {e}")
        finally:
            await self.close_browser()


async def main():
    """Main function to run the crawler"""
    crawler = EnphaseCrawler(headless=False)  # Set to True for headless mode
    await crawler.run()


if __name__ == "__main__":
    asyncio.run(main())