"""
Enhanced AI helper utilities for parsing and processing AI-generated content
"""

import json
import re
from typing import Dict, List, Any, Optional, Union

class AIHelpers:
    """Utility class for AI-related operations"""
    
    def parse_extraction_result(self, ai_result: str) -> dict:
        """Parse AI extraction result into structured data with proper value extraction"""
        
        try:
            # Try to extract JSON from the result
            json_match = re.search(r'\{.*\}', ai_result, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                raw_data = json.loads(json_str)
                
                # Clean and extract actual values from AI structured responses
                return self._extract_values_from_ai_response(raw_data)
                
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"JSON parsing failed: {e}")
            pass
        
        # Fallback: parse using patterns
        return self._parse_with_patterns(ai_result)
    
    def _extract_values_from_ai_response(self, raw_data: dict) -> dict:
        """Extract actual values from AI's structured response format"""
        
        cleaned_data = {}
        
        for key, value in raw_data.items():
            if isinstance(value, dict):
                # Handle structured AI responses like {'value': 20, 'inferred': True}
                if 'value' in value:
                    cleaned_data[key] = value['value']
                elif 'explicit' in value and 'inferred' in value:
                    # Handle responses like {'explicit': 'None stated', 'inferred': []}
                    if value['explicit'].lower() in ['none', 'none stated', 'not specified', 'not mentioned']:
                        cleaned_data[key] = value.get('inferred', [])
                    else:
                        cleaned_data[key] = value['explicit']
                else:
                    # If it's a dict but doesn't match expected structure, take the first reasonable value
                    for sub_key in ['content', 'description', 'text', 'data']:
                        if sub_key in value:
                            cleaned_data[key] = value[sub_key]
                            break
                    else:
                        # If no recognized sub-key, try to extract a reasonable value
                        cleaned_data[key] = self._extract_reasonable_value(value, key)
                        
            elif isinstance(value, list):
                # Handle lists - clean each item
                cleaned_list = []
                for item in value:
                    if isinstance(item, dict) and 'value' in item:
                        cleaned_list.append(item['value'])
                    elif isinstance(item, dict):
                        cleaned_list.append(self._extract_reasonable_value(item, key))
                    else:
                        cleaned_list.append(item)
                cleaned_data[key] = cleaned_list
                
            else:
                # Simple value, use as-is
                cleaned_data[key] = value
        
        # Ensure required fields have proper types and default values
        return self._ensure_proper_types(cleaned_data)
    
    def _extract_reasonable_value(self, value_dict: dict, field_name: str) -> Any:
        """Extract a reasonable value from a complex dict structure"""
        
        # Common patterns for different field types
        if field_name in ['credits', 'credit', 'credit_hours']:
            # Look for numeric values
            for key, val in value_dict.items():
                if isinstance(val, (int, float)) and val > 0:
                    return int(val)
                elif isinstance(val, str) and val.isdigit():
                    return int(val)
            return 15  # Default credits
            
        elif field_name in ['semester', 'term', 'period']:
            # Look for semester information
            for key, val in value_dict.items():
                if isinstance(val, str) and ('semester' in val.lower() or 'term' in val.lower()):
                    return val
            return "Unknown"
            
        elif field_name in ['prerequisites', 'requirements', 'prereq']:
            # Should return a list
            if isinstance(value_dict, dict):
                for key, val in value_dict.items():
                    if isinstance(val, list):
                        return val
                    elif isinstance(val, str) and val.lower() in ['none', 'none stated', 'not specified']:
                        return []
            return []
            
        elif field_name in ['topics', 'main_topics', 'subject_areas']:
            # Should return a list
            for key, val in value_dict.items():
                if isinstance(val, list):
                    return val
            return []
            
        elif field_name in ['teaching_methods', 'delivery_methods']:
            # Should return a list
            for key, val in value_dict.items():
                if isinstance(val, list):
                    return val
            return ['lectures', 'tutorials']  # Default methods
            
        elif field_name in ['learning_approaches', 'pedagogical_approaches']:
            # Should return a list
            for key, val in value_dict.items():
                if isinstance(val, list):
                    return val
            return ['collaborative']  # Default approach
        
        # Default: return the first non-None value or a reasonable default
        for key, val in value_dict.items():
            if val is not None and val != "":
                return val
        
        return None
    
    def _ensure_proper_types(self, data: dict) -> dict:
        """Ensure all fields have proper types and reasonable defaults"""
        
        # Handle credits - must be integer
        if 'credits' in data:
            credits_val = data['credits']
            if isinstance(credits_val, str):
                # Extract number from string
                credit_match = re.search(r'(\d+)', credits_val)
                data['credits'] = int(credit_match.group(1)) if credit_match else 15
            elif isinstance(credits_val, float):
                data['credits'] = int(credits_val)
            elif not isinstance(credits_val, int):
                data['credits'] = 15
        else:
            data['credits'] = 15
        
        # Handle semester - must be string
        if 'semester' in data:
            semester_val = data['semester']
            if not isinstance(semester_val, str):
                if isinstance(semester_val, dict) and 'value' in semester_val:
                    data['semester'] = str(semester_val['value'])
                else:
                    data['semester'] = str(semester_val) if semester_val else "Unknown"
        else:
            data['semester'] = "Unknown"
        
        # Handle prerequisites - must be list
        if 'prerequisites' in data:
            prereq_val = data['prerequisites']
            if isinstance(prereq_val, str):
                if prereq_val.lower() in ['none', 'none stated', 'not specified', 'not mentioned']:
                    data['prerequisites'] = []
                else:
                    # Split string into list
                    data['prerequisites'] = [item.strip() for item in prereq_val.split(',') if item.strip()]
            elif not isinstance(prereq_val, list):
                data['prerequisites'] = []
        else:
            data['prerequisites'] = []
        
        # Handle topics - must be list
        if 'topics' in data:
            topics_val = data['topics']
            if isinstance(topics_val, str):
                data['topics'] = [item.strip() for item in topics_val.split(',') if item.strip()]
            elif not isinstance(topics_val, list):
                data['topics'] = []
        else:
            data['topics'] = []
        
        # Handle teaching_methods - must be list
        if 'teaching_methods' in data:
            methods_val = data['teaching_methods']
            if isinstance(methods_val, str):
                data['teaching_methods'] = [item.strip() for item in methods_val.split(',') if item.strip()]
            elif not isinstance(methods_val, list):
                data['teaching_methods'] = ['lectures', 'tutorials']
        else:
            data['teaching_methods'] = ['lectures', 'tutorials']
        
        # Handle learning_approaches - must be list
        if 'learning_approaches' in data:
            approaches_val = data['learning_approaches']
            if isinstance(approaches_val, str):
                data['learning_approaches'] = [item.strip() for item in approaches_val.split(',') if item.strip()]
            elif not isinstance(approaches_val, list):
                data['learning_approaches'] = ['collaborative']
        else:
            data['learning_approaches'] = ['collaborative']
        
        # Handle learning_outcomes - ensure proper structure
        if 'learning_outcomes' in data:
            outcomes = data['learning_outcomes']
            if isinstance(outcomes, list):
                cleaned_outcomes = []
                for i, outcome in enumerate(outcomes):
                    if isinstance(outcome, dict):
                        if 'value' in outcome:
                            cleaned_outcomes.append(outcome['value'])
                        elif 'description' in outcome:
                            cleaned_outcomes.append(outcome['description'])
                        else:
                            # Extract first reasonable text value
                            for key, val in outcome.items():
                                if isinstance(val, str) and len(val) > 10:
                                    cleaned_outcomes.append(val)
                                    break
                    elif isinstance(outcome, str):
                        cleaned_outcomes.append(outcome)
                data['learning_outcomes'] = cleaned_outcomes
        
        # Handle assessments - ensure proper structure
        if 'assessments' in data:
            assessments = data['assessments']
            if isinstance(assessments, list):
                cleaned_assessments = []
                for assessment in assessments:
                    if isinstance(assessment, dict):
                        # Extract values from structured assessment data
                        cleaned_assessment = {}
                        for key, val in assessment.items():
                            if isinstance(val, dict) and 'value' in val:
                                cleaned_assessment[key] = val['value']
                            else:
                                cleaned_assessment[key] = val
                        cleaned_assessments.append(cleaned_assessment)
                    else:
                        cleaned_assessments.append(assessment)
                data['assessments'] = cleaned_assessments
        
        # Ensure required string fields are strings
        for field in ['title', 'code', 'academic_year', 'description']:
            if field in data and data[field] is not None:
                if isinstance(data[field], dict) and 'value' in data[field]:
                    data[field] = str(data[field]['value'])
                elif not isinstance(data[field], str):
                    data[field] = str(data[field])
        
        # Set defaults for missing required fields
        if 'title' not in data or not data['title']:
            data['title'] = 'Unknown Module'
        if 'code' not in data or not data['code']:
            data['code'] = 'UNKNOWN'
        if 'academic_year' not in data or not data['academic_year']:
            data['academic_year'] = '2024/25'
        
        return data
    
    def parse_weekly_plan_result(self, ai_result: str) -> List[dict]:
        """Parse weekly plan result into list of week dictionaries with proper value extraction"""
        
        try:
            # Try to extract JSON array
            json_match = re.search(r'\[.*\]', ai_result, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                raw_data = json.loads(json_str)
                
                # Clean each week's data
                cleaned_weeks = []
                for week_data in raw_data:
                    if isinstance(week_data, dict):
                        cleaned_week = self._extract_values_from_ai_response(week_data)
                        cleaned_weeks.append(cleaned_week)
                    else:
                        cleaned_weeks.append(week_data)
                
                return cleaned_weeks
                
        except (json.JSONDecodeError, AttributeError):
            pass
        
        # Fallback: create basic structure
        return self._create_default_weekly_plan()
    
    def _parse_with_patterns(self, text: str) -> dict:
        """Parse text using regex patterns as fallback with proper type handling"""
        
        result = {}
        
        # Extract title
        title_match = re.search(r'(?:title|module):\s*(.+)', text, re.IGNORECASE)
        if title_match:
            result['title'] = title_match.group(1).strip()
        
        # Extract code
        code_match = re.search(r'(?:code|module code):\s*([A-Z0-9]+)', text, re.IGNORECASE)
        if code_match:
            result['code'] = code_match.group(1).strip()
        
        # Extract credits - ensure integer
        credits_match = re.search(r'credits?:\s*(\d+)', text, re.IGNORECASE)
        if credits_match:
            result['credits'] = int(credits_match.group(1))
        else:
            result['credits'] = 15
        
        # Extract semester - ensure string
        semester_match = re.search(r'semester:\s*([^.\n]+)', text, re.IGNORECASE)
        if semester_match:
            result['semester'] = semester_match.group(1).strip()
        else:
            result['semester'] = "Unknown"
        
        # Extract learning outcomes - ensure list
        lo_section = re.search(r'learning outcomes?:(.+?)(?:\n\n|\nassessments?|$)', text, re.IGNORECASE | re.DOTALL)
        if lo_section:
            lo_text = lo_section.group(1)
            learning_outcomes = []
            for line in lo_text.split('\n'):
                line = line.strip()
                if line and (line.startswith('-') or line.startswith('•') or re.match(r'\d+\.', line)):
                    clean_line = re.sub(r'^[-•\d.\s]+', '', line).strip()
                    if clean_line:
                        learning_outcomes.append(clean_line)
            result['learning_outcomes'] = learning_outcomes
        else:
            result['learning_outcomes'] = []
        
        # Extract assessments - ensure proper list structure
        assessment_section = re.search(r'assessments?:(.+?)(?:\n\n|$)', text, re.IGNORECASE | re.DOTALL)
        if assessment_section:
            assessment_text = assessment_section.group(1)
            assessments = []
            for line in assessment_text.split('\n'):
                line = line.strip()
                if line and (line.startswith('-') or line.startswith('•') or re.match(r'\d+\.', line)):
                    # Try to extract name, type, and weight
                    weight_match = re.search(r'(\d+)%', line)
                    weight = int(weight_match.group(1)) if weight_match else 0
                    
                    clean_line = re.sub(r'^[-•\d.\s]+', '', line).strip()
                    clean_line = re.sub(r'\(\d+%\)', '', clean_line).strip()
                    
                    assessments.append({
                        'name': clean_line or 'Assessment',
                        'type': 'Unknown',
                        'weight': weight
                    })
            result['assessments'] = assessments
        else:
            result['assessments'] = []
        
        # Ensure prerequisites is a list
        result['prerequisites'] = []
        
        # Ensure other lists are properly initialized
        result['topics'] = []
        result['teaching_methods'] = ['lectures', 'tutorials']
        result['learning_approaches'] = ['collaborative']
        
        return result
    
    def _create_default_weekly_plan(self) -> List[dict]:
        """Create a default 12-week plan structure with proper types"""
        
        weeks = []
        for i in range(1, 13):
            week = {
                'week_number': i,
                'title': f'Week {i} - Topic {i}',
                'description': f'Overview and learning activities for week {i}',
                'learning_outcomes': [f'LO{min(i, 3)}'],
                'lecture_topics': [f'Topic {i}'],
                'tutorial_activities': [f'Tutorial Activity {i}'],
                'lab_activities': [],
                'readings': [],
                'deliverables': [],
                'external_resources': [],
                'resource_files': [],
                'teaching_notes': ''
            }
            weeks.append(week)
        
        return weeks
    
    def clean_ai_content(self, content: str) -> str:
        """Clean up AI-generated content"""
        
        # Remove excessive whitespace
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = re.sub(r'[ \t]+', ' ', content)
        
        # Remove common AI artifacts
        content = re.sub(r'As an AI.*?[.!]', '', content, flags=re.IGNORECASE)
        content = re.sub(r'I hope this helps.*?[.!]', '', content, flags=re.IGNORECASE)
        
        return content.strip()
    
    def validate_learning_outcomes(self, learning_outcomes: List[str]) -> List[str]:
        """Validate and clean learning outcomes"""
        
        validated = []
        for lo in learning_outcomes:
            if isinstance(lo, str) and len(lo.strip()) > 10:
                # Ensure it starts with a verb
                clean_lo = lo.strip()
                if not re.match(r'^(understand|analyze|evaluate|create|apply|remember)', clean_lo, re.IGNORECASE):
                    # Add a default verb if missing
                    clean_lo = f"Understand {clean_lo.lower()}"
                validated.append(clean_lo)
        
        return validated
    
    def extract_json_from_text(self, text: str) -> Optional[dict]:
        """Extract JSON object from mixed text content"""
        
        # Find JSON-like patterns
        patterns = [
            r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # Simple nested objects
            r'\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]',  # Arrays
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            for match in matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue
        
        return None