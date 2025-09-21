#!/usr/bin/env python3
"""
Simple Enphase Energy Dashboard Crawler
Minimal version without complex dependencies
"""

import asyncio
import json
import csv
import time
import re
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from playwright.async_api import async_playwright, Page, Browser


class CustomerData:
    """Simple customer data class"""
    
    def __init__(self, name: str = "", email: str = "", address: str = "", 
                 system_id: str = "", system_size: str = "", equipment: List[str] = None):
        self.name = name
        self.email = email
        self.address = address
        self.system_id = system_id
        self.system_size = system_size
        self.equipment = equipment or []
        self.last_updated = datetime.now().isoformat()
        
    def to_dict(self):
        return {
            'name': self.name,
            'email': self.email,
            'address': self.address,
            'system_id': self.system_id,
            'system_size': self.system_size,
            'equipment': self.equipment,
            'last_updated': self.last_updated
        }


class EnphaseSimpleCrawler:
    """Simple crawler for Enphase Energy dashboard"""
    
    def __init__(self, headless: bool = False, timeout: int = 30000):
        self.headless = headless
        self.timeout = timeout
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.customer_data: List[CustomerData] = []
        
    async def start_browser(self):
        """Initialize Playwright browser"""
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
                '[class*="login"]'
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
        """Handle authentication process"""
        print("Please log in manually in the browser window...")
        print("The crawler will automatically detect when you're logged in.")
        
        # Wait for login completion
        max_wait_time = 300  # 5 minutes
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            current_url = self.page.url
            if 'dashboard' in current_url.lower() or 'systems' in current_url.lower():
                print("✅ Login detected - proceeding with data extraction")
                break
                
            await self.page.wait_for_timeout(2000)
        else:
            print("⏰ Login timeout - proceeding anyway")
            
        await self.page.wait_for_timeout(3000)
        
    async def extract_customer_data(self):
        """Extract customer data from the dashboard"""
        print("🔍 Extracting customer data...")
        
        try:
            # Get all text content from the page
            page_text = await self.page.text_content('body')
            if not page_text:
                print("⚠️  No text content found on page")
                return
                
            print(f"📄 Page text length: {len(page_text)} characters")
            
            # Look for customer data patterns
            customers = self.find_customer_patterns(page_text)
            
            for i, customer_data in enumerate(customers):
                customer = CustomerData(
                    name=customer_data.get('name', f"Customer {i+1}"),
                    email=customer_data.get('email', "N/A"),
                    address=customer_data.get('address', "N/A"),
                    system_id=customer_data.get('system_id', f"SYSTEM_{i+1}"),
                    system_size=customer_data.get('system_size', "N/A"),
                    equipment=customer_data.get('equipment', [])
                )
                self.customer_data.append(customer)
                print(f"✅ Extracted customer {i+1}: {customer.name}")
                
        except Exception as e:
            print(f"❌ Error during data extraction: {e}")
            
    def find_customer_patterns(self, text: str) -> List[Dict[str, Any]]:
        """Find customer data patterns in text"""
        customers = []
        
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
        
        # Look for name patterns (simple approach)
        name_pattern = r'([A-Z][a-z]+ [A-Z][a-z]+)'
        names = re.findall(name_pattern, text)
        
        # Create customer records
        max_customers = max(len(emails), len(system_ids), len(kw_values), len(addresses), len(names), 1)
        
        for i in range(max_customers):
            customer = {
                'name': names[i] if i < len(names) else f"Customer {i+1}",
                'email': emails[i] if i < len(emails) else "N/A",
                'address': addresses[i] if i < len(addresses) else "N/A",
                'system_id': system_ids[i] if i < len(system_ids) else f"SYSTEM_{i+1}",
                'system_size': f"{kw_values[i]} kW" if i < len(kw_values) else "N/A",
                'equipment': []
            }
            customers.append(customer)
            
        return customers
        
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
            json.dump([customer.to_dict() for customer in self.customer_data], f, indent=2)
        print(f"✅ Data saved to JSON: {json_file}")
        
        # Save as CSV
        csv_file = output_path / f"enphase_customers_{timestamp}.csv"
        with open(csv_file, 'w', newline='') as f:
            if self.customer_data:
                writer = csv.DictWriter(f, fieldnames=self.customer_data[0].to_dict().keys())
                writer.writeheader()
                for customer in self.customer_data:
                    writer.writerow(customer.to_dict())
        print(f"✅ Data saved to CSV: {csv_file}")
        
        print(f"\n📊 Summary: Extracted {len(self.customer_data)} customer records")
        
    async def run(self, url: str = "https://enlighten.enphaseenergy.com/manager/dashboard/systems"):
        """Main crawler execution method"""
        try:
            print("🚀 Starting Simple Enphase Energy Dashboard Crawler")
            print("=" * 60)
            
            await self.start_browser()
            await self.navigate_to_dashboard(url)
            await self.extract_customer_data()
            await self.save_data()
            
            print("\n✅ Crawling completed successfully!")
            
        except Exception as e:
            print(f"❌ Crawler error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.close_browser()


async def main():
    """Main function to run the simple crawler"""
    crawler = EnphaseSimpleCrawler(headless=False)
    await crawler.run()


if __name__ == "__main__":
    asyncio.run(main())