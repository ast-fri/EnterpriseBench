#!/usr/bin/env python3
"""
Simple test script to validate EnterpriseBench blog structure
"""

import os
import sys
from pathlib import Path

def test_blog_structure():
    """Test that all required blog files exist"""
    base_dir = Path(__file__).parent
    
    required_files = [
        'index.md',
        '_config.yml',
        'Gemfile',
        '_layouts/default.html',
        'assets/css/style.css',
        'assets/images/architecture_diagram.png',
        'assets/images/evaluation_process.png',
        'assets/images/domain_coverage.png',
        'assets/images/performance_analysis.png',
        '.github/workflows/jekyll.yml'
    ]
    
    missing_files = []
    for file_path in required_files:
        full_path = base_dir / file_path
        if not full_path.exists():
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ Missing required files:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        return False
    
    print("✅ All required blog files exist")
    return True

def test_content_sections():
    """Test that main content sections exist in index.md"""
    base_dir = Path(__file__).parent
    index_file = base_dir / 'index.md'
    
    if not index_file.exists():
        print("❌ index.md not found")
        return False
    
    content = index_file.read_text()
    
    required_sections = [
        '## Abstract',
        '## Introduction',
        '## EnterpriseBench Framework',
        '## Supported Domains',
        '## Evaluation Methods',
        '## Interactive Demos',
        '## Implementation Details',
        '## Authors',
        '## How to Cite'
    ]
    
    missing_sections = []
    for section in required_sections:
        if section not in content:
            missing_sections.append(section)
    
    if missing_sections:
        print("❌ Missing content sections:")
        for section in missing_sections:
            print(f"  - {section}")
        return False
    
    print("✅ All required content sections found")
    return True

def test_image_references():
    """Test that all image references in markdown exist"""
    base_dir = Path(__file__).parent
    index_file = base_dir / 'index.md'
    
    if not index_file.exists():
        print("❌ index.md not found")
        return False
    
    content = index_file.read_text()
    
    # Extract image references
    import re
    image_pattern = r'!\[.*?\]\((assets/images/.*?)\)'
    image_refs = re.findall(image_pattern, content)
    
    missing_images = []
    for img_path in image_refs:
        full_path = base_dir / img_path
        if not full_path.exists():
            missing_images.append(img_path)
    
    if missing_images:
        print("❌ Missing referenced images:")
        for img_path in missing_images:
            print(f"  - {img_path}")
        return False
    
    print(f"✅ All {len(image_refs)} referenced images exist")
    return True

def main():
    """Run all tests"""
    print("🧪 Testing EnterpriseBench blog structure...\n")
    
    tests = [
        test_blog_structure,
        test_content_sections,
        test_image_references
    ]
    
    all_passed = True
    for test in tests:
        if not test():
            all_passed = False
        print()
    
    if all_passed:
        print("🎉 All tests passed! Blog is ready for deployment.")
        return 0
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())