"""
Enhanced Pydantic schemas for data validation and serialization
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class LearningOutcome(BaseModel):
    """Learning outcome data structure"""
    id: str
    description: str
    level: Optional[str] = None

class Assessment(BaseModel):
    """Assessment data structure"""
    name: str
    type: str  # exam, coursework, presentation, etc.
    weight: float  # percentage
    description: Optional[str] = None

class WeekPlan(BaseModel):
    """Enhanced weekly plan structure"""
    week_number: int
    title: str
    description: Optional[str] = None
    learning_outcomes: List[str]
    lecture_topics: List[str]
    tutorial_activities: List[str]
    lab_activities: List[str] = []
    readings: List[str] = []
    deliverables: List[str] = []
    external_resources: List[str] = []
    resource_files: List[Dict[str, Any]] = []
    teaching_notes: Optional[str] = None

class ModuleData(BaseModel):
    """Enhanced module specification data"""
    title: str
    code: str
    credits: int
    semester: str
    academic_year: str
    learning_outcomes: List[LearningOutcome]
    assessments: List[Assessment]
    description: Optional[str] = None
    prerequisites: List[str] = []
    textbooks: List[str] = []
    topics: List[str] = []
    teaching_methods: List[str] = []
    learning_approaches: List[str] = []

class ContentItem(BaseModel):
    """Individual content item"""
    title: str
    content: str
    format: str  # markdown, html, etc.
    file_path: Optional[str] = None

class WeeklyContent(BaseModel):
    """Content for a specific week"""
    week_number: int
    lecture_notes: List[ContentItem]
    lecture_slides: List[ContentItem]
    lab_sheets: List[ContentItem]
    quizzes: List[ContentItem]
    seminar_prompts: List[ContentItem]
    transcripts: List[ContentItem]

class GeneratedContent(BaseModel):
    """Complete generated content structure"""
    module_title: str
    weekly_content: List[WeeklyContent]
    generated_at: datetime = Field(default_factory=datetime.now)
    total_files: int = 0

class SessionData(BaseModel):
    """Enhanced session data structure"""
    session_id: str
    module_data: Optional[ModuleData] = None
    week_plans: List[WeekPlan] = []
    generated_content: Optional[GeneratedContent] = None
    status: str = "initialized"
    created_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)
    teaching_methods: List[str] = []
    learning_approaches: List[str] = []
    resource_files: Dict[str, List[Dict[str, Any]]] = {}

class ResourceFile(BaseModel):
    """Resource file information"""
    original_name: str
    saved_name: str
    path: str
    size: int
    type: str
    upload_date: datetime = Field(default_factory=datetime.now)

class MaterialGenerationRequest(BaseModel):
    """Request model for material generation"""
    session_id: str
    materials: List[str]
    enhance_content: bool = True
    use_resources: bool = True

class RegenerationRequest(BaseModel):
    """Request model for material regeneration"""
    session_id: str
    material_id: str
    enhance_content: bool = True
    keep_original: bool = False
    use_resources: bool = True