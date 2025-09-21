#!/bin/bash

echo "🚀 Setting up Enphase Energy Dashboard Crawler"
echo "=============================================="

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv_crawler
source venv_crawler/bin/activate

# Install requirements
echo "📥 Installing Python packages..."
pip install --upgrade pip
pip install -r requirements_crawler.txt

# Install Playwright browsers
echo "🌐 Installing Playwright browsers..."
playwright install chromium

echo "✅ Setup completed!"
echo ""
echo "To run the crawler:"
echo "1. Activate the virtual environment: source venv_crawler/bin/activate"
echo "2. Run the crawler: python enphase_crawler.py"
echo ""
echo "The crawler will open a browser window where you can log in manually."
echo "After logging in, press Enter in the terminal to continue crawling."