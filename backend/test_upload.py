"""
Simple test script to verify upload functionality
"""

import asyncio
import sys
from pathlib import Path

# Add the backend directory to the path
sys.path.append(str(Path(__file__).parent))

from utils.ai_helpers import AIHelpers

def test_ai_helpers():
    """Test the AI helpers parsing"""
    
    ai_helpers = AIHelpers()
    
    # Test with sample module text
    sample_text = """
    Module Title: Introduction to Computer Science
    Module Code: CS101
    Credits: 15
    Semester: Semester 1
    
    Description: This module introduces students to fundamental concepts in computer science.
    
    Learning Outcomes:
    1. Understand basic programming concepts
    2. Apply problem-solving techniques
    3. Analyze simple algorithms
    
    Assessments:
    - Final Exam (60%)
    - Coursework (40%)
    
    Topics: Programming, Algorithms, Data Structures, Software Engineering
    """
    
    result = ai_helpers.parse_extraction_result(sample_text)
    print("Parsed module data:")
    for key, value in result.items():
        print(f"  {key}: {value}")
    
    # Test weekly plan parsing
    sample_weeks = ai_helpers._create_default_weekly_plan()
    print(f"\nGenerated {len(sample_weeks)} default weeks")
    print(f"Sample week: {sample_weeks[0]}")

if __name__ == "__main__":
    test_ai_helpers()