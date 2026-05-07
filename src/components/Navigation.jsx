import React from 'react'
import { useNavigate } from 'react-router-dom'
import { authService } from '../services/auth'

const Navigation = ({ currentPage }) => {
  const navigate = useNavigate()
  const user = authService.getUserData()
  const isLevel3Admin = user?.role === 'admin' && user?.authorization_level >= 3

  const navItems = [
    { path: '/dashboard', label: 'Dashboard', icon: '📊' },
    { path: '/attendance', label: 'Attendance', icon: '📋' },
    { path: '/enrollment', label: 'Enrollment', icon: '📷' },
    { path: '/override', label: 'Override', icon: '⚙️' },
    ...(isLevel3Admin ? [{ path: '/admin-management', label: 'Admin Management', icon: '🔑' }] : []),
  ]

  return (
    <nav className="bg-white shadow-sm border-r border-gray-200 min-h-screen w-64">
      <div className="p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-8">FR Attendance</h2>
      </div>
      <div className="space-y-2 px-4">
        {navItems.map((item) => (
          <button
            key={item.path}
            onClick={() => navigate(item.path)}
            className={`w-full text-left px-4 py-3 rounded-lg transition flex items-center gap-3 ${
              currentPage === item.path
                ? 'bg-blue-50 text-blue-600 font-semibold'
                : 'text-gray-700 hover:bg-gray-100'
            }`}
          >
            <span className="text-lg">{item.icon}</span>
            {item.label}
          </button>
        ))}
      </div>
    </nav>
  )
}

export default Navigation
