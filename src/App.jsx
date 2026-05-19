import React, { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { authService } from './services/auth'
import SignIn from './pages/SignIn'
import Dashboard from './pages/Dashboard'
import AttendanceView from './pages/AttendanceView'
import EnrollmentHub from './pages/EnrollmentHub'
import ManualOverride from './pages/ManualOverride'
import AdminManagement from './pages/AdminManagement'
import ClassManagement from './pages/ClassManagement'

const getUser = () => authService.getUserData()
const isLevel3Admin = () => { const u = getUser(); return u?.role === 'admin' && u?.authorization_level >= 3 }
const isLevel2Admin = () => { const u = getUser(); return u?.role === 'admin' && u?.authorization_level >= 2 }
const isAdminRole   = () => getUser()?.role === 'admin'

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(authService.isAuthenticated())

  useEffect(() => {
    const handleAuthChange = () => {
      setIsAuthenticated(authService.isAuthenticated())
    }

    window.addEventListener('storage', handleAuthChange)
    return () => window.removeEventListener('storage', handleAuthChange)
  }, [])

  return (
    <Router>
      <Routes>
        <Route
          path="/"
          element={<Navigate to="/signin" replace />}
        />
        <Route
          path="/signin"
          element={<SignIn onLogin={() => setIsAuthenticated(true)} />}
        />
        <Route
          path="/dashboard"
          element={isAuthenticated ? <Dashboard /> : <Navigate to="/signin" />}
        />
        <Route
          path="/attendance"
          element={isAuthenticated ? <AttendanceView /> : <Navigate to="/signin" />}
        />
        <Route
          path="/enrollment"
          element={isAuthenticated
            ? (isAdminRole() ? <EnrollmentHub /> : <Navigate to="/dashboard" />)
            : <Navigate to="/signin" />}
        />
        <Route
          path="/override"
          element={isAuthenticated
            ? (isAdminRole() ? <ManualOverride /> : <Navigate to="/dashboard" />)
            : <Navigate to="/signin" />}
        />
        <Route
          path="/classes"
          element={isAuthenticated
            ? (isLevel2Admin() ? <ClassManagement /> : <Navigate to="/dashboard" />)
            : <Navigate to="/signin" />}
        />
        <Route
          path="/admin-management"
          element={isAuthenticated
            ? (isLevel3Admin() ? <AdminManagement /> : <Navigate to="/dashboard" />)
            : <Navigate to="/signin" />}
        />
        <Route path="*" element={<Navigate to={isAuthenticated ? "/dashboard" : "/signin"} replace />} />
      </Routes>
    </Router>
  )
}

export default App
