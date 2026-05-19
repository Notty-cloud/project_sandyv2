import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { authAPI } from '../services/api'
import { authService } from '../services/auth'

const DEMO_USERS = [
  { username: 'admin',        password: 'Admin@sandy1',  role: 'Head Teacher',  badge: 'bg-purple-100 text-purple-700' },
  { username: 'coordinator1', password: 'Coord@sandy1',  role: 'Coordinator',   badge: 'bg-blue-100 text-blue-700'   },
  { username: 'teacher1',     password: 'Teach@sandy1',  role: 'Teacher',       badge: 'bg-green-100 text-green-700' },
  { username: 'teacher2',     password: 'Teach2@sandy1', role: 'Teacher',       badge: 'bg-green-100 text-green-700' },
]

const ERROR_MESSAGES = {
  'Invalid credentials.': 'Username or password is incorrect.',
  'Account is locked. Contact a level 3 admin to unlock it.': 'This account is locked. Contact your Head Teacher to unlock it.',
}

const SignIn = ({ onLogin }) => {
  const navigate = useNavigate()
  const [adminName, setAdminName] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const response = await authAPI.login(adminName, password)
      const { access_token, admin } = response.data
      authService.login(access_token, admin)
      onLogin()
      navigate('/dashboard')
    } catch (err) {
      const raw = err.response?.data?.detail || err.response?.data?.message || ''
      setError(ERROR_MESSAGES[raw] || raw || 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const fillCredentials = (user) => {
    setAdminName(user.username)
    setPassword(user.password)
    setError('')
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center px-4">
      <div className="w-full max-w-md bg-white rounded-xl shadow-lg p-8">

        {/* Header */}
        <div className="text-center mb-8">
          <div className="text-4xl mb-3">🎓</div>
          <h1 className="text-2xl font-bold text-gray-900">School Attendance</h1>
          <p className="text-sm text-gray-500 mt-1">Facial Recognition System</p>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-5 flex items-start gap-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
            <span className="mt-0.5 shrink-0">⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
            <input
              type="text"
              value={adminName}
              onChange={(e) => setAdminName(e.target.value)}
              placeholder="e.g. jdelacruz"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-2.5 rounded-lg hover:bg-blue-700 transition font-semibold disabled:opacity-50 disabled:cursor-not-allowed mt-2"
          >
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>

        {/* Demo accounts */}
        <div className="mt-8">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Test accounts — click to fill</p>
          <div className="divide-y divide-gray-100 border border-gray-200 rounded-lg overflow-hidden">
            {DEMO_USERS.map((u) => (
              <button
                key={u.username}
                type="button"
                onClick={() => fillCredentials(u)}
                className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-50 transition"
              >
                <div>
                  <span className="text-sm font-medium text-gray-800">{u.username}</span>
                  <span className="ml-2 text-xs text-gray-400">{u.password}</span>
                </div>
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${u.badge}`}>{u.role}</span>
              </button>
            ))}
          </div>
        </div>

        <p className="text-center text-xs text-gray-400 mt-8">© 2026 Facial Recognition Attendance System</p>
      </div>
    </div>
  )
}

export default SignIn
