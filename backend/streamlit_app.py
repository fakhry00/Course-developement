"""
Streamlit Application for AI-Powered Course Material Generator
Converted from FastAPI to Streamlit
"""

import streamlit as st
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
import asyncio
import traceback
import zipfile

from dotenv import load_dotenv

# Import models
from models.schemas import (
    ModuleData, 
    WeekPlan, 
    GeneratedContent, 
    LearningOutcome, 
    Assessment,
    ContentItem,
)

# Import agents
try:
    from agents.ingestion_agent import IngestionAgent
    from agents.planning_agent import PlanningAgent
    from agents.content_generator import ContentGenerator
    from agents.packaging_agent import PackagingAgent
    from utils.export_tools import ExportTools
    AGENTS_AVAILABLE = True
except ImportError as e:
    st.error(f"Warning: Could not import some modules: {e}")
    st.error("Some features may not work properly until all dependencies are installed.")
    AGENTS_AVAILABLE = False

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize directories
OUTPUT_DIR = Path("outputs")
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)

# Page configuration
st.set_page_config(
    page_title="AI Course Material Generator",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #333;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f0f2f6;
        margin: 1rem 0;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        margin: 1rem 0;
    }
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

def init_session_state():
    """Initialize session state variables"""
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    
    if 'module_data' not in st.session_state:
        st.session_state.module_data = None
    
    if 'week_plans' not in st.session_state:
        st.session_state.week_plans = []
    
    if 'generated_materials' not in st.session_state:
        st.session_state.generated_materials = {}
    
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Dashboard"
    
    if 'plan_approved' not in st.session_state:
        st.session_state.plan_approved = False
    
    if 'generation_status' not in st.session_state:
        st.session_state.generation_status = 'initialized'
    
    if 'created_at' not in st.session_state:
        st.session_state.created_at = datetime.now().isoformat()
    
    if 'resource_files' not in st.session_state:
        st.session_state.resource_files = {}

init_session_state()

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def format_file_size(bytes_size: int) -> str:
    """Format file size in human readable format"""
    if bytes_size == 0:
        return '0 B'
    
    size_names = ['B', 'KB', 'MB', 'GB']
    i = int(math.floor(math.log(bytes_size, 1024)))
    p = math.pow(1024, i)
    s = round(bytes_size / p, 2)
    
    return f"{s} {size_names[i]}"

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for cross-platform compatibility"""
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = re.sub(r'\s+', '_', filename)
    return filename[:50]

def save_uploaded_file(uploaded_file, session_id: str) -> Path:
    """Save uploaded file to disk"""
    file_path = UPLOAD_DIR / f"{session_id}_{uploaded_file.name}"
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path

def run_async(coroutine):
    """Run async function in sync context"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(coroutine)
        loop.close()
        return result
    except Exception as e:
        logger.error(f"Error running async function: {str(e)}")
        raise

def get_session_materials(session_id: str) -> list:
    """Get all materials for a session"""
    materials = []
    output_dir = OUTPUT_DIR / session_id
    
    if not output_dir.exists():
        return materials
    
    material_id = 1
    
    for file_path in output_dir.rglob('*'):
        if file_path.is_file() and not file_path.name.startswith('.'):
            relative_path = file_path.relative_to(output_dir)
            
            week_match = re.search(r'Week_(\d+)', file_path.name)
            week = int(week_match.group(1)) if week_match else 0
            
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
    else:
        return 'other'

def create_zip_package(session_id: str) -> Path:
    """Create zip package of all materials"""
    output_dir = OUTPUT_DIR / session_id
    zip_path = output_dir / "complete_package.zip"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in output_dir.rglob('*'):
            if file_path.is_file() and file_path != zip_path:
                arcname = file_path.relative_to(output_dir)
                zipf.write(file_path, arcname)
    
    return zip_path

# ============================================================================
# PAGE FUNCTIONS
# ============================================================================

def show_dashboard():
    """Display the dashboard page"""
    st.markdown('<div class="main-header">📚 AI Course Material Generator</div>', unsafe_allow_html=True)
    
    st.markdown("""
    Welcome to the AI-Powered Course Material Generator! This tool helps you create comprehensive 
    course materials from your module specifications.
    """)
    
    # Session information
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Session ID", st.session_state.session_id[:8] + "...")
    
    with col2:
        status = "✅ Ready" if st.session_state.module_data else "⏳ Pending"
        st.metric("Module Status", status)
    
    with col3:
        week_count = len(st.session_state.week_plans)
        st.metric("Weeks Planned", week_count)
    
    # Quick stats
    if st.session_state.module_data:
        st.markdown('<div class="sub-header">Current Module</div>', unsafe_allow_html=True)
        
        module_data = st.session_state.module_data
        st.info(f"""
        **Title:** {module_data.get('title', 'N/A')}  
        **Code:** {module_data.get('code', 'N/A')}  
        **Credits:** {module_data.get('credits', 'N/A')}  
        **Semester:** {module_data.get('semester', 'N/A')}
        """)
    
    # Materials summary
    materials = get_session_materials(st.session_state.session_id)
    if materials:
        st.markdown('<div class="sub-header">Generated Materials</div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Files", len(materials))
        with col2:
            total_size = sum(m.get('size', 0) for m in materials)
            st.metric("Total Size", format_file_size(total_size))
        with col3:
            weeks = len(set(m.get('week', 0) for m in materials if m.get('week', 0) > 0))
            st.metric("Weeks Generated", weeks)
    
    # Getting started guide
    st.markdown('<div class="sub-header">Getting Started</div>', unsafe_allow_html=True)
    
    st.markdown("""
    1. **Upload** - Upload your module specification and optional textbooks
    2. **Review Plan** - Review and approve the generated weekly plan
    3. **Generate Materials** - Select and generate course materials
    4. **Download** - Download your complete course package
    """)
    
    # Quick actions
    st.markdown('<div class="sub-header">Quick Actions</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🚀 Start New Project", use_container_width=True):
            # Reset session
            for key in list(st.session_state.keys()):
                if key != 'current_page':
                    del st.session_state[key]
            init_session_state()
            st.session_state.current_page = "Upload"
            st.rerun()
    
    with col2:
        if st.session_state.module_data:
            if st.button("📋 View Plan", use_container_width=True):
                st.session_state.current_page = "Review Plan"
                st.rerun()
    
    with col3:
        if materials:
            if st.button("📥 Download Materials", use_container_width=True):
                st.session_state.current_page = "Download"
                st.rerun()

def show_upload_page():
    """Display the upload page"""
    st.markdown('<div class="main-header">📤 Upload Module Specification</div>', unsafe_allow_html=True)
    
    st.markdown("""
    Upload your module specification document and any supporting textbooks or materials.
    The AI will analyze these documents to understand your course structure and requirements.
    """)
    
    # Module specification upload
    st.markdown('<div class="sub-header">Module Specification (Required)</div>', unsafe_allow_html=True)
    
    module_file = st.file_uploader(
        "Upload Module Specification",
        type=['pdf', 'docx', 'doc'],
        help="Upload your module specification document (PDF, DOCX, or DOC)",
        key="module_upload"
    )
    
    # Textbook uploads
    st.markdown('<div class="sub-header">Textbooks and Resources (Optional)</div>', unsafe_allow_html=True)
    
    textbook_files = st.file_uploader(
        "Upload Textbooks or Reference Materials",
        type=['pdf', 'docx', 'doc'],
        accept_multiple_files=True,
        help="Upload any textbooks or reference materials that should be considered",
        key="textbook_upload"
    )
    
    # Process button
    if st.button("🔄 Process Files", type="primary", use_container_width=True):
        if not module_file:
            st.error("Please upload a module specification file")
            return
        
        if not AGENTS_AVAILABLE:
            st.error("AI agents are not available. Please install required dependencies.")
            return
        
        try:
            with st.spinner("Processing files... This may take a few minutes."):
                # Save files
                module_path = save_uploaded_file(module_file, st.session_state.session_id)
                textbook_paths = [save_uploaded_file(f, st.session_state.session_id) for f in textbook_files]
                
                # Progress updates
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                status_text.text("Reading module specification...")
                progress_bar.progress(25)
                
                # Process with ingestion agent
                ingestion_agent = IngestionAgent()
                module_data = run_async(ingestion_agent.process_module_spec(module_path, textbook_paths))
                
                status_text.text("Extracting learning outcomes...")
                progress_bar.progress(50)
                
                status_text.text("Analyzing course structure...")
                progress_bar.progress(75)
                
                # Store in session state
                st.session_state.module_data = module_data.dict()
                
                status_text.text("Processing complete!")
                progress_bar.progress(100)
                
                st.success("✅ Files processed successfully!")
                
                # Display extracted information
                st.markdown('<div class="sub-header">Extracted Information</div>', unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.info(f"""
                    **Module Title:** {module_data.title}  
                    **Code:** {module_data.code}  
                    **Credits:** {module_data.credits}  
                    **Semester:** {module_data.semester}
                    """)
                
                with col2:
                    st.info(f"""
                    **Learning Outcomes:** {len(module_data.learning_outcomes)}  
                    **Assessments:** {len(module_data.assessments)}  
                    **Topics:** {len(module_data.topics)}
                    """)
                
                # Next steps
                st.markdown("---")
                if st.button("➡️ Generate Weekly Plan", type="primary", use_container_width=True):
                    st.session_state.current_page = "Generate Plan"
                    st.rerun()
                
        except Exception as e:
            st.error(f"❌ Error processing files: {str(e)}")
            logger.error(f"Error in upload: {str(e)}", exc_info=True)

def show_generate_plan_page():
    """Display the plan generation page"""
    st.markdown('<div class="main-header">📅 Generate Weekly Plan</div>', unsafe_allow_html=True)
    
    if not st.session_state.module_data:
        st.warning("⚠️ Please upload and process module specification first")
        if st.button("Go to Upload"):
            st.session_state.current_page = "Upload"
            st.rerun()
        return
    
    module_data = st.session_state.module_data
    
    st.markdown(f"""
    Generate a comprehensive weekly plan for **{module_data.get('title', 'your module')}**.
    The AI will create a structured plan covering all learning outcomes and assessments.
    """)
    
    # Display module summary
    with st.expander("📖 Module Summary", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Module Information**")
            st.write(f"- Title: {module_data.get('title')}")
            st.write(f"- Code: {module_data.get('code')}")
            st.write(f"- Credits: {module_data.get('credits')}")
            st.write(f"- Semester: {module_data.get('semester')}")
        
        with col2:
            st.write("**Content Overview**")
            st.write(f"- Learning Outcomes: {len(module_data.get('learning_outcomes', []))}")
            st.write(f"- Assessments: {len(module_data.get('assessments', []))}")
            st.write(f"- Topics: {len(module_data.get('topics', []))}")
    
    # Generate plan button
    if st.button("🎯 Generate Weekly Plan", type="primary", use_container_width=True):
        if not AGENTS_AVAILABLE:
            st.error("AI agents are not available. Please install required dependencies.")
            return
        
        try:
            with st.spinner("Generating weekly plan... This may take a few minutes."):
                # Progress tracking
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                status_text.text("Analyzing module structure...")
                progress_bar.progress(20)
                
                # Generate plan
                planning_agent = PlanningAgent()
                
                # Convert dict to ModuleData object
                module_obj = ModuleData(**module_data)
                
                status_text.text("Creating weekly breakdown...")
                progress_bar.progress(40)
                
                week_plans = run_async(planning_agent.generate_weekly_plan(module_obj))
                
                status_text.text("Aligning with learning outcomes...")
                progress_bar.progress(70)
                
                # Convert to dicts
                week_plans_dict = [plan.dict() for plan in week_plans]
                st.session_state.week_plans = week_plans_dict
                
                status_text.text("Finalizing plan...")
                progress_bar.progress(100)
                
                st.success(f"✅ Generated plan for {len(week_plans)} weeks!")
                
                # Automatically move to review
                st.session_state.current_page = "Review Plan"
                st.rerun()
                
        except Exception as e:
            st.error(f"❌ Error generating plan: {str(e)}")
            logger.error(f"Error in plan generation: {str(e)}", exc_info=True)

def show_review_plan_page():
    """Display the plan review page"""
    st.markdown('<div class="main-header">📋 Review Weekly Plan</div>', unsafe_allow_html=True)
    
    if not st.session_state.module_data:
        st.warning("⚠️ No module data found. Please upload files first.")
        if st.button("Go to Upload"):
            st.session_state.current_page = "Upload"
            st.rerun()
        return
    
    if not st.session_state.week_plans:
        st.warning("⚠️ No weekly plan generated yet.")
        if st.button("Generate Plan"):
            st.session_state.current_page = "Generate Plan"
            st.rerun()
        return
    
    module_data = st.session_state.module_data
    
    st.markdown(f"""
    Review the generated weekly plan for **{module_data.get('title')}**.
    You can expand each week to see detailed information.
    """)
    
    # Plan summary
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Weeks", len(st.session_state.week_plans))
    with col2:
        total_topics = sum(len(w.get('lecture_topics', [])) for w in st.session_state.week_plans)
        st.metric("Total Topics", total_topics)
    with col3:
        total_activities = sum(len(w.get('tutorial_activities', [])) + len(w.get('lab_activities', [])) 
                              for w in st.session_state.week_plans)
        st.metric("Total Activities", total_activities)
    
    st.markdown("---")
    
    # Display each week
    for plan in st.session_state.week_plans:
        week_num = plan.get('week_number', 0)
        title = plan.get('title', 'Untitled')
        
        with st.expander(f"📅 Week {week_num}: {title}", expanded=False):
            # Description
            if plan.get('description'):
                st.markdown(f"**Description:** {plan['description']}")
                st.markdown("---")
            
            # Learning Outcomes
            if plan.get('learning_outcomes'):
                st.markdown("**🎯 Learning Outcomes:**")
                for lo in plan['learning_outcomes']:
                    st.write(f"- {lo}")
            
            # Lecture Topics
            if plan.get('lecture_topics'):
                st.markdown("**📚 Lecture Topics:**")
                for topic in plan['lecture_topics']:
                    st.write(f"- {topic}")
            
            # Tutorial Activities
            if plan.get('tutorial_activities'):
                st.markdown("**👥 Tutorial Activities:**")
                for activity in plan['tutorial_activities']:
                    st.write(f"- {activity}")
            
            # Lab Activities
            if plan.get('lab_activities'):
                st.markdown("**🔬 Lab Activities:**")
                for lab in plan['lab_activities']:
                    st.write(f"- {lab}")
            
            # Readings
            if plan.get('readings'):
                st.markdown("**📖 Required Readings:**")
                for reading in plan['readings']:
                    st.write(f"- {reading}")
            
            # Deliverables
            if plan.get('deliverables'):
                st.markdown("**📝 Deliverables:**")
                for deliverable in plan['deliverables']:
                    st.write(f"- {deliverable}")
    
    st.markdown("---")
    
    # Approval section
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("**Ready to proceed?** Approve this plan to start generating materials.")
    
    with col2:
        if st.button("✅ Approve Plan", type="primary", use_container_width=True):
            st.session_state.plan_approved = True
            st.success("Plan approved!")
            st.session_state.current_page = "Generate Materials"
            st.rerun()

def show_generate_materials_page():
    """Display the materials generation page"""
    st.markdown('<div class="main-header">🎨 Generate Course Materials</div>', unsafe_allow_html=True)
    
    if not st.session_state.plan_approved:
        st.warning("⚠️ Please review and approve the weekly plan first.")
        if st.button("Go to Review Plan"):
            st.session_state.current_page = "Review Plan"
            st.rerun()
        return
    
    st.markdown("""
    Select the types of materials you want to generate for your course.
    The AI will create comprehensive materials for each week.
    """)
    
    # Material selection
    st.markdown('<div class="sub-header">Select Materials to Generate</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        lecture_notes = st.checkbox("📝 Lecture Notes", value=True)
        lecture_slides = st.checkbox("📊 Lecture Slides", value=True)
        transcripts = st.checkbox("📄 Lecture Transcripts", value=False)
    
    with col2:
        lab_materials = st.checkbox("🔬 Lab Materials", value=True)
        assessments = st.checkbox("📋 Assessments/Quizzes", value=True)
        seminar_materials = st.checkbox("💬 Seminar Materials", value=False)
    
    # Collect selected materials
    selected_materials = []
    if lecture_notes:
        selected_materials.append('lecture_notes')
    if lecture_slides:
        selected_materials.append('lecture_slides')
    if transcripts:
        selected_materials.append('transcripts')
    if lab_materials:
        selected_materials.append('lab_materials')
    if assessments:
        selected_materials.append('assessments')
    if seminar_materials:
        selected_materials.append('seminar_materials')
    
    if not selected_materials:
        st.warning("⚠️ Please select at least one material type to generate.")
        return
    
    # Estimate
    total_weeks = len(st.session_state.week_plans)
    total_materials = len(selected_materials) * total_weeks
    
    st.info(f"""
    **Generation Estimate:**  
    - Weeks: {total_weeks}  
    - Material Types: {len(selected_materials)}  
    - Total Items: ~{total_materials}  
    - Estimated Time: {total_materials * 2} - {total_materials * 3} minutes
    """)
    
    # Generate button
    if st.button("🚀 Start Generation", type="primary", use_container_width=True):
        if not AGENTS_AVAILABLE:
            st.error("AI agents are not available. Please install required dependencies.")
            return
        
        try:
            # Initialize generation
            st.session_state.generation_status = 'running'
            
            # Create progress containers
            progress_bar = st.progress(0)
            status_text = st.empty()
            week_status = st.empty()
            
            # Initialize content generator
            content_generator = ContentGenerator()
            export_tools = ExportTools()
            
            completed = 0
            total = total_materials
            
            # Generate materials for each week
            for week_plan_dict in st.session_state.week_plans:
                week_num = week_plan_dict.get('week_number')
                week_title = week_plan_dict.get('title')
                
                week_status.info(f"📅 Generating materials for Week {week_num}: {week_title}")
                
                # Convert to WeekPlan object
                week_plan = WeekPlan(**week_plan_dict)
                module_data = ModuleData(**st.session_state.module_data)
                
                # Generate each material type
                for material_type in selected_materials:
                    status_text.text(f"Generating {material_type.replace('_', ' ').title()} for Week {week_num}...")
                    
                    try:
                        # Generate and save material
                        run_async(generate_and_save_material(
                            st.session_state.session_id,
                            content_generator,
                            export_tools,
                            module_data,
                            week_plan,
                            material_type
                        ))
                        
                        completed += 1
                        progress_bar.progress(completed / total)
                        
                    except Exception as e:
                        st.warning(f"⚠️ Error generating {material_type} for Week {week_num}: {str(e)}")
                        logger.error(f"Error: {str(e)}", exc_info=True)
                        continue
            
            # Complete
            st.session_state.generation_status = 'completed'
            status_text.text("Generation complete!")
            week_status.success(f"✅ Successfully generated {completed} materials!")
            
            st.balloons()
            
            # Next steps
            st.markdown("---")
            if st.button("📥 Go to Downloads", type="primary", use_container_width=True):
                st.session_state.current_page = "Download"
                st.rerun()
                
        except Exception as e:
            st.error(f"❌ Critical error during generation: {str(e)}")
            logger.error(f"Generation error: {str(e)}", exc_info=True)
            st.session_state.generation_status = 'error'

async def generate_and_save_material(session_id: str, content_generator, export_tools, 
                                     module_data, week_plan, material_type: str):
    """Generate and save a specific material type"""
    
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
    
    context = content_generator._prepare_enhanced_context(module_data, week_plan)
    
    # Generate content based on type
    if material_type == 'lecture_notes':
        notes = await content_generator._generate_enhanced_lecture_notes(module_data, week_plan, context)
        for note in notes:
            pdf_path = material_dir / f"Week_{week_plan.week_number:02d}_{sanitize_filename(note.title)}.pdf"
            export_tools.markdown_to_pdf(note.content, pdf_path)
    
    elif material_type == 'lecture_slides':
        slides = await content_generator._generate_enhanced_lecture_slides(module_data, week_plan, context)
        for slide in slides:
            pptx_path = material_dir / f"Week_{week_plan.week_number:02d}_{sanitize_filename(slide.title)}.pptx"
            export_tools.markdown_to_pptx(slide.content, pptx_path)
    
    elif material_type == 'transcripts':
        transcripts = await content_generator._generate_enhanced_transcripts(module_data, week_plan, context)
        for transcript in transcripts:
            txt_path = material_dir / f"Week_{week_plan.week_number:02d}_{sanitize_filename(transcript.title)}.txt"
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(transcript.content)
    
    elif material_type == 'lab_materials':
        labs = await content_generator._generate_enhanced_lab_sheets(module_data, week_plan, context)
        for lab in labs:
            pdf_path = material_dir / f"Week_{week_plan.week_number:02d}_{sanitize_filename(lab.title)}.pdf"
            export_tools.markdown_to_pdf(lab.content, pdf_path)
    
    elif material_type == 'assessments':
        quizzes = await content_generator._generate_enhanced_quizzes(module_data, week_plan, context)
        for quiz in quizzes:
            pdf_path = material_dir / f"Week_{week_plan.week_number:02d}_{sanitize_filename(quiz.title)}.pdf"
            export_tools.markdown_to_pdf(quiz.content, pdf_path)
    
    elif material_type == 'seminar_materials':
        seminars = await content_generator._generate_enhanced_seminar_prompts(module_data, week_plan, context)
        for seminar in seminars:
            pdf_path = material_dir / f"Week_{week_plan.week_number:02d}_{sanitize_filename(seminar.title)}.pdf"
            export_tools.markdown_to_pdf(seminar.content, pdf_path)

def show_download_page():
    """Display the download page"""
    st.markdown('<div class="main-header">📥 Download Materials</div>', unsafe_allow_html=True)
    
    materials = get_session_materials(st.session_state.session_id)
    
    if not materials:
        st.warning("⚠️ No materials have been generated yet.")
        if st.button("Generate Materials"):
            st.session_state.current_page = "Generate Materials"
            st.rerun()
        return
    
    # Summary statistics
    st.markdown('<div class="sub-header">Materials Summary</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Files", len(materials))
    
    with col2:
        total_size = sum(m.get('size', 0) for m in materials)
        st.metric("Total Size", format_file_size(total_size))
    
    with col3:
        weeks = len(set(m.get('week', 0) for m in materials if m.get('week', 0) > 0))
        st.metric("Weeks", weeks)
    
    with col4:
        types = len(set(m.get('type') for m in materials))
        st.metric("Material Types", types)
    
    st.markdown("---")
    
    # Download all button
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**Download Complete Package**")
        st.markdown("Get all materials in a single ZIP file")
    
    with col2:
        if st.button("📦 Download All (ZIP)", type="primary", use_container_width=True):
            try:
                zip_path = create_zip_package(st.session_state.session_id)
                
                with open(zip_path, 'rb') as f:
                    st.download_button(
                        label="💾 Download ZIP Package",
                        data=f,
                        file_name=f"course_materials_{st.session_state.session_id[:8]}.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
            except Exception as e:
                st.error(f"Error creating ZIP package: {str(e)}")
    
    st.markdown("---")
    
    # Materials by week
    st.markdown('<div class="sub-header">Materials by Week</div>', unsafe_allow_html=True)
    
    # Group materials by week
    materials_by_week = {}
    for material in materials:
        week = material.get('week', 0)
        if week not in materials_by_week:
            materials_by_week[week] = []
        materials_by_week[week].append(material)
    
    # Display each week
    for week in sorted(materials_by_week.keys()):
        if week == 0:
            week_label = "General Materials"
        else:
            week_label = f"Week {week}"
        
        with st.expander(f"📅 {week_label} ({len(materials_by_week[week])} files)", expanded=False):
            for material in materials_by_week[week]:
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                
                with col1:
                    st.write(f"📄 {material['name']}")
                
                with col2:
                    st.write(material['format'])
                
                with col3:
                    st.write(format_file_size(material['size']))
                
                with col4:
                    file_path = OUTPUT_DIR / st.session_state.session_id / material['path']
                    if file_path.exists():
                        with open(file_path, 'rb') as f:
                            st.download_button(
                                label="⬇️",
                                data=f,
                                file_name=material['name'],
                                key=f"download_{material['id']}"
                            )
    
    # Materials by type
    st.markdown("---")
    st.markdown('<div class="sub-header">Materials by Type</div>', unsafe_allow_html=True)
    
    materials_by_type = {}
    for material in materials:
        mat_type = material.get('type', 'other')
        if mat_type not in materials_by_type:
            materials_by_type[mat_type] = []
        materials_by_type[mat_type].append(material)
    
    type_labels = {
        'lecture_notes': '📝 Lecture Notes',
        'lecture_slides': '📊 Lecture Slides',
        'transcripts': '📄 Transcripts',
        'lab_materials': '🔬 Lab Materials',
        'assessments': '📋 Assessments',
        'seminar_materials': '💬 Seminar Materials',
        'other': '📁 Other'
    }
    
    for mat_type, type_materials in materials_by_type.items():
        label = type_labels.get(mat_type, mat_type.replace('_', ' ').title())
        st.markdown(f"**{label}** ({len(type_materials)} files)")
        
        for material in type_materials:
            col1, col2, col3 = st.columns([4, 1, 1])
            
            with col1:
                st.write(f"Week {material['week']}: {material['name']}")
            
            with col2:
                st.write(format_file_size(material['size']))
            
            with col3:
                file_path = OUTPUT_DIR / st.session_state.session_id / material['path']
                if file_path.exists():
                    with open(file_path, 'rb') as f:
                        st.download_button(
                            label="⬇️",
                            data=f,
                            file_name=material['name'],
                            key=f"download_type_{material['id']}"
                        )

def show_settings_page():
    """Display settings page"""
    st.markdown('<div class="main-header">⚙️ Settings</div>', unsafe_allow_html=True)
    
    # Session Management
    st.markdown('<div class="sub-header">Session Management</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"""
        **Current Session**  
        ID: `{st.session_state.session_id[:8]}...`  
        Created: {st.session_state.created_at[:10]}  
        Status: {st.session_state.generation_status}
        """)
    
    with col2:
        if st.button("🔄 Start New Session", use_container_width=True):
            if st.checkbox("Confirm: This will reset all data"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                init_session_state()
                st.success("New session started!")
                st.rerun()
    
    st.markdown("---")
    
    # Export Settings
    st.markdown('<div class="sub-header">Export Preferences</div>', unsafe_allow_html=True)
    
    st.checkbox("Include source files in ZIP", value=True, key="include_source")
    st.checkbox("Generate PDF versions of all documents", value=True, key="pdf_versions")
    st.checkbox("Include metadata files", value=False, key="include_metadata")
    
    st.markdown("---")
    
    # Danger Zone
    st.markdown('<div class="sub-header">⚠️ Danger Zone</div>', unsafe_allow_html=True)
    
    if st.button("🗑️ Delete All Session Data", use_container_width=True):
        if st.checkbox("⚠️ Confirm deletion: This cannot be undone"):
            try:
                # Delete session directory
                session_dir = OUTPUT_DIR / st.session_state.session_id
                if session_dir.exists():
                    shutil.rmtree(session_dir)
                
                # Delete upload files
                for file_path in UPLOAD_DIR.glob(f"{st.session_state.session_id}_*"):
                    file_path.unlink()
                
                st.success("✅ Session data deleted")
                
                # Reset session
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                init_session_state()
                st.rerun()
                
            except Exception as e:
                st.error(f"Error deleting session data: {str(e)}")

def show_help_page():
    """Display help and documentation"""
    st.markdown('<div class="main-header">❓ Help & Documentation</div>', unsafe_allow_html=True)
    
    # Quick Start Guide
    with st.expander("🚀 Quick Start Guide", expanded=True):
        st.markdown("""
        ### Getting Started
        
        1. **Upload Module Specification**
           - Go to the Upload page
           - Upload your module specification document (PDF or DOCX)
           - Optionally add textbook PDFs for additional context
           - Click "Process Files"
        
        2. **Generate Weekly Plan**
           - Review the extracted module information
           - Click "Generate Weekly Plan"
           - The AI will create a comprehensive weekly breakdown
        
        3. **Review and Approve**
           - Check each week's content
           - Verify learning outcomes and activities align
           - Click "Approve Plan" when satisfied
        
        4. **Generate Materials**
           - Select the material types you need
           - Click "Start Generation"
           - Wait for materials to be created (this takes time)
        
        5. **Download**
           - Download individual files or complete ZIP package
           - Materials are organized by week and type
        """)
    
    # File Formats
    with st.expander("📄 Supported File Formats"):
        st.markdown("""
        ### Upload Formats
        - **PDF** (.pdf) - Module specifications, textbooks
        - **Word** (.docx, .doc) - Module specifications
        
        ### Generated Formats
        - **Lecture Notes** - PDF and DOCX
        - **Lecture Slides** - PPTX (PowerPoint)
        - **Transcripts** - TXT
        - **Lab Materials** - PDF
        - **Assessments** - PDF
        - **Seminar Materials** - PDF
        """)
    
    # Troubleshooting
    with st.expander("🔧 Troubleshooting"):
        st.markdown("""
        ### Common Issues
        
        **Upload fails:**
        - Check file size (max 50MB)
        - Ensure file is PDF or DOCX
        - Verify file is not corrupted
        
        **Generation is slow:**
        - This is normal - AI generation takes time
        - Average: 2-3 minutes per material
        - Don't refresh the page during generation
        
        **Missing materials:**
        - Check if generation completed successfully
        - Look for error messages in the log
        - Try regenerating specific items
        
        **Download issues:**
        - Ensure generation is complete
        - Check browser download settings
        - Try downloading individual files first
        """)
    
    # API Information
    with st.expander("🔌 API & Technical Details"):
        st.markdown("""
        ### Technical Information
        
        - **AI Model**: Claude Sonnet 4.5
        - **Processing**: Asynchronous generation
        - **Storage**: Local file system
        - **Session**: Browser-based, temporary
        
        ### Data Privacy
        - All processing happens locally
        - No data is stored permanently
        - Session data deleted on cleanup
        - Uploads are temporary
        """)
    
    # Contact and Support
    with st.expander("📧 Support & Feedback"):
        st.markdown("""
        ### Need Help?
        
        If you encounter issues or have suggestions:
        
        1. Check the troubleshooting section above
        2. Review error messages carefully
        3. Try starting a new session
        4. Contact your system administrator
        
        ### Feedback
        We welcome your feedback to improve this tool!
        """)

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application entry point"""
    
    # Sidebar navigation
    with st.sidebar:
        st.image("https://via.placeholder.com/150x50?text=Course+Generator", use_container_width=True)
        
        st.markdown("### 📚 Navigation")
        
        pages = {
            "Dashboard": "🏠",
            "Upload": "📤",
            "Generate Plan": "📅",
            "Review Plan": "📋",
            "Generate Materials": "🎨",
            "Download": "📥",
            "Settings": "⚙️",
            "Help": "❓"
        }
        
        for page_name, icon in pages.items():
            if st.button(f"{icon} {page_name}", use_container_width=True, key=f"nav_{page_name}"):
                st.session_state.current_page = page_name
                st.rerun()
        
        st.markdown("---")
        
        # Session info
        st.markdown("### 📊 Session Info")
        st.markdown(f"**ID:** `{st.session_state.session_id[:8]}...`")
        
        if st.session_state.module_data:
            st.markdown(f"**Module:** {st.session_state.module_data.get('title', 'N/A')[:30]}...")
        
        if st.session_state.week_plans:
            st.markdown(f"**Weeks:** {len(st.session_state.week_plans)}")
        
        st.markdown(f"**Status:** {st.session_state.generation_status}")
        
        st.markdown("---")
        
        # Quick stats
        materials = get_session_materials(st.session_state.session_id)
        if materials:
            st.markdown("### 📈 Quick Stats")
            st.metric("Materials", len(materials))
            total_size = sum(m.get('size', 0) for m in materials)
            st.metric("Total Size", format_file_size(total_size))
    
    # Main content area
    current_page = st.session_state.get('current_page', 'Dashboard')
    
    if current_page == "Dashboard":
        show_dashboard()
    elif current_page == "Upload":
        show_upload_page()
    elif current_page == "Generate Plan":
        show_generate_plan_page()
    elif current_page == "Review Plan":
        show_review_plan_page()
    elif current_page == "Generate Materials":
        show_generate_materials_page()
    elif current_page == "Download":
        show_download_page()
    elif current_page == "Settings":
        show_settings_page()
    elif current_page == "Help":
        show_help_page()
    
    # Footer
    st.markdown("---")
    st.markdown("""
        <div style='text-align: center; color: #666; padding: 1rem;'>
            AI Course Material Generator v1.0.0 | Dr Fakhreldin Saeed
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":

    main()
