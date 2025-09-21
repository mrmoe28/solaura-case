#!/usr/bin/env python3
"""
Status check script for Claude coordination
"""

import os
import json
from datetime import datetime
from pathlib import Path

def check_project_status():
    """Check current project status and files"""
    print("🔍 Claude Coordination Status Check")
    print("=" * 50)
    
    # Check if we're in the right directory
    current_dir = Path.cwd()
    print(f"Current directory: {current_dir}")
    
    # Check for key files
    key_files = [
        "enphase_crawler.py",
        "enphase_advanced_crawler.py", 
        "test_crawler.py",
        "requirements_simple.txt",
        "CLAUDE_COORDINATION.md"
    ]
    
    print("\n📁 Key files status:")
    for file in key_files:
        if Path(file).exists():
            size = Path(file).stat().st_size
            print(f"  ✅ {file} ({size} bytes)")
        else:
            print(f"  ❌ {file} (missing)")
    
    # Check for output directory
    output_dir = Path("output")
    if output_dir.exists():
        print(f"\n📂 Output directory exists with {len(list(output_dir.iterdir()))} files")
    else:
        print("\n📂 Output directory not created yet")
    
    # Check for virtual environment
    venv_dir = Path("venv_crawler")
    if venv_dir.exists():
        print(f"\n🐍 Virtual environment exists")
    else:
        print(f"\n🐍 Virtual environment not found")
    
    # Check for any running processes
    print(f"\n⏰ Status check completed at: {datetime.now().isoformat()}")
    
    return {
        "timestamp": datetime.now().isoformat(),
        "directory": str(current_dir),
        "files": {f: Path(f).exists() for f in key_files},
        "output_dir_exists": output_dir.exists(),
        "venv_exists": venv_dir.exists()
    }

if __name__ == "__main__":
    status = check_project_status()
    
    # Save status to file
    with open("claude_status.json", "w") as f:
        json.dump(status, f, indent=2)
    
    print(f"\n💾 Status saved to claude_status.json")