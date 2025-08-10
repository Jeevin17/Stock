import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Components
const LoadingSpinner = () => (
  <div className="flex justify-center items-center py-8">
    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
  </div>
);

const StatsCard = ({ title, value, subtitle, icon, color = "indigo" }) => (
  <div className="bg-white rounded-xl shadow-lg p-6 border-l-4 border-indigo-500">
    <div className="flex items-center">
      <div className={`text-${color}-600 text-2xl mr-4`}>{icon}</div>
      <div>
        <p className="text-sm font-medium text-gray-600">{title}</p>
        <p className="text-3xl font-bold text-gray-900">{value}</p>
        {subtitle && <p className="text-sm text-gray-500">{subtitle}</p>}
      </div>
    </div>
  </div>
);

const CourseCard = ({ course, onUpdate }) => {
  const [isUpdating, setIsUpdating] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [progress, setProgress] = useState(course.progress);
  const [timeActual, setTimeActual] = useState(course.time_actual);
  const [notes, setNotes] = useState(course.notes);

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-800';
      case 'in_progress': return 'bg-blue-100 text-blue-800'; 
      case 'not_started': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getProgressColor = (progress) => {
    if (progress === 100) return 'bg-green-500';
    if (progress >= 80) return 'bg-blue-500';
    if (progress >= 40) return 'bg-yellow-500';
    return 'bg-gray-300';
  };

  const handleUpdate = async () => {
    setIsUpdating(true);
    try {
      await axios.put(`${API}/courses/${course.id}`, {
        progress: parseFloat(progress),
        time_actual: parseInt(timeActual) || 0,
        notes: notes
      });
      onUpdate();
      setShowModal(false);
    } catch (error) {
      console.error('Failed to update course:', error);
      alert(error.response?.data?.detail || 'Failed to update course');
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <>
      <div className={`bg-white rounded-xl shadow-lg p-6 border ${!course.is_unlocked ? 'opacity-60 border-gray-300' : 'border-gray-200 hover:shadow-xl'} transition-all duration-300`}>
        {/* Course Header */}
        <div className="flex justify-between items-start mb-4">
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">{course.title}</h3>
            <p className="text-sm text-gray-600 mb-2">{course.description}</p>
            <div className="flex flex-wrap gap-2 mb-3">
              <span className="px-2 py-1 text-xs font-medium bg-indigo-100 text-indigo-800 rounded-full">
                {course.category}
              </span>
              <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(course.status)}`}>
                {course.status.replace('_', ' ')}
              </span>
            </div>
          </div>
          {!course.is_unlocked && (
            <div className="text-red-500 text-sm font-medium">🔒 Locked</div>
          )}
        </div>

        {/* Prerequisites */}
        {course.prerequisites && course.prerequisites.length > 0 && (
          <div className="mb-4">
            <p className="text-xs font-medium text-gray-700 mb-1">Prerequisites:</p>
            <div className="text-xs text-gray-600">
              {course.prerequisites.map((prereq, index) => (
                <span key={index} className="inline-block bg-gray-100 rounded px-2 py-1 mr-1 mb-1">
                  {prereq}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Progress Bar */}
        <div className="mb-4">
          <div className="flex justify-between text-sm text-gray-600 mb-1">
            <span>Progress</span>
            <span>{course.progress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className={`h-2 rounded-full transition-all duration-300 ${getProgressColor(course.progress)}`}
              style={{ width: `${course.progress}%` }}
            ></div>
          </div>
        </div>

        {/* Course Info */}
        <div className="flex justify-between text-sm text-gray-600 mb-4">
          <span>Duration: {course.duration}</span>
          {course.time_actual > 0 && <span>Time Spent: {course.time_actual}h</span>}
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          <button
            onClick={() => setShowModal(true)}
            disabled={!course.is_unlocked}
            className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-colors ${
              course.is_unlocked 
                ? 'bg-indigo-600 text-white hover:bg-indigo-700' 
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            Update Progress
          </button>
          {course.url && (
            <a
              href={course.url}
              target="_blank"
              rel="noopener noreferrer"
              className="py-2 px-4 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors inline-flex items-center gap-1"
            >
              <span>🔗</span>
              View Course
            </a>
          )}
        </div>

        {course.notes && (
          <div className="mt-4 p-3 bg-gray-50 rounded-lg">
            <p className="text-xs font-medium text-gray-700 mb-1">Notes:</p>
            <p className="text-sm text-gray-600">{course.notes}</p>
          </div>
        )}
      </div>

      {/* Update Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md mx-4">
            <h3 className="text-lg font-semibold mb-4">Update Progress: {course.title}</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Progress: {progress}%
                </label>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={progress}
                  onChange={(e) => setProgress(e.target.value)}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Time Spent (hours)
                </label>
                <input
                  type="number"
                  value={timeActual}
                  onChange={(e) => setTimeActual(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  placeholder="0"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Notes
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  placeholder="Add your thoughts, key learnings, or next steps..."
                />
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowModal(false)}
                className="flex-1 py-2 px-4 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleUpdate}
                disabled={isUpdating}
                className="flex-1 py-2 px-4 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
              >
                {isUpdating ? 'Updating...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

const FilterBar = ({ filters, onFilterChange, onSearch, curricula }) => (
  <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
    <div className="flex flex-wrap gap-4 items-center">
      {/* Search */}
      <div className="flex-1 min-w-64">
        <input
          type="text"
          placeholder="Search courses..."
          onChange={(e) => onSearch(e.target.value)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
        />
      </div>

      {/* Curriculum Filter */}
      <select
        value={filters.curriculum}
        onChange={(e) => onFilterChange('curriculum', e.target.value)}
        className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
      >
        <option value="">All Curricula</option>
        <option value="computer_science">Computer Science</option>
        <option value="data_science">Data Science</option>
        <option value="mathematics">Mathematics</option>
        <option value="bioinformatics">Bioinformatics</option>
        <option value="precollege_math">Precollege Math</option>
      </select>

      {/* Status Filter */}
      <select
        value={filters.status}
        onChange={(e) => onFilterChange('status', e.target.value)}
        className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
      >
        <option value="">All Status</option>
        <option value="not_started">Not Started</option>
        <option value="in_progress">In Progress</option>
        <option value="completed">Completed</option>
      </select>
    </div>
  </div>
);

// Main App Component
function App() {
  const [courses, setCourses] = useState([]);
  const [stats, setStats] = useState(null);
  const [curricula, setCurricula] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [filters, setFilters] = useState({
    curriculum: '',
    category: '',
    status: ''
  });
  const [searchTerm, setSearchTerm] = useState('');

  const fetchData = async () => {
    try {
      const [coursesRes, statsRes, curriculaRes] = await Promise.all([
        axios.get(`${API}/courses`, { params: { ...filters, search: searchTerm } }),
        axios.get(`${API}/stats`),
        axios.get(`${API}/curricula`)
      ]);

      setCourses(coursesRes.data);
      setStats(statsRes.data);
      setCurricula(curriculaRes.data);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  };

  const syncCourses = async () => {
    setSyncing(true);
    try {
      const response = await axios.post(`${API}/courses/sync`);
      alert(`Success! ${response.data.synced_new} new courses added. Total: ${response.data.total_courses}`);
      await fetchData();
    } catch (error) {
      console.error('Failed to sync courses:', error);
      alert('Failed to sync courses. Please try again.');
    } finally {
      setSyncing(false);
    }
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  useEffect(() => {
    fetchData();
  }, [filters, searchTerm]);

  // Group courses by curriculum
  const groupedCourses = courses.reduce((acc, course) => {
    const curr = course.curriculum;
    if (!acc[curr]) acc[curr] = [];
    acc[curr].push(course);
    return acc;
  }, {});

  if (loading) return <LoadingSpinner />;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">OSSU Course Tracker</h1>
              <p className="text-gray-600 mt-1">Track your Open Source Society University progress</p>
            </div>
            <button
              onClick={syncCourses}
              disabled={syncing}
              className="bg-indigo-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              {syncing ? 'Syncing...' : 'Sync Courses'}
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <StatsCard
              title="Total Courses"
              value={stats.total_courses}
              icon="📚"
            />
            <StatsCard
              title="Completed"
              value={`${stats.completed_courses} (${stats.completion_percentage.toFixed(1)}%)`}
              subtitle={`of ${stats.total_courses} courses`}
              icon="✅"
              color="green"
            />
            <StatsCard
              title="In Progress"
              value={stats.in_progress_courses}
              icon="⏳"
              color="blue"
            />
            <StatsCard
              title="Time Invested"
              value={`${stats.total_time_actual}h`}
              subtitle={stats.total_time_estimated > 0 ? `of ${stats.total_time_estimated}h est.` : ''}
              icon="⏰"
              color="purple"
            />
          </div>
        )}

        {/* Filters */}
        <FilterBar
          filters={filters}
          onFilterChange={handleFilterChange}
          onSearch={setSearchTerm}
          curricula={curricula}
        />

        {/* Course Grid */}
        {Object.entries(groupedCourses).map(([curriculum, curriculumCourses]) => (
          <div key={curriculum} className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 capitalize">
              {curriculum.replace('_', ' ')} ({curriculumCourses.length} courses)
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {curriculumCourses.map(course => (
                <CourseCard
                  key={course.id}
                  course={course}
                  onUpdate={fetchData}
                />
              ))}
            </div>
          </div>
        ))}

        {courses.length === 0 && (
          <div className="text-center py-12">
            <div className="text-gray-400 text-6xl mb-4">📚</div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">No courses found</h3>
            <p className="text-gray-600 mb-6">Get started by syncing the OSSU curriculum</p>
            <button
              onClick={syncCourses}
              disabled={syncing}
              className="bg-indigo-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50"
            >
              {syncing ? 'Syncing...' : 'Sync OSSU Courses'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;