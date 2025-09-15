"""
Enhanced Ingestion Agent with improved AI instruction clarity
"""

import re
from pathlib import Path
from typing import List, Optional
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from models.schemas import ModuleData, LearningOutcome, Assessment
from utils.file_parser import FileParser
from utils.ai_helpers import AIHelpers

class IngestionAgent:
    """Agent responsible for ingesting and parsing module specifications"""
    """
Enhanced Ingestion Agent - Fixed LLM configuration
"""

import re
from pathlib import Path
from typing import List, Optional
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from models.schemas import ModuleData, LearningOutcome, Assessment
from utils.file_parser import FileParser
from utils.ai_helpers import AIHelpers

class IngestionAgent:
    """Agent responsible for ingesting and parsing module specifications"""
    
    def __init__(self):
        # Fix: Use correct model name and configuration
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",  # Changed from gpt-4 to gpt-4o-mini (correct model name)
            temperature=0.1,
            max_tokens=4000,
            request_timeout=120
        )
        self.file_parser = FileParser()
        self.ai_helpers = AIHelpers()
        
        # Define the enhanced extraction agent
        self.extraction_agent = Agent(
            role='Enhanced Module Specification Extractor',
            goal='Extract comprehensive information from academic module documents including topics, teaching methods, and learning approaches',
            backstory="""You are an expert at parsing academic documents and extracting 
            detailed information including learning outcomes, assessments, course structure,
            main topics, suggested teaching methods, and learning approaches.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
    
    
    async def process_module_spec(
        self, 
        module_file_path: Path, 
        textbook_paths: List[Path] = None
    ) -> ModuleData:
        """Process module specification and extract clean structured data"""
        
        # Parse the main module file
        module_text = self.file_parser.extract_text(module_file_path)
        
        # Parse textbooks if provided
        textbook_titles = []
        if textbook_paths:
            for textbook_path in textbook_paths:
                textbook_titles.append(textbook_path.stem)
        
        # Create extraction task with very specific output format requirements
        extraction_task = Task(
            description=f"""
            Extract information from the module specification and return it as clean JSON.
            
            IMPORTANT: Return ONLY simple values, no nested objects with metadata.
            
            Required format:
            {{
                "title": "string - exact module title",
                "code": "string - module code like CS101",
                "credits": integer - just the number (e.g., 15, 20, 30),
                "semester": "string - semester name (e.g., 'Semester 1', 'Fall 2024')",
                "academic_year": "string - academic year (e.g., '2024/25')",
                "description": "string - brief module description",
                "learning_outcomes": ["string1", "string2", "string3"],
                "assessments": [
                    {{
                        "name": "string - assessment name",
                        "type": "string - assessment type",
                        "weight": integer - percentage as number (e.g., 60, 40)
                    }}
                ],
                "prerequisites": ["string1", "string2"] or [] if none,
                "topics": ["string1", "string2", "string3"],
                "teaching_methods": ["lectures", "tutorials", "seminars", "workshops"],
                "learning_approaches": ["collaborative", "problemBased", "experimental"]
            }}
            
            Module content to analyze:
            {module_text[:6000]}...
            
            Textbooks available: {textbook_titles}
            
            EXTRACTION RULES:
            1. credits: Extract ONLY the number (15, 20, 30, etc.)
            2. semester: Extract as simple string ("Semester 1", "Fall", etc.)
            3. prerequisites: If none mentioned, use empty array []
            4. learning_outcomes: Extract as simple strings, no IDs or metadata
            5. assessments: weight should be just the percentage number
            6. topics: Infer main subject areas covered
            7. teaching_methods: Common methods like "lectures", "tutorials", "seminars"
            8. learning_approaches: Use values like "collaborative", "problemBased", "experimental"
            
            Return only the JSON object, no explanations or additional text.
            """,
            agent=self.extraction_agent,
            expected_output="Clean JSON object with simple values only"
        )
        
        # Execute extraction
        crew = Crew(
            agents=[self.extraction_agent],
            tasks=[extraction_task],
            verbose=True
        )
        
        result = crew.kickoff()
        
        # Parse the result and create ModuleData
        parsed_data = self.ai_helpers.parse_extraction_result(str(result))
        
        # Add debugging information
        print("Parsed data:", parsed_data)
        
        return self._create_module_data(parsed_data, textbook_titles)
    
    def _create_module_data(self, parsed_data: dict, textbook_titles: List[str]) -> ModuleData:
        """Create ModuleData object from parsed information with robust error handling"""
        
        try:
            # Extract learning outcomes with proper structure
            learning_outcomes = []
            if 'learning_outcomes' in parsed_data and isinstance(parsed_data['learning_outcomes'], list):
                for i, lo in enumerate(parsed_data['learning_outcomes']):
                    if isinstance(lo, str) and lo.strip():
                        learning_outcomes.append(LearningOutcome(
                            id=f"LO{i+1}",
                            description=lo.strip(),
                            level=None
                        ))
            
            # If no learning outcomes found, create defaults
            if not learning_outcomes:
                learning_outcomes = [
                    LearningOutcome(id="LO1", description="Understand key concepts", level=None),
                    LearningOutcome(id="LO2", description="Apply knowledge to problems", level=None),
                    LearningOutcome(id="LO3", description="Analyze and evaluate information", level=None)
                ]
            
            # Extract assessments with proper structure
            assessments = []
            if 'assessments' in parsed_data and isinstance(parsed_data['assessments'], list):
                for assessment_data in parsed_data['assessments']:
                    if isinstance(assessment_data, dict):
                        try:
                            weight = assessment_data.get('weight', 0)
                            if isinstance(weight, str):
                                # Extract number from string like "60%"
                                weight_match = re.search(r'(\d+)', weight)
                                weight = int(weight_match.group(1)) if weight_match else 0
                            elif isinstance(weight, float):
                                weight = int(weight)
                            
                            assessments.append(Assessment(
                                name=str(assessment_data.get('name', 'Assessment')),
                                type=str(assessment_data.get('type', 'Unknown')),
                                weight=float(weight),
                                description=assessment_data.get('description')
                            ))
                        except (ValueError, TypeError) as e:
                            print(f"Error processing assessment: {e}")
                            continue
            
            # If no assessments found, create defaults
            if not assessments:
                assessments = [
                    Assessment(name="Final Exam", type="Examination", weight=60.0),
                    Assessment(name="Coursework", type="Assignment", weight=40.0)
                ]
            
            # Ensure all required fields have proper types
            module_data = ModuleData(
                title=str(parsed_data.get('title', 'Unknown Module')),
                code=str(parsed_data.get('code', 'UNKNOWN')),
                credits=int(parsed_data.get('credits', 15)),
                semester=str(parsed_data.get('semester', 'Unknown')),
                academic_year=str(parsed_data.get('academic_year', '2024/25')),
                learning_outcomes=learning_outcomes,
                assessments=assessments,
                description=str(parsed_data.get('description', '')) if parsed_data.get('description') else None,
                prerequisites=list(parsed_data.get('prerequisites', [])),
                textbooks=textbook_titles,
                topics=list(parsed_data.get('topics', [])),
                teaching_methods=list(parsed_data.get('teaching_methods', ['lectures', 'tutorials'])),
                learning_approaches=list(parsed_data.get('learning_approaches', ['collaborative']))
            )
            
            return module_data
            
        except Exception as e:
            print(f"Error creating ModuleData: {e}")
            print(f"Parsed data: {parsed_data}")
            
            # Return a minimal valid ModuleData object
            return ModuleData(
                title="Unknown Module",
                code="UNKNOWN",
                credits=15,
                semester="Unknown",
                academic_year="2024/25",
                learning_outcomes=[
                    LearningOutcome(id="LO1", description="Understand key concepts", level=None)
                ],
                assessments=[
                    Assessment(name="Assessment", type="Unknown", weight=100.0)
                ],
                description=None,
                prerequisites=[],
                textbooks=textbook_titles,
                topics=[],
                teaching_methods=['lectures', 'tutorials'],
                learning_approaches=['collaborative']
            )