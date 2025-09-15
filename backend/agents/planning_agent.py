 
"""
Planning Agent - Creates weekly breakdown and content structure
"""

from typing import List
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from models.schemas import ModuleData, WeekPlan
from utils.ai_helpers import AIHelpers

"""
Planning Agent - Fixed LLM configuration
"""

from typing import List
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from models.schemas import ModuleData, WeekPlan
from utils.ai_helpers import AIHelpers

class PlanningAgent:
    """Agent responsible for creating weekly teaching plans"""
    
    def __init__(self):
        # Fix: Use correct model name and configuration
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",  # Changed from gpt-4 to gpt-4o-mini
            temperature=0.5,
            max_tokens=4000,
            request_timeout=120
        )
        self.ai_helpers = AIHelpers()
        
        # Define the planning agent
        self.planning_agent = Agent(
            role='Academic Course Planner',
            goal='Create comprehensive weekly teaching plans for university modules',
            backstory="""You are an experienced academic who excels at breaking down 
            complex subjects into manageable weekly lessons, ensuring proper progression 
            and alignment with learning outcomes.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
    


    async def generate_weekly_plan(self, module_data: ModuleData) -> List[WeekPlan]:
        """Generate weekly breakdown for the module with enhanced information"""

        # Calculate number of weeks (typically 12 for a semester)
        num_weeks = 12

        # Prepare learning outcomes text
        learning_outcomes_text = "\n".join([
            f"LO{i+1}: {lo.description}" 
            for i, lo in enumerate(module_data.learning_outcomes)
        ])

        # Prepare assessments text
        assessments_text = "\n".join([
            f"{assessment.name} ({assessment.weight}%): {assessment.description or assessment.type}"
            for assessment in module_data.assessments
        ])

        # Include topics and teaching methods in the prompt
        topics_text = "\n".join(module_data.topics) if module_data.topics else "Not specified"
        teaching_methods_text = ", ".join(module_data.teaching_methods) if module_data.teaching_methods else "Traditional methods"
        learning_approaches_text = ", ".join(module_data.learning_approaches) if module_data.learning_approaches else "Standard approaches"

        planning_task = Task(
            description=f"""
            Create a {num_weeks}-week teaching plan for the module "{module_data.title}".

            Module Details:
            - Code: {module_data.code}
            - Credits: {module_data.credits}
            - Description: {module_data.description}

            Main Topics to Cover:
            {topics_text}

            Teaching Methods to Use:
            {teaching_methods_text}

            Learning Approaches to Apply:
            {learning_approaches_text}

            Learning Outcomes:
            {learning_outcomes_text}

            Assessments:
            {assessments_text}

            Available Textbooks:
            {', '.join(module_data.textbooks) if module_data.textbooks else 'None specified'}

            For each week, provide:
            1. Week number and descriptive title
            2. Detailed description of the week's focus and objectives
            3. Learning outcomes addressed (reference LO numbers)
            4. 2-3 main lecture topics aligned with teaching methods
            5. Tutorial/seminar activities that use the specified learning approaches
            6. Lab activities (if applicable)
            7. Recommended readings
            8. Any deliverables or milestones

            Ensure logical progression, even distribution of learning outcomes, and
            alignment with the specified teaching methods and learning approaches.
            Consider assessment deadlines and provide preparation weeks.

            Return as structured JSON array with each week as an object.
            """,
            agent=self.planning_agent,
            expected_output="JSON array of weekly plans with enhanced information"
        )

        # Execute planning (rest remains the same)
        crew = Crew(
            agents=[self.planning_agent],
            tasks=[planning_task],
            verbose=True
        )

        result = crew.kickoff()

        # Parse result and create WeekPlan objects
        parsed_weeks = self.ai_helpers.parse_weekly_plan_result(str(result))

        week_plans = []
        for week_data in parsed_weeks:
            week_plan = WeekPlan(
                week_number=week_data.get('week_number', len(week_plans) + 1),
                title=week_data.get('title', f"Week {len(week_plans) + 1}"),
                description=week_data.get('description', ''),
                learning_outcomes=week_data.get('learning_outcomes', []),
                lecture_topics=week_data.get('lecture_topics', []),
                tutorial_activities=week_data.get('tutorial_activities', []),
                lab_activities=week_data.get('lab_activities', []),
                readings=week_data.get('readings', []),
                deliverables=week_data.get('deliverables', []),
                external_resources=week_data.get('external_resources', []),
                resource_files=week_data.get('resource_files', []),
                teaching_notes=week_data.get('teaching_notes', '')
            )
            week_plans.append(week_plan)

        return week_plans[:num_weeks]