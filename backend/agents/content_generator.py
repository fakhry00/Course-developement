"""
Enhanced Content Generator Agent
"""

from typing import List
from crewai import Agent, Task, Crew
from models.schemas import ModuleData, WeekPlan, GeneratedContent, WeeklyContent, ContentItem
from utils.ai_helpers import AIHelpers
from utils.export_tools import ExportTools
from utils.llm_config import LLMConfig

class ContentGenerator:
    """Enhanced agent responsible for generating all course content"""
    
    def __init__(self):
        # Centralized LLM configuration
        self.llm = LLMConfig.get_content_generation_llm()
        self.ai_helpers = AIHelpers()
        self.export_tools = ExportTools()
        
        # Define specialized content generation agents
        self.lecture_agent = Agent(
            role='Advanced Lecture Content Creator',
            goal='Create comprehensive lecture materials that align with specified teaching methods and learning approaches',
            backstory="""You are an expert academic lecturer and instructional designer who creates 
            engaging, well-structured content that incorporates modern pedagogical approaches and 
            adapts to different teaching methods and learning styles.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
        
        self.assessment_agent = Agent(
            role='Pedagogically-Informed Assessment Designer',
            goal='Design assessments that align with learning approaches and use appropriate evaluation methods',
            backstory="""You are an expert in educational assessment who creates fair, challenging, 
            and pedagogically sound learning activities that match specified learning approaches 
            and teaching methodologies.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
        
        self.resource_integration_agent = Agent(
            role='Educational Resource Integration Specialist',
            goal='Integrate uploaded resources and external materials into coherent learning content',
            backstory="""You are skilled at analyzing and integrating various educational resources 
            into cohesive learning materials, making connections between different sources and 
            creating unified learning experiences.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
    

    async def generate_all_content(
        self, 
        module_data: ModuleData, 
        week_plans: List[WeekPlan]
    ) -> GeneratedContent:
        """Generate all content for the module using enhanced information"""
        
        weekly_content = []
        total_files = 0
        
        for week_plan in week_plans:
            week_content = await self._generate_enhanced_weekly_content(module_data, week_plan)
            weekly_content.append(week_content)
            total_files += len(week_content.lecture_notes + week_content.lecture_slides + 
                             week_content.lab_sheets + week_content.quizzes + 
                             week_content.seminar_prompts + week_content.transcripts)
        
        return GeneratedContent(
            module_title=module_data.title,
            weekly_content=weekly_content,
            total_files=total_files
        )
    
    async def _generate_enhanced_weekly_content(
        self, 
        module_data: ModuleData, 
        week_plan: WeekPlan
    ) -> WeeklyContent:
        """Generate enhanced content for a specific week"""
        
        # Prepare context with enhanced information
        context = self._prepare_enhanced_context(module_data, week_plan)
        
        # Generate content with enhanced context
        lecture_notes = await self._generate_enhanced_lecture_notes(module_data, week_plan, context)
        lecture_slides = await self._generate_enhanced_lecture_slides(module_data, week_plan, context)
        lab_sheets = await self._generate_enhanced_lab_sheets(module_data, week_plan, context)
        quizzes = await self._generate_enhanced_quizzes(module_data, week_plan, context)
        seminar_prompts = await self._generate_enhanced_seminar_prompts(module_data, week_plan, context)
        transcripts = await self._generate_enhanced_transcripts(module_data, week_plan, context)
        
        return WeeklyContent(
            week_number=week_plan.week_number,
            lecture_notes=lecture_notes,
            lecture_slides=lecture_slides,
            lab_sheets=lab_sheets,
            quizzes=quizzes,
            seminar_prompts=seminar_prompts,
            transcripts=transcripts
        )
    
    def _prepare_enhanced_context(self, module_data: ModuleData, week_plan: WeekPlan) -> str:
        """Prepare enhanced context including teaching methods, resources, and approaches"""
        
        context_parts = [
            f"Module: {module_data.title}",
            f"Week {week_plan.week_number}: {week_plan.title}",
        ]
        
        if week_plan.description:
            context_parts.append(f"Week Description: {week_plan.description}")
        
        if module_data.topics:
            context_parts.append(f"Module Topics: {', '.join(module_data.topics)}")
        
        if module_data.teaching_methods:
            context_parts.append(f"Teaching Methods: {', '.join(module_data.teaching_methods)}")
        
        if module_data.learning_approaches:
            context_parts.append(f"Learning Approaches: {', '.join(module_data.learning_approaches)}")
        
        if week_plan.resource_files:
            context_parts.append(f"Available Resources: {len(week_plan.resource_files)} uploaded files")
        
        if week_plan.external_resources:
            context_parts.append(f"External Resources: {', '.join(week_plan.external_resources)}")
        
        if week_plan.teaching_notes:
            context_parts.append(f"Teaching Notes: {week_plan.teaching_notes}")
        
        return "\n".join(context_parts)
    
    async def _generate_enhanced_lecture_notes(
        self, 
        module_data: ModuleData, 
        week_plan: WeekPlan,
        context: str
    ) -> List[ContentItem]:
        """Generate enhanced lecture notes incorporating teaching methods and resources"""
        
        lecture_notes = []
        
        for i, topic in enumerate(week_plan.lecture_topics):
            # Determine teaching method approach for this topic
            teaching_methods_text = ", ".join(module_data.teaching_methods) if module_data.teaching_methods else "traditional lecture"
            learning_approaches_text = ", ".join(module_data.learning_approaches) if module_data.learning_approaches else "passive learning"
            
            task = Task(
                description=f"""
                Create comprehensive lecture notes for:
                
                {context}
                Topic: {topic}
                Learning Outcomes: {', '.join(week_plan.learning_outcomes)}
                
                TEACHING METHOD REQUIREMENTS:
                Teaching Methods to Incorporate: {teaching_methods_text}
                Learning Approaches to Apply: {learning_approaches_text}
                
                CONTENT REQUIREMENTS:
                1. Topic introduction aligned with specified teaching methods
                2. Key concepts with examples that support the learning approaches
                3. Interactive elements appropriate for the teaching methods
                4. Activities that engage students using specified learning approaches
                5. Assessment checkpoints that match the pedagogical approach
                6. Summary and reflection prompts
                7. Connection to learning outcomes and real-world applications
                
                PEDAGOGICAL INTEGRATION:
                - If collaborative learning is specified: include group activities and discussions
                - If problem-based learning is used: structure content around problems to solve
                - If experimental learning is emphasized: include hands-on activities and experiments
                - If case study approach is used: incorporate relevant case studies
                - If project-based learning is applied: connect to ongoing projects
                - If flipped classroom is used: create pre-class and in-class components
                
                RESOURCE INTEGRATION:
                {f"Incorporate references to uploaded resources: {[rf['original_name'] for rf in week_plan.resource_files]}" if week_plan.resource_files else ""}
                {f"Reference external resources: {week_plan.external_resources}" if week_plan.external_resources else ""}
                
                Use markdown format with proper headings and structure.
                Aim for 2000-2500 words of substantive, pedagogically-informed content.
                """,
                agent=self.lecture_agent,
                expected_output="Comprehensive pedagogically-informed lecture notes in markdown format"
            )
            
            crew = Crew(agents=[self.lecture_agent], tasks=[task], verbose=False)
            result = crew.kickoff()
            
            lecture_notes.append(ContentItem(
                title=f"Lecture Notes - {topic}",
                content=str(result),
                format="markdown"
            ))
        
        return lecture_notes
    
    async def _generate_enhanced_lecture_slides(
        self, 
        module_data: ModuleData, 
        week_plan: WeekPlan,
        context: str
    ) -> List[ContentItem]:
        """Generate enhanced lecture slides incorporating teaching methods"""
        
        slides = []
        
        for i, topic in enumerate(week_plan.lecture_topics):
            teaching_methods_text = ", ".join(module_data.teaching_methods) if module_data.teaching_methods else "traditional"
            
            task = Task(
                description=f"""
                Create interactive lecture slide content for:
                
                {context}
                Topic: {topic}
                Teaching Methods: {teaching_methods_text}
                
                Create slide content with:
                1. Title slide with topic and learning outcomes
                2. 10-15 content slides designed for the specified teaching methods:
                   - Include interaction prompts if collaborative learning is used
                   - Add problem-solving slides if problem-based learning is emphasized
                   - Include reflection slides if experimental learning is applied
                   - Add case study slides if case study approach is used
                   - Include project connection slides if project-based learning is used
                3. Interactive elements appropriate for the teaching method
                4. Summary slide with reflection questions
                5. Next steps and preparation for tutorials/labs
                
                SLIDE DESIGN PRINCIPLES:
                - Each slide should have a clear title and 3-5 bullet points maximum
                - Include speaker notes with pedagogical guidance
                - Add interaction cues for specified teaching methods
                - Include timing suggestions for activities
                - Reference uploaded resources where relevant
                
                Format as markdown with clear slide breaks (use ---).
                Include detailed speaker notes with teaching method implementation guidance.
                """,
                agent=self.lecture_agent,
                expected_output="Interactive slide content optimized for specified teaching methods"
            )
            
            crew = Crew(agents=[self.lecture_agent], tasks=[task], verbose=False)
            result = crew.kickoff()
            
            slides.append(ContentItem(
                title=f"Slides - {topic}",
                content=str(result),
                format="markdown"
            ))
        
        return slides
    
    async def _generate_enhanced_lab_sheets(
        self, 
        module_data: ModuleData, 
        week_plan: WeekPlan,
        context: str
    ) -> List[ContentItem]:
        """Generate enhanced lab exercises aligned with learning approaches"""
        
        lab_sheets = []
        
        if week_plan.lab_activities:
            for activity in week_plan.lab_activities:
                learning_approaches_text = ", ".join(module_data.learning_approaches) if module_data.learning_approaches else "traditional"
                
                task = Task(
                    description=f"""
                    Create an enhanced practical lab exercise for:
                    
                    {context}
                    Activity: {activity}
                    Learning Approaches: {learning_approaches_text}
                    
                    Design the lab to incorporate the specified learning approaches:
                    
                    LAB STRUCTURE:
                    1. Learning objectives aligned with module outcomes
                    2. Prerequisites and setup (including resource file references)
                    3. Theoretical background connecting to lecture content
                    4. Step-by-step instructions adapted for learning approaches:
                       - Collaborative elements if collaborative learning is used
                       - Problem-solving scenarios if problem-based learning is emphasized
                       - Experimental design if experimental learning is applied
                       - Case analysis if case study approach is used
                       - Project integration if project-based learning is used
                    5. Data collection and analysis sections
                    6. Reflection and discussion questions
                    7. Assessment criteria aligned with learning approaches
                    8. Extension activities for advanced students
                    9. Connections to real-world applications
                    
                    RESOURCE INTEGRATION:
                    {f"Incorporate uploaded resources: {[rf['original_name'] for rf in week_plan.resource_files]}" if week_plan.resource_files else ""}
                    {f"Reference external resources: {week_plan.external_resources}" if week_plan.external_resources else ""}
                    
                    Make it practical, hands-on, and pedagogically sound with clear deliverables.
                    """,
                    agent=self.assessment_agent,
                    expected_output="Comprehensive pedagogically-informed lab exercise sheet"
                )
                
                crew = Crew(agents=[self.assessment_agent], tasks=[task], verbose=False)
                result = crew.kickoff()
                
                lab_sheets.append(ContentItem(
                    title=f"Lab Exercise - {activity}",
                    content=str(result),
                    format="markdown"
                ))
        
        return lab_sheets
    
    # Continue with other enhanced generation methods...
    async def _generate_enhanced_quizzes(
        self, 
        module_data: ModuleData, 
        week_plan: WeekPlan,
        context: str
    ) -> List[ContentItem]:
        """Generate enhanced quizzes aligned with learning approaches"""
        
        learning_approaches_text = ", ".join(module_data.learning_approaches) if module_data.learning_approaches else "traditional assessment"
        
        quiz_task = Task(
            description=f"""
            Create an enhanced assessment quiz for:
            
            {context}
            Topics: {', '.join(week_plan.lecture_topics)}
            Learning Outcomes: {', '.join(week_plan.learning_outcomes)}
            Learning Approaches: {learning_approaches_text}
            
            Design assessment questions that align with the learning approaches:
            
            QUESTION TYPES (adapt based on learning approaches):
            - 5 multiple choice questions (varying complexity levels)
            - 3 short answer questions that test application
            - 2 scenario-based questions if problem-based learning is used
            - 1 collaborative reflection question if collaborative learning is emphasized
            - 1 case analysis question if case study approach is used
            - 1 experimental design question if experimental learning is applied
            
            ASSESSMENT PRINCIPLES:
            - Test understanding and application, not just recall
            - Include questions that require synthesis of multiple concepts
            - Align difficulty with learning outcomes and approaches
            - Provide detailed feedback explanations
            - Include rubrics for subjective questions
            
            Include correct answers, explanations, and marking guidance.
            Ensure questions promote the specified learning approaches.
            """,
            agent=self.assessment_agent,
            expected_output="Comprehensive pedagogically-aligned quiz with answers and rubrics"
        )
        
        crew = Crew(agents=[self.assessment_agent], tasks=[quiz_task], verbose=False)
        result = crew.kickoff()
        
        return [ContentItem(
            title=f"Week {week_plan.week_number} Enhanced Quiz",
            content=str(result),
            format="markdown"
        )]
    
    async def _generate_enhanced_seminar_prompts(
        self, 
        module_data: ModuleData, 
        week_plan: WeekPlan,
        context: str
    ) -> List[ContentItem]:
        """Generate enhanced seminar materials with teaching method integration"""
        
        if not week_plan.tutorial_activities:
            return []
        
        teaching_methods_text = ", ".join(module_data.teaching_methods) if module_data.teaching_methods else "traditional discussion"
        learning_approaches_text = ", ".join(module_data.learning_approaches) if module_data.learning_approaches else "traditional"
        
        seminar_task = Task(
            description=f"""
            Create engaging seminar/tutorial materials for:
            
            {context}
            Activities: {', '.join(week_plan.tutorial_activities)}
            Teaching Methods: {teaching_methods_text}
            Learning Approaches: {learning_approaches_text}
            
            Design seminar content that incorporates specified methods and approaches:
            
            SEMINAR STRUCTURE:
            1. Opening and learning objectives review
            2. Warm-up activity aligned with teaching methods
            3. Main activities designed for learning approaches:
               - Collaborative discussions if collaborative learning is used
               - Problem-solving sessions if problem-based learning is emphasized
               - Hands-on exploration if experimental learning is applied
               - Case study analysis if case study approach is used
               - Project work sessions if project-based learning is used
               - Peer teaching if flipped classroom is used
            4. Reflection and synthesis activities
            5. Preparation for next week
            
            FACILITATION GUIDANCE:
            - Detailed facilitator notes with timing
            - Question banks for different scenarios
            - Troubleshooting common issues
            - Assessment integration points
            - Technology integration suggestions
            
            RESOURCE INTEGRATION:
            {f"Utilize uploaded resources: {[rf['original_name'] for rf in week_plan.resource_files]}" if week_plan.resource_files else ""}
            
            Encourage critical thinking, peer interaction, and active engagement.
            """,
            agent=self.assessment_agent,
            expected_output="Comprehensive seminar materials with facilitation guidance"
        )
        
        crew = Crew(agents=[self.assessment_agent], tasks=[seminar_task], verbose=False)
        result = crew.kickoff()
        
        return [ContentItem(
            title=f"Week {week_plan.week_number} Enhanced Seminar",
            content=str(result),
            format="markdown"
        )]
    
    async def _generate_enhanced_transcripts(
        self, 
        module_data: ModuleData, 
        week_plan: WeekPlan,
        context: str
    ) -> List[ContentItem]:
        """Generate enhanced lecture transcripts with pedagogical cues"""
        
        transcripts = []
        
        for topic in week_plan.lecture_topics:
            teaching_methods_text = ", ".join(module_data.teaching_methods) if module_data.teaching_methods else "traditional lecture"
            
            task = Task(
                description=f"""
                Create an enhanced lecture transcript/narration script for:
                
                {context}
                Topic: {topic}
                Teaching Methods: {teaching_methods_text}
                
                Write as a 20-25 minute interactive lecture incorporating:
                
                SCRIPT ELEMENTS:
                1. Natural speaking rhythm with pedagogical cues
                2. Interactive moments marked with [INTERACTION]
                3. Pauses for reflection marked with [PAUSE]
                4. Emphasis on key points marked with [EMPHASIS]
                5. Activity transitions marked with [ACTIVITY]
                6. Technology integration points marked with [TECH]
                7. Assessment checkpoints marked with [CHECK]
                
                TEACHING METHOD INTEGRATION:
                - Include discussion prompts if collaborative learning is used
                - Add problem presentation if problem-based learning is emphasized
                - Include demonstration cues if experimental learning is applied
                - Reference case studies if case study approach is used
                - Connect to projects if project-based learning is used
                
                Write in a conversational but academic tone.
                Include clear instructions for implementing different teaching methods.
                Provide timing guidance and alternative delivery options.
                """,
                agent=self.lecture_agent,
                expected_output="Enhanced interactive lecture transcript with pedagogical cues"
            )
            
            crew = Crew(agents=[self.lecture_agent], tasks=[task], verbose=False)
            result = crew.kickoff()
            
            transcripts.append(ContentItem(
                title=f"Enhanced Transcript - {topic}",
                content=str(result),
                format="text"
            ))
        
        return transcripts
