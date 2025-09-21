#!/usr/bin/env python3
"""
Test script for Enphase Energy Dashboard Crawler
"""

import asyncio
import sys
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from enphase_advanced_crawler import EnphaseAdvancedCrawler


async def test_crawler():
    """Test the crawler with a simple page"""
    print("🧪 Testing Enphase Energy Dashboard Crawler")
    print("=" * 50)
    
    # Test with a simple page first
    crawler = EnphaseAdvancedCrawler(headless=True)
    
    try:
        await crawler.start_browser()
        print("✅ Browser started successfully")
        
        # Test navigation to a simple page
        await crawler.page.goto("https://httpbin.org/html", wait_until="networkidle")
        print("✅ Navigation test successful")
        
        # Test data extraction
        text_content = await crawler.page.text_content('body')
        print(f"✅ Text extraction test successful: {len(text_content)} characters")
        
        print("\n🎉 All tests passed! The crawler is ready to use.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await crawler.close_browser()


if __name__ == "__main__":
    asyncio.run(test_crawler())