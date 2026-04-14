import React, { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { authService } from './services/auth'
import SignIn from './pages/SignIn'
import Dashboard from './pages/Dashboard'
import AttendanceView from './pages/AttendanceView'
import EnrollmentHub from './pages/EnrollmentHub'
import ManualOverride from './pages/ManualOverride'
import ProtectedRoute from './components/ProtectedRoute'

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
          path="/signin" 
          element={<SignIn onLogin={() => setIsAuthenticated(true)} />} 
        />
        <Route 
          path="/" 
          element={isAuthenticated ? <Dashboard /> : <Navigate to="/signin" />} 
        />
        <Route 
          path="/attendance" 
          element={isAuthenticated ? <AttendanceView /> : <Navigate to="/signin" />} 
        />
        <Route 
          path="/enrollment" 
          element={isAuthenticated ? <EnrollmentHub /> : <Navigate to="/signin" />} 
        />
        <Route 
          path="/override" 
          element={isAuthenticated ? <ManualOverride /> : <Navigate to="/signin" />} 
        />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </Router>
  )
}

export default App
