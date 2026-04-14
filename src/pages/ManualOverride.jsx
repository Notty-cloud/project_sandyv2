import React, { useState, useEffect } from 'react'
import Header from '../components/Header'
import Navigation from '../components/Navigation'
import Alert from '../components/Alert'
import { attendanceAPI, classAPI, studentAPI } from '../services/api'
import { authService } from '../services/auth'

const ManualOverride = () => {
  const [selectedClass, setSelectedClass] = useState('')
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0])
  const [classes, setClasses] = useState([])
  const [failedRecords, setFailedRecords] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')
  
  // Modal state
  const [showModal, setShowModal] = useState(false)
  const [selectedRecord, setSelectedRecord] = useState(null)
  const [newStatus, setNewStatus] = useState('present')
  const [overrideReason, setOverrideReason] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    fetchClasses()
  }, [])

  useEffect(() => {
    if (selectedClass) {
      fetchFailedRecords()
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

  const fetchFailedRecords = async () => {
    try {
      setLoading(true)
      const response = await attendanceAPI.getClassAttendance(selectedClass, selectedDate)
      // Filter for records that need manual review (low confidence or manual override)
      const failed = response.data.filter(
        r => r.confidence === null || r.confidence < 0.7 || r.is_manual_override
      )
      setFailedRecords(failed)
    } catch (err) {
      setError('Failed to load attendance records')
    } finally {
      setLoading(false)
    }
  }

  const openModal = (record) => {
    setSelectedRecord(record)
    setNewStatus(record.status)
    setOverrideReason('')
    setShowModal(true)
  }

  const handleOverride = async () => {
    if (!overrideReason.trim()) {
      setError('Please provide a reason for the override')
      return
    }

    try {
      setSubmitting(true)
      const userData = authService.getUserData()
      
      await attendanceAPI.overrideAttendance(selectedRecord.id, {
        status: newStatus,
        override_reason: overrideReason,
        overridden_by: userData?.id,
      })

      setSuccessMsg(`✓ Attendance overridden to "${newStatus}" successfully`)
      setShowModal(false)
      
      setTimeout(() => {
        fetchFailedRecords()
      }, 500)
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to override attendance')
    } finally {
      setSubmitting(false)
    }
  }

  const getConfidenceBadge = (confidence) => {
    if (confidence === null) return { color: 'bg-gray-100', text: 'text-gray-800', label: 'No Face' }
    if (confidence < 0.5) return { color: 'bg-red-100', text: 'text-red-800', label: 'Very Low' }
    if (confidence < 0.7) return { color: 'bg-orange-100', text: 'text-orange-800', label: 'Low' }
    return { color: 'bg-yellow-100', text: 'text-yellow-800', label: 'Uncertain' }
  }

  const stats = {
    total: failedRecords.length,
    lowConfidence: failedRecords.filter(r => r.confidence && r.confidence < 0.7).length,
    noFace: failedRecords.filter(r => r.confidence === null).length,
    alreadyOverridden: failedRecords.filter(r => r.is_manual_override).length,
  }

  return (
    <div className="flex h-screen bg-gray-50">
      <Navigation currentPage="/override" />

      <div className="flex-1 flex flex-col overflow-hidden">
        <Header title="Manual Override - Failed AI Registrations" />

        <main className="flex-1 overflow-auto p-6">
          <div className="max-w-7xl mx-auto">
            {error && <Alert type="error" message={error} onClose={() => setError('')} />}
            {successMsg && <Alert type="success" message={successMsg} onClose={() => setSuccessMsg('')} />}

            {/* Warning Alert */}
            <Alert 
              type="warning" 
              message="⚠️ Only override attendance when AI recognition failed. Document all manual changes for audit purposes."
            />

            {/* Statistics */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 my-6">
              <div className="bg-white p-4 rounded-lg shadow border-l-4 border-red-500">
                <p className="text-gray-600 text-sm">Total Failures</p>
                <p className="text-2xl font-bold text-red-600 mt-1">{stats.total}</p>
              </div>
              <div className="bg-white p-4 rounded-lg shadow border-l-4 border-orange-500">
                <p className="text-gray-600 text-sm">Low Confidence</p>
                <p className="text-2xl font-bold text-orange-600 mt-1">{stats.lowConfidence}</p>
              </div>
              <div className="bg-white p-4 rounded-lg shadow border-l-4 border-red-700">
                <p className="text-gray-600 text-sm">No Face Detected</p>
                <p className="text-2xl font-bold text-red-700 mt-1">{stats.noFace}</p>
              </div>
              <div className="bg-white p-4 rounded-lg shadow border-l-4 border-blue-500">
                <p className="text-gray-600 text-sm">Already Overridden</p>
                <p className="text-2xl font-bold text-blue-600 mt-1">{stats.alreadyOverridden}</p>
              </div>
            </div>

            {/* Filters */}
            <div className="bg-white rounded-lg shadow p-6 mb-6">
              <h2 className="text-lg font-bold text-gray-900 mb-4">Filters</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Date</label>
                  <input
                    type="date"
                    value={selectedDate}
                    onChange={(e) => setSelectedDate(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div className="flex items-end">
                  <button
                    onClick={fetchFailedRecords}
                    className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition font-semibold"
                  >
                    Refresh
                  </button>
                </div>
              </div>
            </div>

            {/* Failed Records Table */}
            <div className="bg-white rounded-lg shadow">
              <div className="p-6 border-b border-gray-200">
                <h2 className="text-lg font-bold text-gray-900">
                  {selectedClass ? 'Records Requiring Manual Review' : 'Select a class to view failed records'}
                </h2>
              </div>

              {loading ? (
                <div className="p-6 text-center">
                  <p className="text-gray-600">Loading records...</p>
                </div>
              ) : failedRecords.length === 0 ? (
                <div className="p-6 text-center">
                  <p className="text-green-600 font-semibold">✓ No failed registrations! All records are valid.</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50 border-b">
                      <tr>
                        <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Student ID</th>
                        <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Student Name</th>
                        <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Current Status</th>
                        <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Confidence</th>
                        <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Issue</th>
                        <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Check-in Time</th>
                        <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {failedRecords.map((record) => {
                        const confidenceBadge = getConfidenceBadge(record.confidence)
                        return (
                          <tr key={record.id} className="border-b hover:bg-red-50">
                            <td className="px-6 py-3 text-gray-900 font-medium">{record.student_id}</td>
                            <td className="px-6 py-3 text-gray-600">{record.student_name || 'N/A'}</td>
                            <td className="px-6 py-3">
                              <span className={`px-2 py-1 rounded text-xs font-semibold ${
                                record.status === 'present' 
                                  ? 'bg-green-100 text-green-800'
                                  : record.status === 'late'
                                  ? 'bg-yellow-100 text-yellow-800'
                                  : 'bg-red-100 text-red-800'
                              }`}>
                                {record.status.toUpperCase()}
                              </span>
                            </td>
                            <td className="px-6 py-3">
                              <span className={`px-2 py-1 rounded text-xs font-semibold ${confidenceBadge.color} ${confidenceBadge.text}`}>
                                {record.confidence !== null 
                                  ? `${(record.confidence * 100).toFixed(1)}% - ${confidenceBadge.label}`
                                  : confidenceBadge.label
                                }
                              </span>
                            </td>
                            <td className="px-6 py-3 text-sm">
                              {record.confidence === null && <span className="text-red-600">🚫 No face detected</span>}
                              {record.confidence && record.confidence < 0.7 && <span className="text-orange-600">⚠️ Low confidence</span>}
                              {record.is_manual_override && <span className="text-blue-600">✓ Already overridden</span>}
                            </td>
                            <td className="px-6 py-3 text-gray-600 text-sm">
                              {record.checkin_time ? new Date(record.checkin_time).toLocaleTimeString() : '-'}
                            </td>
                            <td className="px-6 py-3">
                              <button
                                onClick={() => openModal(record)}
                                className="px-3 py-1 bg-orange-500 text-white text-xs rounded hover:bg-orange-600 transition font-semibold"
                              >
                                🔧 Override
                              </button>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Guidelines */}
            <div className="mt-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <h3 className="font-semibold text-yellow-900 mb-2">📋 Override Guidelines</h3>
              <ul className="text-sm text-yellow-800 space-y-1">
                <li>• <strong>Low Confidence:</strong> AI detected a face but confidence is below 70% - verify manually</li>
                <li>• <strong>No Face Detected:</strong> Camera couldn't recognize a face - check student presence manually</li>
                <li>• <strong>Document Reason:</strong> Always provide reason for audit trail (e.g., "Student was sick", "Camera malfunction")</li>
                <li>• <strong>Status Options:</strong> Mark as Present, Late, or Absent based on actual attendance</li>
              </ul>
            </div>
          </div>
        </main>
      </div>

      {/* Override Modal */}
      {showModal && selectedRecord && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-lg max-w-md w-full p-6">
            <h3 className="text-lg font-bold text-gray-900 mb-4">Manual Override Attendance</h3>

            {/* Record Details */}
            <div className="bg-gray-50 p-4 rounded-lg mb-4">
              <p className="text-sm text-gray-600"><strong>Student ID:</strong> {selectedRecord.student_id}</p>
              <p className="text-sm text-gray-600"><strong>Current Status:</strong> {selectedRecord.status.toUpperCase()}</p>
              <p className="text-sm text-gray-600">
                <strong>Confidence:</strong> {selectedRecord.confidence 
                  ? `${(selectedRecord.confidence * 100).toFixed(1)}%` 
                  : 'No face detected'
                }
              </p>
            </div>

            {/* Status Selection */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">New Status</label>
              <div className="space-y-2">
                {['present', 'late', 'absent'].map((status) => (
                  <label key={status} className="flex items-center">
                    <input
                      type="radio"
                      name="status"
                      value={status}
                      checked={newStatus === status}
                      onChange={(e) => setNewStatus(e.target.value)}
                      className="mr-2"
                    />
                    <span className="text-sm text-gray-700 capitalize">
                      {status === 'present' ? '✓ Present' : status === 'late' ? '⏰ Late' : '✗ Absent'}
                    </span>
                  </label>
                ))}
              </div>
            </div>

            {/* Reason */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">Override Reason</label>
              <textarea
                value={overrideReason}
                onChange={(e) => setOverrideReason(e.target.value)}
                placeholder="Explain why this attendance is being manually overridden..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                rows="4"
              ></textarea>
              <p className="text-xs text-gray-600 mt-1">Required for audit trail</p>
            </div>

            {/* Error Alert */}
            {error && <Alert type="error" message={error} onClose={() => setError('')} />}

            {/* Actions */}
            <div className="flex gap-3">
              <button
                onClick={() => setShowModal(false)}
                className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition"
              >
                Cancel
              </button>
              <button
                onClick={handleOverride}
                disabled={submitting || !overrideReason.trim()}
                className="flex-1 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition disabled:opacity-50 font-semibold"
              >
                {submitting ? 'Saving...' : 'Confirm Override'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ManualOverride
