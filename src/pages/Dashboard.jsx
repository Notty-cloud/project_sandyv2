import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Header from '../components/Header'
import Navigation from '../components/Navigation'
import Alert from '../components/Alert'
import { classAPI } from '../services/api'

const Dashboard = () => {
  const navigate = useNavigate()
  const [classes, setClasses] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchClasses()
  }, [])

  const fetchClasses = async () => {
    try {
      setLoading(true)
      const response = await classAPI.getClasses()
      setClasses(response.data?.results ?? response.data)
    } catch (err) {
      setError('Failed to load classes. Please try again.')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex h-screen bg-gray-50">
      <Navigation currentPage="/dashboard" />
      
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header title="Central Navigation Dashboard" />

        <main className="flex-1 overflow-auto p-6">
          <div className="max-w-7xl mx-auto">
            {error && <Alert type="error" message={error} onClose={() => setError('')} />}

            {loading ? (
              <div className="text-center py-12">
                <p className="text-gray-600">Loading classes...</p>
              </div>
            ) : (
              <>
                {/* Quick Stats */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
                  <div className="bg-white p-6 rounded-lg shadow border-l-4 border-blue-500">
                    <p className="text-gray-600 text-sm">Total Classes</p>
                    <p className="text-3xl font-bold text-blue-600 mt-2">{classes.length}</p>
                  </div>
                  <div className="bg-white p-6 rounded-lg shadow border-l-4 border-green-500">
                    <p className="text-gray-600 text-sm">Classes Today</p>
                    <p className="text-3xl font-bold text-green-600 mt-2">
                      {classes.filter(c => c.is_active).length}
                    </p>
                  </div>
                  <div className="bg-white p-6 rounded-lg shadow border-l-4 border-purple-500">
                    <p className="text-gray-600 text-sm">Pending Enrollments</p>
                    <p className="text-3xl font-bold text-purple-600 mt-2">12</p>
                  </div>
                  <div className="bg-white p-6 rounded-lg shadow border-l-4 border-orange-500">
                    <p className="text-gray-600 text-sm">Failed Registrations</p>
                    <p className="text-3xl font-bold text-orange-600 mt-2">5</p>
                  </div>
                </div>

                {/* Main Navigation Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                  {/* Attendance Card */}
                  <div className="bg-white rounded-lg shadow hover:shadow-lg transition p-6 cursor-pointer">
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="text-gray-600 text-sm font-semibold">ATTENDANCE</p>
                        <h3 className="text-2xl font-bold text-gray-900 mt-2">📋 View Class Attendance</h3>
                        <p className="text-gray-600 text-sm mt-3">
                          View real-time attendance records and status for all classes
                        </p>
                      </div>
                      <span className="text-3xl">→</span>
                    </div>
                    <button
                      onClick={() => navigate('/attendance')}
                      className="mt-4 w-full bg-blue-500 text-white py-2 rounded-lg hover:bg-blue-600 transition font-semibold"
                    >
                      Go to Attendance
                    </button>
                  </div>

                  {/* Enrollment Card */}
                  <div className="bg-white rounded-lg shadow hover:shadow-lg transition p-6 cursor-pointer">
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="text-gray-600 text-sm font-semibold">ENROLLMENT</p>
                        <h3 className="text-2xl font-bold text-gray-900 mt-2">📷 Register New Students</h3>
                        <p className="text-gray-600 text-sm mt-3">
                          Capture facial embeddings and enroll new students
                        </p>
                      </div>
                      <span className="text-3xl">→</span>
                    </div>
                    <button
                      onClick={() => navigate('/enrollment')}
                      className="mt-4 w-full bg-green-500 text-white py-2 rounded-lg hover:bg-green-600 transition font-semibold"
                    >
                      Go to Enrollment
                    </button>
                  </div>

                  {/* Manual Override Card */}
                  <div className="bg-white rounded-lg shadow hover:shadow-lg transition p-6 cursor-pointer">
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="text-gray-600 text-sm font-semibold">MANUAL OVERRIDE</p>
                        <h3 className="text-2xl font-bold text-gray-900 mt-2">⚙️ Handle Failed Registrations</h3>
                        <p className="text-gray-600 text-sm mt-3">
                          Manually adjust attendance for failed AI registrations
                        </p>
                      </div>
                      <span className="text-3xl">→</span>
                    </div>
                    <button
                      onClick={() => navigate('/override')}
                      className="mt-4 w-full bg-orange-500 text-white py-2 rounded-lg hover:bg-orange-600 transition font-semibold"
                    >
                      Go to Override
                    </button>
                  </div>

                  {/* System Settings Card */}
                  <div className="bg-white rounded-lg shadow hover:shadow-lg transition p-6">
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="text-gray-600 text-sm font-semibold">SETTINGS</p>
                        <h3 className="text-2xl font-bold text-gray-900 mt-2">⚡ System Configuration</h3>
                        <p className="text-gray-600 text-sm mt-3">
                          Manage system settings and user preferences
                        </p>
                      </div>
                      <span className="text-3xl">→</span>
                    </div>
                    <button 
                      className="mt-4 w-full bg-gray-500 text-white py-2 rounded-lg hover:bg-gray-600 transition font-semibold"
                    >
                      Go to Settings
                    </button>
                  </div>
                </div>

                {/* Classes List */}
                <div className="bg-white rounded-lg shadow p-6">
                  <h2 className="text-xl font-bold text-gray-900 mb-4">Active Classes</h2>
                  {classes.length === 0 ? (
                    <p className="text-gray-600 text-center py-6">No classes available</p>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead className="bg-gray-50 border-b">
                          <tr>
                            <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Class</th>
                            <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Grade</th>
                            <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Subject</th>
                            <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Teacher</th>
                            <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {classes.map((cls) => (
                            <tr key={cls.id} className="border-b hover:bg-gray-50">
                              <td className="px-4 py-3 text-gray-900 font-medium">{cls.class_name || `${cls.grade}-${cls.section}`}</td>
                              <td className="px-4 py-3 text-gray-600">{cls.grade}</td>
                              <td className="px-4 py-3 text-gray-600">{cls.subject || '-'}</td>
                              <td className="px-4 py-3 text-gray-600">{cls.teacher_id || 'Unassigned'}</td>
                              <td className="px-4 py-3">
                                <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                                  cls.is_active 
                                    ? 'bg-green-100 text-green-800' 
                                    : 'bg-gray-100 text-gray-800'
                                }`}>
                                  {cls.is_active ? 'Active' : 'Inactive'}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}

export default Dashboard
