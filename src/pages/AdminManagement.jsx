import React, { useState, useEffect } from 'react'
import Header from '../components/Header'
import Navigation from '../components/Navigation'
import Alert from '../components/Alert'
import { adminManagementAPI } from '../services/api'
import { authService } from '../services/auth'

// Role profiles map a friendly label to the underlying role + level fields
const ROLE_PROFILES = [
  { label: 'Teacher',      description: 'Attendance marking and student viewing',          role: 'teacher', level: 1 },
  { label: 'Coordinator',  description: 'Enrollment management and class coordination',    role: 'admin',   level: 2 },
  { label: 'Head Teacher', description: 'Full system administration and account control',  role: 'admin',   level: 3 },
]

const profileOf = (admin) => {
  if (admin.role === 'admin' && admin.authorization_level >= 3) return ROLE_PROFILES[2]
  if (admin.role === 'admin' && admin.authorization_level >= 2) return ROLE_PROFILES[1]
  return ROLE_PROFILES[0]
}

const EMPTY_FORM = {
  admin_name: '',
  email: '',
  password: '',
  role: 'teacher',
  authorization_level: 1,
  profile: 'Teacher',
}

const StatusBadge = ({ admin }) => {
  if (admin.is_locked)
    return <span className="px-2 py-1 rounded-full text-xs font-semibold bg-red-100 text-red-800">Locked</span>
  if (!admin.is_active)
    return <span className="px-2 py-1 rounded-full text-xs font-semibold bg-gray-100 text-gray-700">Inactive</span>
  return <span className="px-2 py-1 rounded-full text-xs font-semibold bg-green-100 text-green-800">Active</span>
}

const AdminManagement = () => {
  const currentUser = authService.getUserData()
  const [admins, setAdmins] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [createForm, setCreateForm] = useState(EMPTY_FORM)
  const [createLoading, setCreateLoading] = useState(false)

  const [editingId, setEditingId] = useState(null)
  const [editForm, setEditForm] = useState({})
  const [editLoading, setEditLoading] = useState(false)

  const [confirmDelete, setConfirmDelete] = useState(null)

  useEffect(() => {
    fetchAdmins()
  }, [])

  const fetchAdmins = async () => {
    try {
      setLoading(true)
      const response = await adminManagementAPI.getAdmins({
        tenant_id: currentUser?.tenant_id,
      })
      setAdmins(response.data?.results ?? response.data)
    } catch {
      setError('Failed to load admin accounts.')
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async (e) => {
    e.preventDefault()
    setCreateLoading(true)
    setError('')
    try {
      const profile = ROLE_PROFILES.find((p) => p.label === createForm.profile) || ROLE_PROFILES[0]
      await adminManagementAPI.createAdmin({
        admin_name: createForm.admin_name,
        email: createForm.email,
        password: createForm.password,
        tenant_id: currentUser?.tenant_id,
        role: profile.role,
        authorization_level: profile.level,
      })
      setSuccess(`Account "${createForm.admin_name}" created successfully.`)
      setShowCreateModal(false)
      setCreateForm(EMPTY_FORM)
      fetchAdmins()
    } catch (err) {
      const data = err.response?.data
      const msg = data
        ? Object.entries(data).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`).join(' | ')
        : 'Failed to create account.'
      setError(msg)
    } finally {
      setCreateLoading(false)
    }
  }

  const startEdit = (admin) => {
    setEditingId(admin.id)
    setEditForm({
      role: admin.role,
      authorization_level: admin.authorization_level,
      is_active: admin.is_active,
    })
  }

  const handleUpdate = async (id) => {
    setEditLoading(true)
    setError('')
    try {
      await adminManagementAPI.updateAdmin(id, {
        ...editForm,
        authorization_level: Number(editForm.authorization_level),
      })
      setSuccess('Account updated.')
      setEditingId(null)
      fetchAdmins()
    } catch {
      setError('Failed to update account.')
    } finally {
      setEditLoading(false)
    }
  }

  const handleUnlock = async (admin) => {
    setError('')
    try {
      await adminManagementAPI.unlockAdmin(admin.id)
      setSuccess(`${admin.admin_name} has been unlocked.`)
      fetchAdmins()
    } catch {
      setError('Failed to unlock account.')
    }
  }

  const handleDelete = async (id) => {
    setError('')
    try {
      await adminManagementAPI.deleteAdmin(id)
      setSuccess('Account deleted.')
      setConfirmDelete(null)
      fetchAdmins()
    } catch {
      setError('Failed to delete account.')
    }
  }

  return (
    <div className="flex h-screen bg-gray-50">
      <Navigation currentPage="/admin-management" />

      <div className="flex-1 flex flex-col overflow-hidden">
        <Header title="Admin Management" />

        <main className="flex-1 overflow-auto p-6">
          <div className="max-w-7xl mx-auto">

            {error && <Alert type="error" message={error} onClose={() => setError('')} />}
            {success && <Alert type="success" message={success} onClose={() => setSuccess('')} />}

            <div className="flex justify-between items-center mt-4 mb-6">
              <p className="text-sm text-gray-500">
                Manage system accounts, roles, and authorization levels.
              </p>
              <button
                onClick={() => { setShowCreateModal(true); setError('') }}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-semibold text-sm"
              >
                + New Account
              </button>
            </div>

            {/* Table */}
            <div className="bg-white rounded-lg shadow overflow-hidden">
              {loading ? (
                <div className="text-center py-12 text-gray-500">Loading accounts...</div>
              ) : admins.length === 0 ? (
                <div className="text-center py-12 text-gray-500">No accounts found.</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 border-b">
                      <tr>
                        <th className="px-4 py-3 text-left font-semibold text-gray-700">Username</th>
                        <th className="px-4 py-3 text-left font-semibold text-gray-700">Email</th>
                        <th className="px-4 py-3 text-left font-semibold text-gray-700">Role Profile</th>
                        <th className="px-4 py-3 text-left font-semibold text-gray-700">Status</th>
                        <th className="px-4 py-3 text-left font-semibold text-gray-700">Last Login</th>
                        <th className="px-4 py-3 text-left font-semibold text-gray-700">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {admins.map((admin) => (
                        <tr key={admin.id} className="border-b hover:bg-gray-50">
                          <td className="px-4 py-3 font-medium text-gray-900">
                            {admin.admin_name}
                            {admin.id === currentUser?.id && (
                              <span className="ml-2 text-xs text-blue-500">(you)</span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-gray-600">{admin.email}</td>

                          {/* Role Profile — editable inline */}
                          <td className="px-4 py-3">
                            {editingId === admin.id ? (
                              <select
                                value={editForm.profile || profileOf(admin).label}
                                onChange={(e) => {
                                  const p = ROLE_PROFILES.find((r) => r.label === e.target.value)
                                  setEditForm({ ...editForm, profile: e.target.value, role: p.role, authorization_level: p.level })
                                }}
                                className="border rounded px-2 py-1 text-sm"
                              >
                                {ROLE_PROFILES.map((p) => <option key={p.label} value={p.label}>{p.label}</option>)}
                              </select>
                            ) : (() => {
                              const p = profileOf(admin)
                              const colors = { Teacher: 'bg-blue-100 text-blue-800', Coordinator: 'bg-purple-100 text-purple-800', 'Head Teacher': 'bg-red-100 text-red-800' }
                              return (
                                <div>
                                  <span className={`px-2 py-1 rounded-full text-xs font-semibold ${colors[p.label]}`}>{p.label}</span>
                                  <p className="text-xs text-gray-400 mt-0.5">{p.description}</p>
                                </div>
                              )
                            })()}
                          </td>

                          {/* Active toggle — editable inline */}
                          <td className="px-4 py-3">
                            {editingId === admin.id ? (
                              <select
                                value={editForm.is_active ? 'true' : 'false'}
                                onChange={(e) => setEditForm({ ...editForm, is_active: e.target.value === 'true' })}
                                className="border rounded px-2 py-1 text-sm"
                              >
                                <option value="true">Active</option>
                                <option value="false">Inactive</option>
                              </select>
                            ) : (
                              <StatusBadge admin={admin} />
                            )}
                          </td>

                          <td className="px-4 py-3 text-gray-500 text-xs">
                            {admin.last_login_at
                              ? new Date(admin.last_login_at).toLocaleDateString()
                              : 'Never'}
                          </td>

                          {/* Actions */}
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              {editingId === admin.id ? (
                                <>
                                  <button
                                    onClick={() => handleUpdate(admin.id)}
                                    disabled={editLoading}
                                    className="px-3 py-1 bg-green-500 text-white rounded text-xs hover:bg-green-600 transition disabled:opacity-50"
                                  >
                                    Save
                                  </button>
                                  <button
                                    onClick={() => setEditingId(null)}
                                    className="px-3 py-1 bg-gray-300 text-gray-700 rounded text-xs hover:bg-gray-400 transition"
                                  >
                                    Cancel
                                  </button>
                                </>
                              ) : (
                                <>
                                  {admin.id !== currentUser?.id && (
                                    <button
                                      onClick={() => startEdit(admin)}
                                      className="px-3 py-1 bg-blue-100 text-blue-700 rounded text-xs hover:bg-blue-200 transition"
                                    >
                                      Edit
                                    </button>
                                  )}
                                  {admin.is_locked && (
                                    <button
                                      onClick={() => handleUnlock(admin)}
                                      className="px-3 py-1 bg-yellow-100 text-yellow-700 rounded text-xs hover:bg-yellow-200 transition"
                                    >
                                      Unlock
                                    </button>
                                  )}
                                  {admin.id !== currentUser?.id && (
                                    <button
                                      onClick={() => setConfirmDelete(admin)}
                                      className="px-3 py-1 bg-red-100 text-red-700 rounded text-xs hover:bg-red-200 transition"
                                    >
                                      Delete
                                    </button>
                                  )}
                                </>
                              )}
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

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50 px-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Create New Account</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
                <input
                  type="text"
                  value={createForm.admin_name}
                  onChange={(e) => setCreateForm({ ...createForm, admin_name: e.target.value })}
                  placeholder="e.g. jdelacruz"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input
                  type="email"
                  value={createForm.email}
                  onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })}
                  placeholder="user@school.com"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Password
                  <span className="text-gray-400 font-normal ml-1">(min 8 chars, 1 uppercase, 1 number, 1 special)</span>
                </label>
                <input
                  type="password"
                  value={createForm.password}
                  onChange={(e) => setCreateForm({ ...createForm, password: e.target.value })}
                  placeholder="••••••••"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Role Profile</label>
                <select
                  value={createForm.profile}
                  onChange={(e) => setCreateForm({ ...createForm, profile: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {ROLE_PROFILES.map((p) => (
                    <option key={p.label} value={p.label}>{p.label} — {p.description}</option>
                  ))}
                </select>
                <p className="text-xs text-gray-400 mt-1">
                  {ROLE_PROFILES.find((p) => p.label === createForm.profile)?.description}
                </p>
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  type="submit"
                  disabled={createLoading}
                  className="flex-1 bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition font-semibold text-sm disabled:opacity-50"
                >
                  {createLoading ? 'Creating...' : 'Create Account'}
                </button>
                <button
                  type="button"
                  onClick={() => { setShowCreateModal(false); setCreateForm(EMPTY_FORM) }}
                  className="flex-1 bg-gray-200 text-gray-700 py-2 rounded-lg hover:bg-gray-300 transition font-semibold text-sm"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {confirmDelete && (
        <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50 px-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-sm p-6">
            <h2 className="text-lg font-bold text-gray-900 mb-2">Delete Account</h2>
            <p className="text-gray-600 text-sm mb-6">
              Are you sure you want to delete <strong>{confirmDelete.admin_name}</strong>? This cannot be undone.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => handleDelete(confirmDelete.id)}
                className="flex-1 bg-red-600 text-white py-2 rounded-lg hover:bg-red-700 transition font-semibold text-sm"
              >
                Delete
              </button>
              <button
                onClick={() => setConfirmDelete(null)}
                className="flex-1 bg-gray-200 text-gray-700 py-2 rounded-lg hover:bg-gray-300 transition font-semibold text-sm"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default AdminManagement
