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
from difflib import SequenceMatcher

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

# Enhanced regex patterns for better parsing
EFFORT_REGEX = r'(\d+)(?:-(\d+))?\s*(?:hours?|hrs?|h)\s*/?\s*(?:week|wk)?'
DURATION_REGEX = r'(\d+)\s*(?:weeks?|wks?|months?|mos?)'

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
        # Try to parse estimated hours from course effort string using enhanced regex
        effort_match = re.search(EFFORT_REGEX, course_effort, re.IGNORECASE)
        if effort_match:
            duration_match = re.search(DURATION_REGEX, course.get("duration", ""), re.IGNORECASE)
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
            effort_match = re.search(EFFORT_REGEX, course_effort, re.IGNORECASE)
            if effort_match:
                duration_match = re.search(DURATION_REGEX, course.get("duration", ""), re.IGNORECASE)
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

def preprocess_content(content: str) -> str:
    """Preprocess README content to normalize formatting"""
    # Convert HTML anchors to markdown links
    content = re.sub(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>', r'[\2](\1)', content)
    
    # Normalize newlines
    content = re.sub(r'\r\n?', '\n', content)
    
    # Remove excessive blank lines
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    return content

def merge_multiline_items(lines: List[str]) -> List[str]:
    """Merge multi-line list items that span across lines"""
    merged = []
    buffer = ""
    
    for line in lines:
        # Check if this line starts a new list item
        if re.match(r'^\s*[\-\*\+\d+\.]\s+', line) or line.startswith('#'):
            if buffer:
                merged.append(buffer.strip())
            buffer = line
        elif buffer and line.strip():
            # Continue previous item if it's not empty and we have a buffer
            buffer += " " + line.strip()
        else:
            # Empty line or standalone line
            if buffer:
                merged.append(buffer.strip())
                buffer = ""
            if line.strip():
                merged.append(line)
    
    # Don't forget the last buffer
    if buffer:
        merged.append(buffer.strip())
        
    return merged

def is_fuzzy_duplicate(name: str, seen_names: List[str]) -> bool:
    """Check if course name is a fuzzy duplicate of existing names"""
    name_lower = name.lower().strip()
    
    for seen in seen_names:
        # High similarity threshold for fuzzy matching
        if SequenceMatcher(None, name_lower, seen.lower()).ratio() > 0.85:
            return True
        
        # Also check if one name contains the other (for "Intro to X" vs "Introduction to X")
        if len(name_lower) > 10 and len(seen.lower()) > 10:
            if name_lower in seen.lower() or seen.lower() in name_lower:
                return True
                
    return False

def extract_course_from_text(text: str, curriculum: CurriculumType, category: str) -> Optional[Dict]:
    """Extract course information from various text formats with enhanced parsing"""
    try:
        text = text.strip()
        if not text or len(text) < 10:
            return None

        # Skip common non-course lines
        skip_patterns = [
            r'^#+\s*',  # Headers
            r'^[\|\-\:]+$',  # Table separators  
            r'^\s*$',  # Empty lines
            r'^course\s*$',  # Just "course"
            r'^name\s*$',  # Just "name"
            r'^duration\s*$',  # Just "duration"
            r'^effort\s*$',  # Just "effort"
            r'^prerequisite',  # "prerequisite" headers
        ]
        
        if any(re.match(pattern, text.lower()) for pattern in skip_patterns):
            return None

        # Extract course name from various formats
        course_name = None
        course_url = None
        
        # Try markdown link formats (enhanced)
        link_patterns = [
            r'\[([^\]]+)\]\(([^)]+)\)',  # [Course Name](URL)
            r'\*\*\[([^\]]+)\]\(([^)]+)\)\*\*',  # **[Course Name](URL)**
            r'\*\[([^\]]+)\]\(([^)]+)\)\*',  # *[Course Name](URL)*
            r'`\[([^\]]+)\]\(([^)]+)\)`',  # `[Course Name](URL)`
        ]
        
        for pattern in link_patterns:
            match = re.search(pattern, text)
            if match:
                course_name = match.group(1).strip()
                course_url = match.group(2).strip()
                break
        
        # If no link found, try to extract course name from formatted text
        if not course_name:
            # Remove common prefixes and clean up
            text_clean = re.sub(r'^[\*\-\+\d\.\s\>]+', '', text)  # Remove bullets, numbers, blockquotes
            text_clean = re.sub(r'\*\*([^*]+)\*\*', r'\1', text_clean)  # Remove bold
            text_clean = re.sub(r'\*([^*]+)\*', r'\1', text_clean)  # Remove italic
            text_clean = re.sub(r'`([^`]+)`', r'\1', text_clean)  # Remove code formatting
            text_clean = re.sub(r'^\s*-\s*', '', text_clean)  # Remove leading dashes
            
            # Extract potential course name
            potential_name = text_clean.strip()
            if len(potential_name) > 5 and not potential_name.lower() in ['course', 'courses', 'name', 'duration', 'effort']:
                course_name = potential_name

        if not course_name or len(course_name) < 5:
            return None

        # Extract duration, effort, prerequisites with enhanced regex
        duration = ""
        effort = ""
        prerequisites = "none"
        
        # If it looks like a table row, try to extract structured data
        if '|' in text:
            parts = [part.strip() for part in text.split('|')]
            parts = [p for p in parts if p]  # Remove empty parts
            
            if len(parts) >= 2:
                if len(parts) > 1:
                    duration = parts[1] if len(parts) > 1 else ""
                if len(parts) > 2:
                    effort = parts[2] if len(parts) > 2 else ""
                if len(parts) > 3:
                    prerequisites = parts[3] if len(parts) > 3 else "none"
        else:
            # Try to extract from free text using enhanced regex
            duration_match = re.search(DURATION_REGEX, text, re.IGNORECASE)
            if duration_match:
                duration = duration_match.group(0)
                
            effort_match = re.search(EFFORT_REGEX, text, re.IGNORECASE)
            if effort_match:
                effort = effort_match.group(0)
        
        return {
            "name": course_name,
            "curriculum": curriculum,
            "category": category,
            "description": f"Part of {curriculum.value.replace('-', ' ').title()} curriculum - {category}",
            "duration": duration,
            "effort": effort,
            "prerequisites": prerequisites if prerequisites and prerequisites.lower() not in ['', '-', 'none', 'n/a'] else "none",
            "url": course_url,
            "topics": []
        }
    
    except Exception as e:
        logging.warning(f"Parse error at line: {text[:100]} - {e}")
        return None

async def sync_curriculum_courses(curriculum: CurriculumType) -> List[Dict]:
    """Bulletproof parsing to extract ALL courses from GitHub README"""
    courses = []
    
    try:
        # GitHub URLs with multiple branch fallbacks
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
            return []

        # Try multiple URLs
        content = None
        for url in github_urls[curriculum]:
            try:
                content = await fetch_github_content(url)
                print(f"✓ Successfully fetched content from {url}")
                break
            except Exception as e:
                print(f"✗ Failed to fetch from {url}: {str(e)}")
                continue

        if not content:
            print(f"❌ Could not fetch any content for {curriculum}")
            return []

        # 1️⃣ Preprocess content
        print("🔧 Preprocessing content...")
        content = preprocess_content(content)
        lines = content.split('\n')
        
        # 2️⃣ Merge multi-line items
        print("🔗 Merging multi-line items...")
        lines = merge_multiline_items(lines)

        current_category = "General"
        courses_found = 0
        seen_names = []  # For fuzzy duplicate detection
        
        print(f"📄 Processing {len(lines)} lines for {curriculum}")
        print(f"🔍 Starting enhanced course extraction...")

        for i, line in enumerate(lines):
            line = line.strip()
            
            # Detect section headers (categories) - enhanced detection
            if line.startswith('#') and len(line) > 2:
                header_text = re.sub(r'^#+\s*', '', line).strip()
                if len(header_text) > 2 and header_text.lower() not in ['ossu', 'faq', 'about', 'table of contents']:
                    current_category = header_text
                    print(f"📂 Found category: {current_category}")
            
            # 4️⃣ Bold text headers
            elif re.match(r'^\*\*(.+)\*\*$', line):
                current_category = re.sub(r'^\*\*|\*\*$', '', line).strip()
                print(f"📂 Found bold category: {current_category}")
            
            # Look for course indicators in multiple ways with try/catch:
            
            # Method 1: Table-based extraction
            elif '|' in line and line.count('|') >= 2:
                course_data = extract_course_from_text(line, curriculum, current_category)
                if course_data and not is_fuzzy_duplicate(course_data['name'], seen_names):
                    courses.append(course_data)
                    seen_names.append(course_data['name'])
                    courses_found += 1
                    print(f"✓ [TABLE] Course {courses_found}: {course_data['name']}")
            
            # Method 2: Markdown link extraction
            elif re.search(r'\[([^\]]+)\]\(([^)]+)\)', line):
                course_data = extract_course_from_text(line, curriculum, current_category)
                if course_data and not is_fuzzy_duplicate(course_data['name'], seen_names):
                    courses.append(course_data)
                    seen_names.append(course_data['name'])
                    courses_found += 1
                    print(f"✓ [LINK] Course {courses_found}: {course_data['name']}")
                elif '[' in line and ']' in line and '(' in line:
                    # 7️⃣ Log skipped potential courses for debugging
                    logging.debug(f"Skipped potential course line: {line[:100]}")
            
            # Method 3: List item extraction
            elif re.match(r'^\s*[\-\*\+]\s+', line):
                course_data = extract_course_from_text(line, curriculum, current_category)
                if course_data and not is_fuzzy_duplicate(course_data['name'], seen_names):
                    courses.append(course_data)
                    seen_names.append(course_data['name'])
                    courses_found += 1
                    print(f"✓ [LIST] Course {courses_found}: {course_data['name']}")
            
            # Method 4: Numbered list extraction
            elif re.match(r'^\s*\d+\.\s+', line):
                course_data = extract_course_from_text(line, curriculum, current_category)
                if course_data and not is_fuzzy_duplicate(course_data['name'], seen_names):
                    courses.append(course_data)
                    seen_names.append(course_data['name'])
                    courses_found += 1
                    print(f"✓ [NUMBERED] Course {courses_found}: {course_data['name']}")
            
            # 3️⃣ Method 5: Blockquoted courses
            elif line.startswith('>'):
                course_data = extract_course_from_text(line[1:].strip(), curriculum, current_category)
                if course_data and not is_fuzzy_duplicate(course_data['name'], seen_names):
                    courses.append(course_data)
                    seen_names.append(course_data['name'])
                    courses_found += 1
                    print(f"✓ [QUOTE] Course {courses_found}: {course_data['name']}")

        print(f"🎯 Successfully extracted {courses_found} courses from {curriculum}")
        print(f"✅ Final count after fuzzy deduplication: {len(courses)} courses for {curriculum}")
        
        return courses

    except Exception as e:
        print(f"❌ Error syncing {curriculum}: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

@api_router.post("/sync-courses")
async def sync_courses():
    """Sync ALL courses from OSSU GitHub repositories using bulletproof parsing"""
    try:
        print("🚀 Starting bulletproof course synchronization from OSSU GitHub repositories...")
        
        # Clear existing courses for fresh sync
        await db.courses.delete_many({})
        print("🗑️  Cleared existing courses from database")

        all_courses = []
        sync_summary = {}

        # Sync each curriculum with detailed tracking
        for curriculum in CurriculumType:
            print(f"\n{'='*60}")
            print(f"🔄 Syncing {curriculum.value} courses...")
            curriculum_courses = await sync_curriculum_courses(curriculum)
            all_courses.extend(curriculum_courses)
            sync_summary[curriculum.value] = len(curriculum_courses)
            print(f"📊 {curriculum.value}: {len(curriculum_courses)} courses extracted")

        print(f"\n{'='*60}")
        print(f"📈 BULLETPROOF SYNC SUMMARY:")
        total_courses = 0
        for curriculum_name, count in sync_summary.items():
            print(f"   📚 {curriculum_name}: {count} courses")
            total_courses += count
        print(f"   🎯 TOTAL: {total_courses} courses extracted from GitHub")

        # Insert all courses with validation
        if all_courses:
            courses_to_insert = []
            for course_data in all_courses:
                try:
                    course = Course(**course_data)
                    courses_to_insert.append(course.dict())
                except Exception as e:
                    print(f"⚠️  Skipped invalid course: {course_data.get('name', 'Unknown')} - {str(e)}")

            # Insert in batches
            batch_size = 100
            for i in range(0, len(courses_to_insert), batch_size):
                batch = courses_to_insert[i:i + batch_size]
                await db.courses.insert_many(batch)
                print(f"💾 Inserted batch {i//batch_size + 1}: {len(batch)} courses")

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
        print(f"\n🎉 BULLETPROOF SYNC COMPLETED!")
        print(f"✅ {final_count} total courses successfully synced from OSSU GitHub repositories")
        
        if final_count < 30:
            print(f"⚠️  Warning: Only {final_count} courses found. This seems low - check logs for parsing issues.")
        else:
            print(f"🎯 Excellent! Found {final_count} courses - bulletproof parsing is working!")
        
        return {
            "message": f"Successfully synced {final_count} courses using bulletproof parsing from OSSU GitHub repositories",
            "total_courses": final_count,
            "per_curriculum": sync_summary,
            "timestamp": datetime.utcnow(),
            "source": "GitHub repositories (bulletproof parsing)",
            "enhancements": [
                "Content preprocessing", "Multi-line merging", "Blockquote detection",
                "Bold header detection", "Enhanced regex patterns", "Fuzzy duplicate detection",
                "Debug logging", "Error resilience"
            ]
        }

    except Exception as e:
        error_msg = f"Failed to sync courses: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
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