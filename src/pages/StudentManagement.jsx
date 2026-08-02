import React, { useState, useEffect, useRef } from 'react'
import Header from '../components/Header'
import Navigation from '../components/Navigation'
import Alert from '../components/Alert'
import { studentAPI } from '../services/api'
import { authService } from '../services/auth'

const GRADES = ['7', '8', '9', '10', '11', '12']
const SECTIONS = ['A', 'B', 'C', 'D', 'E']

function StudentModal({ student, onClose, onSaved }) {
  const user = authService.getUserData()
  const isEdit = !!student

  const [form, setForm] = useState({
    name: student?.name ?? '',
    student_id: student?.student_id ?? '',
    grade: student?.grade ?? '',
    section: student?.section ?? '',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const set = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.name.trim() || !form.student_id.trim() || !form.grade || !form.section) {
      return setError('All fields are required.')
    }
    setLoading(true)
    setError('')
    try {
      if (isEdit) {
        await studentAPI.updateStudent(student.id, form)
      } else {
        await studentAPI.createStudent({ ...form, tenant_id: user.tenant_id })
      }
      onSaved()
      onClose()
    } catch (err) {
      const d = err.response?.data
      setError(
        d?.student_id?.[0] ||
        d?.non_field_errors?.[0] ||
        d?.detail ||
        'Failed to save student.'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4"
      onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md"
        onClick={(e) => e.stopPropagation()}>
        <div className="p-5 border-b border-gray-200 flex items-center justify-between">
          <h3 className="text-lg font-bold text-gray-900">
            {isEdit ? 'Edit Student' : 'Add New Student'}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl leading-none">&times;</button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3">{error}</div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
            <input
              value={form.name}
              onChange={set('name')}
              placeholder="e.g. Jane Smith"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Student ID</label>
            <input
              value={form.student_id}
              onChange={set('student_id')}
              placeholder="e.g. STU-001"
              disabled={isEdit}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm disabled:bg-gray-50 disabled:text-gray-400"
            />
            {isEdit && <p className="text-xs text-gray-400 mt-1">Student ID cannot be changed after creation.</p>}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Grade</label>
              <select
                value={form.grade}
                onChange={set('grade')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              >
                <option value="">Select</option>
                {GRADES.map((g) => <option key={g} value={g}>{g}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Section</label>
              <select
                value={form.section}
                onChange={set('section')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              >
                <option value="">Select</option>
                {SECTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          </div>

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-xl text-sm hover:bg-gray-50 transition">
              Cancel
            </button>
            <button type="submit" disabled={loading}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-xl font-semibold text-sm hover:bg-blue-700 disabled:opacity-50 transition">
              {loading ? 'Saving…' : isEdit ? 'Save Changes' : 'Add Student'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─── CSV roster import ────────────────────────────────────────────────────────
// Always previews before writing: an import creates hundreds of records at once,
// and "undo" means deleting them by hand. The preview calls the same endpoint
// with dry_run, so what it reports is what the import will do.
function ImportCsvModal({ onClose, onImported }) {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const inputRef = useRef(null)

  const submit = async (dryRun) => {
    if (!file) return setError('Choose a CSV file first.')
    const formData = new FormData()
    formData.append('file', file)
    if (dryRun) formData.append('dry_run', 'true')

    try {
      setBusy(true); setError('')
      const res = await studentAPI.importStudentsCsv(formData)
      if (dryRun) {
        setPreview(res.data)
      } else {
        onImported(res.data)
        onClose()
      }
    } catch (err) {
      const data = err.response?.data
      setError(data?.file || data?.detail || 'Import failed.')
      setPreview(null)
    } finally { setBusy(false) }
  }

  const chooseFile = (e) => {
    setFile(e.target.files[0] || null)
    setPreview(null)
    setError('')
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-60 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-screen overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="p-5 border-b border-gray-200 flex items-start justify-between">
          <div>
            <h3 className="font-bold text-gray-900">Import Students from CSV</h3>
            <p className="text-xs text-gray-500 mt-0.5">Add a whole roster at once</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">×</button>
        </div>

        <div className="p-5 space-y-4">
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
            <p className="text-xs font-semibold text-gray-600 mb-1">Required header row</p>
            <code className="text-xs text-gray-800 block">student_id,name,grade,section</code>
            <p className="text-xs text-gray-500 mt-2">
              An optional <code>is_active</code> column is accepted. Extra columns are
              ignored, so a registry export can be used as-is.
            </p>
          </div>

          <input
            ref={inputRef}
            type="file"
            accept=".csv,text/csv"
            onChange={chooseFile}
            className="block w-full text-sm text-gray-600 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
          />

          {error && <p className="text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg p-3">{error}</p>}

          {preview && (
            <div className="border border-gray-200 rounded-lg overflow-hidden">
              <div className="px-4 py-3 bg-gray-50 border-b border-gray-200 flex gap-4 text-sm">
                <span className="text-green-700 font-semibold">{preview.would_create} will be added</span>
                {preview.skipped > 0 && (
                  <span className="text-amber-700 font-semibold">{preview.skipped} skipped</span>
                )}
              </div>

              {preview.preview?.length > 0 && (
                <table className="w-full text-xs">
                  <thead className="bg-gray-50 text-gray-500">
                    <tr>
                      <th className="px-3 py-1.5 text-left">ID</th>
                      <th className="px-3 py-1.5 text-left">Name</th>
                      <th className="px-3 py-1.5 text-left">Grade</th>
                      <th className="px-3 py-1.5 text-left">Section</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.preview.map((row) => (
                      <tr key={row.row} className="border-t border-gray-100">
                        <td className="px-3 py-1.5 font-medium text-gray-800">{row.student_id}</td>
                        <td className="px-3 py-1.5 text-gray-600">{row.name}</td>
                        <td className="px-3 py-1.5 text-gray-600">{row.grade}</td>
                        <td className="px-3 py-1.5 text-gray-600">{row.section}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              {preview.would_create > (preview.preview?.length ?? 0) && (
                <p className="px-3 py-2 text-xs text-gray-400 border-t border-gray-100">
                  …and {preview.would_create - preview.preview.length} more
                </p>
              )}

              {preview.errors?.length > 0 && (
                <div className="border-t border-gray-200 max-h-40 overflow-y-auto">
                  <p className="px-3 pt-2 text-xs font-semibold text-amber-700">Rows that will be skipped</p>
                  <ul className="px-3 pb-2 space-y-0.5">
                    {preview.errors.map((e, i) => (
                      <li key={i} className="text-xs text-amber-700">Row {e.row}: {e.error}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="p-5 border-t border-gray-200 flex gap-3">
          <button onClick={onClose}
            className="flex-1 py-2.5 border border-gray-300 rounded-xl text-sm font-semibold text-gray-700 hover:bg-gray-50 transition">
            Cancel
          </button>
          {!preview ? (
            <button onClick={() => submit(true)} disabled={busy || !file}
              className="flex-1 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-semibold hover:bg-blue-700 disabled:opacity-40 transition">
              {busy ? 'Checking…' : 'Preview'}
            </button>
          ) : (
            <button onClick={() => submit(false)} disabled={busy || preview.would_create === 0}
              className="flex-1 py-2.5 bg-green-600 text-white rounded-xl text-sm font-semibold hover:bg-green-700 disabled:opacity-40 transition">
              {busy ? 'Importing…' : `Import ${preview.would_create}`}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}


const StudentManagement = () => {
  const [students, setStudents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const [search, setSearch] = useState('')
  const [filterGrade, setFilterGrade] = useState('')
  const [filterSection, setFilterSection] = useState('')
  const [filterStatus, setFilterStatus] = useState('active')

  const [modalStudent, setModalStudent] = useState(undefined) // undefined=closed, null=new, object=edit
  const [showImport, setShowImport] = useState(false)

  const fetchStudents = async () => {
    setLoading(true)
    try {
      const res = await studentAPI.getAllStudents()
      setStudents(res.data?.results ?? res.data ?? [])
    } catch {
      setError('Failed to load students.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchStudents() }, [])

  const handleToggleActive = async (student) => {
    try {
      await studentAPI.updateStudent(student.id, { is_active: !student.is_active })
      setSuccess(`${student.name} ${student.is_active ? 'deactivated' : 'reactivated'}.`)
      fetchStudents()
    } catch {
      setError('Failed to update student status.')
    }
  }

  const filtered = students.filter((s) => {
    const matchSearch = !search ||
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      s.student_id.toLowerCase().includes(search.toLowerCase())
    const matchGrade = !filterGrade || s.grade === filterGrade
    const matchSection = !filterSection || s.section === filterSection
    const matchStatus = filterStatus === 'all' ||
      (filterStatus === 'active' && s.is_active) ||
      (filterStatus === 'inactive' && !s.is_active)
    return matchSearch && matchGrade && matchSection && matchStatus
  })

  return (
    <div className="flex h-screen bg-gray-50">
      <Navigation currentPage="/students" />

      <div className="flex-1 flex flex-col overflow-hidden">
        <Header title="Student Management" />

        <main className="flex-1 overflow-auto p-6">
          <div className="max-w-7xl mx-auto">
            {error   && <Alert type="error"   message={error}   onClose={() => setError('')} />}
            {success && <Alert type="success" message={success} onClose={() => setSuccess('')} />}

            {/* Stats row */}
            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="bg-white p-5 rounded-lg shadow border-l-4 border-blue-500">
                <p className="text-gray-500 text-sm">Total Students</p>
                <p className="text-3xl font-bold text-blue-600 mt-1">{students.length}</p>
              </div>
              <div className="bg-white p-5 rounded-lg shadow border-l-4 border-green-500">
                <p className="text-gray-500 text-sm">Active</p>
                <p className="text-3xl font-bold text-green-600 mt-1">{students.filter(s => s.is_active).length}</p>
              </div>
              <div className="bg-white p-5 rounded-lg shadow border-l-4 border-gray-400">
                <p className="text-gray-500 text-sm">Inactive</p>
                <p className="text-3xl font-bold text-gray-500 mt-1">{students.filter(s => !s.is_active).length}</p>
              </div>
            </div>

            {/* Toolbar */}
            <div className="bg-white rounded-lg shadow p-4 mb-6">
              <div className="flex flex-wrap gap-3 items-center justify-between">
                <div className="flex flex-wrap gap-3 flex-1">
                  <input
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Search by name or student ID…"
                    className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 min-w-[220px] flex-1"
                  />
                  <select value={filterGrade} onChange={(e) => setFilterGrade(e.target.value)}
                    className="px-3 py-2 border border-gray-300 rounded-lg text-sm">
                    <option value="">All Grades</option>
                    {GRADES.map((g) => <option key={g} value={g}>Grade {g}</option>)}
                  </select>
                  <select value={filterSection} onChange={(e) => setFilterSection(e.target.value)}
                    className="px-3 py-2 border border-gray-300 rounded-lg text-sm">
                    <option value="">All Sections</option>
                    {SECTIONS.map((s) => <option key={s} value={s}>Section {s}</option>)}
                  </select>
                  <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}
                    className="px-3 py-2 border border-gray-300 rounded-lg text-sm">
                    <option value="active">Active Only</option>
                    <option value="inactive">Inactive Only</option>
                    <option value="all">All</option>
                  </select>
                </div>
                {(user?.authorization_level ?? 0) >= 2 && (
                  <button
                    onClick={() => setShowImport(true)}
                    className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg text-sm font-semibold hover:bg-gray-50 transition whitespace-nowrap">
                    Import CSV
                  </button>
                )}
                <button
                  onClick={() => setModalStudent(null)}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 transition whitespace-nowrap">
                  + Add Student
                </button>
              </div>
            </div>

            {/* Table */}
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="p-4 border-b border-gray-200 flex items-center justify-between">
                <h2 className="font-bold text-gray-900">
                  {filtered.length} student{filtered.length !== 1 ? 's' : ''}
                  {(search || filterGrade || filterSection) ? ' matching filters' : ''}
                </h2>
                <button onClick={fetchStudents}
                  className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg text-sm hover:bg-gray-200 transition">
                  Refresh
                </button>
              </div>

              {loading ? (
                <div className="p-10 text-center text-gray-400">Loading students…</div>
              ) : filtered.length === 0 ? (
                <div className="p-10 text-center text-gray-400">
                  {students.length === 0 ? 'No students added yet. Click "Add Student" to get started.' : 'No students match your filters.'}
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 border-b">
                      <tr>
                        {['Name', 'Student ID', 'Grade', 'Section', 'Photos', 'Status', 'Actions'].map((h) => (
                          <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {filtered.map((s) => (
                        <tr key={s.id} className={`hover:bg-gray-50 transition ${!s.is_active ? 'opacity-50' : ''}`}>
                          <td className="px-4 py-3 font-medium text-gray-900">{s.name}</td>
                          <td className="px-4 py-3 text-gray-500 font-mono text-xs">{s.student_id}</td>
                          <td className="px-4 py-3 text-gray-600">Grade {s.grade}</td>
                          <td className="px-4 py-3 text-gray-600">{s.section}</td>
                          <td className="px-4 py-3">
                            <span className={`text-xs font-semibold px-2 py-1 rounded-full ${
                              (s.photo_count ?? 0) > 0
                                ? 'bg-green-100 text-green-700'
                                : 'bg-gray-100 text-gray-500'
                            }`}>
                              {s.photo_count ?? 0}/5
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                              s.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                            }`}>
                              {s.is_active ? 'Active' : 'Inactive'}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => setModalStudent(s)}
                                className="px-2.5 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition font-medium">
                                Edit
                              </button>
                              <button
                                onClick={() => handleToggleActive(s)}
                                className={`px-2.5 py-1 text-xs rounded font-medium transition ${
                                  s.is_active
                                    ? 'bg-red-100 text-red-700 hover:bg-red-200'
                                    : 'bg-green-100 text-green-700 hover:bg-green-200'
                                }`}>
                                {s.is_active ? 'Deactivate' : 'Reactivate'}
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </main>
      </div>

      {modalStudent !== undefined && (
        <StudentModal
          student={modalStudent}
          onClose={() => setModalStudent(undefined)}
          onSaved={() => { fetchStudents(); setSuccess(modalStudent ? 'Student updated.' : 'Student added successfully.') }}
        />
      )}

      {showImport && (
        <ImportCsvModal
          onClose={() => setShowImport(false)}
          onImported={(result) => {
            fetchStudents()
            setSuccess(
              result.skipped
                ? `Imported ${result.created} students. ${result.skipped} row(s) were skipped.`
                : `Imported ${result.created} students.`
            )
          }}
        />
      )}
    </div>
  )
}

export default StudentManagement
