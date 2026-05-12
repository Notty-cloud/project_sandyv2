import React, { useState, useEffect } from 'react'
import Header from '../components/Header'
import Navigation from '../components/Navigation'
import Alert from '../components/Alert'
import { classAPI, adminManagementAPI } from '../services/api'
import { authService } from '../services/auth'

const SUBJECTS = [
  'Mathematics', 'English', 'Science', 'Filipino', 'Social Studies',
  'Physical Education', 'Arts', 'Music', 'Values Education', 'Technology',
  'History', 'Geography', 'Chemistry', 'Physics', 'Biology',
]

const GRADES = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']
const SECTIONS = ['A', 'B', 'C', 'D', 'E', 'F']

const EMPTY_FORM = {
  subject: '',
  grade: '',
  section: 'A',
  class_name: '',
  teacher: '',
  academic_year: '',
  is_active: true,
}

const subjectColor = (subject) => {
  const map = {
    Mathematics: 'bg-blue-100 text-blue-800',
    English: 'bg-green-100 text-green-800',
    Science: 'bg-purple-100 text-purple-800',
    Filipino: 'bg-yellow-100 text-yellow-800',
    'Social Studies': 'bg-orange-100 text-orange-800',
    'Physical Education': 'bg-red-100 text-red-800',
    History: 'bg-amber-100 text-amber-800',
    Chemistry: 'bg-indigo-100 text-indigo-800',
    Physics: 'bg-cyan-100 text-cyan-800',
    Biology: 'bg-emerald-100 text-emerald-800',
  }
  return map[subject] || 'bg-gray-100 text-gray-700'
}

const ClassManagement = () => {
  const currentUser = authService.getUserData()
  const canEdit = currentUser?.role === 'admin' && currentUser?.authorization_level >= 2

  const [classes, setClasses] = useState([])
  const [teachers, setTeachers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const [filterSubject, setFilterSubject] = useState('')
  const [filterGrade, setFilterGrade] = useState('')

  const [showModal, setShowModal] = useState(false)
  const [editingClass, setEditingClass] = useState(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)

  const [confirmDelete, setConfirmDelete] = useState(null)

  const currentYear = (() => {
    const y = new Date().getFullYear()
    return new Date().getMonth() >= 6 ? `${y}-${y + 1}` : `${y - 1}-${y}`
  })()

  useEffect(() => {
    fetchClasses()
    fetchTeachers()
  }, [])

  const fetchClasses = async () => {
    try {
      setLoading(true)
      const res = await classAPI.getClasses({ tenant_id: currentUser?.tenant_id })
      const data = res.data?.results ?? res.data
      setClasses(Array.isArray(data) ? data : [])
    } catch {
      setError('Failed to load classes.')
    } finally {
      setLoading(false)
    }
  }

  const fetchTeachers = async () => {
    try {
      const res = await adminManagementAPI.getAdmins({ tenant_id: currentUser?.tenant_id })
      const data = res.data?.results ?? res.data
      setTeachers(Array.isArray(data) ? data : [])
    } catch {
      // non-fatal — teacher dropdown just stays empty
    }
  }

  const autoClassName = (f) => {
    if (f.subject && f.grade && f.section)
      return `${f.subject} — Grade ${f.grade}${f.section}`
    return ''
  }

  const openCreate = () => {
    const f = { ...EMPTY_FORM, academic_year: currentYear }
    setForm(f)
    setEditingClass(null)
    setShowModal(true)
  }

  const openEdit = (cls) => {
    setForm({
      subject: cls.subject || '',
      grade: cls.grade || '',
      section: cls.section || 'A',
      class_name: cls.class_name || '',
      teacher: cls.teacher || '',
      academic_year: cls.academic_year || currentYear,
      is_active: cls.is_active,
    })
    setEditingClass(cls)
    setShowModal(true)
  }

  const closeModal = () => {
    setShowModal(false)
    setEditingClass(null)
    setForm(EMPTY_FORM)
  }

  const handleFormChange = (field, value) => {
    setForm((prev) => {
      const next = { ...prev, [field]: value }
      if (['subject', 'grade', 'section'].includes(field)) {
        next.class_name = autoClassName(next)
      }
      return next
    })
  }

  const handleSave = async (e) => {
    e.preventDefault()
    if (!form.subject) return setError('Subject is required.')
    if (!form.grade) return setError('Grade is required.')

    const payload = {
      ...form,
      tenant_id: currentUser?.tenant_id,
      teacher: form.teacher || null,
      class_name: form.class_name || autoClassName(form),
      authorization_level: Number(form.authorization_level),
    }

    try {
      setSaving(true)
      setError('')
      if (editingClass) {
        await classAPI.updateClass(editingClass.id, payload)
        setSuccess('Class updated successfully.')
      } else {
        await classAPI.createClass(payload)
        setSuccess('Class created successfully.')
      }
      closeModal()
      fetchClasses()
    } catch (err) {
      const d = err.response?.data
      const msg = d
        ? Object.entries(d).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`).join(' | ')
        : 'Failed to save class.'
      setError(msg)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (cls) => {
    try {
      await classAPI.deleteClass(cls.id)
      setSuccess(`"${cls.class_name || cls.subject}" deleted.`)
      setConfirmDelete(null)
      fetchClasses()
    } catch {
      setError('Failed to delete class.')
    }
  }

  const filtered = classes.filter((c) => {
    if (filterSubject && c.subject !== filterSubject) return false
    if (filterGrade && c.grade !== filterGrade) return false
    return true
  })

  const subjects = [...new Set(classes.map((c) => c.subject).filter(Boolean))].sort()
  const grades = [...new Set(classes.map((c) => c.grade).filter(Boolean))].sort((a, b) => Number(a) - Number(b))

  const stats = {
    total: classes.length,
    active: classes.filter((c) => c.is_active).length,
    subjects: new Set(classes.map((c) => c.subject).filter(Boolean)).size,
    withTeacher: classes.filter((c) => c.teacher).length,
  }

  return (
    <div className="flex h-screen bg-gray-50">
      <Navigation currentPage="/classes" />

      <div className="flex-1 flex flex-col overflow-hidden">
        <Header title="Class Management" />

        <main className="flex-1 overflow-auto p-6">
          <div className="max-w-7xl mx-auto">
            {error   && <Alert type="error"   message={error}   onClose={() => setError('')} />}
            {success && <Alert type="success" message={success} onClose={() => setSuccess('')} />}

            {/* Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              {[
                { label: 'Total Classes',    value: stats.total,       border: 'border-gray-400',   text: 'text-gray-700'   },
                { label: 'Active',           value: stats.active,      border: 'border-green-500',  text: 'text-green-600'  },
                { label: 'Subjects',         value: stats.subjects,    border: 'border-blue-500',   text: 'text-blue-600'   },
                { label: 'With Teacher',     value: stats.withTeacher, border: 'border-purple-500', text: 'text-purple-600' },
              ].map(({ label, value, border, text }) => (
                <div key={label} className={`bg-white p-4 rounded-lg shadow border-l-4 ${border}`}>
                  <p className="text-gray-500 text-sm">{label}</p>
                  <p className={`text-2xl font-bold mt-1 ${text}`}>{value}</p>
                </div>
              ))}
            </div>

            {/* Toolbar */}
            <div className="bg-white rounded-lg shadow mb-6 p-4 flex flex-wrap items-center gap-3">
              <select value={filterSubject} onChange={(e) => setFilterSubject(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                <option value="">All Subjects</option>
                {subjects.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
              <select value={filterGrade} onChange={(e) => setFilterGrade(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                <option value="">All Grades</option>
                {grades.map((g) => <option key={g} value={g}>Grade {g}</option>)}
              </select>
              <button onClick={fetchClasses}
                className="px-3 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm hover:bg-gray-200 transition">
                Refresh
              </button>
              <div className="flex-1" />
              {canEdit && (
                <button onClick={openCreate}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 transition">
                  + New Class
                </button>
              )}
            </div>

            {/* Table */}
            <div className="bg-white rounded-lg shadow overflow-hidden">
              {loading ? (
                <div className="py-12 text-center text-gray-400">Loading classes…</div>
              ) : filtered.length === 0 ? (
                <div className="py-12 text-center text-gray-400">
                  {classes.length === 0 ? 'No classes yet. Click "+ New Class" to create one.' : 'No classes match the selected filters.'}
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 border-b">
                      <tr>
                        {['Subject', 'Grade', 'Section', 'Class Name', 'Teacher', 'Academic Year', 'Status', ...(canEdit ? ['Actions'] : [])].map((h) => (
                          <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {filtered.map((cls) => (
                        <tr key={cls.id} className="hover:bg-gray-50 transition">
                          <td className="px-4 py-3">
                            <span className={`px-2 py-1 rounded-full text-xs font-semibold ${subjectColor(cls.subject)}`}>
                              {cls.subject || '—'}
                            </span>
                          </td>
                          <td className="px-4 py-3 font-medium text-gray-800">Grade {cls.grade}</td>
                          <td className="px-4 py-3 text-gray-600">{cls.section}</td>
                          <td className="px-4 py-3 text-gray-700">{cls.class_name || '—'}</td>
                          <td className="px-4 py-3 text-gray-600">{cls.teacher_name || <span className="text-gray-400 italic">Unassigned</span>}</td>
                          <td className="px-4 py-3 text-gray-500">{cls.academic_year || '—'}</td>
                          <td className="px-4 py-3">
                            <span className={`px-2 py-1 rounded-full text-xs font-semibold ${cls.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}`}>
                              {cls.is_active ? 'Active' : 'Inactive'}
                            </span>
                          </td>
                          {canEdit && (
                            <td className="px-4 py-3">
                              <div className="flex gap-2">
                                <button onClick={() => openEdit(cls)}
                                  className="px-3 py-1 bg-blue-100 text-blue-700 rounded text-xs hover:bg-blue-200 transition font-medium">
                                  Edit
                                </button>
                                <button onClick={() => setConfirmDelete(cls)}
                                  className="px-3 py-1 bg-red-100 text-red-700 rounded text-xs hover:bg-red-200 transition font-medium">
                                  Delete
                                </button>
                              </div>
                            </td>
                          )}
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

      {/* Create / Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50 px-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-5">
              {editingClass ? 'Edit Class' : 'Create New Class'}
            </h2>

            <form onSubmit={handleSave} className="space-y-4">
              {/* Subject */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Subject <span className="text-red-500">*</span></label>
                <select value={form.subject} onChange={(e) => handleFormChange('subject', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required>
                  <option value="">— Select subject —</option>
                  {SUBJECTS.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>

              {/* Grade + Section */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Grade <span className="text-red-500">*</span></label>
                  <select value={form.grade} onChange={(e) => handleFormChange('grade', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required>
                    <option value="">— Grade —</option>
                    {GRADES.map((g) => <option key={g} value={g}>Grade {g}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Section</label>
                  <select value={form.section} onChange={(e) => handleFormChange('section', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                    {SECTIONS.map((s) => <option key={s} value={s}>Section {s}</option>)}
                  </select>
                </div>
              </div>

              {/* Class Name (auto-filled) */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Class Name</label>
                <input type="text" value={form.class_name}
                  onChange={(e) => setForm((p) => ({ ...p, class_name: e.target.value }))}
                  placeholder="Auto-filled from subject + grade + section"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-gray-50" />
              </div>

              {/* Teacher */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Assigned Teacher</label>
                <select value={form.teacher} onChange={(e) => setForm((p) => ({ ...p, teacher: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                  <option value="">— Unassigned —</option>
                  {teachers.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.admin_name} ({t.role === 'admin' ? (t.authorization_level === 3 ? 'Head Teacher' : 'Coordinator') : 'Teacher'})
                    </option>
                  ))}
                </select>
              </div>

              {/* Academic Year + Status */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Academic Year</label>
                  <input type="text" value={form.academic_year}
                    onChange={(e) => setForm((p) => ({ ...p, academic_year: e.target.value }))}
                    placeholder="e.g. 2024-2025"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
                  <select value={form.is_active ? 'true' : 'false'}
                    onChange={(e) => setForm((p) => ({ ...p, is_active: e.target.value === 'true' }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                    <option value="true">Active</option>
                    <option value="false">Inactive</option>
                  </select>
                </div>
              </div>

              <div className="flex gap-3 pt-2">
                <button type="submit" disabled={saving}
                  className="flex-1 bg-blue-600 text-white py-2.5 rounded-lg font-semibold text-sm hover:bg-blue-700 transition disabled:opacity-50">
                  {saving ? 'Saving…' : editingClass ? 'Save Changes' : 'Create Class'}
                </button>
                <button type="button" onClick={closeModal}
                  className="flex-1 bg-gray-200 text-gray-700 py-2.5 rounded-lg font-semibold text-sm hover:bg-gray-300 transition">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation */}
      {confirmDelete && (
        <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50 px-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-sm p-6">
            <h2 className="text-lg font-bold text-gray-900 mb-2">Delete Class</h2>
            <p className="text-gray-600 text-sm mb-6">
              Delete <strong>{confirmDelete.class_name || confirmDelete.subject}</strong>? This cannot be undone.
            </p>
            <div className="flex gap-3">
              <button onClick={() => handleDelete(confirmDelete)}
                className="flex-1 bg-red-600 text-white py-2 rounded-lg font-semibold text-sm hover:bg-red-700 transition">
                Delete
              </button>
              <button onClick={() => setConfirmDelete(null)}
                className="flex-1 bg-gray-200 text-gray-700 py-2 rounded-lg font-semibold text-sm hover:bg-gray-300 transition">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ClassManagement
