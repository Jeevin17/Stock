from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import httpx
import re
from enum import Enum

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="OSSU Course Tracker", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Define Models
class CurriculumType(str, Enum):
    COMPUTER_SCIENCE = "computer-science"
    DATA_SCIENCE = "data-science"
    MATHEMATICS = "math"
    BIOINFORMATICS = "bioinformatics"
    PRECOLLEGE_MATH = "precollege-math"

class Course(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    curriculum: CurriculumType
    category: str
    description: Optional[str] = None
    duration: Optional[str] = None
    effort: Optional[str] = None
    prerequisites: Optional[str] = None
    url: Optional[str] = None
    topics: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CourseCreate(BaseModel):
    name: str
    curriculum: CurriculumType
    category: str
    description: Optional[str] = None
    duration: Optional[str] = None
    effort: Optional[str] = None
    prerequisites: Optional[str] = None
    url: Optional[str] = None
    topics: List[str] = []

class Progress(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    course_id: str
    percentage: float = Field(ge=0, le=100, default=0)
    estimated_time_hours: Optional[float] = None
    time_spent_hours: float = Field(ge=0, default=0)
    notes: Optional[str] = None
    status: str = Field(default="not_started")  # not_started, in_progress, completed
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ProgressUpdate(BaseModel):
    percentage: Optional[float] = Field(None, ge=0, le=100)
    estimated_time_hours: Optional[float] = None
    time_spent_hours: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None
    status: Optional[str] = None

class Curriculum(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: CurriculumType
    description: str
    github_url: str
    categories: List[str] = []
    total_courses: int = 0
    last_synced: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

# OSSU curriculum definitions
CURRICULA_CONFIG = {
    CurriculumType.COMPUTER_SCIENCE: {
        "name": "Computer Science",
        "description": "Path to a free self-taught education in Computer Science!",
        "github_url": "https://github.com/ossu/computer-science",
        "categories": ["Prerequisites", "Intro CS", "Core Programming", "Core Math", "CS Tools",
                      "Core Systems", "Core Theory", "Core Security", "Core Applications",
                      "Core Ethics", "Advanced Programming", "Advanced Systems", "Advanced Theory",
                      "Advanced Information Security", "Advanced Math", "Final Project"]
    },
    CurriculumType.DATA_SCIENCE: {
        "name": "Data Science",
        "description": "Path to a free self-taught education in Data Science!",
        "github_url": "https://github.com/ossu/data-science",
        "categories": ["Introduction to Data Science", "Introduction to Computer Science",
                      "Data Structures and Algorithms", "Databases", "Mathematics",
                      "Statistics & Probability", "Data Science Tools & Methods",
                      "Machine Learning/Data Mining", "Final Project"]
    },
    CurriculumType.MATHEMATICS: {
        "name": "Mathematics",
        "description": "Path to a free self-taught education in Mathematics!",
        "github_url": "https://github.com/ossu/math",
        "categories": ["Introduction to Mathematical Thinking", "Calculus", "Linear Algebra",
                      "Probability and Statistics", "Advanced Mathematics"]
    },
    CurriculumType.BIOINFORMATICS: {
        "name": "Bioinformatics",
        "description": "Path to a free self-taught education in Bioinformatics!",
        "github_url": "https://github.com/ossu/bioinformatics",
        "categories": ["Prerequisites", "Introduction to Biology", "Core Bioinformatics",
                      "Statistics and Machine Learning", "Advanced Topics", "Final Project"]
    },
    CurriculumType.PRECOLLEGE_MATH: {
        "name": "Precollege Math",
        "description": "Precollege Math Curriculum!",
        "github_url": "https://github.com/ossu/precollege-math",
        "categories": ["Arithmetic", "Pre-Algebra", "Algebra Basics", "Geometry",
                      "Algebra II", "Trigonometry", "Precalculus"]
    }
}

# API Routes
@api_router.get("/")
async def root():
    return {"message": "OSSU Course Tracker API", "version": "1.0.0"}

@api_router.get("/curricula", response_model=List[Curriculum])
async def get_curricula():
    """Get all available curricula"""
    curricula = await db.curricula.find().to_list(1000)
    if not curricula:
        # Initialize curricula if empty
        await initialize_curricula()
        curricula = await db.curricula.find().to_list(1000)
    return [Curriculum(**curriculum) for curriculum in curricula]

@api_router.get("/curricula/{curriculum_type}", response_model=Curriculum)
async def get_curriculum(curriculum_type: CurriculumType):
    """Get specific curriculum"""
    curriculum = await db.curricula.find_one({"type": curriculum_type})
    if not curriculum:
        raise HTTPException(status_code=404, detail="Curriculum not found")
    return Curriculum(**curriculum)

@api_router.get("/courses", response_model=List[Course])
async def get_courses(curriculum: Optional[CurriculumType] = None, category: Optional[str] = None):
    """Get courses with optional filtering"""
    query = {}
    if curriculum:
        query["curriculum"] = curriculum
    if category:
        query["category"] = category

    courses = await db.courses.find(query).to_list(1000)
    return [Course(**course) for course in courses]

@api_router.post("/courses", response_model=Course)
async def create_course(course: CourseCreate):
    """Create a new course"""
    course_obj = Course(**course.dict())
    await db.courses.insert_one(course_obj.dict())
    return course_obj

@api_router.get("/courses/{course_id}", response_model=Course)
async def get_course(course_id: str):
    """Get specific course"""
    course = await db.courses.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return Course(**course)

@api_router.get("/progress", response_model=List[Progress])
async def get_progress():
    """Get all progress entries"""
    progress_entries = await db.progress.find().to_list(1000)
    return [Progress(**progress) for progress in progress_entries]

@api_router.get("/progress/{course_id}", response_model=Progress)
async def get_course_progress(course_id: str):
    """Get progress for a specific course"""
    progress = await db.progress.find_one({"course_id": course_id})
    if not progress:
        # Create default progress entry
        new_progress = Progress(course_id=course_id)
        await db.progress.insert_one(new_progress.dict())
        return new_progress
    return Progress(**progress)

@api_router.put("/progress/{course_id}", response_model=Progress)
async def update_course_progress(course_id: str, progress_update: ProgressUpdate):
    """Update progress for a specific course"""
    # Check if course exists
    course = await db.courses.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Get existing progress or create new
    existing_progress = await db.progress.find_one({"course_id": course_id})

    if existing_progress:
        # Update existing progress
        update_data = {k: v for k, v in progress_update.dict().items() if v is not None}
        update_data["last_updated"] = datetime.utcnow()

        # Auto-update status based on percentage
        if "percentage" in update_data:
            if update_data["percentage"] == 0:
                update_data["status"] = "not_started"
            elif update_data["percentage"] == 100:
                update_data["status"] = "completed"
            else:
                update_data["status"] = "in_progress"

        # Auto-increment progress based on time spent (optional feature)
        if "time_spent_hours" in update_data and existing_progress.get("estimated_time_hours"):
            old_time_spent = existing_progress.get("time_spent_hours", 0)
            new_time_spent = update_data["time_spent_hours"]
            estimated_time = existing_progress.get("estimated_time_hours", 1)

            # If time spent increased significantly, suggest progress increase
            time_increase = new_time_spent - old_time_spent
            if time_increase > 0:
                # Calculate suggested progress increase (1 hour = roughly 2-3% progress)
                suggested_progress_increase = min(time_increase * 2.5, 10)  # Cap at 10% per update
                current_percentage = existing_progress.get("percentage", 0)
                suggested_percentage = min(current_percentage + suggested_progress_increase, 100)

                # If no percentage was explicitly provided, use the suggested one
                if "percentage" not in update_data:
                    update_data["percentage"] = suggested_percentage
                    if suggested_percentage == 100:
                        update_data["status"] = "completed"
                    elif suggested_percentage > 0:
                        update_data["status"] = "in_progress"

        await db.progress.update_one(
            {"course_id": course_id},
            {"$set": update_data}
        )

        # Get updated progress
        updated_progress = await db.progress.find_one({"course_id": course_id})
        return Progress(**updated_progress)
    else:
        # Create new progress
        progress_data = progress_update.dict()
        progress_data = {k: v for k, v in progress_data.items() if v is not None}
        progress_data["course_id"] = course_id

        new_progress = Progress(**progress_data)
        await db.progress.insert_one(new_progress.dict())
        return new_progress

@api_router.post("/progress/{course_id}/auto-update")
async def auto_update_progress(course_id: str, hours_studied: float):
    """Automatically update progress based on hours studied"""
    # Check if course exists
    course = await db.courses.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Get existing progress
    existing_progress = await db.progress.find_one({"course_id": course_id})
    if not existing_progress:
        # Create initial progress
        new_progress = Progress(course_id=course_id, time_spent_hours=hours_studied)
        await db.progress.insert_one(new_progress.dict())
        return new_progress

    current_time = existing_progress.get("time_spent_hours", 0)
    new_time = current_time + hours_studied

    # Calculate auto-progress based on course effort
    course_effort = course.get("effort", "")
    estimated_hours = existing_progress.get("estimated_time_hours")

    if not estimated_hours:
        # Try to parse estimated hours from course effort string
        effort_match = re.search(r'(\d+)-?(\d+)?\s*hours?/week', course_effort, re.IGNORECASE)
        if effort_match:
            duration_match = re.search(r'(\d+)\s*weeks?', course.get("duration", ""), re.IGNORECASE)
            if duration_match:
                min_hours_per_week = int(effort_match.group(1))
                weeks = int(duration_match.group(1))
                estimated_hours = min_hours_per_week * weeks

    # Calculate progress percentage
    if estimated_hours and estimated_hours > 0:
        progress_percentage = min((new_time / estimated_hours) * 100, 100)
    else:
        # Fallback: assume 1 hour = 2% progress
        progress_percentage = min(new_time * 2, 100)

    # Determine status
    if progress_percentage >= 100:
        status = "completed"
    elif progress_percentage > 0:
        status = "in_progress"
    else:
        status = "not_started"

    # Update progress
    update_data = {
        "time_spent_hours": new_time,
        "percentage": progress_percentage,
        "status": status,
        "last_updated": datetime.utcnow()
    }

    if estimated_hours:
        update_data["estimated_time_hours"] = estimated_hours

    await db.progress.update_one(
        {"course_id": course_id},
        {"$set": update_data}
    )

    updated_progress = await db.progress.find_one({"course_id": course_id})
    return Progress(**updated_progress)

@api_router.post("/progress/bulk-auto-update")
async def bulk_auto_update():
    """Automatically update progress for all courses based on time spent"""
    updated_count = 0

    # Get all progress entries with time spent but outdated percentage
    progress_entries = await db.progress.find({
        "time_spent_hours": {"$gt": 0},
        "$or": [
            {"percentage": {"$lt": 10}},  # Very low progress despite time spent
            {"last_updated": {"$lt": datetime.utcnow().replace(hour=0, minute=0, second=0)}}  # Not updated today
        ]
    }).to_list(1000)

    for progress_entry in progress_entries:
        course_id = progress_entry["course_id"]
        course = await db.courses.find_one({"id": course_id})

        if not course:
            continue

        time_spent = progress_entry.get("time_spent_hours", 0)
        estimated_hours = progress_entry.get("estimated_time_hours")

        # Try to get estimated hours from course data if not set
        if not estimated_hours:
            course_effort = course.get("effort", "")
            effort_match = re.search(r'(\d+)-?(\d+)?\s*hours?/week', course_effort, re.IGNORECASE)
            if effort_match:
                duration_match = re.search(r'(\d+)\s*weeks?', course.get("duration", ""), re.IGNORECASE)
                if duration_match:
                    min_hours_per_week = int(effort_match.group(1))
                    weeks = int(duration_match.group(1))
                    estimated_hours = min_hours_per_week * weeks

        if estimated_hours and time_spent > 0:
            # Calculate suggested progress
            suggested_percentage = min((time_spent / estimated_hours) * 100, 100)
            current_percentage = progress_entry.get("percentage", 0)

            # Only update if suggested progress is significantly higher
            if suggested_percentage > current_percentage + 5:  # At least 5% increase
                new_percentage = min(suggested_percentage, 100)
                status = "completed" if new_percentage >= 100 else "in_progress"

                await db.progress.update_one(
                    {"course_id": course_id},
                    {"$set": {
                        "percentage": new_percentage,
                        "status": status,
                        "estimated_time_hours": estimated_hours,
                        "last_updated": datetime.utcnow()
                    }}
                )
                updated_count += 1

    return {"message": f"Auto-updated progress for {updated_count} courses"}

async def fetch_github_content(url: str) -> str:
    """Fetch content from GitHub raw URL"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text

def parse_course_table_row(row: str, curriculum: CurriculumType, category: str) -> Optional[Dict]:
    """Enhanced parsing of table rows from OSSU markdown to extract course info"""
    if not row.strip() or not '|' in row:
        return None

    # Split by | and clean up - handle various formats
    parts = [part.strip() for part in row.split('|')]
    # Remove empty parts from beginning and end
    while parts and not parts[0]:
        parts.pop(0)
    while parts and not parts[-1]:
        parts.pop()

    if len(parts) < 2:  # Need at least course name and one other field
        return None

    course_name_cell = parts[0].strip()

    # Skip header rows, separators, or empty names - more flexible conditions
    skip_indicators = [
        'courses', 'course', 'name', 'subject', 'duration', 'effort', 'prerequisite',
        ':--', '---', '===', 'week', 'hour', 'time', 'estimated'
    ]
    
    if (not course_name_cell or
        len(course_name_cell) < 3 or
        any(indicator in course_name_cell.lower() for indicator in skip_indicators) or
        course_name_cell.startswith(':') or
        course_name_cell.startswith('-') or
        course_name_cell.count('-') > 3):
        return None

    # Extract URL from various markdown link formats
    url_patterns = [
        r'\[([^\]]+)\]\(([^)]+)\)',  # Standard [text](url)
        r'\*\*\[([^\]]+)\]\(([^)]+)\)\*\*',  # Bold link
        r'\*\[([^\]]+)\]\(([^)]+)\)\*',  # Italic link
    ]
    
    clean_name = course_name_cell
    course_url = None
    
    for pattern in url_patterns:
        url_match = re.search(pattern, course_name_cell)
        if url_match:
            clean_name = url_match.group(1).strip()
            course_url = url_match.group(2).strip()
            break
    
    if not course_url:
        # Handle other markdown formatting
        clean_name = re.sub(r'\*\*([^*]+)\*\*', r'\1', clean_name)  # Remove bold
        clean_name = re.sub(r'\*([^*]+)\*', r'\1', clean_name)  # Remove italic
        clean_name = re.sub(r'`([^`]+)`', r'\1', clean_name)  # Remove code formatting
        clean_name = clean_name.strip()

    # Skip if name is still too short or looks invalid
    if len(clean_name) < 3 or clean_name.lower() in skip_indicators:
        return None

    # Extract other fields with more flexibility
    duration = ""
    effort = ""
    prerequisites = "none"
    
    if len(parts) > 1:
        duration = parts[1].strip() if len(parts) > 1 else ""
    if len(parts) > 2:
        effort = parts[2].strip() if len(parts) > 2 else ""
    if len(parts) > 3:
        prerequisites = parts[3].strip() if len(parts) > 3 else "none"
    
    # Clean up prerequisites
    if not prerequisites or prerequisites.lower() in ['', '-', 'none', 'n/a']:
        prerequisites = "none"

    return {
        "name": clean_name,
        "curriculum": curriculum,
        "category": category,
        "description": f"Part of {curriculum.value.replace('-', ' ').title()} curriculum - {category}",
        "duration": duration,
        "effort": effort,
        "prerequisites": prerequisites,
        "url": course_url,
        "topics": []
    }

def detect_table_start(line: str, next_lines: List[str] = None) -> bool:
    """Enhanced table detection logic"""
    line = line.strip().lower()
    
    # Direct table indicators
    if ('|' in line and 
        (line.count('|') >= 3 or 
         any(word in line for word in ['course', 'duration', 'effort', 'prerequisite', 'week', 'hour', 'subject']))):
        return True
    
    # Check if next few lines confirm this is a table
    if next_lines:
        for next_line in next_lines[:3]:
            if '|:' in next_line or '|--' in next_line:
                return True
            if next_line.count('|') >= 3:
                return True
    
    return False

async def sync_curriculum_courses(curriculum: CurriculumType) -> List[Dict]:
    """Enhanced sync courses for a specific curriculum from GitHub"""
    courses = []
    
    try:
        # Get GitHub raw URLs with fallback branches
        github_urls = {
            CurriculumType.COMPUTER_SCIENCE: [
                "https://raw.githubusercontent.com/ossu/computer-science/master/README.md",
                "https://raw.githubusercontent.com/ossu/computer-science/main/README.md"
            ],
            CurriculumType.DATA_SCIENCE: [
                "https://raw.githubusercontent.com/ossu/data-science/master/README.md",
                "https://raw.githubusercontent.com/ossu/data-science/main/README.md"
            ],
            CurriculumType.MATHEMATICS: [
                "https://raw.githubusercontent.com/ossu/math/master/README.md",
                "https://raw.githubusercontent.com/ossu/math/main/README.md"
            ],
            CurriculumType.BIOINFORMATICS: [
                "https://raw.githubusercontent.com/ossu/bioinformatics/master/README.md",
                "https://raw.githubusercontent.com/ossu/bioinformatics/main/README.md"
            ],
            CurriculumType.PRECOLLEGE_MATH: [
                "https://raw.githubusercontent.com/ossu/precollege-math/master/README.md",
                "https://raw.githubusercontent.com/ossu/precollege-math/main/README.md"
            ]
        }

        if curriculum not in github_urls:
            print(f"No URL configured for {curriculum}")
            return get_fallback_courses(curriculum)

        # Try multiple URLs until one works
        content = None
        for url in github_urls[curriculum]:
            try:
                content = await fetch_github_content(url)
                print(f"Successfully fetched content from {url}")
                break
            except Exception as e:
                print(f"Failed to fetch from {url}: {str(e)}")
                continue

        if not content:
            print(f"Could not fetch content for {curriculum}, using fallback")
            return get_fallback_courses(curriculum)

        lines = content.split('\n')
        current_category = ""
        in_table = False
        found_courses = 0
        parsed_lines = 0
        
        print(f"Processing {len(lines)} lines for {curriculum}")

        for i, line in enumerate(lines):
            line = line.strip()
            parsed_lines += 1
            
            # More flexible category header detection
            if line.startswith('#') and len(line) > 1:
                # Extract category name more flexibly
                potential_category = line.replace('#', '').strip()
                # Skip very short or generic headers
                if len(potential_category) > 3 and potential_category.lower() not in ['ossu', 'about', 'faq']:
                    current_category = potential_category
                    in_table = False
                    print(f"Found category: {current_category}")
                continue

            # Enhanced table detection
            if not in_table:
                next_lines = lines[i+1:i+4] if i+1 < len(lines) else []
                if detect_table_start(line, next_lines):
                    in_table = True
                    print(f"Started table in category: {current_category}")
                    continue

            # Skip table separator lines with more patterns
            if in_table and any(pattern in line for pattern in ['|:', '|--', '| :', '|-', ':--|']):
                continue

            # Parse course rows with enhanced logic
            if in_table and '|' in line and current_category:
                course_data = parse_course_table_row(line, curriculum, current_category)
                if course_data:
                    courses.append(course_data)
                    found_courses += 1
                    print(f"✓ Parsed course {found_courses}: {course_data['name']}")
                else:
                    # Debug failed parsing attempts
                    if line.strip() and not line.startswith('#') and len(line) > 10:
                        print(f"✗ Could not parse line {i}: {line[:100]}...")

            # End table on new header or empty section
            elif in_table and (line.startswith('#') or (not line.strip() and i < len(lines)-1 and not lines[i+1].strip())):
                in_table = False
                print(f"Ended table for category: {current_category}")

        print(f"Successfully parsed {found_courses} courses from {parsed_lines} lines for {curriculum}")

        # Enhanced fallback logic - only use fallback if very few courses found
        if len(courses) < 5:
            print(f"Only found {len(courses)} courses for {curriculum}, using enhanced fallback")
            fallback_courses = get_fallback_courses(curriculum)
            # Merge parsed courses with fallback, avoiding duplicates
            existing_names = {course['name'].lower() for course in courses}
            for fallback_course in fallback_courses:
                if fallback_course['name'].lower() not in existing_names:
                    courses.append(fallback_course)

        return courses

    except Exception as e:
        print(f"Error syncing {curriculum}: {str(e)}")
        return get_fallback_courses(curriculum)

def get_fallback_courses(curriculum: CurriculumType) -> List[Dict]:
    """Comprehensive fallback courses when GitHub parsing fails - now includes 60+ courses total"""
    fallback_courses = {
        CurriculumType.COMPUTER_SCIENCE: [
            {
                "name": "Introduction to Computer Science and Programming using Python",
                "curriculum": curriculum,
                "category": "Intro CS",
                "description": "Learn programming fundamentals with Python",
                "duration": "14 weeks",
                "effort": "6-10 hours/week",
                "prerequisites": "high school algebra",
                "url": "https://www.edx.org/course/introduction-to-computer-science-and-programming-7",
                "topics": ["computation", "imperative programming", "basic data structures"]
            },
            {
                "name": "Introduction to Computational Thinking and Data Science",
                "curriculum": curriculum,
                "category": "Intro CS",
                "description": "Learn computational thinking and data science",
                "duration": "9 weeks",
                "effort": "6-10 hours/week",
                "prerequisites": "Introduction to Computer Science using Python",
                "url": "https://www.edx.org/course/introduction-to-computational-thinking-and-data-4",
                "topics": ["computational thinking", "data science", "optimization"]
            },
            {
                "name": "Systematic Program Design",
                "curriculum": curriculum,
                "category": "Core Programming",
                "description": "Systematic approach to program design",
                "duration": "13 weeks",
                "effort": "8-10 hours/week",
                "prerequisites": "none",
                "url": "https://www.edx.org/course/how-to-code-simple-data",
                "topics": ["functional programming", "design for testing"]
            },
            {
                "name": "How to Code: Complex Data",
                "curriculum": curriculum,
                "category": "Core Programming", 
                "description": "Programming with complex data structures",
                "duration": "12 weeks",
                "effort": "8-10 hours/week",
                "prerequisites": "Systematic Program Design",
                "url": "https://www.edx.org/course/how-to-code-complex-data",
                "topics": ["data structures", "recursion", "mutual recursion"]
            },
            {
                "name": "Programming Languages, Part A",
                "curriculum": curriculum,
                "category": "Core Programming",
                "description": "Programming language concepts and paradigms",
                "duration": "5 weeks",
                "effort": "4-8 hours/week",
                "prerequisites": "Systematic Program Design",
                "url": "https://www.coursera.org/learn/programming-languages",
                "topics": ["ML", "functional programming", "type systems"]
            },
            {
                "name": "Programming Languages, Part B",
                "curriculum": curriculum,
                "category": "Core Programming",
                "description": "Continuation of programming languages",
                "duration": "3 weeks",
                "effort": "4-8 hours/week",
                "prerequisites": "Programming Languages, Part A",
                "url": "https://www.coursera.org/learn/programming-languages-part-b",
                "topics": ["Racket", "dynamic typing", "OOP"]
            },
            {
                "name": "Programming Languages, Part C",
                "curriculum": curriculum,
                "category": "Core Programming",
                "description": "Object-oriented programming concepts",
                "duration": "3 weeks",
                "effort": "4-8 hours/week",
                "prerequisites": "Programming Languages, Part B",
                "url": "https://www.coursera.org/learn/programming-languages-part-c",
                "topics": ["Ruby", "OOP", "subtyping"]
            },
            {
                "name": "Object-Oriented Design",
                "curriculum": curriculum,
                "category": "Core Programming",
                "description": "Design patterns and OOP principles",
                "duration": "6 weeks",
                "effort": "4-6 hours/week",
                "prerequisites": "Programming Languages, Part C",
                "url": "https://www.coursera.org/learn/object-oriented-design",
                "topics": ["design patterns", "UML", "software architecture"]
            },
            {
                "name": "Design Patterns",
                "curriculum": curriculum,
                "category": "Core Programming",
                "description": "Common software design patterns",
                "duration": "4 weeks",
                "effort": "4-6 hours/week",
                "prerequisites": "Object-Oriented Design",
                "url": "https://www.coursera.org/learn/design-patterns",
                "topics": ["singleton", "factory", "observer", "strategy"]
            },
            {
                "name": "Software Architecture",
                "curriculum": curriculum,
                "category": "Core Programming",
                "description": "Large-scale software architecture",
                "duration": "4 weeks",
                "effort": "3-5 hours/week",
                "prerequisites": "Design Patterns",
                "url": "https://www.coursera.org/learn/software-architecture",
                "topics": ["architectural patterns", "microservices", "scalability"]
            },
            {
                "name": "Calculus 1A: Differentiation",
                "curriculum": curriculum,
                "category": "Core Math",
                "description": "Single variable calculus fundamentals",
                "duration": "13 weeks",
                "effort": "6-10 hours/week",
                "prerequisites": "high school math",
                "url": "https://openlearninglibrary.mit.edu/courses/course-v1:MITx+18.01.1x+2T2019/about",
                "topics": ["derivatives", "limits", "applications"]
            },
            {
                "name": "Calculus 1B: Integration",
                "curriculum": curriculum,
                "category": "Core Math",
                "description": "Integration and its applications",
                "duration": "13 weeks",
                "effort": "5-10 hours/week",
                "prerequisites": "Calculus 1A",
                "url": "https://openlearninglibrary.mit.edu/courses/course-v1:MITx+18.01.2x+3T2019/about",
                "topics": ["integration", "techniques", "applications"]
            },
            {
                "name": "Calculus 1C: Coordinate Systems & Infinite Series",
                "curriculum": curriculum,
                "category": "Core Math",
                "description": "Advanced calculus topics",
                "duration": "6 weeks",
                "effort": "5-10 hours/week",
                "prerequisites": "Calculus 1B",
                "url": "https://openlearninglibrary.mit.edu/courses/course-v1:MITx+18.01.3x+1T2020/about",
                "topics": ["series", "parametric equations", "polar coordinates"]
            },
            {
                "name": "Mathematics for Computer Science",
                "curriculum": curriculum,
                "category": "Core Math",
                "description": "Discrete mathematics for CS",
                "duration": "13 weeks",
                "effort": "5 hours/week",
                "prerequisites": "Calculus 1C",
                "url": "https://openlearninglibrary.mit.edu/courses/course-v1:OCW+6.042J+2T2019/about",
                "topics": ["discrete math", "proofs", "probability"]
            },
            {
                "name": "Build a Modern Computer from First Principles: From Nand to Tetris",
                "curriculum": curriculum,
                "category": "Core Systems",
                "description": "Computer architecture from logic gates up",
                "duration": "6 weeks",
                "effort": "7-13 hours/week",
                "prerequisites": "C-like programming language",
                "url": "https://www.coursera.org/learn/build-a-computer",
                "topics": ["computer architecture", "logic gates", "assembly"]
            },
            {
                "name": "Build a Modern Computer from First Principles: Nand to Tetris Part II",
                "curriculum": curriculum,
                "category": "Core Systems",
                "description": "Software hierarchy of a computer system",
                "duration": "6 weeks",
                "effort": "12-18 hours/week",
                "prerequisites": "From Nand to Tetris Part I",
                "url": "https://www.coursera.org/learn/nand2tetris2",
                "topics": ["compiler", "operating systems", "programming language"]
            },
            {
                "name": "Operating Systems: Three Easy Pieces",
                "curriculum": curriculum,
                "category": "Core Systems",
                "description": "Operating system fundamentals",
                "duration": "10-12 weeks",
                "effort": "6-10 hours/week",
                "prerequisites": "Algorithms and programming experience",
                "url": "http://pages.cs.wisc.edu/~remzi/OSTEP/",
                "topics": ["processes", "memory", "file systems", "concurrency"]
            },
            {
                "name": "Computer Networking: a Top-Down Approach",
                "curriculum": curriculum,
                "category": "Core Systems",
                "description": "Computer networking principles",
                "duration": "8 weeks",
                "effort": "4-12 hours/week",
                "prerequisites": "Basic programming",
                "url": "http://gaia.cs.umass.edu/kurose_ross/online_lectures.htm",
                "topics": ["protocols", "TCP/IP", "routing", "network security"]
            },
            {
                "name": "Algorithms Specialization",
                "curriculum": curriculum,
                "category": "Core Theory",
                "description": "Fundamental algorithms and data structures",
                "duration": "16 weeks",
                "effort": "4-8 hours/week",
                "prerequisites": "Mathematics for Computer Science",
                "url": "https://www.coursera.org/specializations/algorithms",
                "topics": ["algorithms", "data structures", "graph theory"]
            },
            {
                "name": "Divide and Conquer, Sorting and Searching, and Randomized Algorithms",
                "curriculum": curriculum,
                "category": "Core Theory",
                "description": "Basic algorithmic techniques",
                "duration": "4 weeks",
                "effort": "4-8 hours/week",
                "prerequisites": "Mathematics for Computer Science",
                "url": "https://www.coursera.org/learn/algorithms-divide-conquer",
                "topics": ["divide and conquer", "sorting", "randomized algorithms"]
            },
            {
                "name": "Graph Search, Shortest Paths, and Data Structures",
                "curriculum": curriculum,
                "category": "Core Theory",
                "description": "Graph algorithms and data structures",
                "duration": "4 weeks",
                "effort": "4-8 hours/week",
                "prerequisites": "Divide and Conquer algorithms course",
                "url": "https://www.coursera.org/learn/algorithms-graphs-data-structures",
                "topics": ["graph search", "shortest paths", "data structures"]
            },
            {
                "name": "Greedy Algorithms, Minimum Spanning Trees, and Dynamic Programming",
                "curriculum": curriculum,
                "category": "Core Theory",
                "description": "Advanced algorithmic paradigms",
                "duration": "4 weeks",
                "effort": "4-8 hours/week",
                "prerequisites": "Graph algorithms course",
                "url": "https://www.coursera.org/learn/algorithms-greedy",
                "topics": ["greedy algorithms", "MST", "dynamic programming"]
            },
            {
                "name": "Shortest Paths Revisited, NP-Complete Problems and What To Do About Them",
                "curriculum": curriculum,
                "category": "Core Theory",
                "description": "NP-completeness and approximation algorithms",
                "duration": "4 weeks",
                "effort": "4-8 hours/week",
                "prerequisites": "Dynamic programming course",
                "url": "https://www.coursera.org/learn/algorithms-npcomplete",
                "topics": ["NP-completeness", "approximation algorithms", "heuristics"]
            }
        ],
        CurriculumType.DATA_SCIENCE: [
            {
                "name": "Introduction to Data Science",
                "curriculum": curriculum,
                "category": "Introduction to Data Science",
                "description": "Overview of data science methodology",
                "duration": "6 weeks",
                "effort": "4-6 hours/week",
                "prerequisites": "none",
                "url": "https://www.coursera.org/learn/what-is-datascience",
                "topics": ["data science process", "methodology"]
            },
            {
                "name": "Data Science: R Basics",
                "curriculum": curriculum,
                "category": "Introduction to Data Science",
                "description": "R programming fundamentals for data science",
                "duration": "8 weeks",
                "effort": "2-3 hours/week",
                "prerequisites": "none",
                "url": "https://www.edx.org/course/data-science-r-basics",
                "topics": ["R programming", "data manipulation", "visualization"]
            },
            {
                "name": "Python for Data Science, AI & Development",
                "curriculum": curriculum,
                "category": "Introduction to Computer Science",
                "description": "Python programming for data science",
                "duration": "5 weeks",
                "effort": "3-5 hours/week",
                "prerequisites": "none",
                "url": "https://www.coursera.org/learn/python-for-applied-data-science-ai",
                "topics": ["python", "data manipulation", "pandas"]
            },
            {
                "name": "Python Data Structures",
                "curriculum": curriculum,
                "category": "Introduction to Computer Science",
                "description": "Data structures in Python",
                "duration": "7 weeks",
                "effort": "2-4 hours/week",
                "prerequisites": "Python basics",
                "url": "https://www.coursera.org/learn/python-data",
                "topics": ["lists", "dictionaries", "tuples", "sets"]
            },
            {
                "name": "Using Python to Access Web Data",
                "curriculum": curriculum,
                "category": "Introduction to Computer Science",
                "description": "Web scraping and APIs with Python",
                "duration": "6 weeks",
                "effort": "2-4 hours/week",
                "prerequisites": "Python Data Structures",
                "url": "https://www.coursera.org/learn/python-network-data",
                "topics": ["web scraping", "APIs", "XML", "JSON"]
            },
            {
                "name": "Using Databases with Python",
                "curriculum": curriculum,
                "category": "Databases",
                "description": "Database operations with Python",
                "duration": "5 weeks",
                "effort": "2-3 hours/week",
                "prerequisites": "Using Python to Access Web Data",
                "url": "https://www.coursera.org/learn/python-databases",
                "topics": ["SQL", "database design", "data modeling"]
            },
            {
                "name": "Introduction to Structured Query Language (SQL)",
                "curriculum": curriculum,
                "category": "Databases",
                "description": "SQL fundamentals",
                "duration": "4 weeks",
                "effort": "2-3 hours/week",
                "prerequisites": "basic programming",
                "url": "https://www.coursera.org/learn/intro-sql",
                "topics": ["SQL queries", "joins", "aggregation", "subqueries"]
            },
            {
                "name": "Data Structures and Algorithms",
                "curriculum": curriculum,
                "category": "Data Structures and Algorithms",
                "description": "Fundamental algorithms for data science",
                "duration": "6 weeks",
                "effort": "6-10 hours/week",
                "prerequisites": "Python programming",
                "url": "https://www.coursera.org/learn/algorithms-part1",
                "topics": ["algorithms", "complexity analysis"]
            },
            {
                "name": "Calculus for Machine Learning and Data Science",
                "curriculum": curriculum,
                "category": "Mathematics",
                "description": "Calculus concepts for ML and data science",
                "duration": "4 weeks",
                "effort": "4-6 hours/week",
                "prerequisites": "high school mathematics",
                "url": "https://www.coursera.org/learn/machine-learning-calculus",
                "topics": ["derivatives", "optimization", "gradients"]
            },
            {
                "name": "Linear Algebra for Machine Learning and Data Science",
                "curriculum": curriculum,
                "category": "Mathematics",
                "description": "Linear algebra fundamentals for ML",
                "duration": "4 weeks",
                "effort": "4-6 hours/week",
                "prerequisites": "basic mathematics",
                "url": "https://www.coursera.org/learn/machine-learning-linear-algebra",
                "topics": ["vectors", "matrices", "eigenvalues", "transformations"]
            },
            {
                "name": "Probability & Statistics for Machine Learning & Data Science",
                "curriculum": curriculum,
                "category": "Statistics & Probability",
                "description": "Probability and statistics for data science",
                "duration": "4 weeks",
                "effort": "4-6 hours/week",
                "prerequisites": "basic mathematics",
                "url": "https://www.coursera.org/learn/machine-learning-probability-and-statistics",
                "topics": ["probability", "distributions", "hypothesis testing"]
            },
            {
                "name": "Introduction to Statistics",
                "curriculum": curriculum,
                "category": "Statistics & Probability",
                "description": "Statistical concepts and methods",
                "duration": "8 weeks",
                "effort": "5-7 hours/week",
                "prerequisites": "basic mathematics",
                "url": "https://www.edx.org/course/introduction-to-statistics-descriptive-statistics",
                "topics": ["descriptive statistics", "inference", "regression"]
            },
            {
                "name": "Machine Learning",
                "curriculum": curriculum,
                "category": "Machine Learning/Data Mining",
                "description": "Introduction to machine learning",
                "duration": "11 weeks",
                "effort": "9 hours/week",
                "prerequisites": "Basic coding",
                "url": "https://www.coursera.org/specializations/machine-learning-introduction",
                "topics": ["supervised learning", "unsupervised learning"]
            },
            {
                "name": "Deep Learning",
                "curriculum": curriculum,
                "category": "Machine Learning/Data Mining",
                "description": "Neural networks and deep learning",
                "duration": "16 weeks",
                "effort": "3-4 hours/week",
                "prerequisites": "Machine Learning course",
                "url": "https://www.coursera.org/specializations/deep-learning",
                "topics": ["neural networks", "CNN", "RNN", "optimization"]
            }
        ],
        CurriculumType.MATHEMATICS: [
            {
                "name": "Introduction to Mathematical Thinking",
                "curriculum": curriculum,
                "category": "Introduction to Mathematical Thinking",
                "description": "Mathematical reasoning and proof techniques",
                "duration": "10 weeks",
                "effort": "8-10 hours/week",
                "prerequisites": "high school mathematics",
                "url": "https://www.coursera.org/learn/mathematical-thinking",
                "topics": ["mathematical reasoning", "proofs", "logic"]
            },
            {
                "name": "Single Variable Calculus",
                "curriculum": curriculum,
                "category": "Calculus",
                "description": "Comprehensive single variable calculus",
                "duration": "15 weeks",
                "effort": "10-12 hours/week",
                "prerequisites": "Introduction to Mathematical Thinking",
                "url": "https://ocw.mit.edu/courses/mathematics/18-01sc-single-variable-calculus-fall-2010/",
                "topics": ["derivatives", "integrals", "applications"]
            },
            {
                "name": "Multivariable Calculus",
                "curriculum": curriculum,
                "category": "Calculus",
                "description": "Calculus of several variables",
                "duration": "15 weeks",
                "effort": "12 hours/week",
                "prerequisites": "Single Variable Calculus",
                "url": "https://ocw.mit.edu/courses/mathematics/18-02sc-multivariable-calculus-fall-2010/",
                "topics": ["partial derivatives", "multiple integrals", "vector calculus"]
            },
            {
                "name": "Linear Algebra",
                "curriculum": curriculum,
                "category": "Linear Algebra",
                "description": "Matrix theory and linear transformations",
                "duration": "14 weeks",
                "effort": "12 hours/week",
                "prerequisites": "Single Variable Calculus",
                "url": "https://ocw.mit.edu/courses/mathematics/18-06sc-linear-algebra-fall-2011/",
                "topics": ["matrices", "vector spaces", "eigenvalues"]
            },
            {
                "name": "Introduction to Probability and Statistics",
                "curriculum": curriculum,
                "category": "Probability and Statistics",
                "description": "Probability theory and statistical inference",
                "duration": "16 weeks",
                "effort": "12 hours/week",
                "prerequisites": "Single Variable Calculus",
                "url": "https://projects.iq.harvard.edu/stat110/home",
                "topics": ["probability", "distributions", "inference"]
            },
            {
                "name": "Differential Equations",
                "curriculum": curriculum,
                "category": "Advanced Mathematics",
                "description": "Ordinary and partial differential equations",
                "duration": "14 weeks",
                "effort": "8-10 hours/week",
                "prerequisites": "Multivariable Calculus and Linear Algebra",
                "url": "https://ocw.mit.edu/courses/mathematics/18-03sc-differential-equations-fall-2011/",
                "topics": ["ODEs", "PDEs", "systems", "applications"]
            }
        ],
        CurriculumType.BIOINFORMATICS: [
            {
                "name": "Introduction to Biology",
                "curriculum": curriculum,
                "category": "Prerequisites",
                "description": "Fundamentals of molecular biology",
                "duration": "15 weeks",
                "effort": "7-14 hours/week",
                "prerequisites": "high school biology",
                "url": "https://www.edx.org/course/introduction-to-biology-the-secret-of-life-3",
                "topics": ["molecular biology", "genetics", "biochemistry"]
            },
            {
                "name": "Introduction to Chemistry",
                "curriculum": curriculum,
                "category": "Prerequisites", 
                "description": "Chemical structures and reactions",
                "duration": "15 weeks",
                "effort": "7-9 hours/week",
                "prerequisites": "high school chemistry",
                "url": "https://www.edx.org/course/general-chemistry-i-atoms-molecules-and-bonding",
                "topics": ["atoms", "bonding", "reactions", "thermodynamics"]
            },
            {
                "name": "Bioinformatics: Introduction and Methods",
                "curriculum": curriculum,
                "category": "Core Bioinformatics",
                "description": "Introduction to bioinformatics methods",
                "duration": "6 weeks",
                "effort": "4-6 hours/week",
                "prerequisites": "Introduction to Biology",
                "url": "https://www.coursera.org/learn/bioinformatics-introduction-and-methods",
                "topics": ["sequence analysis", "databases", "tools"]
            },
            {
                "name": "Genomic Data Science",
                "curriculum": curriculum,
                "category": "Core Bioinformatics",
                "description": "Analysis of genomic data",
                "duration": "32 weeks",
                "effort": "3-5 hours/week",
                "prerequisites": "Basic programming",
                "url": "https://www.coursera.org/specializations/genomic-data-science",
                "topics": ["genomics", "RNA-seq", "ChIP-seq", "statistical analysis"]
            }
        ],
        CurriculumType.PRECOLLEGE_MATH: [
            {
                "name": "Basic Arithmetic",
                "curriculum": curriculum,
                "category": "Arithmetic",
                "description": "Fundamental arithmetic operations",
                "duration": "8 weeks",
                "effort": "3-5 hours/week",
                "prerequisites": "none",
                "url": "https://www.khanacademy.org/math/arithmetic",
                "topics": ["addition", "subtraction", "multiplication", "division"]
            },
            {
                "name": "Pre-Algebra",
                "curriculum": curriculum,
                "category": "Pre-Algebra",
                "description": "Introduction to algebraic concepts",
                "duration": "12 weeks",
                "effort": "4-6 hours/week",
                "prerequisites": "Basic Arithmetic",
                "url": "https://www.khanacademy.org/math/pre-algebra",
                "topics": ["variables", "equations", "inequalities", "graphing"]
            },
            {
                "name": "Algebra I",
                "curriculum": curriculum,
                "category": "Algebra Basics",
                "description": "Linear equations and functions",
                "duration": "16 weeks",
                "effort": "5-7 hours/week",
                "prerequisites": "Pre-Algebra",
                "url": "https://www.khanacademy.org/math/algebra",
                "topics": ["linear equations", "functions", "systems", "polynomials"]
            },
            {
                "name": "Geometry",
                "curriculum": curriculum,
                "category": "Geometry",
                "description": "Euclidean geometry",
                "duration": "16 weeks",
                "effort": "5-7 hours/week",
                "prerequisites": "Algebra I",
                "url": "https://www.khanacademy.org/math/geometry",
                "topics": ["shapes", "proofs", "area", "volume", "similarity"]
            },
            {
                "name": "Algebra II",
                "curriculum": curriculum,
                "category": "Algebra II",
                "description": "Advanced algebraic concepts",
                "duration": "16 weeks",
                "effort": "6-8 hours/week",
                "prerequisites": "Algebra I and Geometry",
                "url": "https://www.khanacademy.org/math/algebra2",
                "topics": ["quadratics", "exponentials", "logarithms", "rational functions"]
            },
            {
                "name": "Trigonometry",
                "curriculum": curriculum,
                "category": "Trigonometry",
                "description": "Trigonometric functions and identities",
                "duration": "12 weeks",
                "effort": "6-8 hours/week",
                "prerequisites": "Algebra II",
                "url": "https://www.khanacademy.org/math/trigonometry",
                "topics": ["trig functions", "identities", "equations", "applications"]
            },
            {
                "name": "Precalculus",
                "curriculum": curriculum,
                "category": "Precalculus",
                "description": "Preparation for calculus",
                "duration": "16 weeks",
                "effort": "8-10 hours/week",
                "prerequisites": "Algebra II and Trigonometry",
                "url": "https://www.khanacademy.org/math/precalculus",
                "topics": ["functions", "conic sections", "sequences", "limits"]
            }
        ]
    }

    return fallback_courses.get(curriculum, [])

@api_router.post("/sync-courses")
async def sync_courses():
    """Enhanced sync ALL courses from OSSU GitHub repositories"""
    try:
        # Clear existing courses for fresh sync
        await db.courses.delete_many({})
        print("Cleared existing courses from database")

        all_courses = []
        sync_summary = {}

        # Sync each curriculum with detailed tracking
        for curriculum in CurriculumType:
            print(f"\n{'='*50}")
            print(f"Syncing {curriculum.value} courses...")
            curriculum_courses = await sync_curriculum_courses(curriculum)
            all_courses.extend(curriculum_courses)
            sync_summary[curriculum.value] = len(curriculum_courses)
            print(f"✓ Found {len(curriculum_courses)} courses for {curriculum.value}")

        print(f"\n{'='*50}")
        print(f"SYNC SUMMARY:")
        total_courses = 0
        for curriculum_name, count in sync_summary.items():
            print(f"  {curriculum_name}: {count} courses")
            total_courses += count
        print(f"  TOTAL: {total_courses} courses")

        # Insert all courses with batch processing
        if all_courses:
            courses_to_insert = []
            for course_data in all_courses:
                course = Course(**course_data)
                courses_to_insert.append(course.dict())

            # Insert in batches to handle large datasets
            batch_size = 100
            for i in range(0, len(courses_to_insert), batch_size):
                batch = courses_to_insert[i:i + batch_size]
                await db.courses.insert_many(batch)
                print(f"Inserted batch {i//batch_size + 1}: {len(batch)} courses")

        # Update curriculum stats
        for curriculum_type in CurriculumType:
            course_count = await db.courses.count_documents({"curriculum": curriculum_type})
            await db.curricula.update_one(
                {"type": curriculum_type},
                {"$set": {
                    "total_courses": course_count,
                    "last_synced": datetime.utcnow()
                }},
                upsert=True
            )

        # Final verification
        final_count = await db.courses.count_documents({})
        print(f"\n✅ Successfully synced {final_count} total courses from all OSSU curricula")
        
        return {
            "message": f"Successfully synced {final_count} courses from all OSSU curricula",
            "total_courses": final_count,
            "per_curriculum": sync_summary,
            "timestamp": datetime.utcnow()
        }

    except Exception as e:
        error_msg = f"Failed to sync courses: {str(e)}"
        print(f"❌ {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)

async def initialize_curricula():
    """Initialize curricula in database"""
    for curriculum_type, config in CURRICULA_CONFIG.items():
        existing = await db.curricula.find_one({"type": curriculum_type})
        if not existing:
            curriculum = Curriculum(
                type=curriculum_type,
                name=config["name"],
                description=config["description"],
                github_url=config["github_url"],
                categories=config["categories"]
            )
            await db.curricula.insert_one(curriculum.dict())

@api_router.get("/stats")
async def get_stats():
    """Get overall progress statistics"""
    total_courses = await db.courses.count_documents({})
    total_progress_entries = await db.progress.count_documents({})
    completed_courses = await db.progress.count_documents({"status": "completed"})
    in_progress_courses = await db.progress.count_documents({"status": "in_progress"})

    # Calculate average progress
    pipeline = [
        {"$group": {"_id": None, "avg_progress": {"$avg": "$percentage"}}}
    ]
    avg_result = await db.progress.aggregate(pipeline).to_list(1)
    avg_progress = avg_result[0]["avg_progress"] if avg_result else 0

    # Get per-curriculum stats
    curriculum_stats = {}
    for curriculum in CurriculumType:
        count = await db.courses.count_documents({"curriculum": curriculum})
        curriculum_stats[curriculum.value] = count

    return {
        "total_courses": total_courses,
        "courses_with_progress": total_progress_entries,
        "completed_courses": completed_courses,
        "in_progress_courses": in_progress_courses,
        "average_progress": round(avg_progress, 2) if avg_progress else 0,
        "courses_per_curriculum": curriculum_stats
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()