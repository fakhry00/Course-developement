"""
Main FastAPI application for the AI-Powered Course Material Generator
"""

import os
import shutil
import json
import re
import math
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import logging
import asyncio
import shutil
import tempfile
import zipfile
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, File, UploadFile, Request, Form, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
from dotenv import load_dotenv

# Import the models from the models module
from models.schemas import (
    ModuleData, 
    WeekPlan, 
    GeneratedContent, 
    LearningOutcome, 
    Assessment,
    ContentItem,
    WeeklyContent,
    SessionData,
    ResourceFile,
    MaterialGenerationRequest,
    RegenerationRequest
)

try:
    from agents.ingestion_agent import IngestionAgent
    from agents.planning_agent import PlanningAgent
    from agents.content_generator import ContentGenerator
    from agents.packaging_agent import PackagingAgent
    from utils.file_parser import FileParser
    from utils.export_tools import ExportTools
except ImportError as e:
    print(f"Warning: Could not import some modules: {e}")
    print("Some features may not work properly until all dependencies are installed.")

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Course Material Generator", 
    version="1.0.0",
    description="Generate comprehensive course materials with AI assistance"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Initialize directories
OUTPUT_DIR = Path("outputs")
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)

# Persistent storage for session data (SQLite-backed)
from db import SessionStore
session_store = SessionStore(Path("data") / "app.db")
regeneration_requests = {}

class SessionManager:
    @staticmethod
    def create_session() -> str:
        session_id = str(uuid.uuid4())
        base = {
            'session_id': session_id,
            'module_data': None,
            'week_plans': [],
            'generated_content': {},
            'status': 'initialized',
            'generation_status': 'initialized',
            'created_at': datetime.now().isoformat(),
            'last_activity': datetime.now().isoformat(),
            'total_materials': 0,
            'completed_materials': [],
            'progress_updates': [],
            'teaching_methods': [],
            'learning_approaches': [],
            'resource_files': {}
        }
        session_store.create(base)
        return session_id
    
    @staticmethod
    def get_session(session_id: str) -> dict:
        return session_store.get(session_id)
    
    @staticmethod
    def update_session(session_id: str, data: dict):
        if session_store.exists(session_id):
            session_store.update(session_id, data)

# Error handling middleware
@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"Unhandled error in {request.url.path}: {str(e)}")
        if request.url.path.startswith("/api/"):
            return JSONResponse(
                status_code=500,
                content={"detail": f"Internal server error: {str(e)}"}
            )
        else:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error": "An unexpected error occurred. Please try again."
            })

# Utility functions
def format_file_size(bytes_size: int) -> str:
    """Format file size in human readable format"""
    if bytes_size == 0:
        return '0 B'
    
    size_names = ['B', 'KB', 'MB', 'GB']
    i = int(math.floor(math.log(bytes_size, 1024)))
    p = math.pow(1024, i)
    s = round(bytes_size / p, 2)
    
    return f"{s} {size_names[i]}"

def get_media_type(file_extension: str) -> str:
    """Get media type for file extension"""
    media_types = {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.txt': 'text/plain',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif'
    }
    return media_types.get(file_extension.lower(), 'application/octet-stream')

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for cross-platform compatibility"""
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = re.sub(r'\s+', '_', filename)
    return filename[:50]

def send_progress_update(session_id: str, update: dict):
    """Send progress update to session with timestamp"""
    session_data = SessionManager.get_session(session_id)
    progress_updates = session_data.get('progress_updates', [])
    
    # Add timestamp to update
    update['timestamp'] = datetime.now().isoformat()
    
    progress_updates.append(update)
    SessionManager.update_session(session_id, {'progress_updates': progress_updates})

def get_session_materials(session_id: str) -> list:
    """Get all materials for a session"""
    materials = []
    output_dir = OUTPUT_DIR / session_id
    
    if not output_dir.exists():
        return materials
    
    material_id = 1
    
    # Scan all files in output directory
    for file_path in output_dir.rglob('*'):
        if file_path.is_file() and not file_path.name.startswith('.'):
            # Extract information from file path and name
            relative_path = file_path.relative_to(output_dir)
            
            # Determine week number from filename or path
            week_match = re.search(r'Week_(\d+)', file_path.name)
            week = int(week_match.group(1)) if week_match else 0
            
            # Determine material type from path
            material_type = determine_material_type(relative_path)
            
            materials.append({
                'id': str(material_id),
                'name': file_path.name,
                'path': str(relative_path),
                'week': week,
                'type': material_type,
                'format': file_path.suffix[1:].upper(),
                'size': file_path.stat().st_size,
                'generated_at': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                'status': 'completed'
            })
            
            material_id += 1
    
    return materials

def determine_material_type(file_path: Path) -> str:
    """Determine material type from file path"""
    path_str = str(file_path).lower()
    
    if 'lecture_notes' in path_str:
        return 'lecture_notes'
    elif 'lecture_slides' in path_str:
        return 'lecture_slides'
    elif 'transcripts' in path_str:
        return 'transcripts'
    elif 'lab_materials' in path_str:
        return 'lab_materials'
    elif 'assessments' in path_str:
        return 'assessments'
    elif 'seminar_materials' in path_str:
        return 'seminar_materials'
    elif 'module_overview' in path_str:
        return 'module_overview'
    elif 'instructor_guide' in path_str:
        return 'instructor_guide'
    else:
        return 'other'

# Main routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page - dashboard"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    """Upload page for module specifications"""
    session_id = SessionManager.create_session()
    return templates.TemplateResponse("upload.html", {
        "request": request,
        "session_id": session_id
    })

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Upload and processing endpoints
@app.post("/api/upload")
async def upload_files(
    session_id: str = Form(...),
    module_file: UploadFile = File(...),
    textbook_files: List[UploadFile] = File(default=[])
):
    """Handle file uploads and process module specifications"""
    
    # Validate file types
    allowed_extensions = ['pdf', 'docx', 'doc']
    if not any(module_file.filename.lower().endswith(ext) for ext in allowed_extensions):
        raise HTTPException(status_code=400, detail="Invalid file type for module specification")
    
    try:
        logger.info(f"Processing upload for session {session_id}")
        
        # Save uploaded files
        module_path = UPLOAD_DIR / f"{session_id}_{module_file.filename}"
        with open(module_path, "wb") as buffer:
            shutil.copyfileobj(module_file.file, buffer)
        
        textbook_paths = []
        for textbook in textbook_files:
            if textbook.filename:
                textbook_path = UPLOAD_DIR / f"{session_id}_{textbook.filename}"
                with open(textbook_path, "wb") as buffer:
                    shutil.copyfileobj(textbook.file, buffer)
                textbook_paths.append(textbook_path)
        
        logger.info(f"Files saved for session {session_id}")
        
        # Process files with ingestion agent
        ingestion_agent = IngestionAgent()
        module_data = await ingestion_agent.process_module_spec(
            module_path, textbook_paths
        )
        
        logger.info(f"Module data processed: {module_data.title}")
        
        # Convert ModuleData to dict for storage
        module_data_dict = {
            'title': module_data.title,
            'code': module_data.code,
            'credits': module_data.credits,
            'semester': module_data.semester,
            'academic_year': module_data.academic_year,
            'learning_outcomes': [
                {
                    'id': lo.id,
                    'description': lo.description,
                    'level': lo.level
                } for lo in module_data.learning_outcomes
            ],
            'assessments': [
                {
                    'name': assessment.name,
                    'type': assessment.type,
                    'weight': assessment.weight,
                    'description': assessment.description
                } for assessment in module_data.assessments
            ],
            'description': module_data.description,
            'prerequisites': module_data.prerequisites,
            'textbooks': module_data.textbooks,
            'topics': module_data.topics,
            'teaching_methods': module_data.teaching_methods,
            'learning_approaches': module_data.learning_approaches
        }
        
        # Update session with proper logging
        SessionManager.update_session(session_id, {
            'module_data': module_data_dict,
            'status': 'ingested',
            'upload_files': {
                'module_file': module_file.filename,
                'textbook_files': [f.filename for f in textbook_files if f.filename]
            }
        })
        
        # Verify the data was stored
        stored_session = SessionManager.get_session(session_id)
        if not stored_session.get('module_data'):
            raise Exception("Failed to store module data in session")
        
        logger.info(f"Session {session_id} updated successfully with module data")
        
        return JSONResponse({
            "status": "success",
            "message": "Files processed successfully",
            "module_data": module_data_dict,
            "session_id": session_id
        })
        
    except Exception as e:
        logger.error(f"Error processing files for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing files: {str(e)}")

def create_fallback_module_data(filename: str) -> dict:
    """Create fallback module data when AI agents are not available"""
    return {
        "title": f"Module from {filename}",
        "code": "UNKNOWN",
        "credits": 15,
        "semester": "Unknown",
        "academic_year": "2024/25",
        "learning_outcomes": [
            {"id": "LO1", "description": "Understand key concepts", "level": None},
            {"id": "LO2", "description": "Apply knowledge to problems", "level": None},
            {"id": "LO3", "description": "Analyze and evaluate information", "level": None}
        ],
        "assessments": [
            {"name": "Exam", "type": "exam", "weight": 60.0, "description": None},
            {"name": "Coursework", "type": "coursework", "weight": 40.0, "description": None}
        ],
        "description": "Module description will be extracted from uploaded file",
        "prerequisites": [],
        "textbooks": [],
        "topics": [],
        "teaching_methods": ["lectures", "tutorials"],
        "learning_approaches": ["collaborative"]
    }

@app.post("/api/generate-plan")
async def generate_weekly_plan(
    session_id: str = Form(...),
    module_info: Optional[str] = Form(None)
):
    """Generate weekly plan using planning agent"""
    
    try:
        session_data = SessionManager.get_session(session_id)
        
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found. Please start a new session.")
        
        module_data_dict = session_data.get('module_data')
        
        if not module_data_dict:
            raise HTTPException(
                status_code=400, 
                detail="Module data not found. Please go back to upload and process your module specification first."
            )
        
        # Convert dict back to ModuleData object
        try:
            # Reconstruct learning outcomes
            learning_outcomes = []
            for lo_data in module_data_dict.get('learning_outcomes', []):
                learning_outcomes.append(LearningOutcome(
                    id=lo_data.get('id', ''),
                    description=lo_data.get('description', ''),
                    level=lo_data.get('level')
                ))
            
            # Reconstruct assessments
            assessments = []
            for assess_data in module_data_dict.get('assessments', []):
                assessments.append(Assessment(
                    name=assess_data.get('name', ''),
                    type=assess_data.get('type', ''),
                    weight=assess_data.get('weight', 0),
                    description=assess_data.get('description')
                ))
            
            # Create ModuleData object
            module_data = ModuleData(
                title=module_data_dict.get('title', ''),
                code=module_data_dict.get('code', ''),
                credits=module_data_dict.get('credits', 15),
                semester=module_data_dict.get('semester', ''),
                academic_year=module_data_dict.get('academic_year', ''),
                description=module_data_dict.get('description'),
                prerequisites=module_data_dict.get('prerequisites', []),
                textbooks=module_data_dict.get('textbooks', []),
                topics=module_data_dict.get('topics', []),
                teaching_methods=module_data_dict.get('teaching_methods', []),
                learning_approaches=module_data_dict.get('learning_approaches', []),
                learning_outcomes=learning_outcomes,
                assessments=assessments
            )
            
        except Exception as e:
            logger.error(f"Error reconstructing module data: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail="Error processing module data. Please re-upload your module specification."
            )
        
        # Update module data with any additional info from the form
        if module_info:
            try:
                additional_info = json.loads(module_info)
                if 'topics' in additional_info:
                    module_data.topics.extend(additional_info['topics'])
                if 'teaching_methods' in additional_info:
                    module_data.teaching_methods = additional_info['teaching_methods']
                if 'learning_approaches' in additional_info:
                    module_data.learning_approaches = additional_info['learning_approaches']
            except json.JSONDecodeError:
                logger.warning("Could not parse additional module info")
        
        # Generate weekly plan
        planning_agent = PlanningAgent()
        week_plans = await planning_agent.generate_weekly_plan(module_data)
        
        # Convert WeekPlan objects to dicts for storage
        week_plans_dict = []
        for plan in week_plans:
            week_plans_dict.append({
                "week_number": plan.week_number,
                "title": plan.title,
                "description": plan.description or "",
                "learning_outcomes": plan.learning_outcomes,
                "lecture_topics": plan.lecture_topics,
                "tutorial_activities": plan.tutorial_activities,
                "lab_activities": plan.lab_activities,
                "readings": plan.readings,
                "deliverables": plan.deliverables,
                "external_resources": plan.external_resources,
                "resource_files": plan.resource_files,
                "teaching_notes": plan.teaching_notes or ""
            })
        
        # Update session
        SessionManager.update_session(session_id, {
            'week_plans': week_plans_dict,
            'status': 'planned',
            'plan_generated_at': datetime.now().isoformat()
        })
        
        return JSONResponse({
            "status": "success",
            "week_plans": week_plans_dict
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating plan for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating plan: {str(e)}")

def create_fallback_weekly_plan() -> List[dict]:
    """Create fallback weekly plan when AI agents are not available"""
    weeks = []
    for i in range(1, 13):
        weeks.append({
            'week_number': i,
            'title': f'Week {i} - Topic {i}',
            'description': f'This week covers topic {i} with related activities and assessments',
            'learning_outcomes': [f'LO{min(i, 3)}'],
            'lecture_topics': [f'Topic {i}.1', f'Topic {i}.2'],
            'tutorial_activities': [f'Tutorial Activity {i}'],
            'lab_activities': [] if i % 3 != 0 else [f'Lab Exercise {i}'],
            'readings': [f'Reading {i}'],
            'deliverables': [] if i % 4 != 0 else [f'Assignment {i}'],
            'external_resources': [],
            'resource_files': [],
            'teaching_notes': f'Focus on practical application of concepts in week {i}'
        })
    return weeks

# Review and approval endpoints
@app.get("/review/{session_id}", response_class=HTMLResponse)
async def review_plan(request: Request, session_id: str):
    """Review page for weekly plans with enhanced error handling"""
    
    try:
        logger.info(f"Loading review page for session {session_id}")
        
        session_data = SessionManager.get_session(session_id)
        
        if not session_data:
            logger.error(f"Session {session_id} not found")
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error": f"Session {session_id} not found. Please start a new project."
            })
        
        module_data = session_data.get('module_data')
        if not module_data:
            logger.error(f"No module data found for session {session_id}")
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error": "Module Data Missing - No module specification data was found for this session. Please upload and process your module specification first.",
                "show_upload_button": True
            })
        
        week_plans = session_data.get('week_plans', [])
        
        logger.info(f"Review page loaded for session {session_id}: module='{module_data.get('title', 'Unknown')}', weeks={len(week_plans)}")
        
        return templates.TemplateResponse("week_review.html", {
            "request": request,
            "session_id": session_id,
            "module_data": module_data,
            "week_plans": week_plans
        })
        
    except Exception as e:
        logger.error(f"Error loading review page for session {session_id}: {str(e)}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": f"Error loading review page: {str(e)}"
        })

@app.post("/api/approve-plan")
async def approve_plan(
    session_id: str = Form(...),
    approved_weeks: str = Form(...)
):
    """Approve or modify weekly plans"""
    
    try:
        week_plans = json.loads(approved_weeks)
        SessionManager.update_session(session_id, {
            'week_plans': week_plans,
            'status': 'approved'
        })
        
        return JSONResponse({"status": "success", "message": "Plan approved"})
        
    except Exception as e:
        logger.error(f"Error approving plan: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error approving plan: {str(e)}")

@app.post("/api/save-weekly-plan")
async def save_weekly_plan(request: Request):
    """Save weekly plan to text file with enhanced information"""
    data = await request.json()
    session_id = data.get('session_id')
    
    session_data = SessionManager.get_session(session_id)
    if not session_data.get('week_plans'):
        raise HTTPException(status_code=400, detail="No weekly plan found")
    
    try:
        # Create output directory
        output_dir = OUTPUT_DIR / session_id
        output_dir.mkdir(exist_ok=True)
        
        # Save detailed weekly plan as text file
        plan_file = output_dir / "weekly_plan_detailed.txt"
        with open(plan_file, 'w', encoding='utf-8') as f:
            f.write(f"DETAILED WEEKLY PLAN\n")
            f.write(f"Session: {session_id}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")
            
            module_data = session_data.get('module_data', {})
            f.write(f"MODULE INFORMATION\n")
            f.write("-" * 30 + "\n")
            f.write(f"Title: {module_data.get('title', 'Unknown')}\n")
            f.write(f"Code: {module_data.get('code', 'Unknown')}\n")
            f.write(f"Credits: {module_data.get('credits', 'Unknown')}\n")
            f.write(f"Semester: {module_data.get('semester', 'Unknown')}\n\n")
            
            # Add teaching methods and learning approaches if available
            teaching_methods = session_data.get('teaching_methods', [])
            if teaching_methods:
                f.write(f"Teaching Methods: {', '.join(teaching_methods)}\n")
            
            learning_approaches = session_data.get('learning_approaches', [])
            if learning_approaches:
                f.write(f"Learning Approaches: {', '.join(learning_approaches)}\n")
            
            f.write("\n" + "=" * 60 + "\n\n")
            
            for week in session_data['week_plans']:
                f.write(f"WEEK {week.get('week_number', '?')}: {week.get('title', 'Untitled')}\n")
                f.write("=" * 50 + "\n")
                
                # Week description
                if week.get('description'):
                    f.write(f"Description:\n{week['description']}\n\n")
                
                if week.get('learning_outcomes'):
                    f.write("Learning Outcomes:\n")
                    for lo in week['learning_outcomes']:
                        f.write(f"  • {lo}\n")
                    f.write("\n")
                
                if week.get('lecture_topics'):
                    f.write("Lecture Topics:\n")
                    for topic in week['lecture_topics']:
                        f.write(f"  • {topic}\n")
                    f.write("\n")
                
                if week.get('tutorial_activities'):
                    f.write("Tutorial Activities:\n")
                    for activity in week['tutorial_activities']:
                        f.write(f"  • {activity}\n")
                    f.write("\n")
                
                if week.get('lab_activities'):
                    f.write("Lab Activities:\n")
                    for lab in week['lab_activities']:
                        f.write(f"  • {lab}\n")
                    f.write("\n")
                
                if week.get('readings'):
                    f.write("Required Readings:\n")
                    for reading in week['readings']:
                        f.write(f"  • {reading}\n")
                    f.write("\n")
                
                if week.get('deliverables'):
                    f.write("Deliverables:\n")
                    for deliverable in week['deliverables']:
                        f.write(f"  • {deliverable}\n")
                    f.write("\n")
                
                if week.get('external_resources'):
                    f.write("External Resources:\n")
                    for resource in week['external_resources']:
                        f.write(f"  • {resource}\n")
                    f.write("\n")
                
                # Resource files information
                resource_files = session_data.get('resource_files', {}).get(f"week_{week.get('week_number', 0)}", [])
                if resource_files:
                    f.write("Uploaded Resource Files:\n")
                    for file_info in resource_files:
                        f.write(f"  • {file_info.get('original_name', 'Unknown')} ({format_file_size(file_info.get('size', 0))})\n")
                    f.write("\n")
                
                # Teaching notes
                if week.get('teaching_notes'):
                    f.write("Teaching Notes:\n")
                    f.write(f"{week['teaching_notes']}\n\n")
                
                f.write("\n" + "-" * 50 + "\n\n")
        
        return JSONResponse({"status": "success", "file_path": str(plan_file)})
        
    except Exception as e:
        logger.error(f"Error saving plan: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error saving plan: {str(e)}")

# Material selection and generation endpoints
@app.get("/material-selection/{session_id}", response_class=HTMLResponse)
async def material_selection_page(request: Request, session_id: str):
    """Material selection page"""
    return templates.TemplateResponse("material_selection.html", {
        "request": request,
        "session_id": session_id
    })

@app.get("/generate/{session_id}", response_class=HTMLResponse)
async def generation_page(request: Request, session_id: str, materials: str = ""):
    """Generation progress page"""
    selected_materials = materials.split(',') if materials else []
    return templates.TemplateResponse("generation_progress.html", {
        "request": request,
        "session_id": session_id,
        "selected_materials": materials
    })

@app.post("/api/start-generation")
async def start_generation(request: Request):
    """Start the generation process"""
    data = await request.json()
    session_id = data.get('session_id')
    materials = data.get('materials', [])
    
    session_data = SessionManager.get_session(session_id)
    if not session_data:
        raise HTTPException(status_code=400, detail="Session not found")
    
    # Calculate totals
    week_plans = session_data.get('week_plans', [])
    total_weeks = len(week_plans)
    
    # Calculate total materials based on selection
    materials_per_week = 0
    for material_type in materials:
        if material_type in ['lecture_notes', 'lecture_slides', 'transcripts']:
            materials_per_week += 2  # Assume 2 items per week for these types
        elif material_type in ['lab_materials', 'assessments', 'seminar_materials']:
            materials_per_week += 1  # 1 item per week for these
    
    overview_materials = 0
    if 'module_overview' in materials:
        overview_materials += 1
    if 'instructor_guide' in materials:
        overview_materials += 1
    
    total_materials = (materials_per_week * total_weeks) + overview_materials
    
    # Store generation parameters
    SessionManager.update_session(session_id, {
        'generation_materials': materials,
        'generation_status': 'started',
        'total_materials': total_materials,
        'completed_materials': []
    })
    
    # Start background generation
    import asyncio
    asyncio.create_task(generate_materials_background(session_id, materials))
    
    return JSONResponse({
        "status": "started",
        "total_weeks": total_weeks,
        "total_materials": total_materials
    })

@app.get("/api/generation-progress/{session_id}")
async def generation_progress_stream(session_id: str):
    """Server-sent events for generation progress"""
    import asyncio
    
    async def event_stream():
        while True:
            session_data = SessionManager.get_session(session_id)
            status = session_data.get('generation_status', 'unknown')
            
            if status == 'completed':
                yield f"data: {json.dumps({'type': 'generation_complete'})}\n\n"
                break
            elif status == 'error':
                yield f"data: {json.dumps({'type': 'error', 'message': session_data.get('error_message', 'Unknown error')})}\n\n"
                break
            
            # Check for progress updates
            progress_updates = session_data.get('progress_updates', [])
            for update in progress_updates:
                yield f"data: {json.dumps(update)}\n\n"
            
            # Clear sent updates
            SessionManager.update_session(session_id, {'progress_updates': []})
            
            await asyncio.sleep(1)  # Check every second
    
    return StreamingResponse(event_stream(), media_type="text/plain")

async def generate_materials_background1(session_id: str, materials: List[str]):
    """Background task to generate materials with fallback"""
    try:
        session_data = SessionManager.get_session(session_id)
        module_data_dict = session_data['module_data']
        week_plans = session_data['week_plans']
        
        # Send generation start event
        send_progress_update(session_id, {
            'type': 'generation_start',
            'module_title': module_data_dict.get('title', 'Unknown Module'),
            'total_weeks': len(week_plans)
        })
        
        # Simulate generation process
        import asyncio
        
        for i, week_plan in enumerate(week_plans):
            # Check if generation should continue
            current_status = SessionManager.get_session(session_id).get('generation_status')
            if current_status in ['paused', 'stopped']:
                break
            
            # Send week start update
            send_progress_update(session_id, {
                'type': 'week_start',
                'week_number': week_plan.get('week_number', i + 1),
                'week_title': week_plan.get('title', f'Week {i + 1}')
            })
            
            # Generate materials for this week
            for material_type in materials:
                if current_status in ['paused', 'stopped']:
                    break
                
                await simulate_material_generation(session_id, week_plan, material_type)
            
            # Send week complete update
            send_progress_update(session_id, {
                'type': 'week_complete',
                'week_number': week_plan.get('week_number', i + 1)
            })
        
        # Generate overview materials
        if 'module_overview' in materials:
            await simulate_overview_generation(session_id, 'module_overview', 'Module Overview')
        
        if 'instructor_guide' in materials:
            await simulate_overview_generation(session_id, 'instructor_guide', 'Instructor Guide')
        
        # Mark as completed
        SessionManager.update_session(session_id, {'generation_status': 'completed'})
        send_progress_update(session_id, {'type': 'generation_complete'})
        
    except Exception as e:
        logger.error(f"Error in background generation: {str(e)}")
        SessionManager.update_session(session_id, {
            'generation_status': 'error',
            'error_message': str(e)
        })
        send_progress_update(session_id, {
            'type': 'error',
            'message': str(e)
        })

async def generate_materials_background(session_id: str, materials: List[str]):
    """Background task to generate materials with fallback"""
    try:
        session_data = SessionManager.get_session(session_id)
        module_data_dict = session_data['module_data']
        week_plans = session_data['week_plans']
        
        # Send generation start event
        send_progress_update(session_id, {
            'type': 'generation_start',
            'module_title': module_data_dict.get('title', 'Unknown Module'),
            'total_weeks': len(week_plans)
        })
        
        # Simulate generation process
        import asyncio
        content_generator = ContentGenerator()
        for i, week_plan in enumerate(week_plans):
            # Check if generation should continue
            current_status = SessionManager.get_session(session_id).get('generation_status')
            if current_status in ['paused', 'stopped']:
                break
            
            # Send week start update
            send_progress_update(session_id, {
                'type': 'week_start',
                'week_number': week_plan.get('week_number', i + 1),
                'week_title': week_plan.get('title', f'Week {i + 1}')
            })
            
            # Generate materials for this week
            if 'lecture_notes' in materials:
                if current_status in ['paused', 'stopped']:
                    break
                await generate_and_save_material(
                    session_id, content_generator, module_data_dict, week_plan,
                    'lecture_notes', 'Lecture Notes'
                )
            
            if 'lecture_slides' in materials:
                if current_status in ['paused', 'stopped']:
                    break
                await generate_and_save_material(
                    session_id, content_generator, module_data_dict, week_plan,
                    'lecture_slides', 'Lecture Slides'
                )
            
            if 'transcripts' in materials:
                if current_status in ['paused', 'stopped']:
                    break
                await generate_and_save_material(
                    session_id, content_generator, module_data_dict, week_plan,
                    'transcripts', 'Lecture Transcripts'
                )
            
            if 'lab_materials' in materials:
                if current_status in ['paused', 'stopped']:
                    break
                await generate_and_save_material(
                    session_id, content_generator, module_data_dict, week_plan,
                    'lab_materials', 'Lab Materials'
                )
            
            if 'assessments' in materials:
                if current_status in ['paused', 'stopped']:
                    break
                await generate_and_save_material(
                    session_id, content_generator, module_data_dict, week_plan,
                    'assessments', 'Assessments'
                )
            
            if 'seminar_materials' in materials:
                if current_status in ['paused', 'stopped']:
                    break
                await generate_and_save_material(
                    session_id, content_generator, module_data_dict, week_plan,
                    'seminar_materials', 'Seminar Materials'
                )
            #for material_type in materials:
            #    if current_status in ['paused', 'stopped']:
            #        break
            #    
            #    await simulate_material_generation(session_id, week_plan, material_type)
            
            # Send week complete update
            send_progress_update(session_id, {
                'type': 'week_complete',
                'week_number': week_plan.get('week_number', i + 1)
            })
        
        # Generate overview materials
        if 'module_overview' in materials or 'instructor_guide' in materials:
            packaging_agent = PackagingAgent()
            if 'module_overview' in materials:
                await packaging_agent._create_module_overview(module_data_dict, OUTPUT_DIR / session_id)
                send_progress_update(session_id, {
                    'type': 'material_complete',
                    'week_number': 0,
                    'material_type': 'module_overview',
                    'material_name': 'Module Overview',
                    'file_path': '00_Module_Overview.pdf',
                    'file_format': 'PDF'
                })
            
            if 'instructor_guide' in materials:
                generated_content = GeneratedContent(
                    module_title=module_data_dict.title,
                    weekly_content=[],
                    total_files=len(session_data.get('completed_materials', []))
                )
                await packaging_agent._create_instructor_guide(module_data_dict, generated_content, OUTPUT_DIR / session_id)
                send_progress_update(session_id, {
                    'type': 'material_complete',
                    'week_number': 0,
                    'material_type': 'instructor_guide',
                    'material_name': 'Instructor Guide',
                    'file_path': '00_Instructor_Guide.pdf',
                    'file_format': 'PDF'
                })
        #if 'module_overview' in materials:
        #    await simulate_overview_generation(session_id, 'module_overview', 'Module Overview')
        #
        #if 'instructor_guide' in materials:
        #    await simulate_overview_generation(session_id, 'instructor_guide', 'Instructor Guide')
        
        # Mark as completed
        SessionManager.update_session(session_id, {'generation_status': 'completed'})
        send_progress_update(session_id, {'type': 'generation_complete'})
        
    except Exception as e:
        logger.error(f"Error in background generation: {str(e)}")
        SessionManager.update_session(session_id, {
            'generation_status': 'error',
            'error_message': str(e)
        })
        send_progress_update(session_id, {
            'type': 'error',
            'message': str(e)
        })

async def simulate_material_generation(session_id: str, week_plan: dict, material_type: str):
    """Simulate material generation for demonstration"""
    import asyncio
    
    material_name = f"{material_type.replace('_', ' ').title()} for {week_plan.get('title', 'Week')}"
    
    # Send start update
    send_progress_update(session_id, {
        'type': 'material_start',
        'week_number': week_plan.get('week_number', 1),
        'material_type': material_type,
        'material_name': material_name
    })
    
    # Simulate generation time
    await asyncio.sleep(2)
    
    # Create output directory
    output_dir = OUTPUT_DIR / session_id
    output_dir.mkdir(exist_ok=True)
    
    # Create material-specific directories
    material_dirs = {
        'lecture_notes': output_dir / "01_Lecture_Notes",
        'lecture_slides': output_dir / "02_Lecture_Slides",
        'lab_materials': output_dir / "03_Lab_Materials",
        'assessments': output_dir / "04_Assessments",
        'seminar_materials': output_dir / "05_Seminar_Materials",
        'transcripts': output_dir / "06_Transcripts"
    }
    
    material_dir = material_dirs.get(material_type, output_dir)
    material_dir.mkdir(exist_ok=True)
    
    # Create sample file
    week_num = week_plan.get('week_number', 1)
    file_name = f"Week_{week_num:02d}_{sanitize_filename(material_name)}.txt"
    file_path = material_dir / file_name
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(f"Generated {material_name}\n")
        f.write(f"Week: {week_num}\n")
        f.write(f"Title: {week_plan.get('title', 'Untitled')}\n")
        f.write(f"Description: {week_plan.get('description', 'No description')}\n")
        f.write(f"Generated at: {datetime.now().isoformat()}\n\n")
        f.write("This is a sample generated content file.\n")
    
    # Send completion update
    send_progress_update(session_id, {
        'type': 'material_complete',
        'week_number': week_num,
        'material_type': material_type,
        'material_name': material_name,
        'file_path': str(file_path.relative_to(OUTPUT_DIR / session_id)),
        'file_format': 'TXT',
        'file_size': file_path.stat().st_size
    })

async def simulate_overview_generation(session_id: str, material_type: str, material_name: str):
    """Simulate overview material generation"""
    import asyncio
    
    await asyncio.sleep(1)
    
    output_dir = OUTPUT_DIR / session_id
    file_name = f"00_{sanitize_filename(material_name)}.txt"
    file_path = output_dir / file_name
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(f"Generated {material_name}\n")
        f.write(f"Generated at: {datetime.now().isoformat()}\n\n")
        f.write("This is a sample overview document.\n")
    
    send_progress_update(session_id, {
        'type': 'material_complete',
        'week_number': 0,
        'material_type': material_type,
        'material_name': material_name,
        'file_path': str(file_path.relative_to(OUTPUT_DIR / session_id)),
        'file_format': 'TXT',
        'file_size': file_path.stat().st_size
    })


async def generate_and_save_material(session_id: str, content_generator, module_data, week_plan, material_type: str, material_name: str):
    """Generate and save a specific material type"""
    
    # Send start update
    send_progress_update(session_id, {
        'type': 'material_start',
        'week_number': week_plan.week_number,
        'material_type': material_type,
        'material_name': material_name
    })
    
    try:
        output_dir = OUTPUT_DIR / session_id
        output_dir.mkdir(exist_ok=True)
        
        # Create material-specific directories
        material_dirs = {
            'lecture_notes': output_dir / "01_Lecture_Notes",
            'lecture_slides': output_dir / "02_Lecture_Slides",
            'lab_materials': output_dir / "03_Lab_Materials",
            'assessments': output_dir / "04_Assessments",
            'seminar_materials': output_dir / "05_Seminar_Materials",
            'transcripts': output_dir / "06_Transcripts"
        }
        
        material_dir = material_dirs.get(material_type, output_dir)
        material_dir.mkdir(exist_ok=True)
        
        # Generate content based on type
        if material_type == 'lecture_notes':
            notes = await content_generator._generate_lecture_notes(module_data, week_plan)
            export_tools = ExportTools()
            
            for note in notes:
                # Save as PDF
                pdf_path = material_dir / f"Week_{week_plan.week_number:02d}_{sanitize_filename(note.title)}.pdf"
                export_tools.markdown_to_pdf(note.content, pdf_path)
                
                # Save as Word
                docx_path = material_dir / f"Week_{week_plan.week_number:02d}_{sanitize_filename(note.title)}.docx"
                export_tools.markdown_to_docx(note.content, docx_path)
                
                # Send completion update
                send_progress_update(session_id, {
                    'type': 'material_complete',
                    'week_number': week_plan.week_number,
                    'material_type': material_type,
                    'material_name': f"{material_name} - {note.title}",
                    'file_path': str(pdf_path.relative_to(OUTPUT_DIR / session_id)),
                    'file_format': 'PDF'
                })
        
        elif material_type == 'lecture_slides':
            slides = await content_generator._generate_lecture_slides(module_data, week_plan)
            export_tools = ExportTools()
            
            for slide in slides:
                # Save as PowerPoint
                pptx_path = material_dir / f"Week_{week_plan.week_number:02d}_{sanitize_filename(slide.title)}.pptx"
                export_tools.markdown_to_pptx(slide.content, pptx_path)
                
                send_progress_update(session_id, {
                    'type': 'material_complete',
                    'week_number': week_plan.week_number,
                    'material_type': material_type,
                    'material_name': f"{material_name} - {slide.title}",
                    'file_path': str(pptx_path.relative_to(OUTPUT_DIR / session_id)),
                    'file_format': 'PPTX'
                })
        
        elif material_type == 'transcripts':
            transcripts = await content_generator._generate_transcripts(module_data, week_plan)
            
            for transcript in transcripts:
                txt_path = material_dir / f"Week_{week_plan.week_number:02d}_{sanitize_filename(transcript.title)}.txt"
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write(transcript.content)
                
                send_progress_update(session_id, {
                    'type': 'material_complete',
                    'week_number': week_plan.week_number,
                    'material_type': material_type,
                    'material_name': f"{material_name} - {transcript.title}",
                    'file_path': str(txt_path.relative_to(OUTPUT_DIR / session_id)),
                    'file_format': 'TXT'
                })
        
        elif material_type == 'lab_materials':
            labs = await content_generator._generate_lab_sheets(module_data, week_plan)
            export_tools = ExportTools()
            
            for lab in labs:
                pdf_path = material_dir / f"Week_{week_plan.week_number:02d}_{sanitize_filename(lab.title)}.pdf"
                export_tools.markdown_to_pdf(lab.content, pdf_path)
                
                send_progress_update(session_id, {
                    'type': 'material_complete',
                    'week_number': week_plan.week_number,
                    'material_type': material_type,
                    'material_name': f"{material_name} - {lab.title}",
                    'file_path': str(pdf_path.relative_to(OUTPUT_DIR / session_id)),
                    'file_format': 'PDF'
                })
        
        elif material_type == 'assessments':
            quizzes = await content_generator._generate_quizzes(module_data, week_plan)
            export_tools = ExportTools()
            
            for quiz in quizzes:
                pdf_path = material_dir / f"Week_{week_plan.week_number:02d}_{sanitize_filename(quiz.title)}.pdf"
                export_tools.markdown_to_pdf(quiz.content, pdf_path)
                
                send_progress_update(session_id, {
                    'type': 'material_complete',
                    'week_number': week_plan.week_number,
                    'material_type': material_type,
                    'material_name': f"{material_name} - {quiz.title}",
                    'file_path': str(pdf_path.relative_to(OUTPUT_DIR / session_id)),
                    'file_format': 'PDF'
                })
        
        elif material_type == 'seminar_materials':
            seminars = await content_generator._generate_seminar_prompts(module_data, week_plan)
            export_tools = ExportTools()
            
            for seminar in seminars:
                pdf_path = material_dir / f"Week_{week_plan.week_number:02d}_{sanitize_filename(seminar.title)}.pdf"
                export_tools.markdown_to_pdf(seminar.content, pdf_path)
                
                send_progress_update(session_id, {
                    'type': 'material_complete',
                    'week_number': week_plan.week_number,
                    'material_type': material_type,
                    'material_name': f"{material_name} - {seminar.title}",
                    'file_path': str(pdf_path.relative_to(OUTPUT_DIR / session_id)),
                    'file_format': 'PDF'#,
                    #'file_size': file_path.stat().st_size
                })
        
    except Exception as e:
        send_progress_update(session_id, {
            'type': 'error',
            'message': f"Error generating {material_name} for Week {week_plan.week_number}: {str(e)}"
        })

def send_progress_update(session_id: str, update: dict):
    """Send progress update to session"""
    session_data = SessionManager.get_session(session_id)
    progress_updates = session_data.get('progress_updates', [])
    progress_updates.append(update)
    SessionManager.update_session(session_id, {'progress_updates': progress_updates})

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for cross-platform compatibility"""
    import re
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = re.sub(r'\s+', '_', filename)
    return filename[:50]


# Resource file upload endpoints
@app.post("/api/upload-resource-files")
async def upload_resource_files(
    session_id: str = Form(...),
    week_number: int = Form(...),
    resource_files: List[UploadFile] = File(...)
):
    """Upload resource files for a specific week"""
    
    try:
        # Create week-specific resource directory
        resource_dir = OUTPUT_DIR / session_id / "resources" / f"week_{week_number}"
        resource_dir.mkdir(parents=True, exist_ok=True)
        
        uploaded_files = []
        
        for file in resource_files:
            if file.filename:
                # Save file with timestamp to avoid conflicts
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{timestamp}_{file.filename}"
                file_path = resource_dir / filename
                
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                
                uploaded_files.append({
                    "original_name": file.filename,
                    "saved_name": filename,
                    "path": str(file_path.relative_to(OUTPUT_DIR / session_id)),
                    "size": file_path.stat().st_size,
                    "type": file.content_type or "unknown"
                })
        
        # Update session data with uploaded resources
        session_data = SessionManager.get_session(session_id)
        if not session_data.get('resource_files'):
            session_data['resource_files'] = {}
        
        session_data['resource_files'][f'week_{week_number}'] = uploaded_files
        SessionManager.update_session(session_id, session_data)
        
        return JSONResponse({
            "status": "success",
            "uploaded_files": uploaded_files,
            "message": f"Uploaded {len(uploaded_files)} files for week {week_number}"
        })
        
    except Exception as e:
        logger.error(f"Error uploading resource files: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error uploading resource files: {str(e)}")

# Materials review endpoints
@app.get("/materials-review/{session_id}", response_class=HTMLResponse)
async def materials_review_page(request: Request, session_id: str):
    """Materials review page after generation completion"""
    
    try:
        # Get session data
        session_data = SessionManager.get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get generated materials
        materials = get_session_materials(session_id)
        
        # Calculate statistics
        total_files = len(materials)
        total_size = sum(material.get('size', 0) for material in materials)
        total_weeks = len(set(m.get('week', 0) for m in materials if m.get('week', 0) > 0))
        
        return templates.TemplateResponse("materials_review.html", {
            "request": request,
            "session_id": session_id,
            "materials_json": json.dumps(materials),
            "total_files": total_files,
            "total_size": format_file_size(total_size),
            "total_weeks": total_weeks
        })
        
    except Exception as e:
        logger.error(f"Error loading review page: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error loading review page: {str(e)}")

@app.get("/api/preview-file/{session_id}")
async def preview_file(session_id: str, file: str):
    """Get preview content for a file"""
    
    try:
        file_path = OUTPUT_DIR / session_id / file
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        file_extension = file_path.suffix.lower()
        
        if file_extension == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return {"type": "text", "content": content}
            
        elif file_extension == '.pdf':
            return {"type": "pdf", "path": file, "message": "PDF preview available"}
            
        else:
            return {"type": "unsupported", "message": "Preview not available for this file type"}
            
    except Exception as e:
        logger.error(f"Error generating preview: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating preview: {str(e)}")

# Download endpoints
@app.get("/download-all/{session_id}")
async def download_all_materials(session_id: str):
    """Download all materials as a zip file"""
    
    try:
        output_dir = OUTPUT_DIR / session_id
        package_path = output_dir / "complete_package.zip"
        
        if not package_path.exists():
            # Create package
            import zipfile
            with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in output_dir.rglob('*'):
                    if file_path.is_file() and file_path != package_path:
                        arcname = file_path.relative_to(output_dir)
                        zipf.write(file_path, arcname)
        
        return FileResponse(
            package_path,
            media_type='application/zip',
            filename=f"course_materials_{session_id}.zip"
        )
        
    except Exception as e:
        logger.error(f"Error creating download package: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating download package: {str(e)}")

@app.get("/api/download-file/{session_id}")
async def download_single_file(session_id: str, file: str):
    """Download a single file"""
    file_path = OUTPUT_DIR / session_id / file
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_path, filename=file_path.name)

# Dashboard and session management endpoints
@app.get("/api/sessions")
async def get_user_sessions():
    """Get all user sessions with summary information (DB-only)."""
    try:
        sessions = session_store.list_all()
        user_sessions = []
        for s in sessions:
            completed = s.get('completed_materials', []) or []
            # compute total size from DB entries if present
            total_size = sum((m.get('size', 0) or 0) for m in completed if isinstance(m, dict))
            user_sessions.append({
                'id': s.get('session_id'),
                'module_title': (s.get('module_data') or {}).get('title', 'Untitled Module') if isinstance(s.get('module_data'), dict) else 'Untitled Module',
                'module_description': (s.get('module_data') or {}).get('description') if isinstance(s.get('module_data'), dict) else None,
                'status': s.get('generation_status', 'unknown'),
                'created_at': s.get('created_at', datetime.now().isoformat()),
                'last_activity': s.get('last_activity', datetime.now().isoformat()),
                'total_materials': s.get('total_materials', 0),
                'completed_materials': len(completed),
                'total_weeks': len(s.get('week_plans', []) or []),
                'total_size': total_size,
                'selected_materials': s.get('generation_materials', []) or [],
                'error_message': s.get('error_message')
            })
        # Sort by last activity (most recent first)
        user_sessions.sort(key=lambda x: x['last_activity'], reverse=True)
        return JSONResponse(user_sessions)
    except Exception as e:
        logger.error(f"Error retrieving sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving sessions: {str(e)}")

@app.get("/api/usage-statistics")
async def get_usage_statistics():
    """Get user usage statistics"""
    
    try:
        total_sessions = 0
        completed_sessions = 0
        total_materials = 0
        total_size = 0
        
        if OUTPUT_DIR.exists():
            for session_dir in OUTPUT_DIR.iterdir():
                if session_dir.is_dir():
                    session_id = session_dir.name
                    session_data = SessionManager.get_session(session_id)
                    
                    if session_data:
                        total_sessions += 1
                        
                        if session_data.get('generation_status') == 'completed':
                            completed_sessions += 1
                        
                        materials = get_session_materials(session_id)
                        total_materials += len(materials)
                        total_size += sum(m.get('size', 0) for m in materials)
        
        return JSONResponse({
            'total_sessions': total_sessions,
            'completed_sessions': completed_sessions,
            'total_materials': total_materials,
            'total_size': total_size
        })
        
    except Exception as e:
        logger.error(f"Error retrieving statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving statistics: {str(e)}")

@app.delete("/api/delete-session/{session_id}")
async def delete_session(session_id: str):
    """Delete a specific session and all its data"""
    
    try:
        # Remove from persistent storage
        SessionManager.delete_session(session_id)
        
        # Remove files
        session_dir = OUTPUT_DIR / session_id
        if session_dir.exists():
            shutil.rmtree(session_dir)
        
        # Remove from uploads if exists
        for file_path in UPLOAD_DIR.glob(f"{session_id}_*"):
            file_path.unlink()
        
        return JSONResponse({
            "status": "success", 
            "message": f"Session {session_id} deleted successfully"
        })
        
    except Exception as e:
        logger.error(f"Error deleting session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting session: {str(e)}")

# Control endpoints for pause/resume/stop
@app.post("/api/pause-generation/{session_id}")
async def pause_generation(session_id: str):
    """Pause the generation process"""
    try:
        SessionManager.update_session(session_id, {
            'generation_status': 'paused',
            'paused_at': datetime.now().isoformat()
        })
        
        send_progress_update(session_id, {'type': 'paused'})
        
        return JSONResponse({"status": "success", "message": "Generation paused"})
    except Exception as e:
        logger.error(f"Error pausing generation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error pausing generation: {str(e)}")

@app.post("/api/resume-generation/{session_id}")
async def resume_generation(session_id: str):
    """Resume the generation process"""
    try:
        SessionManager.update_session(session_id, {
            'generation_status': 'running',
            'resumed_at': datetime.now().isoformat()
        })
        
        # Restart generation from where it left off
        import asyncio
        session_data = SessionManager.get_session(session_id)
        materials = session_data.get('generation_materials', [])
        asyncio.create_task(generate_materials_background(session_id, materials))
        
        return JSONResponse({"status": "success", "message": "Generation resumed"})
    except Exception as e:
        logger.error(f"Error resuming generation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error resuming generation: {str(e)}")

@app.post("/api/stop-generation/{session_id}")
async def stop_generation(session_id: str):
    """Stop the generation process"""
    try:
        SessionManager.update_session(session_id, {
            'generation_status': 'stopped',
            'stopped_at': datetime.now().isoformat()
        })
        
        send_progress_update(session_id, {'type': 'stopped'})
        
        return JSONResponse({"status": "success", "message": "Generation stopped"})
    except Exception as e:
        logger.error(f"Error stopping generation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error stopping generation: {str(e)}")

# Error page
@app.get("/error", response_class=HTMLResponse)
async def error_page(request: Request):
    """Error page"""
    return templates.TemplateResponse("error.html", {
        "request": request,
        "error": "An error occurred"
    })

# Add session recovery endpoint
@app.post("/api/recover-session/{session_id}")
async def recover_session(session_id: str):
    """Attempt to recover a session by scanning for existing data"""
    try:
        # Check if session exists in memory
        session_data = SessionManager.get_session(session_id)
        
        # If not in memory, try to recover from filesystem
        if not session_data:
            output_dir = OUTPUT_DIR / session_id
            upload_files = list(UPLOAD_DIR.glob(f"{session_id}_*"))
            
            if output_dir.exists() or upload_files:
                # Create new session data in store
                base = {
                    'session_id': session_id,
                    'module_data': None,
                    'week_plans': [],
                    'generated_content': {},
                    'status': 'recovered',
                    'generation_status': 'recovered',
                    'created_at': datetime.now().isoformat(),
                    'last_activity': datetime.now().isoformat(),
                    'recovered': True
                }
                session_store.create(base)
                
                # Scan for materials
                materials = get_session_materials(session_id)
                
                # Try to recover module data from plan file if it exists
                plan_file = output_dir / "weekly_plan_detailed.txt"
                if plan_file.exists():
                    # Could parse basic info from the plan file
                    pass
                
                SessionManager.update_session(session_id, {
                    'completed_materials': materials,
                    'generation_status': 'completed' if materials else 'recovered'
                })
                
                logger.info(f"Recovered session {session_id} with {len(materials)} materials")
                
                return JSONResponse({
                    'status': 'success',
                    'message': f'Session recovered with {len(materials)} materials',
                    'materials_found': len(materials)
                })
        
        return JSONResponse({
            'status': 'success',
            'message': 'Session already exists',
            'session_data': session_data
        })
        
    except Exception as e:
        logger.error(f"Error recovering session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error recovering session: {str(e)}")

@app.post("/api/upload")
async def upload_files(
    session_id: str = Form(...),
    module_file: UploadFile = File(...),
    textbook_files: List[UploadFile] = File(default=[])
):
    """Handle file uploads and process module specifications with better error handling"""
    
    try:
        # Validate session exists
        session_data = SessionManager.get_session(session_id)
        if not session_data:
            # Create session if it doesn't exist
            session_store.create({
                'session_id': session_id,
                'module_data': None,
                'week_plans': [],
                'generated_content': {},
                'status': 'initialized',
                'generation_status': 'processing_upload',
                'created_at': datetime.now().isoformat(),
                'last_activity': datetime.now().isoformat()
            })
            logger.info(f"Created new session for upload: {session_id}")
        
        # Validate file types
        allowed_extensions = ['pdf', 'docx', 'doc']
        if not any(module_file.filename.lower().endswith(ext) for ext in allowed_extensions):
            raise HTTPException(status_code=400, detail="Invalid file type for module specification. Please upload PDF, DOCX, or DOC files.")
        
        # Check file size (limit to 50MB)
        max_size = 50 * 1024 * 1024  # 50MB
        if module_file.size and module_file.size > max_size:
            raise HTTPException(status_code=400, detail="File too large. Maximum size is 50MB.")
        
        # Update session status
        SessionManager.update_session(session_id, {
            'generation_status': 'uploading_files'
        })
        
        # Save uploaded files
        module_path = UPLOAD_DIR / f"{session_id}_{module_file.filename}"
        try:
            with open(module_path, "wb") as buffer:
                content = await module_file.read()
                buffer.write(content)
            logger.info(f"Saved module file: {module_path}")
        except Exception as e:
            logger.error(f"Error saving module file: {str(e)}")
            raise HTTPException(status_code=500, detail="Error saving uploaded file")
        
        textbook_paths = []
        for textbook in textbook_files:
            if textbook.filename and textbook.size:
                try:
                    if textbook.size > max_size:
                        logger.warning(f"Skipping large textbook file: {textbook.filename}")
                        continue
                    
                    textbook_path = UPLOAD_DIR / f"{session_id}_{textbook.filename}"
                    with open(textbook_path, "wb") as buffer:
                        content = await textbook.read()
                        buffer.write(content)
                    textbook_paths.append(textbook_path)
                    logger.info(f"Saved textbook file: {textbook_path}")
                except Exception as e:
                    logger.error(f"Error saving textbook {textbook.filename}: {str(e)}")
                    # Continue with other files
        
        # Update session status
        SessionManager.update_session(session_id, {
            'generation_status': 'processing_documents'
        })
        
        # Process files with ingestion agent
        try:
            ingestion_agent = IngestionAgent()
            module_data = await ingestion_agent.process_module_spec(
                module_path, textbook_paths
            )
            logger.info(f"Successfully processed module spec for session: {session_id}")
        except Exception as e:
            logger.error(f"Error processing module spec: {str(e)}")
            SessionManager.update_session(session_id, {
                'generation_status': 'error',
                'error_message': f"Error processing uploaded documents: {str(e)}"
            })
            raise HTTPException(status_code=500, detail=f"Error processing uploaded documents: {str(e)}")
        
        # Update session with processed data
        SessionManager.update_session(session_id, {
            'module_data': module_data.dict(),
            'generation_status': 'documents_processed',
            'upload_complete': True
        })
        
        return JSONResponse({
            "status": "success",
            "message": "Files processed successfully",
            "module_data": module_data.dict(),
            "session_status": "documents_processed"
        })
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error in upload: {str(e)}")
        # Update session with error status
        SessionManager.update_session(session_id, {
            'generation_status': 'error',
            'error_message': str(e)
        })
        raise HTTPException(status_code=500, detail=f"Unexpected error processing upload: {str(e)}")
    
# Add these missing endpoints to main.py

@app.get("/api/session-status/{session_id}")
async def get_session_status(session_id: str):
    """Get current status of a session"""
    try:
        session_data = SessionManager.get_session(session_id)
        
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get materials information
        materials = get_session_materials(session_id)
        total_size = sum(m.get('size', 0) for m in materials)
        
        # Calculate progress
        total_materials = session_data.get('total_materials', 0)
        completed_materials = len(materials)
        progress_percentage = 0
        if total_materials > 0:
            progress_percentage = (completed_materials / total_materials) * 100
        
        status_info = {
            'session_id': session_id,
            'status': session_data.get('generation_status', 'unknown'),
            'module_title': session_data.get('module_data', {}).get('title', 'Unknown Module'),
            'progress_percentage': round(progress_percentage, 2),
            'completed_materials': completed_materials,
            'total_materials': total_materials,
            'total_size': total_size,
            'created_at': session_data.get('created_at'),
            'last_activity': session_data.get('last_activity'),
            'week_plans_count': len(session_data.get('week_plans', [])),
            'has_materials': completed_materials > 0,
            'error_message': session_data.get('error_message')
        }
        
        return JSONResponse(status_info)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving session status: {str(e)}")

@app.get("/api/session-health/{session_id}")
async def check_session_health(session_id: str):
    """Health check for a specific session"""
    try:
        session_data = SessionManager.get_session(session_id)
        
        if not session_data:
            return JSONResponse({
                'healthy': False,
                'exists': False,
                'message': 'Session not found'
            })
        
        # Check if session is in a valid state
        status = session_data.get('generation_status', 'unknown')
        healthy = status not in ['error', 'corrupted']
        
        # Check if files exist
        output_dir = OUTPUT_DIR / session_id
        files_exist = output_dir.exists() and any(output_dir.iterdir())
        
        return JSONResponse({
            'healthy': healthy,
            'exists': True,
            'status': status,
            'has_files': files_exist,
            'last_activity': session_data.get('last_activity'),
            'message': 'Session is healthy' if healthy else 'Session has issues'
        })
        
    except Exception as e:
        logger.error(f"Error checking session health: {str(e)}")
        return JSONResponse({
            'healthy': False,
            'exists': False,
            'error': str(e),
            'message': 'Error checking session health'
        })

@app.post("/api/refresh-session/{session_id}")
async def refresh_session_data(session_id: str):
    """Refresh session data by scanning filesystem"""
    try:
        session_data = SessionManager.get_session(session_id)
        
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Scan for materials
        materials = get_session_materials(session_id)
        
        # Update session data
        SessionManager.update_session(session_id, {
            'completed_materials': materials,
            'last_scan': datetime.now().isoformat()
        })
        
        return JSONResponse({
            'status': 'success',
            'materials_found': len(materials),
            'message': 'Session data refreshed successfully'
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error refreshing session: {str(e)}")


# Add periodic session cleanup
import asyncio
from typing import Set

# Keep track of active sessions
active_sessions: Set[str] = set()

async def cleanup_inactive_sessions():
    """Cleanup sessions that haven't been active for more than 24 hours"""
    try:
        cutoff_time = datetime.now().timestamp() - (24 * 60 * 60)  # 24 hours ago
        
        sessions_to_remove = []
        for session in session_store.list_all():
            session_id = session.get('session_id')
            session_data = session
            try:
                last_activity = datetime.fromisoformat(session_data.get('last_activity', datetime.now().isoformat()))
                if last_activity.timestamp() < cutoff_time and session_id not in active_sessions:
                    sessions_to_remove.append(session_id)
            except Exception as e:
                logger.error(f"Error checking session {session_id} for cleanup: {str(e)}")
        
        # Remove inactive sessions
        for session_id in sessions_to_remove:
            try:
                SessionManager.delete_session(session_id)
                # Also cleanup files
                session_dir = OUTPUT_DIR / session_id
                if session_dir.exists():
                    shutil.rmtree(session_dir)
                logger.info(f"Cleaned up inactive session: {session_id}")
            except Exception as e:
                logger.error(f"Error cleaning up session {session_id}: {str(e)}")
                
    except Exception as e:
        logger.error(f"Error in session cleanup: {str(e)}")

# Add startup event to schedule cleanup
@app.on_event("startup")
async def startup_event():
    """Initialize application"""
    logger.info("AI Course Generator starting up...")
    
    # Create directories if they don't exist
    OUTPUT_DIR.mkdir(exist_ok=True)
    UPLOAD_DIR.mkdir(exist_ok=True)
    
    # Schedule periodic cleanup (every 6 hours)
    async def schedule_cleanup():
        while True:
            await asyncio.sleep(6 * 60 * 60)  # 6 hours
            await cleanup_inactive_sessions()
    
    asyncio.create_task(schedule_cleanup())
    logger.info("Periodic session cleanup scheduled")

# Add session activity tracking middleware
@app.middleware("http")
async def track_session_activity(request: Request, call_next):
    """Track session activity for cleanup purposes"""
    response = await call_next(request)
    
    # Extract session ID from URL or headers
    path_parts = request.url.path.split('/')
    session_id = None
    
    # Look for session ID in path
    for i, part in enumerate(path_parts):
        if len(part) == 36 and '-' in part:  # UUID format
            session_id = part
            break
    
    # Add to active sessions if found
    if session_id and session_store.exists(session_id):
        active_sessions.add(session_id)
        # Remove from active set after 1 hour
        asyncio.create_task(remove_from_active_later(session_id))
    
    return response

async def remove_from_active_later(session_id: str):
    """Remove session from active set after delay"""
    await asyncio.sleep(60 * 60)  # 1 hour
    active_sessions.discard(session_id)    

# Add this endpoint to main.py

@app.post("/api/generate-week")
async def generate_week_content(request: Request):
    """Generate content for a specific week"""
    
    try:
        data = await request.json()
        session_id = data.get('session_id')
        week_number = data.get('week_number')
        material_types = data.get('material_types', [])
        
        if not session_id or not week_number:
            raise HTTPException(status_code=400, detail="Missing session_id or week_number")
        
        # Get session data
        session_data = SessionManager.get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get module data and week plan
        module_data = session_data.get('module_data')
        week_plans = session_data.get('week_plans', [])
        
        if not module_data:
            raise HTTPException(status_code=400, detail="No module data found")
        
        # Find the specific week plan
        week_plan = None
        for plan in week_plans:
            if plan.get('week_number') == week_number:
                week_plan = plan
                break
        
        if not week_plan:
            raise HTTPException(status_code=404, detail=f"Week {week_number} plan not found")
        
        # Convert to proper objects
        module_obj = ModuleData(**module_data)
        week_obj = WeekPlan(**week_plan)
        
        # Generate content for this week
        content_generator = ContentGenerator()
        
        # Generate specified materials
        generated_materials = []
        
        if 'lecture_notes' in material_types:
            notes = await content_generator._generate_enhanced_lecture_notes(
                module_obj, week_obj, content_generator._prepare_enhanced_context(module_obj, week_obj)
            )
            for note in notes:
                # Save the content
                file_path = await save_generated_content(session_id, week_number, note, 'lecture_notes')
                generated_materials.append({
                    'type': 'lecture_notes',
                    'title': note.title,
                    'file_path': file_path,
                    'format': 'PDF'
                })
        
        if 'lecture_slides' in material_types:
            slides = await content_generator._generate_enhanced_lecture_slides(
                module_obj, week_obj, content_generator._prepare_enhanced_context(module_obj, week_obj)
            )
            for slide in slides:
                # Save the content
                file_path = await save_generated_content(session_id, week_number, slide, 'lecture_slides')
                generated_materials.append({
                    'type': 'lecture_slides',
                    'title': slide.title,
                    'file_path': file_path,
                    'format': 'PPTX'
                })
        
        if 'transcripts' in material_types:
            transcripts = await content_generator._generate_enhanced_transcripts(
                module_obj, week_obj, content_generator._prepare_enhanced_context(module_obj, week_obj)
            )
            for transcript in transcripts:
                # Save the content
                file_path = await save_generated_content(session_id, week_number, transcript, 'transcripts')
                generated_materials.append({
                    'type': 'transcripts',
                    'title': transcript.title,
                    'file_path': file_path,
                    'format': 'TXT'
                })
        
        if 'lab_materials' in material_types:
            labs = await content_generator._generate_enhanced_lab_sheets(
                module_obj, week_obj, content_generator._prepare_enhanced_context(module_obj, week_obj)
            )
            for lab in labs:
                # Save the content
                file_path = await save_generated_content(session_id, week_number, lab, 'lab_materials')
                generated_materials.append({
                    'type': 'lab_materials',
                    'title': lab.title,
                    'file_path': file_path,
                    'format': 'PDF'
                })
        
        if 'assessments' in material_types:
            quizzes = await content_generator._generate_enhanced_quizzes(
                module_obj, week_obj, content_generator._prepare_enhanced_context(module_obj, week_obj)
            )
            for quiz in quizzes:
                # Save the content
                file_path = await save_generated_content(session_id, week_number, quiz, 'assessments')
                generated_materials.append({
                    'type': 'assessments',
                    'title': quiz.title,
                    'file_path': file_path,
                    'format': 'PDF'
                })
        
        if 'seminar_materials' in material_types:
            seminars = await content_generator._generate_enhanced_seminar_prompts(
                module_obj, week_obj, content_generator._prepare_enhanced_context(module_obj, week_obj)
            )
            for seminar in seminars:
                # Save the content
                file_path = await save_generated_content(session_id, week_number, seminar, 'seminar_materials')
                generated_materials.append({
                    'type': 'seminar_materials',
                    'title': seminar.title,
                    'file_path': file_path,
                    'format': 'PDF'
                })
        
        # Update session with generated materials
        if 'generated_materials' not in session_data:
            session_data['generated_materials'] = {}
        
        session_data['generated_materials'][f'week_{week_number}'] = generated_materials
        SessionManager.update_session(session_id, session_data)
        
        return JSONResponse({
            "status": "success",
            "message": f"Generated {len(generated_materials)} materials for week {week_number}",
            "materials": generated_materials
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in generate_week_content: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating week content: {str(e)}")

async def save_generated_content(session_id: str, week_number: int, content_item: ContentItem, material_type: str) -> str:
    """Save generated content to appropriate directory and format"""
    
    try:
        # Create output directories
        output_dir = OUTPUT_DIR / session_id
        
        # Create material-specific directories
        material_dirs = {
            'lecture_notes': output_dir / "01_Lecture_Notes",
            'lecture_slides': output_dir / "02_Lecture_Slides",
            'lab_materials': output_dir / "03_Lab_Materials",
            'assessments': output_dir / "04_Assessments",
            'seminar_materials': output_dir / "05_Seminar_Materials",
            'transcripts': output_dir / "06_Transcripts"
        }
        
        material_dir = material_dirs.get(material_type, output_dir)
        material_dir.mkdir(parents=True, exist_ok=True)
        
        # Sanitize filename
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', content_item.title)
        safe_title = re.sub(r'\s+', '_', safe_title)[:50]
        
        export_tools = ExportTools()
        
        # Save content based on material type
        if material_type == 'lecture_notes':
            # Save as PDF
            pdf_path = material_dir / f"Week_{week_number:02d}_{safe_title}.pdf"
            export_tools.markdown_to_pdf(content_item.content, pdf_path)
            
            # Save as Word
            docx_path = material_dir / f"Week_{week_number:02d}_{safe_title}.docx"
            export_tools.markdown_to_docx(content_item.content, docx_path)
            
            return str(pdf_path.relative_to(output_dir))
            
        elif material_type == 'lecture_slides':
            # Save as PowerPoint
            pptx_path = material_dir / f"Week_{week_number:02d}_{safe_title}.pptx"
            export_tools.markdown_to_pptx(content_item.content, pptx_path)
            
            return str(pptx_path.relative_to(output_dir))
            
        elif material_type == 'transcripts':
            # Save as text file
            txt_path = material_dir / f"Week_{week_number:02d}_{safe_title}.txt"
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(content_item.content)
            
            return str(txt_path.relative_to(output_dir))
            
        else:
            # Save as PDF for other types
            pdf_path = material_dir / f"Week_{week_number:02d}_{safe_title}.pdf"
            export_tools.markdown_to_pdf(content_item.content, pdf_path)
            
            return str(pdf_path.relative_to(output_dir))
    
    except Exception as e:
        logger.error(f"Error saving content: {str(e)}")
        raise Exception(f"Failed to save content: {str(e)}")

# Also add a session health check endpoint that seems to be called
@app.get("/api/session-health/{session_id}")
async def session_health_check(session_id: str):
    """Check if session is healthy and accessible"""
    
    try:
        session_data = SessionManager.get_session(session_id)
        
        return JSONResponse({
            "status": "healthy",
            "exists": bool(session_data),
            "last_activity": session_data.get('last_activity') if session_data else None
        })
        
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "exists": False,
            "error": str(e)
        })
# Update the existing generate-plan endpoint to be more robust
@app.post("/api/generate-plan")
async def generate_weekly_plan(session_id: str = Form(...)):
    """Generate weekly plan using planning agent"""
    
    session_data = SessionManager.get_session(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    module_data = session_data.get('module_data')
    if not module_data:
        raise HTTPException(status_code=400, detail="No module data found in session")
    
    try:
        planning_agent = PlanningAgent()
        
        # Convert dict to ModuleData object
        module_obj = ModuleData(**module_data)
        
        week_plans = await planning_agent.generate_weekly_plan(module_obj)
        
        # Convert back to dicts for JSON serialization
        week_plans_dict = [plan.dict() for plan in week_plans]
        
        SessionManager.update_session(session_id, {
            'week_plans': week_plans_dict,
            'status': 'planned'
        })
        
        return JSONResponse({
            "status": "success",
            "week_plans": week_plans_dict
        })
        
    except Exception as e:
        logger.error(f"Error generating plan for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating plan: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=os.getenv("APP_HOST", "127.0.0.1"),
        port=int(os.getenv("APP_PORT", 8000)),
        reload=os.getenv("DEBUG", "True").lower() == "true"
    )

