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
    setError(''); setReady(false)
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
    streamRef.current = null; setReady(false)
  }, [])

  const capture = useCallback(() => new Promise((resolve) => {
    const video = videoRef.current; const canvas = canvasRef.current
    if (!video || !canvas) return resolve(null)
    canvas.width = video.videoWidth || 640; canvas.height = video.videoHeight || 480
    canvas.getContext('2d').drawImage(video, 0, 0)
    const preview = canvas.toDataURL('image/jpeg', 0.92)
    canvas.toBlob((blob) => resolve(blob ? { blob, preview } : null), 'image/jpeg', 0.92)
  }), [])

  useEffect(() => () => stop(), [stop])
  return { videoRef, canvasRef, ready, error, start, stop, capture }
}

// ─── Viewfinder ───────────────────────────────────────────────────────────────
function Viewfinder({ videoRef, canvasRef, ready, error, onCapture, label = 'Take Photo' }) {
  return (
    <div>
      {error && <p className="text-red-500 text-sm text-center mb-2 bg-red-50 p-2 rounded-lg">{error}</p>}
      <div className="relative bg-black rounded-xl overflow-hidden" style={{ paddingTop: '75%' }}>
        <video ref={videoRef} autoPlay playsInline muted className="absolute inset-0 w-full h-full object-cover" />
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
      <button onClick={onCapture} disabled={!ready}
        className="mt-3 w-full py-3 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700 disabled:opacity-40 transition text-sm">
        {label}
      </button>
      <p className="text-xs text-gray-400 text-center mt-1">Centre face in the circle, then click</p>
    </div>
  )
}

// ─── Enrollment Modal (shared between teacher and coordinator views) ───────────
function EnrollmentModal({ student, onClose, onEnrolled }) {
  const userData = authService.getUserData()

  // phases: enroll → enrolled → verify → verified
  const [phase, setPhase] = useState('enroll')
  const [enrollResult, setEnrollResult] = useState(null)
  const [verifyResult, setVerifyResult] = useState(null)

  // Enroll phase
  const enrollCam = useCamera()
  const [enrollMode, setEnrollMode] = useState('camera')
  const [enrollBlob, setEnrollBlob] = useState(null)
  const [enrollPreview, setEnrollPreview] = useState(null)
  const [enrollLoading, setEnrollLoading] = useState(false)
  const [enrollError, setEnrollError] = useState('')
  const enrollFileRef = useRef(null)
  const [academicYear] = useState(() => {
    const y = new Date().getFullYear()
    return new Date().getMonth() >= 6 ? `${y}-${y + 1}` : `${y - 1}-${y}`
  })

  // Verify phase
  const verifyCam = useCamera()
  const [verifyMode, setVerifyMode] = useState('camera')
  const [verifyBlob, setVerifyBlob] = useState(null)
  const [verifyPreview, setVerifyPreview] = useState(null)
  const [verifyLoading, setVerifyLoading] = useState(false)
  const [verifyError, setVerifyError] = useState('')
  const verifyFileRef = useRef(null)

  useEffect(() => {
    if (phase === 'enroll' && enrollMode === 'camera' && !enrollPreview) enrollCam.start()
    if (phase === 'verify' && verifyMode === 'camera' && !verifyPreview) verifyCam.start()
    return () => { enrollCam.stop(); verifyCam.stop() }
  }, [phase, enrollMode, verifyMode]) // eslint-disable-line react-hooks/exhaustive-deps

  const close = () => { enrollCam.stop(); verifyCam.stop(); onClose() }

  const handleEnrollCapture = async () => {
    const r = await enrollCam.capture(); if (!r) return
    setEnrollBlob(r.blob); setEnrollPreview(r.preview); enrollCam.stop()
  }
  const handleEnrollFile = (e) => {
    const f = e.target.files[0]; if (!f) return
    const reader = new FileReader()
    reader.onload = (ev) => { setEnrollPreview(ev.target.result); setEnrollBlob(f) }
    reader.readAsDataURL(f)
  }
  const handleEnrollRetake = () => { setEnrollBlob(null); setEnrollPreview(null); enrollCam.start() }

  const handleEnroll = async () => {
    if (!enrollBlob) return setEnrollError('Please capture or select a photo first.')
    const enrolledById = userData?.id || userData?.admin_id
    if (!enrolledById) return setEnrollError('Session expired — please sign in again.')

    const imageFile = enrollBlob instanceof File ? enrollBlob : new File([enrollBlob], 'capture.jpg', { type: 'image/jpeg' })
    const formData = new FormData()
    formData.append('image', imageFile)
    formData.append('academic_year', academicYear)
    formData.append('enrolled_by', enrolledById)

    try {
      setEnrollLoading(true); setEnrollError('')
      const res = await enrollmentAPI.uploadStudentImage(student.id, formData)
      setEnrollResult({ quality_score: res.data.quality_score, embedding_version: res.data.embedding_version, message: res.data.message })
      setPhase('enrolled')
      if (onEnrolled) onEnrolled()
    } catch (err) {
      const d = err.response?.data
      setEnrollError(d?.image || d?.detail || d?.message || 'Enrollment failed.')
    } finally { setEnrollLoading(false) }
  }

  const handleVerifyCapture = async () => {
    const r = await verifyCam.capture(); if (!r) return
    setVerifyBlob(r.blob); setVerifyPreview(r.preview); verifyCam.stop()
  }
  const handleVerifyFile = (e) => {
    const f = e.target.files[0]; if (!f) return
    const reader = new FileReader()
    reader.onload = (ev) => { setVerifyPreview(ev.target.result); setVerifyBlob(f) }
    reader.readAsDataURL(f)
  }
  const handleVerifyRetake = () => { setVerifyBlob(null); setVerifyPreview(null); verifyCam.start() }

  const handleVerify = async () => {
    if (!verifyBlob) return setVerifyError('Please capture or select a photo first.')
    const tenantId = userData?.tenant_id
    if (!tenantId) return setVerifyError('Session expired.')
    const imageFile = verifyBlob instanceof File ? verifyBlob : new File([verifyBlob], 'verify.jpg', { type: 'image/jpeg' })
    const formData = new FormData()
    formData.append('image', imageFile)
    formData.append('tenant_id', tenantId)
    formData.append('threshold', '0.3')
    try {
      setVerifyLoading(true); setVerifyError('')
      const res = await studentAPI.identifyStudent(formData)
      setVerifyResult({ match: res.data.match, confidence: res.data.confidence })
    } catch (err) {
      const d = err.response?.data
      if (err.response?.status === 404) setVerifyResult({ match: null, confidence: d?.confidence ?? 0 })
      else setVerifyError(d?.error || d?.detail || 'Verification failed.')
    } finally { setVerifyLoading(false); setPhase('verified') }
  }

  const phaseTitle = { enroll: 'Enrol Student', enrolled: 'Enrolment Complete', verify: 'Verify Recognition', verified: 'Recognition Result' }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-60 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md max-h-screen overflow-y-auto">
        {/* Header */}
        <div className="p-5 border-b border-gray-200 flex items-start justify-between sticky top-0 bg-white rounded-t-2xl z-10">
          <div>
            <h3 className="text-lg font-bold text-gray-900">{phaseTitle[phase]}</h3>
            <p className="text-sm text-gray-500 mt-0.5">{student.name} · {student.student_id}</p>
          </div>
          <button onClick={close} className="text-gray-400 hover:text-gray-600 text-2xl leading-none ml-4">&times;</button>
        </div>

        <div className="p-5">
          {/* ── Phase 1: Enrol ── */}
          {phase === 'enroll' && (
            <>
              <div className="flex gap-2 mb-4">
                {[['camera', '📷 Live Camera'], ['file', 'Existing Image']].map(([m, lbl]) => (
                  <button key={m} onClick={() => { if (m === 'file') { enrollCam.stop(); setEnrollBlob(null); setEnrollPreview(null) } setEnrollMode(m) }}
                    className={`flex-1 py-2 text-sm rounded-lg font-medium transition ${enrollMode === m ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
                    {lbl}
                  </button>
                ))}
              </div>

              {enrollMode === 'camera' && (
                <div className="mb-4">
                  {enrollPreview ? (
                    <>
                      <img src={enrollPreview} alt="Captured" className="w-full rounded-xl" style={{ maxHeight: 280, objectFit: 'cover' }} />
                      <button onClick={handleEnrollRetake} className="mt-2 w-full py-2 border border-gray-300 rounded-lg text-sm text-gray-700 hover:bg-gray-50 transition">Retake Photo</button>
                    </>
                  ) : (
                    <Viewfinder videoRef={enrollCam.videoRef} canvasRef={enrollCam.canvasRef} ready={enrollCam.ready} error={enrollCam.error} onCapture={handleEnrollCapture} />
                  )}
                </div>
              )}

              {enrollMode === 'file' && (
                <div className="mb-4">
                  <label className="block w-full border-2 border-dashed border-gray-300 rounded-xl p-5 text-center cursor-pointer hover:border-blue-400 transition">
                    <p className="text-gray-500 text-sm mb-1">Click to select a photo</p>
                    <p className="text-gray-400 text-xs">JPG or PNG · clear frontal face, good lighting</p>
                    <input ref={enrollFileRef} type="file" accept="image/*" onChange={handleEnrollFile} className="hidden" />
                  </label>
                  {enrollPreview && <img src={enrollPreview} alt="Preview" className="mt-3 w-full rounded-xl" style={{ maxHeight: 200, objectFit: 'cover' }} />}
                </div>
              )}

              {enrollError && <p className="text-red-500 text-sm mb-3 bg-red-50 p-2 rounded-lg">{enrollError}</p>}

              <div className="flex gap-3">
                <button onClick={close} className="flex-1 px-4 py-2.5 border border-gray-300 text-gray-700 rounded-xl text-sm hover:bg-gray-50 transition">Cancel</button>
                <button onClick={handleEnroll} disabled={enrollLoading || !enrollBlob}
                  className="flex-1 px-4 py-2.5 bg-green-600 text-white rounded-xl font-semibold text-sm hover:bg-green-700 disabled:opacity-50 transition">
                  {enrollLoading ? <span className="flex items-center justify-center gap-2"><svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/></svg>Processing…</span> : 'Enrol Student'}
                </button>
              </div>
            </>
          )}

          {/* ── Phase 2: Enrolled ── */}
          {phase === 'enrolled' && enrollResult && (
            <>
              <div className="text-center mb-5">
                <div className="text-5xl mb-3">✅</div>
                <h4 className="text-xl font-bold text-green-700">Enrolled Successfully!</h4>
                <p className="text-gray-500 text-sm mt-1">{enrollResult.message}</p>
              </div>
              <div className="bg-gray-50 rounded-xl p-4 mb-5 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Face Quality Score</span>
                  <div className="flex items-center gap-2">
                    <div className="w-24 bg-gray-200 rounded-full h-2">
                      <div className="bg-blue-500 h-2 rounded-full" style={{ width: `${((enrollResult.quality_score || 0) * 100).toFixed(0)}%` }} />
                    </div>
                    <span className="text-sm font-bold text-blue-700">{((enrollResult.quality_score || 0) * 100).toFixed(1)}%</span>
                  </div>
                </div>
                <div className="flex justify-between text-sm"><span className="text-gray-600">Embedding Version</span><span className="font-bold text-gray-800">#{enrollResult.embedding_version}</span></div>
                <div className="flex justify-between text-sm"><span className="text-gray-600">Model</span><span className="font-bold text-gray-800">Facenet512 (512-D)</span></div>
                <div className="flex justify-between text-sm"><span className="text-gray-600">Metric</span><span className="font-bold text-gray-800">Cosine Similarity</span></div>
              </div>
              <p className="text-sm text-gray-500 text-center mb-4">Scan the student's face again to verify the system can recognise them.</p>
              <div className="flex gap-3">
                <button onClick={close} className="flex-1 px-4 py-2.5 border border-gray-300 text-gray-700 rounded-xl text-sm hover:bg-gray-50 transition">Done</button>
                <button onClick={() => setPhase('verify')} className="flex-1 px-4 py-2.5 bg-blue-600 text-white rounded-xl font-semibold text-sm hover:bg-blue-700 transition">Test Recognition →</button>
              </div>
            </>
          )}

          {/* ── Phase 3: Verify ── */}
          {phase === 'verify' && (
            <>
              <p className="text-sm text-gray-600 mb-4 bg-blue-50 p-3 rounded-lg">Scan <strong>{student.name}</strong>'s face again to see the cosine similarity score.</p>
              <div className="flex gap-2 mb-4">
                {[['camera', '📷 Live Camera'], ['file', 'Existing Image']].map(([m, lbl]) => (
                  <button key={m} onClick={() => { if (m === 'file') { verifyCam.stop(); setVerifyBlob(null); setVerifyPreview(null) } setVerifyMode(m) }}
                    className={`flex-1 py-2 text-sm rounded-lg font-medium transition ${verifyMode === m ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
                    {lbl}
                  </button>
                ))}
              </div>
              {verifyMode === 'camera' && (
                <div className="mb-4">
                  {verifyPreview ? (
                    <>
                      <img src={verifyPreview} alt="Verify" className="w-full rounded-xl" style={{ maxHeight: 280, objectFit: 'cover' }} />
                      <button onClick={handleVerifyRetake} className="mt-2 w-full py-2 border border-gray-300 rounded-lg text-sm text-gray-700 hover:bg-gray-50 transition">Retake</button>
                    </>
                  ) : (
                    <Viewfinder videoRef={verifyCam.videoRef} canvasRef={verifyCam.canvasRef} ready={verifyCam.ready} error={verifyCam.error} onCapture={handleVerifyCapture} label="Capture for Verification" />
                  )}
                </div>
              )}
              {verifyMode === 'file' && (
                <div className="mb-4">
                  <label className="block w-full border-2 border-dashed border-gray-300 rounded-xl p-5 text-center cursor-pointer hover:border-blue-400 transition">
                    <p className="text-gray-500 text-sm mb-1">Click to select a photo</p>
                    <input ref={verifyFileRef} type="file" accept="image/*" onChange={handleVerifyFile} className="hidden" />
                  </label>
                  {verifyPreview && <img src={verifyPreview} alt="Preview" className="mt-3 w-full rounded-xl" style={{ maxHeight: 200, objectFit: 'cover' }} />}
                </div>
              )}
              {verifyError && <p className="text-red-500 text-sm mb-3 bg-red-50 p-2 rounded-lg">{verifyError}</p>}
              <div className="flex gap-3">
                <button onClick={() => setPhase('enrolled')} className="flex-1 px-4 py-2.5 border border-gray-300 text-gray-700 rounded-xl text-sm hover:bg-gray-50 transition">← Back</button>
                <button onClick={handleVerify} disabled={verifyLoading || !verifyBlob}
                  className="flex-1 px-4 py-2.5 bg-blue-600 text-white rounded-xl font-semibold text-sm hover:bg-blue-700 disabled:opacity-50 transition">
                  {verifyLoading ? <span className="flex items-center justify-center gap-2"><svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/></svg>Identifying…</span> : 'Run Identification'}
                </button>
              </div>
            </>
          )}

          {/* ── Phase 4: Verified ── */}
          {phase === 'verified' && verifyResult && (
            <>
              <div className="text-center mb-5">
                <p className="text-sm text-gray-500 mb-1">Cosine Similarity Score</p>
                <div className="text-5xl font-black mb-1" style={{ color: verifyResult.confidence >= 0.65 ? '#16a34a' : verifyResult.confidence >= 0.45 ? '#d97706' : '#dc2626' }}>
                  {verifyResult.confidence.toFixed(4)}
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3 mt-2 mb-1">
                  <div className="h-3 rounded-full transition-all duration-700" style={{ width: `${Math.min(verifyResult.confidence * 100, 100)}%`, backgroundColor: verifyResult.confidence >= 0.65 ? '#16a34a' : verifyResult.confidence >= 0.45 ? '#d97706' : '#dc2626' }} />
                </div>
                <div className="flex justify-between text-xs text-gray-400 px-1"><span>0.0 No match</span><span>0.65 Threshold</span><span>1.0 Perfect</span></div>
              </div>
              <div className={`rounded-xl p-4 mb-4 ${verifyResult.match ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
                {verifyResult.match ? (
                  <div className="flex items-start gap-3">
                    <span className="text-2xl">✅</span>
                    <div>
                      <p className="font-bold text-green-800">Match Confirmed</p>
                      <p className="text-green-700 text-sm mt-0.5">Identified as <strong>{verifyResult.match.name}</strong> ({verifyResult.match.student_id})</p>
                      <p className="text-green-600 text-xs mt-1">Score {(verifyResult.confidence * 100).toFixed(2)}% — above 65% threshold</p>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-start gap-3">
                    <span className="text-2xl">❌</span>
                    <div>
                      <p className="font-bold text-red-800">No Match</p>
                      <p className="text-red-700 text-sm mt-0.5">Score {(verifyResult.confidence * 100).toFixed(2)}% is below the 65% threshold.</p>
                      <p className="text-red-600 text-xs mt-1">Try re-enrolling with a clearer, well-lit photo.</p>
                    </div>
                  </div>
                )}
              </div>
              <div className="bg-gray-50 rounded-xl p-4 mb-4 space-y-1.5 text-sm">
                {[['Algorithm', 'Cosine Similarity'], ['Model', 'Facenet512 (512-D)'], ['Threshold', '0.65'], ['Score', `${verifyResult.confidence.toFixed(4)} ${verifyResult.confidence >= 0.65 ? '✓' : '✗'}`]].map(([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <span className="text-gray-600">{k}</span>
                    <span className={`font-bold ${k === 'Score' ? (verifyResult.confidence >= 0.65 ? 'text-green-600' : 'text-red-600') : 'text-gray-800'}`}>{v}</span>
                  </div>
                ))}
              </div>
              <div className="flex gap-3">
                <button onClick={() => { setVerifyBlob(null); setVerifyPreview(null); setPhase('verify') }}
                  className="flex-1 px-4 py-2.5 border border-gray-300 text-gray-700 rounded-xl text-sm hover:bg-gray-50 transition">Try Again</button>
                <button onClick={close} className="flex-1 px-4 py-2.5 bg-blue-600 text-white rounded-xl font-semibold text-sm hover:bg-blue-700 transition">Done</button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Student table (shared component) ─────────────────────────────────────────
function StudentTable({ students, enrollments, onEnroll }) {
  const getEnrollment = (id) => enrollments.find((e) => e.student === id)
  const statusStyle = (s) => ({
    pending:  { bg: 'bg-yellow-100', text: 'text-yellow-800', label: 'Pending' },
    enrolled: { bg: 'bg-green-100',  text: 'text-green-800',  label: 'Enrolled' },
    failed:   { bg: 'bg-red-100',    text: 'text-red-800',    label: 'Failed' },
    expired:  { bg: 'bg-gray-100',   text: 'text-gray-700',   label: 'Expired' },
  }[s] || { bg: 'bg-gray-100', text: 'text-gray-500', label: 'Not Enrolled' })

  if (students.length === 0)
    return <p className="text-center text-gray-400 py-8">No students found</p>

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b">
          <tr>
            {['Name', 'Student ID', 'Grade', 'Enrolment', 'Embedding', 'Action'].map((h) => (
              <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {students.map((student) => {
            const enr = getEnrollment(student.id)
            const style = statusStyle(enr?.status)
            const isEnrolled = enr?.status === 'enrolled'
            return (
              <tr key={student.id} className="hover:bg-gray-50 transition">
                <td className="px-4 py-3 font-medium text-gray-900">{student.name}</td>
                <td className="px-4 py-3 text-gray-500">{student.student_id}</td>
                <td className="px-4 py-3 text-gray-500">Gr.{student.grade}{student.section ? `-${student.section}` : ''}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 rounded-full text-xs font-semibold ${style.bg} ${style.text}`}>{style.label}</span>
                </td>
                <td className="px-4 py-3 text-sm">
                  {enr?.embedding_generated ? <span className="text-green-600 font-medium">✓ Ready</span> : <span className="text-gray-400">—</span>}
                </td>
                <td className="px-4 py-3">
                  <button onClick={() => onEnroll(student)}
                    className={`px-3 py-1 text-xs rounded font-semibold transition ${isEnrolled ? 'bg-orange-100 text-orange-700 hover:bg-orange-200' : 'bg-blue-600 text-white hover:bg-blue-700'}`}>
                    {isEnrolled ? '🔄 Re-enrol' : '📷 Enrol'}
                  </button>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────
const EnrollmentHub = () => {
  const userData = authService.getUserData()
  const isTeacher = userData?.role === 'teacher'

  const [pageError, setPageError] = useState('')
  const [pageSuccess, setPageSuccess] = useState('')

  // Shared data
  const [enrollments, setEnrollments] = useState([])
  const [modalStudent, setModalStudent] = useState(null)

  // Teacher-specific
  const [myClasses, setMyClasses] = useState([])
  const [selectedClass, setSelectedClass] = useState(null)
  const [classStudents, setClassStudents] = useState([])
  const [loadingStudents, setLoadingStudents] = useState(false)

  // Coordinator/Head Teacher
  const [allStudents, setAllStudents] = useState([])
  const [allClasses, setAllClasses] = useState([])
  const [filterClass, setFilterClass] = useState('')
  const [filterStatus, setFilterStatus] = useState('all')

  useEffect(() => {
    fetchEnrollments()
    if (isTeacher) {
      fetchMyClasses()
    } else {
      fetchAllStudents()
      fetchAllClasses()
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const fetchEnrollments = async () => {
    try {
      const res = await enrollmentAPI.getEnrollments()
      setEnrollments(res.data?.results ?? res.data ?? [])
    } catch { setEnrollments([]) }
  }

  // ── Teacher paths ────────────────────────────────────────────────────────────
  const fetchMyClasses = async () => {
    try {
      const res = await classAPI.getClasses({ teacher: userData.id })
      const data = res.data?.results ?? res.data ?? []
      setMyClasses(Array.isArray(data) ? data : [])
    } catch { setPageError('Failed to load your classes.') }
  }

  const selectClass = async (cls) => {
    setSelectedClass(cls)
    setLoadingStudents(true)
    try {
      const res = await studentAPI.getAllStudents({ grade: cls.grade, section: cls.section })
      const data = res.data?.results ?? res.data ?? []
      setClassStudents(Array.isArray(data) ? data : [])
    } catch { setPageError('Failed to load students for this class.') }
    finally { setLoadingStudents(false) }
  }

  // ── Coordinator/Head Teacher paths ───────────────────────────────────────────
  const fetchAllStudents = async () => {
    try {
      const res = await studentAPI.getAllStudents()
      setAllStudents(res.data?.results ?? res.data ?? [])
    } catch { setPageError('Failed to load students.') }
  }

  const fetchAllClasses = async () => {
    try {
      const res = await classAPI.getClasses()
      setAllClasses(res.data?.results ?? res.data ?? [])
    } catch {}
  }

  const onEnrolled = () => {
    fetchEnrollments()
    setPageSuccess('Student enrolled successfully!')
    if (isTeacher && selectedClass) selectClass(selectedClass)
  }

  // ── Filtered views for coordinator ───────────────────────────────────────────
  const displayedStudents = (() => {
    if (isTeacher) return classStudents
    let students = allStudents
    if (filterClass) {
      const cls = allClasses.find((c) => c.id === filterClass)
      if (cls) students = students.filter((s) => s.grade === cls.grade && s.section === cls.section)
    }
    return students
  })()

  const filteredEnrollments = filterStatus === 'all'
    ? enrollments : enrollments.filter((e) => e.status === filterStatus)

  const stats = {
    total: enrollments.length,
    enrolled: enrollments.filter((e) => e.status === 'enrolled').length,
    pending: enrollments.filter((e) => e.status === 'pending').length,
    failed: enrollments.filter((e) => e.status === 'failed').length,
  }

  // ─────────────────────────────────────────────────────────────────────────────
  return (
    <div className="flex h-screen bg-gray-50">
      <Navigation currentPage="/enrollment" />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header title={isTeacher ? 'Enrol Students — My Classes' : 'Enrolment Hub'} />
        <main className="flex-1 overflow-auto p-6">
          <div className="max-w-7xl mx-auto">
            {pageError   && <Alert type="error"   message={pageError}   onClose={() => setPageError('')} />}
            {pageSuccess && <Alert type="success" message={pageSuccess} onClose={() => setPageSuccess('')} />}

            {/* ── TEACHER VIEW ── */}
            {isTeacher && (
              <>
                {myClasses.length === 0 ? (
                  <div className="bg-white rounded-xl shadow p-10 text-center">
                    <p className="text-4xl mb-3">🏫</p>
                    <p className="text-lg font-semibold text-gray-700">No classes assigned yet</p>
                    <p className="text-sm text-gray-400 mt-1">Ask your coordinator to assign you to a class in the Class Management page.</p>
                  </div>
                ) : (
                  <>
                    {/* Class cards */}
                    {!selectedClass && (
                      <>
                        <p className="text-sm text-gray-500 mb-4">Select a class to view its students and enrol them.</p>
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
                          {myClasses.map((cls) => {
                            const classEnrolments = enrollments.filter((e) => {
                              const s = allStudents.find((st) => st.id === e.student)
                              return s?.grade === cls.grade && s?.section === cls.section
                            })
                            return (
                              <button key={cls.id} onClick={() => selectClass(cls)}
                                className="bg-white rounded-xl shadow p-5 text-left hover:shadow-md hover:border-blue-300 border-2 border-transparent transition">
                                <div className="flex items-start justify-between mb-3">
                                  <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs font-semibold rounded-full">{cls.subject}</span>
                                  <span className={`px-2 py-1 text-xs font-semibold rounded-full ${cls.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>{cls.is_active ? 'Active' : 'Inactive'}</span>
                                </div>
                                <p className="font-bold text-gray-900 text-base">{cls.class_name || `${cls.subject} — Grade ${cls.grade}${cls.section}`}</p>
                                <p className="text-sm text-gray-500 mt-0.5">Grade {cls.grade} · Section {cls.section}</p>
                                <p className="text-xs text-gray-400 mt-1">{cls.academic_year}</p>
                              </button>
                            )
                          })}
                        </div>
                      </>
                    )}

                    {/* Selected class → student list */}
                    {selectedClass && (
                      <div className="bg-white rounded-xl shadow">
                        <div className="p-5 border-b border-gray-200 flex items-center justify-between">
                          <div>
                            <button onClick={() => { setSelectedClass(null); setClassStudents([]) }}
                              className="text-blue-600 text-sm hover:underline mb-1 flex items-center gap-1">
                              ← My Classes
                            </button>
                            <h2 className="text-lg font-bold text-gray-900">{selectedClass.class_name}</h2>
                            <p className="text-sm text-gray-500">Grade {selectedClass.grade} · Section {selectedClass.section} · {selectedClass.academic_year}</p>
                          </div>
                          <button onClick={() => selectClass(selectedClass)}
                            className="px-3 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm hover:bg-gray-200 transition">Refresh</button>
                        </div>
                        {loadingStudents ? (
                          <p className="text-center text-gray-400 py-8">Loading students…</p>
                        ) : (
                          <StudentTable students={classStudents} enrollments={enrollments} onEnroll={setModalStudent} />
                        )}
                      </div>
                    )}
                  </>
                )}
              </>
            )}

            {/* ── COORDINATOR / HEAD TEACHER VIEW ── */}
            {!isTeacher && (
              <>
                {/* Stats */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                  {[
                    { label: 'Total',    value: stats.total,    border: 'border-gray-400',   text: 'text-gray-700'   },
                    { label: 'Enrolled', value: stats.enrolled, border: 'border-green-500',  text: 'text-green-600'  },
                    { label: 'Pending',  value: stats.pending,  border: 'border-yellow-500', text: 'text-yellow-600' },
                    { label: 'Failed',   value: stats.failed,   border: 'border-red-500',    text: 'text-red-600'    },
                  ].map(({ label, value, border, text }) => (
                    <div key={label} className={`bg-white p-4 rounded-lg shadow border-l-4 ${border}`}>
                      <p className="text-gray-500 text-sm">{label}</p>
                      <p className={`text-2xl font-bold mt-1 ${text}`}>{value}</p>
                    </div>
                  ))}
                </div>

                {/* Students panel */}
                <div className="bg-white rounded-lg shadow mb-6">
                  <div className="p-5 border-b border-gray-200 flex flex-wrap items-center justify-between gap-3">
                    <h2 className="text-lg font-bold text-gray-900">Students</h2>
                    <div className="flex items-center gap-3">
                      <select value={filterClass} onChange={(e) => setFilterClass(e.target.value)}
                        className="px-3 py-2 border border-gray-300 rounded-lg text-sm">
                        <option value="">All Classes</option>
                        {allClasses.map((c) => <option key={c.id} value={c.id}>{c.class_name || `${c.subject} Gr.${c.grade}${c.section}`}</option>)}
                      </select>
                      <button onClick={() => { fetchAllStudents(); fetchEnrollments() }}
                        className="px-3 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm hover:bg-gray-200 transition">Refresh</button>
                    </div>
                  </div>
                  <StudentTable students={displayedStudents} enrollments={enrollments} onEnroll={setModalStudent} />
                </div>

                {/* Enrollment records */}
                <div className="bg-white rounded-lg shadow">
                  <div className="p-5 border-b border-gray-200 flex flex-wrap items-center justify-between gap-3">
                    <h2 className="text-lg font-bold text-gray-900">Enrolment Records</h2>
                    <div className="flex items-center gap-3">
                      <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}
                        className="px-3 py-2 border border-gray-300 rounded-lg text-sm">
                        {['all','enrolled','pending','failed','expired'].map((s) => (
                          <option key={s} value={s}>{s === 'all' ? 'All Statuses' : s.charAt(0).toUpperCase() + s.slice(1)}</option>
                        ))}
                      </select>
                      <button onClick={fetchEnrollments} className="px-3 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 transition">Refresh</button>
                    </div>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50 border-b">
                        <tr>
                          {['Student','Status','Academic Year','Date','Quality','Embedding'].map((h) => (
                            <th key={h} className="px-5 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {filteredEnrollments.length === 0 ? (
                          <tr><td colSpan={6} className="px-5 py-8 text-center text-gray-400">No enrolment records</td></tr>
                        ) : filteredEnrollments.map((e) => {
                          const s = { enrolled: { bg:'bg-green-100',text:'text-green-800',label:'Enrolled' }, pending:{bg:'bg-yellow-100',text:'text-yellow-800',label:'Pending'}, failed:{bg:'bg-red-100',text:'text-red-800',label:'Failed'}, expired:{bg:'bg-gray-100',text:'text-gray-600',label:'Expired'} }[e.status] || {bg:'bg-gray-100',text:'text-gray-500',label:e.status}
                          return (
                            <tr key={e.id} className="hover:bg-gray-50 transition">
                              <td className="px-5 py-3 font-medium text-gray-900">{e.student_name || '—'}</td>
                              <td className="px-5 py-3"><span className={`px-2 py-1 rounded-full text-xs font-semibold ${s.bg} ${s.text}`}>{s.label}</span></td>
                              <td className="px-5 py-3 text-gray-500">{e.academic_year}</td>
                              <td className="px-5 py-3 text-gray-500 text-xs">{e.enrollment_date ? new Date(e.enrollment_date).toLocaleDateString() : '—'}</td>
                              <td className="px-5 py-3 text-sm font-medium">{e.quality_score != null ? <span className="text-blue-600">{(e.quality_score * 100).toFixed(1)}%</span> : <span className="text-gray-400">—</span>}</td>
                              <td className="px-5 py-3 text-sm">{e.embedding_generated ? <span className="text-green-600 font-semibold">✓ Generated</span> : <span className="text-red-400">✗ Not yet</span>}</td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              </>
            )}
          </div>
        </main>
      </div>

      {modalStudent && (
        <EnrollmentModal
          student={modalStudent}
          onClose={() => setModalStudent(null)}
          onEnrolled={onEnrolled}
        />
      )}
    </div>
  )
}

export default EnrollmentHub
