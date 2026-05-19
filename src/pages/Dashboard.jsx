import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Header from '../components/Header'
import Navigation from '../components/Navigation'
import Alert from '../components/Alert'
import { classAPI } from '../services/api'
import { authService } from '../services/auth'

const NAV_CARDS = [
  {
    section: 'ATTENDANCE',
    title: '📋 View Class Attendance',
    desc: 'View real-time attendance records and mark students present',
    path: '/attendance',
    btnLabel: 'Go to Attendance',
    color: 'bg-blue-500 hover:bg-blue-600',
    minLevel: 1,
  },
  {
    section: 'ENROLLMENT',
    title: '📷 Register New Students',
    desc: 'Capture facial embeddings and enroll new students into the system',
    path: '/enrollment',
    btnLabel: 'Go to Enrollment',
    color: 'bg-green-500 hover:bg-green-600',
    minLevel: 2,
    adminOnly: true,
  },
  {
    section: 'MANUAL OVERRIDE',
    title: '⚙️ Handle Failed Registrations',
    desc: 'Manually adjust attendance for cases where face recognition failed',
    path: '/override',
    btnLabel: 'Go to Override',
    color: 'bg-orange-500 hover:bg-orange-600',
    minLevel: 2,
    adminOnly: true,
  },
  {
    section: 'ADMIN MANAGEMENT',
    title: '🔑 Manage Staff Accounts',
    desc: 'Create, unlock, and manage teacher and coordinator accounts',
    path: '/admin-management',
    btnLabel: 'Go to Admin Management',
    color: 'bg-purple-500 hover:bg-purple-600',
    minLevel: 3,
    adminOnly: true,
  },
]

const Dashboard = () => {
  const navigate = useNavigate()
  const user = authService.getUserData()
  const isTeacher = user?.role === 'teacher'
  const level = user?.authorization_level ?? 1

  const [classes, setClasses] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const params = isTeacher ? { teacher: user.id } : {}
    classAPI.getClasses(params)
      .then(r => setClasses(r.data?.results ?? r.data))
      .catch(() => setError('Failed to load classes.'))
      .finally(() => setLoading(false))
  }, [])

  const visibleCards = NAV_CARDS.filter(c =>
    level >= c.minLevel && (!c.adminOnly || !isTeacher)
  )

  const activeClasses = classes.filter(c => c.is_active)

  return (
    <div className="flex h-screen bg-gray-50">
      <Navigation currentPage="/dashboard" />

      <div className="flex-1 flex flex-col overflow-hidden">
        <Header title={isTeacher ? 'My Classes' : 'Dashboard'} />

        <main className="flex-1 overflow-auto p-6">
          <div className="max-w-7xl mx-auto">
            {error && <Alert type="error" message={error} onClose={() => setError('')} />}

            {loading ? (
              <div className="text-center py-12 text-gray-500">Loading…</div>
            ) : (
              <>
                {/* Stats */}
                <div className={`grid gap-4 mb-8 ${isTeacher ? 'grid-cols-2' : 'grid-cols-2 md:grid-cols-4'}`}>
                  <div className="bg-white p-6 rounded-lg shadow border-l-4 border-blue-500">
                    <p className="text-gray-500 text-sm">{isTeacher ? 'My Classes' : 'Total Classes'}</p>
                    <p className="text-3xl font-bold text-blue-600 mt-2">{classes.length}</p>
                  </div>
                  <div className="bg-white p-6 rounded-lg shadow border-l-4 border-green-500">
                    <p className="text-gray-500 text-sm">Active Classes</p>
                    <p className="text-3xl font-bold text-green-600 mt-2">{activeClasses.length}</p>
                  </div>
                  {!isTeacher && (
                    <>
                      <div className="bg-white p-6 rounded-lg shadow border-l-4 border-purple-500">
                        <p className="text-gray-500 text-sm">Pending Enrollments</p>
                        <p className="text-3xl font-bold text-purple-600 mt-2">—</p>
                      </div>
                      <div className="bg-white p-6 rounded-lg shadow border-l-4 border-orange-500">
                        <p className="text-gray-500 text-sm">Failed Registrations</p>
                        <p className="text-3xl font-bold text-orange-600 mt-2">—</p>
                      </div>
                    </>
                  )}
                </div>

                {/* Navigation cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                  {visibleCards.map(card => (
                    <div key={card.path} className="bg-white rounded-lg shadow hover:shadow-lg transition p-6">
                      <p className="text-gray-500 text-xs font-semibold tracking-wide">{card.section}</p>
                      <h3 className="text-xl font-bold text-gray-900 mt-2">{card.title}</h3>
                      <p className="text-gray-500 text-sm mt-2">{card.desc}</p>
                      <button
                        onClick={() => navigate(card.path)}
                        className={`mt-4 w-full text-white py-2 rounded-lg transition font-semibold ${card.color}`}
                      >
                        {card.btnLabel}
                      </button>
                    </div>
                  ))}
                </div>

                {/* Class list */}
                <div className="bg-white rounded-lg shadow p-6">
                  <h2 className="text-lg font-bold text-gray-900 mb-4">
                    {isTeacher ? 'Your Assigned Classes' : 'All Classes'}
                  </h2>
                  {classes.length === 0 ? (
                    <p className="text-gray-500 text-center py-8">
                      {isTeacher ? 'No classes assigned to your account yet.' : 'No classes found.'}
                    </p>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead className="bg-gray-50 border-b">
                          <tr>
                            <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Class</th>
                            <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Grade</th>
                            <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Subject</th>
                            {!isTeacher && <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Teacher</th>}
                            <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {classes.map(cls => (
                            <tr key={cls.id} className="border-b hover:bg-gray-50">
                              <td className="px-4 py-3 font-medium text-gray-900">{cls.class_name || `${cls.grade}-${cls.section}`}</td>
                              <td className="px-4 py-3 text-gray-600">{cls.grade}</td>
                              <td className="px-4 py-3 text-gray-600">{cls.subject || '—'}</td>
                              {!isTeacher && <td className="px-4 py-3 text-gray-600">{cls.teacher_name || cls.teacher_id || 'Unassigned'}</td>}
                              <td className="px-4 py-3">
                                <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${
                                  cls.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
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
