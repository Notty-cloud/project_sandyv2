import React, { useState, useEffect, useRef } from 'react'
import Header from '../components/Header'
import Navigation from '../components/Navigation'
import Alert from '../components/Alert'
import { attendanceAPI, classAPI } from '../services/api'
import { authService } from '../services/auth'

const AttendanceView = () => {
  const [selectedClass, setSelectedClass] = useState('')
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0])
  const [classes, setClasses] = useState([])
  const [attendance, setAttendance] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')
  const [filterStatus, setFilterStatus] = useState('all')

  // Mark-by-face state
  const [showFaceModal, setShowFaceModal] = useState(false)
  const [faceImage, setFaceImage] = useState(null)
  const [facePreview, setFacePreview] = useState(null)
  const [faceThreshold, setFaceThreshold] = useState(0.65)
  const [faceLoading, setFaceLoading] = useState(false)
  const [faceResult, setFaceResult] = useState(null)
  const [sessionLog, setSessionLog] = useState([])
  const fileInputRef = useRef(null)

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
      const data = response.data?.results ?? response.data
      setClasses(data)
      if (data.length > 0) {
        setSelectedClass(data[0].id)
      }
    } catch (err) {
      setError('Failed to load classes')
    }
  }

  const fetchAttendance = async () => {
    try {
      setLoading(true)
      const response = await attendanceAPI.getClassAttendance(selectedClass, selectedDate)
      setAttendance(response.data?.results ?? response.data)
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

  const handleFaceImageChange = (e) => {
    const file = e.target.files[0]
    if (!file) return
    setFaceImage(file)
    setFacePreview(URL.createObjectURL(file))
    setFaceResult(null)
  }

  const handleMarkByFace = async () => {
    if (!faceImage) { setError('Please select an image.'); return }
    if (!selectedClass) { setError('Please select a class first.'); return }

    const user = authService.getUserData()
    const tenantId = user?.tenant_id
    if (!tenantId) { setError('Session missing tenant ID. Please log in again.'); return }

    const formData = new FormData()
    formData.append('image', faceImage)
    formData.append('tenant_id', tenantId)
    formData.append('class_id', selectedClass)
    formData.append('date', selectedDate)
    formData.append('threshold', faceThreshold)

    setFaceLoading(true)
    setFaceResult(null)
    try {
      const response = await attendanceAPI.markAttendanceByFace(formData)
      setFaceResult({ type: 'success', data: response.data })
      setSessionLog((prev) => [{
        name: response.data.match?.name ?? 'Unknown',
        student_id: response.data.match?.student_id ?? '—',
        confidence: response.data.confidence,
        status: response.data.status ?? 'present',
        already_marked: response.data.already_marked ?? false,
        time: new Date().toLocaleTimeString(),
      }, ...prev])
      fetchAttendance()
    } catch (err) {
      const data = err.response?.data
      if (err.response?.status === 404) {
        setFaceResult({ type: 'nomatch', data })
      } else {
        setFaceResult({ type: 'error', data })
      }
    } finally {
      setFaceLoading(false)
    }
  }

  const closeFaceModal = () => {
    setShowFaceModal(false)
    setFaceImage(null)
    setFacePreview(null)
    setFaceResult(null)
    setSessionLog([])
    if (fileInputRef.current) fileInputRef.current.value = ''
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
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-bold text-gray-900">Filters</h2>
                <button
                  onClick={() => { setShowFaceModal(true); setFaceResult(null) }}
                  disabled={!selectedClass}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-semibold text-sm disabled:opacity-40 disabled:cursor-not-allowed"
                  title={!selectedClass ? 'Select a class first' : 'Mark attendance by face photo'}
                >
                  📷 Mark by Face
                </button>
              </div>
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

      {/* Mark by Face Modal */}
      {showFaceModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md">
            <div className="flex items-center justify-between p-6 border-b">
              <h2 className="text-xl font-bold text-gray-900">📷 Mark Attendance by Face</h2>
              <button onClick={closeFaceModal} className="text-gray-400 hover:text-gray-600 text-2xl leading-none">&times;</button>
            </div>

            <div className="p-6 space-y-5">
              {/* Class + Date summary */}
              <div className="bg-blue-50 rounded-lg p-3 text-sm text-blue-800">
                <span className="font-semibold">Class:</span> {classes.find(c => String(c.id) === String(selectedClass))?.class_name || selectedClass}
                &nbsp;&nbsp;<span className="font-semibold">Date:</span> {selectedDate}
              </div>

              {/* Image upload */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Face Photo</label>
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center cursor-pointer hover:border-blue-400 transition"
                >
                  {facePreview ? (
                    <img src={facePreview} alt="Preview" className="mx-auto max-h-48 rounded-lg object-contain" />
                  ) : (
                    <div className="py-6 text-gray-500">
                      <div className="text-4xl mb-2">🖼️</div>
                      <p className="text-sm">Click to upload a face photo</p>
                      <p className="text-xs mt-1">JPG, PNG — max 10 MB</p>
                    </div>
                  )}
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={handleFaceImageChange}
                />
                {facePreview && (
                  <button
                    onClick={() => { setFaceImage(null); setFacePreview(null); setFaceResult(null); fileInputRef.current.value = '' }}
                    className="mt-2 text-xs text-red-500 hover:underline"
                  >
                    Remove image
                  </button>
                )}
              </div>

              {/* Threshold slider */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Similarity Threshold: <span className="font-bold text-blue-600">{faceThreshold.toFixed(2)}</span>
                </label>
                <input
                  type="range"
                  min="0.30"
                  max="0.99"
                  step="0.01"
                  value={faceThreshold}
                  onChange={(e) => setFaceThreshold(parseFloat(e.target.value))}
                  className="w-full accent-blue-600"
                />
                <div className="flex justify-between text-xs text-gray-400 mt-1">
                  <span>0.30 (lenient)</span>
                  <span>0.99 (strict)</span>
                </div>
              </div>

              {/* Result */}
              {faceResult && (
                <div className={`rounded-lg p-4 text-sm ${
                  faceResult.type === 'success' ? 'bg-green-50 border border-green-200' :
                  faceResult.type === 'nomatch' ? 'bg-yellow-50 border border-yellow-200' :
                  'bg-red-50 border border-red-200'
                }`}>
                  {faceResult.type === 'success' && (
                    <>
                      <p className="font-bold text-green-800 text-base">
                        {faceResult.data.already_marked ? '⚠️ Already Marked' : '✓ Match Found'}
                      </p>
                      <p className="text-green-700 mt-1">
                        <span className="font-semibold">{faceResult.data.match?.name}</span>
                        {' '}({faceResult.data.match?.student_id})
                      </p>
                      <p className="text-green-700">
                        Cosine similarity: <span className="font-bold">{faceResult.data.confidence != null ? `${(faceResult.data.confidence * 100).toFixed(1)}%` : '—'}</span>
                      </p>
                      {!faceResult.data.already_marked && (
                        <p className="text-green-700">
                          Status: <span className="font-semibold capitalize">{faceResult.data.status}</span>
                        </p>
                      )}
                      <p className="text-green-600 text-xs mt-1">{faceResult.data.message}</p>
                    </>
                  )}
                  {faceResult.type === 'nomatch' && (
                    <>
                      <p className="font-bold text-yellow-800 text-base">No Match</p>
                      <p className="text-yellow-700 mt-1">
                        Best cosine similarity: <span className="font-bold">
                          {faceResult.data?.confidence != null ? `${(faceResult.data.confidence * 100).toFixed(1)}%` : '—'}
                        </span>
                      </p>
                      <p className="text-yellow-600 text-xs mt-1">{faceResult.data?.message || 'No enrolled student exceeded the threshold.'}</p>
                    </>
                  )}
                  {faceResult.type === 'error' && (
                    <>
                      <p className="font-bold text-red-800 text-base">Error</p>
                      <p className="text-red-700 text-xs mt-1">{faceResult.data?.error || 'An unexpected error occurred.'}</p>
                    </>
                  )}
                </div>
              )}
            </div>

            {/* Session log */}
            {sessionLog.length > 0 && (
              <div className="px-6 pb-4">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    Session Log — {sessionLog.length} marked
                  </p>
                  <button onClick={() => setSessionLog([])}
                    className="text-xs text-red-400 hover:text-red-600">Clear</button>
                </div>
                <div className="max-h-40 overflow-y-auto space-y-1.5 pr-1">
                  {sessionLog.map((entry, i) => (
                    <div key={i} className={`flex items-center justify-between px-3 py-2 rounded-lg text-xs ${
                      entry.already_marked ? 'bg-yellow-50 border border-yellow-200' : 'bg-green-50 border border-green-200'
                    }`}>
                      <div>
                        <span className="font-semibold text-gray-800">{entry.name}</span>
                        <span className="text-gray-400 ml-1.5">{entry.student_id}</span>
                      </div>
                      <div className="flex items-center gap-2 text-right">
                        <span className={`font-bold ${entry.already_marked ? 'text-yellow-600' : 'text-green-600'}`}>
                          {entry.already_marked ? 'Already marked' : `${(entry.confidence * 100).toFixed(1)}%`}
                        </span>
                        <span className="text-gray-400">{entry.time}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="flex gap-3 p-6 pt-0">
              <button
                onClick={handleMarkByFace}
                disabled={faceLoading || !faceImage}
                className="flex-1 bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition font-semibold disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {faceLoading ? 'Processing...' : 'Identify & Mark'}
              </button>
              <button
                onClick={closeFaceModal}
                className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default AttendanceView
