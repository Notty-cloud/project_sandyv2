import React, { useState, useEffect } from 'react'
import Header from '../components/Header'
import Navigation from '../components/Navigation'
import Alert from '../components/Alert'
import { attendanceAPI, classAPI, studentAPI } from '../services/api'

const AttendanceView = () => {
  const [selectedClass, setSelectedClass] = useState('')
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0])
  const [classes, setClasses] = useState([])
  const [attendance, setAttendance] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')
  const [filterStatus, setFilterStatus] = useState('all')

  // Fetch classes on mount
  useEffect(() => {
    fetchClasses()
  }, [])

  // Fetch attendance when class or date changes
  useEffect(() => {
    if (selectedClass) {
      fetchAttendance()
    }
  }, [selectedClass, selectedDate])

  const fetchClasses = async () => {
    try {
      const response = await classAPI.getClasses()
      setClasses(response.data)
      if (response.data.length > 0) {
        setSelectedClass(response.data[0].id)
      }
    } catch (err) {
      setError('Failed to load classes')
    }
  }

  const fetchAttendance = async () => {
    try {
      setLoading(true)
      const response = await attendanceAPI.getClassAttendance(selectedClass, selectedDate)
      setAttendance(response.data)
    } catch (err) {
      setError('Failed to load attendance records')
    } finally {
      setLoading(false)
    }
  }

  const getStatusBadge = (status) => {
    const statusMap = {
      present: { bg: 'bg-green-100', text: 'text-green-800', label: 'Present ✓' },
      absent: { bg: 'bg-red-100', text: 'text-red-800', label: 'Absent ✗' },
      late: { bg: 'bg-yellow-100', text: 'text-yellow-800', label: 'Late ⏰' },
    }
    return statusMap[status] || { bg: 'bg-gray-100', text: 'text-gray-800', label: 'Unknown' }
  }

  const filteredAttendance = filterStatus === 'all' 
    ? attendance 
    : attendance.filter(a => a.status === filterStatus)

  const stats = {
    total: attendance.length,
    present: attendance.filter(a => a.status === 'present').length,
    absent: attendance.filter(a => a.status === 'absent').length,
    late: attendance.filter(a => a.status === 'late').length,
  }

  return (
    <div className="flex h-screen bg-gray-50">
      <Navigation currentPage="/attendance" />

      <div className="flex-1 flex flex-col overflow-hidden">
        <Header title="Class Attendance View" />

        <main className="flex-1 overflow-auto p-6">
          <div className="max-w-7xl mx-auto">
            {error && <Alert type="error" message={error} onClose={() => setError('')} />}
            {successMsg && <Alert type="success" message={successMsg} onClose={() => setSuccessMsg('')} />}

            {/* Filters */}
            <div className="bg-white rounded-lg shadow p-6 mb-6">
              <h2 className="text-lg font-bold text-gray-900 mb-4">Filters</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Class Selection */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Select Class</label>
                  <select
                    value={selectedClass}
                    onChange={(e) => setSelectedClass(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">-- Select Class --</option>
                    {classes.map((cls) => (
                      <option key={cls.id} value={cls.id}>
                        {cls.class_name || `${cls.grade}-${cls.section}`}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Date Selection */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Date</label>
                  <input
                    type="date"
                    value={selectedDate}
                    onChange={(e) => setSelectedDate(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                {/* Status Filter */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Filter by Status</label>
                  <select
                    value={filterStatus}
                    onChange={(e) => setFilterStatus(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="all">All</option>
                    <option value="present">Present</option>
                    <option value="absent">Absent</option>
                    <option value="late">Late</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Statistics */}
            {selectedClass && (
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <div className="bg-white p-4 rounded-lg shadow border-l-4 border-gray-400">
                  <p className="text-gray-600 text-sm">Total Students</p>
                  <p className="text-2xl font-bold text-gray-700 mt-1">{stats.total}</p>
                </div>
                <div className="bg-white p-4 rounded-lg shadow border-l-4 border-green-500">
                  <p className="text-gray-600 text-sm">Present</p>
                  <p className="text-2xl font-bold text-green-600 mt-1">{stats.present}</p>
                </div>
                <div className="bg-white p-4 rounded-lg shadow border-l-4 border-red-500">
                  <p className="text-gray-600 text-sm">Absent</p>
                  <p className="text-2xl font-bold text-red-600 mt-1">{stats.absent}</p>
                </div>
                <div className="bg-white p-4 rounded-lg shadow border-l-4 border-yellow-500">
                  <p className="text-gray-600 text-sm">Late</p>
                  <p className="text-2xl font-bold text-yellow-600 mt-1">{stats.late}</p>
                </div>
              </div>
            )}

            {/* Attendance Table */}
            <div className="bg-white rounded-lg shadow">
              <div className="p-6 border-b border-gray-200">
                <h2 className="text-lg font-bold text-gray-900">
                  {selectedClass ? 'Attendance Records' : 'Select a class to view attendance'}
                </h2>
              </div>

              {loading ? (
                <div className="p-6 text-center">
                  <p className="text-gray-600">Loading attendance records...</p>
                </div>
              ) : filteredAttendance.length === 0 ? (
                <div className="p-6 text-center">
                  <p className="text-gray-600">No attendance records found</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50 border-b">
                      <tr>
                        <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Student ID</th>
                        <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Student Name</th>
                        <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Status</th>
                        <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Check-in Time</th>
                        <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Confidence</th>
                        <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Manual Override</th>
                        <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Location</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredAttendance.map((record, idx) => {
                        const statusStyle = getStatusBadge(record.status)
                        return (
                          <tr key={record.id} className="border-b hover:bg-gray-50">
                            <td className="px-6 py-3 text-gray-900 font-medium">{record.student_id}</td>
                            <td className="px-6 py-3 text-gray-600">{record.student_name || 'N/A'}</td>
                            <td className="px-6 py-3">
                              <span className={`px-3 py-1 rounded-full text-xs font-semibold ${statusStyle.bg} ${statusStyle.text}`}>
                                {statusStyle.label}
                              </span>
                            </td>
                            <td className="px-6 py-3 text-gray-600">
                              {record.checkin_time ? new Date(record.checkin_time).toLocaleTimeString() : '-'}
                            </td>
                            <td className="px-6 py-3 text-gray-600">
                              {record.confidence ? `${(record.confidence * 100).toFixed(1)}%` : '-'}
                            </td>
                            <td className="px-6 py-3">
                              <span className={`text-xs font-semibold ${
                                record.is_manual_override 
                                  ? 'text-orange-600' 
                                  : 'text-gray-600'
                              }`}>
                                {record.is_manual_override ? '⚠️ Overridden' : 'AI'}
                              </span>
                            </td>
                            <td className="px-6 py-3 text-gray-600 text-sm">{record.location || '-'}</td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}

export default AttendanceView
