from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import requests
import json
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
from enum import Enum


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="OSSU Course Tracker", version="2.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Enums
class CourseStatus(str, Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"

class Curriculum(str, Enum):
    computer_science = "computer_science"
    data_science = "data_science"
    mathematics = "mathematics"
    bioinformatics = "bioinformatics"
    precollege_math = "precollege_math"

# Models
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

class Course(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str = ""
    curriculum: Curriculum
    category: str
    url: str = ""
    duration: str = ""
    prerequisites: List[str] = []  # List of course IDs
    status: CourseStatus = CourseStatus.not_started
    progress: float = 0.0  # 0-100%
    time_estimated: int = 0  # hours
    time_actual: int = 0  # hours
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_unlocked: bool = True  # Will be calculated based on prerequisites

class CourseCreate(BaseModel):
    title: str
    description: str = ""
    curriculum: Curriculum
    category: str
    url: str = ""
    duration: str = ""
    prerequisites: List[str] = []

class CourseUpdate(BaseModel):
    status: Optional[CourseStatus] = None
    progress: Optional[float] = None
    time_actual: Optional[int] = None
    notes: Optional[str] = None

class ProgressStats(BaseModel):
    total_courses: int
    completed_courses: int
    in_progress_courses: int
    completion_percentage: float
    total_time_estimated: int
    total_time_actual: int

# OSSU Course Data
OSSU_CS_COURSES = [
    {
        "title": "Introduction to Computer Science - CS50",
        "description": "Harvard's introduction to computer science and programming",
        "curriculum": "computer_science",
        "category": "Introduction",
        "url": "https://cs50.harvard.edu/x/",
        "duration": "12 weeks",
        "prerequisites": []
    },
    {
        "title": "Programming Methodology",
        "description": "Programming methodology and good software engineering practices",
        "curriculum": "computer_science", 
        "category": "Core Programming",
        "url": "https://see.stanford.edu/Course/CS106A",
        "duration": "10 weeks",
        "prerequisites": ["Introduction to Computer Science - CS50"]
    },
    {
        "title": "Programming Abstractions",
        "description": "Advanced programming concepts and data structures",
        "curriculum": "computer_science",
        "category": "Core Programming", 
        "url": "https://see.stanford.edu/Course/CS106B",
        "duration": "10 weeks",
        "prerequisites": ["Programming Methodology"]
    },
    {
        "title": "Programming Paradigms",
        "description": "Different programming paradigms and languages",
        "curriculum": "computer_science",
        "category": "Core Programming",
        "url": "https://see.stanford.edu/Course/CS107",
        "duration": "10 weeks", 
        "prerequisites": ["Programming Abstractions"]
    },
    {
        "title": "Calculus 1A: Differentiation",
        "description": "Differential calculus fundamentals",
        "curriculum": "computer_science",
        "category": "Core Math",
        "url": "https://www.edx.org/course/calculus-1a-differentiation",
        "duration": "13 weeks",
        "prerequisites": []
    },
    {
        "title": "Calculus 1B: Integration", 
        "description": "Integral calculus fundamentals",
        "curriculum": "computer_science",
        "category": "Core Math",
        "url": "https://www.edx.org/course/calculus-1b-integration",
        "duration": "13 weeks",
        "prerequisites": ["Calculus 1A: Differentiation"]
    },
    {
        "title": "Calculus 1C: Coordinate Systems",
        "description": "Coordinate systems and infinite series",
        "curriculum": "computer_science", 
        "category": "Core Math",
        "url": "https://www.edx.org/course/calculus-1c-coordinate-systems-infinite-series",
        "duration": "13 weeks",
        "prerequisites": ["Calculus 1B: Integration"]
    },
    {
        "title": "Mathematics for Computer Science",
        "description": "Discrete mathematics for computer science",
        "curriculum": "computer_science",
        "category": "Core Math", 
        "url": "https://ocw.mit.edu/courses/6-042j-mathematics-for-computer-science-fall-2010/",
        "duration": "16 weeks",
        "prerequisites": ["Calculus 1A: Differentiation"]
    },
    {
        "title": "Algorithms: Design and Analysis Part 1",
        "description": "Fundamental algorithms and analysis techniques",
        "curriculum": "computer_science",
        "category": "Core Systems",
        "url": "https://www.coursera.org/learn/algorithms-divide-conquer", 
        "duration": "6 weeks",
        "prerequisites": ["Programming Paradigms", "Mathematics for Computer Science"]
    },
    {
        "title": "Algorithms: Design and Analysis Part 2", 
        "description": "Advanced algorithms and graph algorithms",
        "curriculum": "computer_science",
        "category": "Core Systems",
        "url": "https://www.coursera.org/learn/algorithms-graphs-data-structures",
        "duration": "6 weeks",
        "prerequisites": ["Algorithms: Design and Analysis Part 1"]
    },
    {
        "title": "Computer Architecture",
        "description": "How computers work from hardware to software",
        "curriculum": "computer_science",
        "category": "Core Systems",
        "url": "https://www.coursera.org/learn/comparch",
        "duration": "6 weeks", 
        "prerequisites": ["Programming Paradigms"]
    },
    {
        "title": "Operating Systems",
        "description": "Operating system principles and design",
        "curriculum": "computer_science",
        "category": "Core Systems",
        "url": "https://pages.cs.wisc.edu/~remzi/OSTEP/",
        "duration": "16 weeks",
        "prerequisites": ["Computer Architecture"]
    },
    {
        "title": "Computer Networks",
        "description": "Network protocols and distributed systems",
        "curriculum": "computer_science", 
        "category": "Core Systems",
        "url": "https://gaia.cs.umass.edu/kurose_ross/online_lectures.htm",
        "duration": "8 weeks",
        "prerequisites": ["Operating Systems"]
    },
    {
        "title": "Databases",
        "description": "Database systems and SQL",
        "curriculum": "computer_science",
        "category": "Core Applications",
        "url": "https://www.edx.org/course/databases-5-sql",
        "duration": "12 weeks",
        "prerequisites": ["Programming Paradigms"]
    },
    {
        "title": "Software Engineering",
        "description": "Software engineering principles and practices", 
        "curriculum": "computer_science",
        "category": "Core Applications",
        "url": "https://www.edx.org/course/software-engineering-introduction",
        "duration": "6 weeks",
        "prerequisites": ["Databases"]
    },
    {
        "title": "Programming Languages",
        "description": "Programming language theory and implementation",
        "curriculum": "computer_science",
        "category": "Core Theory", 
        "url": "https://www.coursera.org/learn/programming-languages",
        "duration": "5 weeks",
        "prerequisites": ["Programming Paradigms", "Mathematics for Computer Science"]
    },
    {
        "title": "Computer Graphics",
        "description": "3D computer graphics and rendering",
        "curriculum": "computer_science",
        "category": "Advanced Applications",
        "url": "https://www.edx.org/course/computer-graphics-2",
        "duration": "6 weeks",
        "prerequisites": ["Algorithms: Design and Analysis Part 1", "Calculus 1C: Coordinate Systems"]
    },
    {
        "title": "Artificial Intelligence",
        "description": "AI fundamentals and search algorithms", 
        "curriculum": "computer_science",
        "category": "Advanced Applications",
        "url": "https://www.edx.org/course/artificial-intelligence-ai",
        "duration": "12 weeks",
        "prerequisites": ["Algorithms: Design and Analysis Part 2", "Mathematics for Computer Science"]
    },
    {
        "title": "Machine Learning",
        "description": "Statistical learning and machine learning algorithms",
        "curriculum": "computer_science",
        "category": "Advanced Applications", 
        "url": "https://www.coursera.org/learn/machine-learning",
        "duration": "11 weeks",
        "prerequisites": ["Artificial Intelligence", "Calculus 1C: Coordinate Systems"]
    },
    {
        "title": "Parallel Computing",
        "description": "Parallel and concurrent programming",
        "curriculum": "computer_science", 
        "category": "Advanced Systems",
        "url": "https://www.coursera.org/learn/parprog1",
        "duration": "4 weeks",
        "prerequisites": ["Operating Systems", "Programming Languages"]
    }
]

OSSU_DS_COURSES = [
    {
        "title": "Introduction to Data Science",
        "description": "Overview of data science field and methodologies",
        "curriculum": "data_science",
        "category": "Introduction",
        "url": "https://www.edx.org/course/introduction-to-data-science",
        "duration": "6 weeks",
        "prerequisites": []
    },
    {
        "title": "Python for Data Science",
        "description": "Python programming for data analysis",
        "curriculum": "data_science",
        "category": "Programming",
        "url": "https://www.coursera.org/learn/python-data-analysis",
        "duration": "4 weeks", 
        "prerequisites": ["Introduction to Data Science"]
    },
    {
        "title": "R Programming",
        "description": "R language for statistical computing",
        "curriculum": "data_science",
        "category": "Programming",
        "url": "https://www.coursera.org/learn/r-programming",
        "duration": "4 weeks",
        "prerequisites": ["Introduction to Data Science"]
    },
    {
        "title": "Data Structures and Algorithms",
        "description": "Essential data structures for data science",
        "curriculum": "data_science",
        "category": "Programming", 
        "url": "https://www.coursera.org/specializations/data-structures-algorithms",
        "duration": "8 weeks",
        "prerequisites": ["Python for Data Science"]
    },
    {
        "title": "Probability and Statistics",
        "description": "Statistical foundations for data science",
        "curriculum": "data_science",
        "category": "Statistics",
        "url": "https://www.khanacademy.org/math/statistics-probability",
        "duration": "12 weeks", 
        "prerequisites": []
    },
    {
        "title": "Statistical Inference",
        "description": "Inferential statistics and hypothesis testing", 
        "curriculum": "data_science",
        "category": "Statistics",
        "url": "https://www.coursera.org/learn/statistical-inference",
        "duration": "4 weeks",
        "prerequisites": ["Probability and Statistics"]
    },
    {
        "title": "Linear Algebra",
        "description": "Linear algebra for data science applications",
        "curriculum": "data_science",
        "category": "Mathematics",
        "url": "https://www.khanacademy.org/math/linear-algebra", 
        "duration": "10 weeks",
        "prerequisites": []
    },
    {
        "title": "Calculus for Data Science",
        "description": "Essential calculus concepts for ML/AI",
        "curriculum": "data_science",
        "category": "Mathematics",
        "url": "https://www.coursera.org/learn/calculus-data-science",
        "duration": "8 weeks",
        "prerequisites": ["Linear Algebra"]
    },
    {
        "title": "Data Cleaning and Preprocessing",
        "description": "Data cleaning and preparation techniques",
        "curriculum": "data_science",
        "category": "Data Engineering",
        "url": "https://www.coursera.org/learn/data-cleaning",
        "duration": "4 weeks",
        "prerequisites": ["Python for Data Science", "R Programming"]
    },
    {
        "title": "Exploratory Data Analysis",
        "description": "Data exploration and visualization techniques",
        "curriculum": "data_science",
        "category": "Data Analysis",
        "url": "https://www.coursera.org/learn/exploratory-data-analysis", 
        "duration": "4 weeks",
        "prerequisites": ["Data Cleaning and Preprocessing"]
    },
    {
        "title": "Data Visualization",
        "description": "Creating effective data visualizations",
        "curriculum": "data_science",
        "category": "Data Analysis",
        "url": "https://www.coursera.org/learn/datavisualization",
        "duration": "4 weeks",
        "prerequisites": ["Exploratory Data Analysis"]
    },
    {
        "title": "Machine Learning Fundamentals", 
        "description": "Introduction to machine learning algorithms",
        "curriculum": "data_science",
        "category": "Machine Learning",
        "url": "https://www.coursera.org/learn/machine-learning-course",
        "duration": "11 weeks",
        "prerequisites": ["Statistical Inference", "Linear Algebra", "Calculus for Data Science"]
    },
    {
        "title": "Deep Learning",
        "description": "Neural networks and deep learning",
        "curriculum": "data_science",
        "category": "Machine Learning",
        "url": "https://www.coursera.org/specializations/deep-learning",
        "duration": "16 weeks", 
        "prerequisites": ["Machine Learning Fundamentals"]
    },
    {
        "title": "Natural Language Processing",
        "description": "Text processing and NLP techniques",
        "curriculum": "data_science", 
        "category": "Applied ML",
        "url": "https://www.coursera.org/learn/nlp-sequence-models",
        "duration": "4 weeks",
        "prerequisites": ["Deep Learning"]
    },
    {
        "title": "Computer Vision",
        "description": "Image processing and computer vision",
        "curriculum": "data_science",
        "category": "Applied ML",
        "url": "https://www.coursera.org/learn/convolutional-neural-networks",
        "duration": "4 weeks", 
        "prerequisites": ["Deep Learning"]
    },
    {
        "title": "Big Data Analytics",
        "description": "Processing and analyzing large datasets",
        "curriculum": "data_science",
        "category": "Big Data",
        "url": "https://www.coursera.org/learn/big-data-analytics",
        "duration": "6 weeks",
        "prerequisites": ["Data Structures and Algorithms", "Machine Learning Fundamentals"]
    },
    {
        "title": "Data Engineering",
        "description": "Building data pipelines and infrastructure", 
        "curriculum": "data_science",
        "category": "Big Data",
        "url": "https://www.coursera.org/learn/data-engineering-gcp",
        "duration": "4 weeks",
        "prerequisites": ["Big Data Analytics"]
    },
    {
        "title": "Ethics in Data Science",
        "description": "Ethical considerations in data science",
        "curriculum": "data_science",
        "category": "Ethics",
        "url": "https://www.edx.org/course/data-science-ethics",
        "duration": "2 weeks",
        "prerequisites": ["Machine Learning Fundamentals"]
    }
]

# Helper functions
async def calculate_course_unlock_status(course: dict, all_courses: List[dict]) -> bool:
    """Calculate if a course should be unlocked based on prerequisites"""
    if not course.get("prerequisites"):
        return True
    
    # Get prerequisite courses from database
    prerequisite_titles = course["prerequisites"]
    for prereq_title in prerequisite_titles:
        prereq_course = await db.courses.find_one({"title": prereq_title})
        if not prereq_course:
            return False
        
        # Check if prerequisite has 80% or more completion
        if prereq_course.get("progress", 0) < 80.0:
            return False
    
    return True

async def update_all_unlock_statuses():
    """Update unlock status for all courses"""
    courses = await db.courses.find().to_list(None)
    
    for course in courses:
        is_unlocked = await calculate_course_unlock_status(course, courses)
        await db.courses.update_one(
            {"id": course["id"]},
            {"$set": {"is_unlocked": is_unlocked, "updated_at": datetime.utcnow()}}
        )

# API Routes
@api_router.get("/")
async def root():
    return {"message": "OSSU Course Tracker API v2.0", "status": "active"}

# Legacy status check routes (preserve existing data)
@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

# Course management routes
@api_router.post("/courses/sync")
async def sync_courses():
    """Sync all OSSU courses to database"""
    try:
        all_courses = OSSU_CS_COURSES + OSSU_DS_COURSES
        synced_count = 0
        
        for course_data in all_courses:
            # Check if course already exists
            existing = await db.courses.find_one({"title": course_data["title"]})
            
            if not existing:
                course = Course(**course_data)
                await db.courses.insert_one(course.dict())
                synced_count += 1
            else:
                # Update existing course with new data (preserve progress)
                update_data = {k: v for k, v in course_data.items() 
                             if k not in ["status", "progress", "time_actual", "notes"]}
                update_data["updated_at"] = datetime.utcnow()
                await db.courses.update_one(
                    {"title": course_data["title"]},
                    {"$set": update_data}
                )
        
        # Update unlock statuses for all courses
        await update_all_unlock_statuses()
        
        total_courses = await db.courses.count_documents({})
        return {
            "message": f"Successfully synced courses",
            "synced_new": synced_count,
            "total_courses": total_courses
        }
    
    except Exception as e:
        logging.error(f"Error syncing courses: {e}")
        raise HTTPException(status_code=500, detail="Failed to sync courses")

@api_router.get("/courses", response_model=List[Course])
async def get_courses(
    curriculum: Optional[Curriculum] = None,
    category: Optional[str] = None,
    status: Optional[CourseStatus] = None,
    search: Optional[str] = None
):
    """Get courses with optional filtering"""
    query = {}
    
    if curriculum:
        query["curriculum"] = curriculum
    if category:
        query["category"] = category  
    if status:
        query["status"] = status
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]
    
    courses = await db.courses.find(query).to_list(1000)
    
    # Calculate unlock status for each course
    for course in courses:
        course["is_unlocked"] = await calculate_course_unlock_status(course, courses)
    
    return [Course(**course) for course in courses]

@api_router.get("/courses/{course_id}", response_model=Course)
async def get_course(course_id: str):
    """Get a specific course by ID"""
    course = await db.courses.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Calculate unlock status
    all_courses = await db.courses.find().to_list(None)
    course["is_unlocked"] = await calculate_course_unlock_status(course, all_courses)
    
    return Course(**course)

@api_router.put("/courses/{course_id}", response_model=Course)
async def update_course(course_id: str, update_data: CourseUpdate):
    """Update course progress and status"""
    course = await db.courses.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Check if course is unlocked before allowing updates
    all_courses = await db.courses.find().to_list(None)
    is_unlocked = await calculate_course_unlock_status(course, all_courses)
    
    if not is_unlocked:
        raise HTTPException(status_code=403, detail="Course is locked. Complete prerequisites first.")
    
    update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
    
    # Auto-update status based on progress
    if update_data.progress is not None:
        if update_data.progress == 0:
            update_dict["status"] = CourseStatus.not_started
        elif update_data.progress == 100:
            update_dict["status"] = CourseStatus.completed
        else:
            update_dict["status"] = CourseStatus.in_progress
    
    update_dict["updated_at"] = datetime.utcnow()
    
    await db.courses.update_one({"id": course_id}, {"$set": update_dict})
    
    # Update unlock statuses for all courses (in case this completion unlocked others)
    await update_all_unlock_statuses()
    
    updated_course = await db.courses.find_one({"id": course_id})
    updated_course["is_unlocked"] = await calculate_course_unlock_status(updated_course, all_courses)
    
    return Course(**updated_course)

@api_router.get("/stats", response_model=ProgressStats)
async def get_progress_stats():
    """Get overall progress statistics"""
    total_courses = await db.courses.count_documents({})
    completed_courses = await db.courses.count_documents({"status": "completed"})
    in_progress_courses = await db.courses.count_documents({"status": "in_progress"})
    
    completion_percentage = (completed_courses / total_courses * 100) if total_courses > 0 else 0
    
    # Calculate time estimates
    pipeline = [
        {"$group": {
            "_id": None,
            "total_estimated": {"$sum": "$time_estimated"},
            "total_actual": {"$sum": "$time_actual"}
        }}
    ]
    
    time_stats = await db.courses.aggregate(pipeline).to_list(1)
    time_estimated = time_stats[0]["total_estimated"] if time_stats else 0
    time_actual = time_stats[0]["total_actual"] if time_stats else 0
    
    return ProgressStats(
        total_courses=total_courses,
        completed_courses=completed_courses, 
        in_progress_courses=in_progress_courses,
        completion_percentage=completion_percentage,
        total_time_estimated=time_estimated,
        total_time_actual=time_actual
    )

@api_router.get("/curricula")
async def get_curricula():
    """Get available curricula with course counts"""
    pipeline = [
        {"$group": {
            "_id": "$curriculum",
            "total_courses": {"$sum": 1},
            "completed_courses": {
                "$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}
            },
            "categories": {"$addToSet": "$category"}
        }}
    ]
    
    results = await db.courses.aggregate(pipeline).to_list(10)
    
    curricula = []
    for result in results:
        completion_rate = (result["completed_courses"] / result["total_courses"] * 100) if result["total_courses"] > 0 else 0
        curricula.append({
            "curriculum": result["_id"],
            "total_courses": result["total_courses"], 
            "completed_courses": result["completed_courses"],
            "completion_rate": completion_rate,
            "categories": result["categories"]
        })
    
    return curricula

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