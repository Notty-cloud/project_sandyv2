import React from 'react'
import { useNavigate } from 'react-router-dom'
import { authService } from '../services/auth'

const Header = ({ title, showLogout = true }) => {
  const navigate = useNavigate()
  const userData = authService.getUserData()

  const handleLogout = () => {
    authService.logout()
    navigate('/signin')
  }

  return (
    <header className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
          {userData && (
            <p className="text-sm text-gray-600 mt-1">
              {userData.admin_name} • {userData.role}
            </p>
          )}
        </div>
        {showLogout && (
          <button
            onClick={handleLogout}
            className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition"
          >
            Logout
          </button>
        )}
      </div>
    </header>
  )
}

export default Header
