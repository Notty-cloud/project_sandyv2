import React, { useState, useEffect, useRef, useCallback } from 'react'
import Header from '../components/Header'
import Navigation from '../components/Navigation'
import Alert from '../components/Alert'
import { enrollmentAPI, studentAPI, classAPI } from '../services/api'
import { authService } from '../services/auth'

// ─── Camera hook ──────────────────────────────────────────────────────────────
function useCamera() {
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const streamRef = useRef(null)
  const [ready, setReady] = useState(false)
  const [error, setError] = useState('')

  const start = useCallback(async () => {
    setError('')
    setReady(false)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } },
      })
      streamRef.current = stream
      const video = videoRef.current
      if (video) {
        video.srcObject = stream
        video.addEventListener('loadedmetadata', () => setReady(true), { once: true })
        video.play().catch(() => {})
      }
    } catch (err) {
      setError('Camera unavailable: ' + (err.message || 'Permission denied'))
    }
  }, [])

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    setReady(false)
  }, [])

  const capture = useCallback(() => {
    return new Promise((resolve) => {
      const video = videoRef.current
      const canvas = canvasRef.current
      if (!video || !canvas) return resolve(null)
      canvas.width = video.videoWidth || 640
      canvas.height = video.videoHeight || 480
      canvas.getContext('2d').drawImage(video, 0, 0)
      const preview = canvas.toDataURL('image/jpeg', 0.92)
      canvas.toBlob((blob) => resolve(blob ? { blob, preview } : null), 'image/jpeg', 0.92)
    })
  }, [])

  useEffect(() => () => stop(), [stop])

  return { videoRef, canvasRef, ready, error, start, stop, capture }
}

// ─── Viewfinder component ──────────────────────────────────────────────────────
function Viewfinder({ videoRef, canvasRef, ready, error, onCapture, captureLabel = 'Take Photo' }) {
  return (
    <div>
      {error && (
        <p className="text-red-500 text-sm text-center mb-2 bg-red-50 p-2 rounded-lg">{error}</p>
      )}
      <div className="relative bg-black rounded-xl overflow-hidden" style={{ paddingTop: '75%' }}>
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="absolute inset-0 w-full h-full object-cover"
        />
        <canvas ref={canvasRef} className="hidden" />
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none" style={{ paddingTop: '5%' }}>
          <div className="border-2 border-white rounded-full opacity-40" style={{ width: '50%', paddingTop: '50%' }} />
        </div>
        {!ready && !error && (
          <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-50">
            <p className="text-white text-sm animate-pulse">Starting camera…</p>
          </div>
        )}
      </div>
      <button
        onClick={onCapture}
        disabled={!ready}
        className="mt-3 w-full py-3 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700 disabled:opacity-40 transition text-sm"
      >
        {captureLabel}
      </button>
      <p className="text-xs text-gray-400 text-center mt-1">
        Centre your face in the circle, then click the button
      </p>
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────
const EnrollmentHub = () => {
  const [students, setStudents] = useState([])
  const [classes, setClasses] = useState([])
  const [selectedClass, setSelectedClass] = useState('')
  const [enrollments, setEnrollments] = useState([])
  const [filterStatus, setFilterStatus] = useState('all')
  const [pageError, setPageError] = useState('')
  const [pageSuccess, setPageSuccess] = useState('')

  // Modal phases: 'enroll' | 'enrolled' | 'verify' | 'verified'
  const [phase, setPhase] = useState('enroll')
  const [showModal, setShowModal] = useState(false)
  const [enrollingStudent, setEnrollingStudent] = useState(null)

  // Enroll phase
  const enrollCam = useCamera()
  const [enrollMode, setEnrollMode] = useState('camera')   // 'camera' | 'file'
  const [enrollBlob, setEnrollBlob] = useState(null)
  const [enrollPreview, setEnrollPreview] = useState(null)
  const [academicYear, setAcademicYear] = useState(() => {
    const y = new Date().getFullYear()
    return new Date().getMonth() >= 6 ? `${y}-${y + 1}` : `${y - 1}-${y}`
  })
  const [enrollLoading, setEnrollLoading] = useState(false)
  const [enrollError, setEnrollError] = useState('')
  const enrollFileRef = useRef(null)

  // Result after enrollment
  const [enrollResult, setEnrollResult] = useState(null)   // { quality_score, embedding_version }

  // Verify phase
  const verifyCam = useCamera()
  const [verifyMode, setVerifyMode] = useState('camera')
  const [verifyBlob, setVerifyBlob] = useState(null)
  const [verifyPreview, setVerifyPreview] = useState(null)
  const [verifyLoading, setVerifyLoading] = useState(false)
  const [verifyError, setVerifyError] = useState('')
  const [verifyResult, setVerifyResult] = useState(null)   // { match, confidence }
  const verifyFileRef = useRef(null)

  // ── Data fetching ────────────────────────────────────────────────────────────
  useEffect(() => {
    fetchClasses(); fetchStudents(); fetchEnrollments()
  }, [])

  useEffect(() => { if (selectedClass) fetchStudents() }, [selectedClass])

  const fetchClasses = async () => {
    try {
      const res = await classAPI.getClasses()
      setClasses(Array.isArray(res.data?.results ?? res.data) ? (res.data?.results ?? res.data) : [])
    } catch { setPageError('Failed to load classes') }
  }

  const fetchStudents = async () => {
    try {
      const res = await studentAPI.getAllStudents()
      const data = res.data?.results ?? res.data
      setStudents(Array.isArray(data) ? data : [])
    } catch { setPageError('Failed to load students') }
  }

  const fetchEnrollments = async () => {
    try {
      const res = await enrollmentAPI.getEnrollments()
      const data = res.data?.results ?? res.data
      setEnrollments(Array.isArray(data) ? data : [])
    } catch { setPageError('Failed to load enrollments') }
  }

  // ── Modal open / close ───────────────────────────────────────────────────────
  const openModal = (student) => {
    setEnrollingStudent(student)
    setPhase('enroll')
    setEnrollBlob(null); setEnrollPreview(null); setEnrollError('')
    setEnrollMode('camera')
    setVerifyBlob(null); setVerifyPreview(null); setVerifyError('')
    setVerifyMode('camera')
    setEnrollResult(null); setVerifyResult(null)
    setShowModal(true)
  }

  const closeModal = () => {
    enrollCam.stop(); verifyCam.stop()
    setShowModal(false)
  }

  // Start cameras when phase changes
  useEffect(() => {
    if (!showModal) return
    if (phase === 'enroll' && enrollMode === 'camera' && !enrollPreview) enrollCam.start()
    if (phase === 'verify' && verifyMode === 'camera' && !verifyPreview) verifyCam.start()
    return () => {
      if (phase === 'enroll') enrollCam.stop()
      if (phase === 'verify') verifyCam.stop()
    }
  }, [showModal, phase, enrollMode, verifyMode]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Enroll handlers ──────────────────────────────────────────────────────────
  const handleEnrollCapture = async () => {
    const result = await enrollCam.capture()
    if (!result) return
    setEnrollBlob(result.blob)
    setEnrollPreview(result.preview)
    enrollCam.stop()
  }

  const handleEnrollFileSelect = (e) => {
    const file = e.target.files[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => { setEnrollPreview(ev.target.result); setEnrollBlob(file) }
    reader.readAsDataURL(file)
  }

  const handleEnrollRetake = () => {
    setEnrollBlob(null); setEnrollPreview(null)
    enrollCam.start()
  }

  const handleEnroll = async () => {
    if (!enrollBlob) return setEnrollError('Please capture or select a photo first.')
    if (!academicYear.trim()) return setEnrollError('Academic year is required.')

    const userData = authService.getUserData()
    const enrolledById = userData?.id || userData?.admin_id
    if (!enrolledById) return setEnrollError('Session expired — please sign in again.')

    const imageFile = enrollBlob instanceof File
      ? enrollBlob
      : new File([enrollBlob], 'capture.jpg', { type: 'image/jpeg' })

    const formData = new FormData()
    formData.append('image', imageFile)
    formData.append('academic_year', academicYear.trim())
    formData.append('enrolled_by', enrolledById)

    try {
      setEnrollLoading(true)
      setEnrollError('')
      const res = await enrollmentAPI.uploadStudentImage(enrollingStudent.id, formData)
      setEnrollResult({
        quality_score: res.data.quality_score,
        embedding_version: res.data.embedding_version,
        message: res.data.message,
      })
      setPhase('enrolled')
      fetchEnrollments()
    } catch (err) {
      const d = err.response?.data
      setEnrollError(d?.image || d?.detail || d?.message || 'Enrollment failed. Please try again.')
    } finally {
      setEnrollLoading(false)
    }
  }

  // ── Verify handlers ──────────────────────────────────────────────────────────
  const handleVerifyCapture = async () => {
    const result = await verifyCam.capture()
    if (!result) return
    setVerifyBlob(result.blob)
    setVerifyPreview(result.preview)
    verifyCam.stop()
  }

  const handleVerifyFileSelect = (e) => {
    const file = e.target.files[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => { setVerifyPreview(ev.target.result); setVerifyBlob(file) }
    reader.readAsDataURL(file)
  }

  const handleVerifyRetake = () => {
    setVerifyBlob(null); setVerifyPreview(null)
    verifyCam.start()
  }

  const handleVerify = async () => {
    if (!verifyBlob) return setVerifyError('Please capture or select a photo first.')

    const userData = authService.getUserData()
    const tenantId = userData?.tenant_id
    if (!tenantId) return setVerifyError('Session expired — please sign in again.')

    const imageFile = verifyBlob instanceof File
      ? verifyBlob
      : new File([verifyBlob], 'verify.jpg', { type: 'image/jpeg' })

    const formData = new FormData()
    formData.append('image', imageFile)
    formData.append('tenant_id', tenantId)
    formData.append('threshold', '0.3')  // Low threshold so we always get a score back

    try {
      setVerifyLoading(true)
      setVerifyError('')
      const res = await studentAPI.identifyStudent(formData)
      setVerifyResult({ match: res.data.match, confidence: res.data.confidence })
    } catch (err) {
      const d = err.response?.data
      if (err.response?.status === 404) {
        // No match above threshold — still show the score
        setVerifyResult({ match: null, confidence: d?.confidence ?? 0 })
      } else {
        setVerifyError(d?.error || d?.detail || 'Verification failed. Please try again.')
      }
    } finally {
      setVerifyLoading(false)
      setPhase('verified')
    }
  }

  // ── Helpers ──────────────────────────────────────────────────────────────────
  const getStudentEnrollment = (studentId) => enrollments.find((e) => e.student === studentId)

  const statusStyle = (s) => ({
    pending:  { bg: 'bg-yellow-100', text: 'text-yellow-800', label: 'Pending' },
    enrolled: { bg: 'bg-green-100',  text: 'text-green-800',  label: 'Enrolled' },
    failed:   { bg: 'bg-red-100',    text: 'text-red-800',    label: 'Failed' },
    expired:  { bg: 'bg-gray-100',   text: 'text-gray-700',   label: 'Expired' },
  }[s] || { bg: 'bg-gray-100', text: 'text-gray-500', label: 'Not Enrolled' })

  const filteredEnrollments = filterStatus === 'all'
    ? enrollments
    : enrollments.filter((e) => e.status === filterStatus)

  const stats = {
    total:    enrollments.length,
    pending:  enrollments.filter((e) => e.status === 'pending').length,
    enrolled: enrollments.filter((e) => e.status === 'enrolled').length,
    failed:   enrollments.filter((e) => e.status === 'failed').length,
  }

  // ── Render ───────────────────────────────────────────────────────────────────
  return (
    <div className="flex h-screen bg-gray-50">
      <Navigation currentPage="/enrollment" />

      <div className="flex-1 flex flex-col overflow-hidden">
        <Header title="Enrollment Hub — Student Registration" />

        <main className="flex-1 overflow-auto p-6">
          <div className="max-w-7xl mx-auto">
            {pageError  && <Alert type="error"   message={pageError}   onClose={() => setPageError('')} />}
            {pageSuccess && <Alert type="success" message={pageSuccess} onClose={() => setPageSuccess('')} />}

            {/* Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              {[
                { label: 'Total',    value: stats.total,    border: 'border-gray-400',   text: 'text-gray-700'   },
                { label: 'Pending',  value: stats.pending,  border: 'border-yellow-500', text: 'text-yellow-600' },
                { label: 'Enrolled', value: stats.enrolled, border: 'border-green-500',  text: 'text-green-600'  },
                { label: 'Failed',   value: stats.failed,   border: 'border-red-500',    text: 'text-red-600'    },
              ].map(({ label, value, border, text }) => (
                <div key={label} className={`bg-white p-4 rounded-lg shadow border-l-4 ${border}`}>
                  <p className="text-gray-500 text-sm">{label}</p>
                  <p className={`text-2xl font-bold mt-1 ${text}`}>{value}</p>
                </div>
              ))}
            </div>

            {/* Student Panel */}
            <div className="bg-white rounded-lg shadow mb-6">
              <div className="p-5 border-b border-gray-200 flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-lg font-bold text-gray-900">Students</h2>
                <div className="flex items-center gap-3">
                  <select
                    value={selectedClass}
                    onChange={(e) => setSelectedClass(e.target.value)}
                    className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
                  >
                    <option value="">All Classes</option>
                    {classes.map((cls) => (
                      <option key={cls.id} value={cls.id}>
                        {cls.class_name || `${cls.grade}-${cls.section}`}
                      </option>
                    ))}
                  </select>
                  <button onClick={() => { fetchStudents(); fetchEnrollments() }}
                    className="px-3 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm hover:bg-gray-200 transition">
                    Refresh
                  </button>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      {['Name', 'Student ID', 'Grade', 'Enrollment', 'Embedding', 'Action'].map((h) => (
                        <th key={h} className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {students.length === 0 ? (
                      <tr><td colSpan={6} className="px-6 py-10 text-center text-gray-400">No students found</td></tr>
                    ) : students.map((student) => {
                      const enr = getStudentEnrollment(student.id)
                      const style = statusStyle(enr?.status)
                      const isEnrolled = enr?.status === 'enrolled'
                      return (
                        <tr key={student.id} className="hover:bg-gray-50 transition">
                          <td className="px-6 py-3 font-medium text-gray-900">{student.name}</td>
                          <td className="px-6 py-3 text-gray-500 text-sm">{student.student_id}</td>
                          <td className="px-6 py-3 text-gray-500 text-sm">{student.grade}{student.section ? `-${student.section}` : ''}</td>
                          <td className="px-6 py-3">
                            <span className={`px-2 py-1 rounded-full text-xs font-semibold ${style.bg} ${style.text}`}>
                              {style.label}
                            </span>
                          </td>
                          <td className="px-6 py-3 text-sm">
                            {enr?.embedding_generated
                              ? <span className="text-green-600 font-medium">✓ Ready</span>
                              : <span className="text-gray-400">—</span>}
                          </td>
                          <td className="px-6 py-3">
                            <button onClick={() => openModal(student)}
                              className={`px-3 py-1 text-xs rounded font-semibold transition ${isEnrolled
                                ? 'bg-orange-100 text-orange-700 hover:bg-orange-200'
                                : 'bg-blue-600 text-white hover:bg-blue-700'}`}>
                              {isEnrolled ? '🔄 Re-enroll' : '📷 Enroll'}
                            </button>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Enrollment Records */}
            <div className="bg-white rounded-lg shadow">
              <div className="p-5 border-b border-gray-200 flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-lg font-bold text-gray-900">Enrollment Records</h2>
                <div className="flex items-center gap-3">
                  <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}
                    className="px-3 py-2 border border-gray-300 rounded-lg text-sm">
                    <option value="all">All Statuses</option>
                    <option value="pending">Pending</option>
                    <option value="enrolled">Enrolled</option>
                    <option value="failed">Failed</option>
                    <option value="expired">Expired</option>
                  </select>
                  <button onClick={fetchEnrollments}
                    className="px-3 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 transition">
                    Refresh
                  </button>
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      {['Student', 'Status', 'Academic Year', 'Date', 'Quality Score', 'Embedding'].map((h) => (
                        <th key={h} className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {filteredEnrollments.length === 0 ? (
                      <tr><td colSpan={6} className="px-6 py-10 text-center text-gray-400">No enrollment records</td></tr>
                    ) : filteredEnrollments.map((e) => {
                      const s = statusStyle(e.status)
                      return (
                        <tr key={e.id} className="hover:bg-gray-50 transition">
                          <td className="px-6 py-3 font-medium text-gray-900">{e.student_name || '—'}</td>
                          <td className="px-6 py-3">
                            <span className={`px-2 py-1 rounded-full text-xs font-semibold ${s.bg} ${s.text}`}>{s.label}</span>
                          </td>
                          <td className="px-6 py-3 text-gray-500 text-sm">{e.academic_year}</td>
                          <td className="px-6 py-3 text-gray-500 text-sm">
                            {e.enrollment_date ? new Date(e.enrollment_date).toLocaleDateString() : '—'}
                          </td>
                          <td className="px-6 py-3 text-sm font-medium">
                            {e.quality_score != null
                              ? <span className="text-blue-600">{(e.quality_score * 100).toFixed(1)}%</span>
                              : <span className="text-gray-400">—</span>}
                          </td>
                          <td className="px-6 py-3 text-sm">
                            {e.embedding_generated
                              ? <span className="text-green-600 font-semibold">✓ Generated</span>
                              : <span className="text-red-400">✗ Not yet</span>}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </main>
      </div>

      {/* ── Modal ── */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-60 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md max-h-screen overflow-y-auto">

            {/* Header */}
            <div className="p-5 border-b border-gray-200 flex items-start justify-between sticky top-0 bg-white rounded-t-2xl z-10">
              <div>
                <h3 className="text-lg font-bold text-gray-900">
                  {phase === 'enroll'   && 'Face Enrollment'}
                  {phase === 'enrolled' && 'Enrollment Complete'}
                  {phase === 'verify'   && 'Verify Recognition'}
                  {phase === 'verified' && 'Recognition Result'}
                </h3>
                {enrollingStudent && (
                  <p className="text-sm text-gray-500 mt-0.5">
                    {enrollingStudent.name} · {enrollingStudent.student_id}
                  </p>
                )}
              </div>
              <button onClick={closeModal}
                className="text-gray-400 hover:text-gray-600 text-2xl leading-none ml-4">
                &times;
              </button>
            </div>

            <div className="p-5">

              {/* ── PHASE 1: Enroll ── */}
              {phase === 'enroll' && (
                <>
                  {/* Mode toggle */}
                  <div className="flex gap-2 mb-4">
                    {['camera', 'file'].map((m) => (
                      <button key={m} onClick={() => {
                        if (m === 'file') { enrollCam.stop(); setEnrollBlob(null); setEnrollPreview(null) }
                        setEnrollMode(m)
                      }}
                        className={`flex-1 py-2 text-sm rounded-lg font-medium transition ${enrollMode === m
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
                        {m === 'camera' ? '📷 Camera' : 'Upload File'}
                      </button>
                    ))}
                  </div>

                  {/* Camera */}
                  {enrollMode === 'camera' && (
                    <div className="mb-4">
                      {enrollPreview ? (
                        <>
                          <img src={enrollPreview} alt="Captured" className="w-full rounded-xl" style={{ maxHeight: 280, objectFit: 'cover' }} />
                          <button onClick={handleEnrollRetake}
                            className="mt-2 w-full py-2 border border-gray-300 rounded-lg text-sm text-gray-700 hover:bg-gray-50 transition">
                            Retake Photo
                          </button>
                        </>
                      ) : (
                        <Viewfinder
                          videoRef={enrollCam.videoRef}
                          canvasRef={enrollCam.canvasRef}
                          ready={enrollCam.ready}
                          error={enrollCam.error}
                          onCapture={handleEnrollCapture}
                        />
                      )}
                    </div>
                  )}

                  {/* File upload */}
                  {enrollMode === 'file' && (
                    <div className="mb-4">
                      <label className="block w-full border-2 border-dashed border-gray-300 rounded-xl p-5 text-center cursor-pointer hover:border-blue-400 transition">
                        <p className="text-gray-500 text-sm mb-1">Click to select a photo</p>
                        <p className="text-gray-400 text-xs">JPG or PNG · clear frontal face</p>
                        <input ref={enrollFileRef} type="file" accept="image/*" onChange={handleEnrollFileSelect} className="hidden" />
                      </label>
                      {enrollPreview && (
                        <img src={enrollPreview} alt="Preview" className="mt-3 w-full rounded-xl" style={{ maxHeight: 200, objectFit: 'cover' }} />
                      )}
                    </div>
                  )}

                  {/* Academic year */}
                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-1">Academic Year</label>
                    <input type="text" value={academicYear} onChange={(e) => setAcademicYear(e.target.value)}
                      placeholder="e.g. 2024-2025"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                  </div>

                  {enrollError && (
                    <p className="text-red-500 text-sm mb-3 bg-red-50 p-2 rounded-lg">{enrollError}</p>
                  )}

                  <div className="flex gap-3">
                    <button onClick={closeModal}
                      className="flex-1 px-4 py-2.5 border border-gray-300 text-gray-700 rounded-xl text-sm hover:bg-gray-50 transition">
                      Cancel
                    </button>
                    <button onClick={handleEnroll}
                      disabled={enrollLoading || !enrollBlob}
                      className="flex-1 px-4 py-2.5 bg-green-600 text-white rounded-xl font-semibold text-sm hover:bg-green-700 disabled:opacity-50 transition">
                      {enrollLoading ? (
                        <span className="flex items-center justify-center gap-2">
                          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                          </svg>
                          Processing…
                        </span>
                      ) : 'Enroll Student'}
                    </button>
                  </div>
                </>
              )}

              {/* ── PHASE 2: Enrolled ── */}
              {phase === 'enrolled' && enrollResult && (
                <>
                  <div className="text-center mb-6">
                    <div className="text-5xl mb-3">✅</div>
                    <h4 className="text-xl font-bold text-green-700">Enrolled Successfully!</h4>
                    <p className="text-gray-500 text-sm mt-1">{enrollResult.message}</p>
                  </div>

                  {/* Enrollment details */}
                  <div className="bg-gray-50 rounded-xl p-4 mb-5 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Face Quality Score</span>
                      <div className="flex items-center gap-2">
                        <div className="w-24 bg-gray-200 rounded-full h-2">
                          <div className="bg-blue-500 h-2 rounded-full transition-all"
                            style={{ width: `${((enrollResult.quality_score || 0) * 100).toFixed(0)}%` }} />
                        </div>
                        <span className="text-sm font-bold text-blue-700">
                          {((enrollResult.quality_score || 0) * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Embedding Version</span>
                      <span className="text-sm font-bold text-gray-800">#{enrollResult.embedding_version}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Embedding Dimensions</span>
                      <span className="text-sm font-bold text-gray-800">512-D (Facenet512)</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Similarity Metric</span>
                      <span className="text-sm font-bold text-gray-800">Cosine Similarity</span>
                    </div>
                  </div>

                  <p className="text-sm text-gray-600 text-center mb-4">
                    Want to verify the recognition works? Scan the student's face again to see the cosine similarity score.
                  </p>

                  <div className="flex gap-3">
                    <button onClick={closeModal}
                      className="flex-1 px-4 py-2.5 border border-gray-300 text-gray-700 rounded-xl text-sm hover:bg-gray-50 transition">
                      Close
                    </button>
                    <button onClick={() => setPhase('verify')}
                      className="flex-1 px-4 py-2.5 bg-blue-600 text-white rounded-xl font-semibold text-sm hover:bg-blue-700 transition">
                      Test Recognition →
                    </button>
                  </div>
                </>
              )}

              {/* ── PHASE 3: Verify ── */}
              {phase === 'verify' && (
                <>
                  <p className="text-sm text-gray-600 mb-4 bg-blue-50 p-3 rounded-lg">
                    Scan <strong>{enrollingStudent?.name}</strong>'s face again. The system will compare it against the stored embedding and show the cosine similarity.
                  </p>

                  {/* Mode toggle */}
                  <div className="flex gap-2 mb-4">
                    {['camera', 'file'].map((m) => (
                      <button key={m} onClick={() => {
                        if (m === 'file') { verifyCam.stop(); setVerifyBlob(null); setVerifyPreview(null) }
                        setVerifyMode(m)
                      }}
                        className={`flex-1 py-2 text-sm rounded-lg font-medium transition ${verifyMode === m
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
                        {m === 'camera' ? '📷 Camera' : 'Upload File'}
                      </button>
                    ))}
                  </div>

                  {/* Camera */}
                  {verifyMode === 'camera' && (
                    <div className="mb-4">
                      {verifyPreview ? (
                        <>
                          <img src={verifyPreview} alt="Verification" className="w-full rounded-xl" style={{ maxHeight: 280, objectFit: 'cover' }} />
                          <button onClick={handleVerifyRetake}
                            className="mt-2 w-full py-2 border border-gray-300 rounded-lg text-sm text-gray-700 hover:bg-gray-50 transition">
                            Retake
                          </button>
                        </>
                      ) : (
                        <Viewfinder
                          videoRef={verifyCam.videoRef}
                          canvasRef={verifyCam.canvasRef}
                          ready={verifyCam.ready}
                          error={verifyCam.error}
                          onCapture={handleVerifyCapture}
                          captureLabel="Capture for Verification"
                        />
                      )}
                    </div>
                  )}

                  {/* File upload */}
                  {verifyMode === 'file' && (
                    <div className="mb-4">
                      <label className="block w-full border-2 border-dashed border-gray-300 rounded-xl p-5 text-center cursor-pointer hover:border-blue-400 transition">
                        <p className="text-gray-500 text-sm mb-1">Click to select a photo</p>
                        <input ref={verifyFileRef} type="file" accept="image/*" onChange={handleVerifyFileSelect} className="hidden" />
                      </label>
                      {verifyPreview && (
                        <img src={verifyPreview} alt="Preview" className="mt-3 w-full rounded-xl" style={{ maxHeight: 200, objectFit: 'cover' }} />
                      )}
                    </div>
                  )}

                  {verifyError && (
                    <p className="text-red-500 text-sm mb-3 bg-red-50 p-2 rounded-lg">{verifyError}</p>
                  )}

                  <div className="flex gap-3">
                    <button onClick={() => setPhase('enrolled')}
                      className="flex-1 px-4 py-2.5 border border-gray-300 text-gray-700 rounded-xl text-sm hover:bg-gray-50 transition">
                      ← Back
                    </button>
                    <button onClick={handleVerify}
                      disabled={verifyLoading || !verifyBlob}
                      className="flex-1 px-4 py-2.5 bg-blue-600 text-white rounded-xl font-semibold text-sm hover:bg-blue-700 disabled:opacity-50 transition">
                      {verifyLoading ? (
                        <span className="flex items-center justify-center gap-2">
                          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                          </svg>
                          Identifying…
                        </span>
                      ) : 'Run Identification'}
                    </button>
                  </div>
                </>
              )}

              {/* ── PHASE 4: Verified ── */}
              {phase === 'verified' && verifyResult && (
                <>
                  {/* Cosine similarity meter */}
                  <div className="text-center mb-5">
                    <p className="text-sm text-gray-500 mb-1">Cosine Similarity Score</p>
                    <div className="text-5xl font-black mb-1"
                      style={{ color: verifyResult.confidence >= 0.65 ? '#16a34a' : verifyResult.confidence >= 0.45 ? '#d97706' : '#dc2626' }}>
                      {verifyResult.confidence.toFixed(4)}
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-3 mt-2 mb-1">
                      <div className="h-3 rounded-full transition-all duration-700"
                        style={{
                          width: `${Math.min(verifyResult.confidence * 100, 100)}%`,
                          backgroundColor: verifyResult.confidence >= 0.65 ? '#16a34a' : verifyResult.confidence >= 0.45 ? '#d97706' : '#dc2626',
                        }} />
                    </div>
                    <div className="flex justify-between text-xs text-gray-400 px-1">
                      <span>0.0 — No match</span>
                      <span>0.65 — Threshold</span>
                      <span>1.0 — Perfect</span>
                    </div>
                  </div>

                  {/* Result card */}
                  <div className={`rounded-xl p-4 mb-5 ${verifyResult.match ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
                    {verifyResult.match ? (
                      <div className="flex items-start gap-3">
                        <span className="text-2xl">✅</span>
                        <div>
                          <p className="font-bold text-green-800">Match Confirmed</p>
                          <p className="text-green-700 text-sm mt-0.5">
                            Identified as <strong>{verifyResult.match.name}</strong> ({verifyResult.match.student_id})
                          </p>
                          <p className="text-green-600 text-xs mt-1">
                            Similarity {(verifyResult.confidence * 100).toFixed(2)}% — above the 65% recognition threshold
                          </p>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-start gap-3">
                        <span className="text-2xl">❌</span>
                        <div>
                          <p className="font-bold text-red-800">No Match</p>
                          <p className="text-red-700 text-sm mt-0.5">
                            Score {(verifyResult.confidence * 100).toFixed(2)}% is below the 65% recognition threshold.
                          </p>
                          <p className="text-red-600 text-xs mt-1">Try re-enrolling with a clearer, well-lit photo.</p>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Tech details */}
                  <div className="bg-gray-50 rounded-xl p-4 mb-5">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Recognition Details</p>
                    <div className="space-y-1.5 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-600">Algorithm</span>
                        <span className="font-medium text-gray-800">Cosine Similarity</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Embedding Model</span>
                        <span className="font-medium text-gray-800">Facenet512 (512-D)</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Recognition Threshold</span>
                        <span className="font-medium text-gray-800">0.65</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Score</span>
                        <span className={`font-bold ${verifyResult.confidence >= 0.65 ? 'text-green-600' : 'text-red-600'}`}>
                          {verifyResult.confidence.toFixed(4)} {verifyResult.confidence >= 0.65 ? '✓' : '✗'}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex gap-3">
                    <button onClick={() => setPhase('verify')}
                      className="flex-1 px-4 py-2.5 border border-gray-300 text-gray-700 rounded-xl text-sm hover:bg-gray-50 transition">
                      Try Again
                    </button>
                    <button onClick={closeModal}
                      className="flex-1 px-4 py-2.5 bg-blue-600 text-white rounded-xl font-semibold text-sm hover:bg-blue-700 transition">
                      Done
                    </button>
                  </div>
                </>
              )}

            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default EnrollmentHub
