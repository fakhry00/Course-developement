"""
Packaging Agent - Creates final downloadable packages
"""

import zipfile
from pathlib import Path
from typing import Dict, Any
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from models.schemas import ModuleData, GeneratedContent
from utils.export_tools import ExportTools

class PackagingAgent:
    """Agent responsible for packaging and exporting content"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",  # Changed from gpt-4 to gpt-4o-mini (correct model name)
            temperature=0.3,
            #max_tokens=4000,
            #request_timeout=120
        )
        self.export_tools = ExportTools()
        
        # Define the packaging agent
        self.packaging_agent = Agent(
            role='Content Packager',
            goal='Organize and package course materials for easy distribution',
            backstory="""You are an expert at organizing educational materials 
            into well-structured packages that are easy for lecturers to use.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
    
    async def create_package(
        self, 
        session_id: str, 
        module_data: ModuleData, 
        generated_content: GeneratedContent
    ) -> Path:
        """Create a complete downloadable package"""
        
        # Create output directory for this session
        output_dir = Path("outputs") / session_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create folder structure
        folders = {
            "lecture_notes": output_dir / "01_Lecture_Notes",
            "lecture_slides": output_dir / "02_Lecture_Slides", 
            "lab_materials": output_dir / "03_Lab_Materials",
            "assessments": output_dir / "04_Assessments",
            "seminar_materials": output_dir / "05_Seminar_Materials",
            "transcripts": output_dir / "06_Transcripts"
        }
        
        for folder in folders.values():
            folder.mkdir(exist_ok=True)
        
        # Export content in various formats
        await self._export_weekly_content(generated_content, folders)
        
        # Create module overview document
        await self._create_module_overview(module_data, output_dir)
        
        # Create instructor guide
        await self._create_instructor_guide(module_data, generated_content, output_dir)
        
        # Create zip package
        package_path = output_dir / "complete_package.zip"
        self._create_zip_package(output_dir, package_path)
        
        return package_path
    
    async def _export_weekly_content(
        self, 
        generated_content: GeneratedContent, 
        folders: Dict[str, Path]
    ):
        """Export all weekly content to appropriate folders"""
        
        for week_content in generated_content.weekly_content:
            week_num = week_content.week_number
            
            # Export lecture notes
            for note in week_content.lecture_notes:
                # Export as PDF
                pdf_path = folders["lecture_notes"] / f"Week_{week_num:02d}_{self._sanitize_filename(note.title)}.pdf"
                self.export_tools.markdown_to_pdf(note.content, pdf_path)
                
                # Export as Word
                docx_path = folders["lecture_notes"] / f"Week_{week_num:02d}_{self._sanitize_filename(note.title)}.docx"
                self.export_tools.markdown_to_docx(note.content, docx_path)
            
            # Export lecture slides
            for slide in week_content.lecture_slides:
                # Export as PowerPoint
                pptx_path = folders["lecture_slides"] / f"Week_{week_num:02d}_{self._sanitize_filename(slide.title)}.pptx"
                self.export_tools.markdown_to_pptx(slide.content, pptx_path)
                
                # Export as PDF
                pdf_path = folders["lecture_slides"] / f"Week_{week_num:02d}_{self._sanitize_filename(slide.title)}.pdf"
                self.export_tools.markdown_to_pdf(slide.content, pdf_path)
            
            # Export lab materials
            for lab in week_content.lab_sheets:
                pdf_path = folders["lab_materials"] / f"Week_{week_num:02d}_{self._sanitize_filename(lab.title)}.pdf"
                self.export_tools.markdown_to_pdf(lab.content, pdf_path)
                
                docx_path = folders["lab_materials"] / f"Week_{week_num:02d}_{self._sanitize_filename(lab.title)}.docx"
                self.export_tools.markdown_to_docx(lab.content, docx_path)
            
            # Export assessments
            for quiz in week_content.quizzes:
                pdf_path = folders["assessments"] / f"Week_{week_num:02d}_{self._sanitize_filename(quiz.title)}.pdf"
                self.export_tools.markdown_to_pdf(quiz.content, pdf_path)
            
            # Export seminar materials
            for seminar in week_content.seminar_prompts:
                pdf_path = folders["seminar_materials"] / f"Week_{week_num:02d}_{self._sanitize_filename(seminar.title)}.pdf"
                self.export_tools.markdown_to_pdf(seminar.content, pdf_path)
            
            # Export transcripts
            for transcript in week_content.transcripts:
                txt_path = folders["transcripts"] / f"Week_{week_num:02d}_{self._sanitize_filename(transcript.title)}.txt"
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write(transcript.content)
    
    async def _create_module_overview(self, module_data: ModuleData, output_dir: Path):
        """Create a module overview document"""
        
        task = Task(
            description=f"""
            Create a comprehensive module overview document for:
            
            Module: {module_data.title} ({module_data.code})
            Credits: {module_data.credits}
            Semester: {module_data.semester}
            
            Learning Outcomes:
            {chr(10).join([f"- {lo.description}" for lo in module_data.learning_outcomes])}
            
            Assessments:
            {chr(10).join([f"- {a.name} ({a.weight}%): {a.type}" for a in module_data.assessments])}
            
            Include:
            1. Module description and objectives
            2. Learning outcomes mapped to weeks
            3. Assessment schedule and requirements
            4. Reading list and resources
            5. Module structure overview
            
            Format as a professional academic document in markdown.
            """,
            agent=self.packaging_agent,
            expected_output="Module overview document in markdown"
        )
        
        crew = Crew(agents=[self.packaging_agent], tasks=[task], verbose=False)
        result = crew.kickoff()
        
        # Export as both PDF and Word
        overview_pdf = output_dir / "00_Module_Overview.pdf"
        overview_docx = output_dir / "00_Module_Overview.docx"
        
        self.export_tools.markdown_to_pdf(str(result), overview_pdf)
        self.export_tools.markdown_to_docx(str(result), overview_docx)
    
    async def _create_instructor_guide(
        self, 
        module_data: ModuleData, 
        generated_content: GeneratedContent, 
        output_dir: Path
    ):
        """Create an instructor guide"""
        
        task = Task(
            description=f"""
            Create an instructor guide for the module "{module_data.title}".
            
            The module has {len(generated_content.weekly_content)} weeks of content
            with {generated_content.total_files} total files generated.
            
            Include:
            1. How to use the generated materials
            2. Customization suggestions
            3. Technical requirements
            4. Assessment guidance
            5. File organization explanation
            6. Tips for effective delivery
            
            Make it practical and actionable for university lecturers.
            """,
            agent=self.packaging_agent,
            expected_output="Comprehensive instructor guide"
        )
        
        crew = Crew(agents=[self.packaging_agent], tasks=[task], verbose=False)
        result = crew.kickoff()
        
        # Export as PDF
        guide_pdf = output_dir / "00_Instructor_Guide.pdf"
        self.export_tools.markdown_to_pdf(str(result), guide_pdf)
    
    def _create_zip_package(self, source_dir: Path, zip_path: Path):
        """Create a zip file containing all materials"""
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in source_dir.rglob('*'):
                if file_path.is_file() and file_path != zip_path:
                    arcname = file_path.relative_to(source_dir)
                    zipf.write(file_path, arcname)
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for cross-platform compatibility"""
        
        import re
        # Remove or replace problematic characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'\s+', '_', filename)
        return filename[:50]  # Limit length 
