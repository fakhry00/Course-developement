# AI-Powered Course Material Generator

An intelligent platform that helps university lecturers co-create comprehensive module materials using AI agents in an interactive, step-by-step workflow.

-----

## 🎯 Features

  * **Document Processing**: Upload and parse module specifications (PDF/Word).
  * **AI-Powered Planning**: Generate weekly breakdowns with learning outcomes mapped to the content.
  * **Content Generation**: Create detailed lecture notes, slides, labs, quizzes, and assessments.
  * **Interactive Review**: Review and modify AI suggestions at each stage of the workflow.
  * **Multi-Format Export**: Export materials in PDF, Word, and PowerPoint formats.
  * **Complete Packaging**: Get an organized folder structure ready for institutional use.

-----

## 🏗️ Architecture

The project is built on a robust backend that orchestrates a series of specialized **AI agents** to handle the content generation workflow.

### Backend Components

  * **FastAPI**: Web framework and API endpoints.
  * **CrewAI**: AI agent orchestration and workflow management.
  * **LangChain**: AI model integration and prompt management.
  * **Document Parsers**: PyMuPDF and docx2txt for file processing.
  * **Export Tools**: Multi-format document generation.

### AI Agents

1.  **Ingestion Agent**: Extracts module specifications and requirements.
2.  **Planning Agent**: Creates weekly teaching plans and content structure.
3.  **Content Generator**: Produces all teaching materials.
4.  **Packaging Agent**: Organizes and exports final deliverables.

-----

## 🚀 Quick Start

### Prerequisites

  * Python 3.8+
  * OpenAI API key
  * 4GB+ RAM recommended

### Installation

1.  **Clone the repository**:

    ```powershell
    git clone <repository-url>
    cd coursegen-v1
    ```

2.  **Create and activate a virtual environment**:

    On Windows (PowerShell):

    ```powershell
    python -m venv .venv
    .venv\Scripts\Activate.ps1
    ```

    On macOS / Linux:

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies**:

    ```powershell
    pip install --upgrade pip
    pip install -r requirements.txt
    ```

4.  **Set up environment variables**:

    ```powershell
    copy .env.example .env
    # Edit .env file and add your OPENAI_API_KEY and other settings
    ```

5.  **Run the application**:

    ```powershell
    cd backend
    python main.py
    ```

6.  **Access the application**:

    Open http://localhost:8000 in your browser.

-----

## 📁 Project Structure

```
coursegen/
├── backend/
│   ├── main.py                  # FastAPI application entry point
│   ├── agents/                  # AI agent implementations
│   ├── utils/                   # Utility functions for file parsing, exports, etc.
│   ├── models/                  # Pydantic data models and schemas
│   ├── templates/               # HTML templates
│   └── static/                  # CSS and JavaScript assets
├── outputs/                     # Generated content storage
├── uploads/                     # Uploaded files storage
└── requirements.txt             # Python dependencies
```

-----

## 🔧 Configuration

Environment variables are configured in the `.env` file.

| Variable | Description | Default |
| :--- | :--- | :--- |
| `OPENAI_API_KEY` | Your OpenAI API key (required) | N/A |
| `APP_PORT` | Application port | `8000` |
| `MAX_FILE_SIZE_MB` | Maximum upload file size | `50` |

-----

## 🔄 Workflow

The platform follows an intuitive, step-by-step process:

1.  **Upload**: Upload module specifications and optional textbooks.
2.  **Extract**: The AI extracts learning outcomes, assessments, and structure.
3.  **Plan**: The AI generates a weekly teaching plan for your review.
4.  **Generate**: AI agents create all course materials.
5.  **Export**: Download the complete package in your desired format.

-----

## 📤 Output Structure

Generated packages include a clean folder structure for all materials:

```
course_materials/
├── 01_Lecture_Notes/           # PDF and Word formats
├── 02_Lecture_Slides/          # PowerPoint and PDF formats
├── 03_Lab_Materials/           # Exercise sheets and solutions
├── 04_Assessments/             # Quizzes and exam materials
├── 05_Seminar_Materials/       # Discussion prompts and activities
├── 06_Transcripts/             # Lecture narration scripts
├── 00_Module_Overview.pdf      # Complete module overview
└── 00_Instructor_Guide.pdf     # Usage instructions
```

-----

## 🤖 Detailed AI Agents

Each agent has a specific role in the workflow, with the output of one serving as the input for the next.

### Ingestion Agent

This agent is the **information extractor**. It analyzes uploaded documents to identify and pull out key elements, such as:

  * **Learning Outcomes**: The core knowledge and skills students should acquire.
  * **Assessment Requirements**: Details on how students will be evaluated.
  * **Course Structure**: Weekly topics and thematic organization.

### Planning Agent

This agent is the **virtual course designer**. It uses the data from the Ingestion Agent to create a detailed, week-by-week teaching plan, ensuring a logical flow and mapping all content back to the learning outcomes.

### Content Generator

The **creative powerhouse**, this agent takes the detailed plan and produces all the course materials, including lecture notes, slides, lab exercises, and quizzes.

### Packaging Agent

The **organizer and formatter**, this final agent takes all the generated content, arranges it into a clean folder structure, and exports it into multiple formats for easy use.



## 🙏 Acknowledgments

  * **OpenAI** for the GPT-4 API.
  * **CrewAI** for the agent orchestration framework.
  * **FastAPI** for the excellent web framework.
  * The broader open-source community for the tools and libraries that made this possible.
