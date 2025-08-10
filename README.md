# OSSU Course Tracker

A modern web application to track your progress through Open Source Society University (OSSU) courses across Computer Science and Data Science curricula with intelligent prerequisite management.

![OSSU Course Tracker](https://images.unsplash.com/photo-1522202176988-66273c2fd55f?auto=format&fit=crop&w=1200&h=400&q=80)

## 🌟 Features

### 📚 **Complete Course Coverage**
- **Computer Science**: 20 courses covering Introduction, Core Programming, Math, Systems, Theory, and Advanced Applications
- **Data Science**: 18 courses spanning Programming, Statistics, Machine Learning, Big Data, and Applied ML
- **ALL 38 OSSU courses** loaded and tracked (not limited to 14)

### 🔒 **Smart Prerequisite System**
- **80% Completion Threshold**: Courses unlock when prerequisites reach 80%+ completion
- **Visual Lock Indicators**: Clear 🔒 symbols for locked courses
- **Dynamic Unlocking**: Real-time prerequisite checking and course unlocking
- **Prerequisite Visualization**: See required courses for each class

### 🎨 **Modern UI Design**
- **Responsive Dashboard**: Clean, professional interface with Tailwind CSS
- **Progress Tracking**: Interactive sliders, progress bars, and completion percentages
- **Statistics Dashboard**: Real-time analytics showing completion rates and time invested
- **Advanced Filtering**: Search and filter by curriculum, status, and categories
- **Mobile Optimized**: Fully responsive design for all devices

### 📊 **Progress Management**
- **Flexible Progress Control**: Set completion percentage with interactive slider (0-100%)
- **Time Tracking**: Log estimated vs actual time spent on courses
- **Personal Notes**: Add thoughts, key learnings, and next steps for each course
- **Status Automation**: Automatic status updates (not started → in progress → completed)

### 💾 **Data Persistence**
- **MongoDB Storage**: All progress data persists across sessions
- **Real-time Updates**: Changes saved instantly to database
- **Data Integrity**: Preserves existing progress while adding new courses

## 🚀 **Live Demo**

- **Application**: https://42801da8-c189-453f-8e83-123e79572297.preview.emergentagent.com
- **API Documentation**: https://42801da8-c189-453f-8e83-123e79572297.preview.emergentagent.com/docs

## 🛠 **Technology Stack**

- **Frontend**: React 19 + Tailwind CSS + Modern Hooks
- **Backend**: FastAPI (Python) with async/await
- **Database**: MongoDB for persistent storage
- **Architecture**: REST API with prerequisite validation

## 🏃‍♂️ **Quick Start**

### Prerequisites
- **Node.js** (v16 or higher) 
- **Python** (3.8 or higher)
- **MongoDB** (local or Docker)
- **Yarn** package manager

### Installation

1. **Clone and Setup**
```bash
git clone <your-repo-url>
cd ossu-course-tracker
```

2. **Backend Setup**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Frontend Setup** 
```bash
cd frontend
yarn install
```

4. **Start Services**
```bash
# Backend (Terminal 1)
cd backend && uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# Frontend (Terminal 2) 
cd frontend && yarn start
```

5. **Access Application**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8001
- API Docs: http://localhost:8001/docs

## 📖 **Usage Guide**

### Getting Started
1. **Sync Courses**: Click "Sync Courses" to load all 38 OSSU courses
2. **Browse Curricula**: Explore Computer Science and Data Science tracks
3. **Track Progress**: Click "Update Progress" on unlocked courses

### Progress Workflow
1. **Start Course**: Set progress to 5-10% (status → "in progress")
2. **Regular Updates**: Update percentage as you complete sections
3. **Add Notes**: Log key learnings and insights
4. **Complete**: Reach 100% (status → "completed", unlocks dependent courses)

### Prerequisite System
- **Locked Courses**: Show 🔒 icon when prerequisites incomplete
- **Unlock Threshold**: Complete prerequisites to 80%+ to unlock next courses
- **Visual Indicators**: Clear prerequisite requirements shown on each card
- **Auto-Updates**: Course availability updates in real-time

## 🎯 **Key Features Demonstrated**

### Statistics Dashboard
- **Total Courses**: 38 (20 CS + 18 DS)
- **Completion Tracking**: Real-time percentage and course count
- **Time Investment**: Track estimated vs actual hours spent
- **Progress Analytics**: Visual progress indicators and trends

### Course Management
- **Smart Filtering**: Filter by curriculum, status, or search terms
- **Progress Control**: Interactive sliders for precise progress tracking  
- **Note Taking**: Personal learning journal for each course
- **External Links**: Direct access to course materials

### Prerequisite Logic Example
1. Complete "Introduction to Computer Science - CS50" to 80%+
2. Unlocks "Programming Methodology" 
3. Complete "Programming Methodology" to 80%+
4. Unlocks "Programming Abstractions" 
5. Continue the learning pathway...

## 🔧 **API Endpoints**

### Course Management
- `GET /api/courses` - List all courses with filtering
- `PUT /api/courses/{id}` - Update course progress
- `POST /api/courses/sync` - Sync OSSU course data
- `GET /api/stats` - Get progress statistics
- `GET /api/curricula` - Get curriculum information

### Example API Usage
```bash
# Get all courses
curl https://your-domain.com/api/courses

# Update course progress
curl -X PUT https://your-domain.com/api/courses/{id} \
  -H "Content-Type: application/json" \
  -d '{"progress": 85, "notes": "Great progress!"}'

# Get statistics
curl https://your-domain.com/api/stats
```

## 🤝 **Contributing**

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

## 📝 **License**

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 **Acknowledgments**

- [Open Source Society University](https://github.com/ossu) for excellent free curricula
- [OSSU Computer Science](https://github.com/ossu/computer-science)
- [OSSU Data Science](https://github.com/ossu/data-science)

---

**Start your OSSU learning journey today!** 🎓✨

*Built with ❤️ for the open source education community*
