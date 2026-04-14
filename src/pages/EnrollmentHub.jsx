import React, { useState, useEffect, useRef } from 'react'
import Header from '../components/Header'
import Navigation from '../components/Navigation'
import Alert from '../components/Alert'
import { enrollmentAPI, studentAPI, classAPI } from '../services/api'

const EnrollmentHub = () => {
  const [students, setStudents] = useState([])
  const [classes, setClasses] = useState([])
  const [selectedClass, setSelectedClass] = useState('')
  const [selectedStudent, setSelectedStudent] = useState('')
  const [enrollments, setEnrollments] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')
  
  // Camera/Upload state
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [uploadingId, setUploadingId] = useState(null)
  const [uploadProgress, setUploadProgress] = useState(0)
  const fileInputRef = useRef(null)
  const [previewImage, setPreviewImage] = useState(null)
  const [filterStatus, setFilterStatus] = useState('pending')

  useEffect(() => {
    fetchClasses()
    fetchEnrollments()
  }, [])

  useEffect(() => {
    if (selectedClass) {
      fetchStudents()
    }
  }, [selectedClass])

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

  const fetchStudents = async () => {
    try {
      const response = await classAPI.getClassStudents(selectedClass)
      setStudents(response.data)
    } catch (err) {
      setError('Failed to load students')
    }
  }

  const fetchEnrollments = async () => {
    try {
      const response = await enrollmentAPI.getEnrollments()
      setEnrollments(response.data)
    } catch (err) {
      setError('Failed to load enrollments')
    }
  }

  const getStatusBadge = (status) => {
    const statusMap = {
      pending: { bg: 'bg-yellow-100', text: 'text-yellow-800', label: '⏳ Pending' },
      processing: { bg: 'bg-blue-100', text: 'text-blue-800', label: '⚙️ Processing' },
      completed: { bg: 'bg-green-100', text: 'text-green-800', label: '✓ Completed' },
      failed: { bg: 'bg-red-100', text: 'text-red-800', label: '✗ Failed' },
      re_enroll: { bg: 'bg-orange-100', text: 'text-orange-800', label: '🔄 Re-enroll' },
    }
    return statusMap[status] || { bg: 'bg-gray-100', text: 'text-gray-800', label: status }
  }

  const handleFileSelect = (e) => {
    const file = e.target.files[0]
    if (file) {
      const reader = new FileReader()
      reader.onload = (event) => {
        setPreviewImage(event.target.result)
      }
      reader.readAsDataURL(file)
    }
  }

  const handleUpload = async () => {
    if (!fileInputRef.current?.files[0]) {
      setError('Please select an image')
      return
    }

    if (!uploadingId) {
      setError('Please select a student')
      return
    }

    try {
      setLoading(true)
      const formData = new FormData()
      formData.append('image', fileInputRef.current.files[0])

      await enrollmentAPI.uploadStudentImage(uploadingId, formData)
      
      setSuccessMsg('Image uploaded successfully! Processing facial embedding...')
      setShowUploadModal(false)
      setPreviewImage(null)
      setUploadProgress(0)
      fileInputRef.current.value = ''
      
      setTimeout(() => {
        fetchEnrollments()
      }, 1000)
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to upload image')
    } finally {
      setLoading(false)
    }
  }

  const openUploadModal = (enrollmentId) => {
    setUploadingId(enrollmentId)
    setShowUploadModal(true)
  }

  const filteredEnrollments = filterStatus === 'all' 
    ? enrollments 
    : enrollments.filter(e => e.status === filterStatus)

  const stats = {
    total: enrollments.length,
    pending: enrollments.filter(e => e.status === 'pending').length,
    completed: enrollments.filter(e => e.status === 'completed').length,
    failed: enrollments.filter(e => e.status === 'failed').length,
  }

  return (
    <div className="flex h-screen bg-gray-50">
      <Navigation currentPage="/enrollment" />

      <div className="flex-1 flex flex-col overflow-hidden">
        <Header title="Enrollment Hub - Student Registration" />

        <main className="flex-1 overflow-auto p-6">
          <div className="max-w-7xl mx-auto">
            {error && <Alert type="error" message={error} onClose={() => setError('')} />}
            {successMsg && <Alert type="success" message={successMsg} onClose={() => setSuccessMsg('')} />}

            {/* Statistics */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-white p-4 rounded-lg shadow border-l-4 border-gray-400">
                <p className="text-gray-600 text-sm">Total Enrollments</p>
                <p className="text-2xl font-bold text-gray-700 mt-1">{stats.total}</p>
              </div>
              <div className="bg-white p-4 rounded-lg shadow border-l-4 border-yellow-500">
                <p className="text-gray-600 text-sm">Pending</p>
                <p className="text-2xl font-bold text-yellow-600 mt-1">{stats.pending}</p>
              </div>
              <div className="bg-white p-4 rounded-lg shadow border-l-4 border-green-500">
                <p className="text-gray-600 text-sm">Completed</p>
                <p className="text-2xl font-bold text-green-600 mt-1">{stats.completed}</p>
              </div>
              <div className="bg-white p-4 rounded-lg shadow border-l-4 border-red-500">
                <p className="text-gray-600 text-sm">Failed</p>
                <p className="text-2xl font-bold text-red-600 mt-1">{stats.failed}</p>
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
                  <label className="block text-sm font-medium text-gray-700 mb-1">Filter by Status</label>
                  <select
                    value={filterStatus}
                    onChange={(e) => setFilterStatus(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="all">All</option>
                    <option value="pending">Pending</option>
                    <option value="processing">Processing</option>
                    <option value="completed">Completed</option>
                    <option value="failed">Failed</option>
                    <option value="re_enroll">Re-enroll</option>
                  </select>
                </div>

                <div className="flex items-end">
                  <button
                    onClick={fetchEnrollments}
                    className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition font-semibold"
                  >
                    Refresh
                  </button>
                </div>
              </div>
            </div>

            {/* Enrollments Table */}
            <div className="bg-white rounded-lg shadow">
              <div className="p-6 border-b border-gray-200">
                <h2 className="text-lg font-bold text-gray-900">Enrollment Records</h2>
              </div>

              {loading && filteredEnrollments.length === 0 ? (
                <div className="p-6 text-center">
                  <p className="text-gray-600">Loading enrollments...</p>
                </div>
              ) : filteredEnrollments.length === 0 ? (
                <div className="p-6 text-center">
                  <p className="text-gray-600">No enrollment records found</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50 border-b">
                      <tr>
                        <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Student ID</th>
                        <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Status</th>
                        <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Academic Year</th>
                        <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Enrollment Date</th>
                        <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Quality Score</th>
                        <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Embedding</th>
                        <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredEnrollments.map((enrollment) => {
                        const statusStyle = getStatusBadge(enrollment.status)
                        const isUploadable = ['pending', 'failed', 're_enroll'].includes(enrollment.status)
                        return (
                          <tr key={enrollment.id} className="border-b hover:bg-gray-50">
                            <td className="px-6 py-3 text-gray-900 font-medium">{enrollment.student_id}</td>
                            <td className="px-6 py-3">
                              <span className={`px-3 py-1 rounded-full text-xs font-semibold ${statusStyle.bg} ${statusStyle.text}`}>
                                {statusStyle.label}
                              </span>
                            </td>
                            <td className="px-6 py-3 text-gray-600">{enrollment.academic_year}</td>
                            <td className="px-6 py-3 text-gray-600 text-sm">
                              {new Date(enrollment.enrollment_date).toLocaleDateString()}
                            </td>
                            <td className="px-6 py-3 text-gray-600">
                              {enrollment.quality_score ? `${(enrollment.quality_score * 100).toFixed(1)}%` : '-'}
                            </td>
                            <td className="px-6 py-3 text-gray-600 text-sm">
                              <span className={enrollment.embedding_generated ? 'text-green-600 font-semibold' : 'text-red-600'}>
                                {enrollment.embedding_generated ? '✓ Generated' : '✗ Not Generated'}
                              </span>
                            </td>
                            <td className="px-6 py-3">
                              {isUploadable && (
                                <button
                                  onClick={() => openUploadModal(enrollment.id)}
                                  className="px-3 py-1 bg-blue-500 text-white text-xs rounded hover:bg-blue-600 transition font-semibold"
                                >
                                  📷 Upload Image
                                </button>
                              )}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Instructions */}
            <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h3 className="font-semibold text-blue-900 mb-2">📸 How to Enroll Students</h3>
              <ul className="text-sm text-blue-800 space-y-1">
                <li>1. Select the class and student from the list</li>
                <li>2. Click "Upload Image" to capture or upload a clear facial image</li>
                <li>3. The system will process the image and generate a facial embedding (512-d ArcFace)</li>
                <li>4. Once completed, the student is ready for attendance recognition</li>
              </ul>
            </div>
          </div>
        </main>
      </div>

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-lg max-w-md w-full p-6">
            <h3 className="text-lg font-bold text-gray-900 mb-4">Upload Student Photo</h3>

            {/* Preview */}
            {previewImage && (
              <div className="mb-4">
                <img src={previewImage} alt="Preview" className="w-full h-64 object-cover rounded-lg" />
              </div>
            )}

            {/* File Input */}
            <div className="mb-4">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleFileSelect}
                className="w-full"
              />
              <p className="text-xs text-gray-600 mt-2">Recommended: JPG/PNG, clear frontal face</p>
            </div>

            {/* Progress */}
            {uploadProgress > 0 && (
              <div className="mb-4">
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all"
                    style={{ width: `${uploadProgress}%` }}
                  ></div>
                </div>
                <p className="text-xs text-gray-600 mt-1">{uploadProgress}%</p>
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3">
              <button
                onClick={() => setShowUploadModal(false)}
                className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition"
              >
                Cancel
              </button>
              <button
                onClick={handleUpload}
                disabled={loading}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50 font-semibold"
              >
                {loading ? 'Uploading...' : 'Upload'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default EnrollmentHub
