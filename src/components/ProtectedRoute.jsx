import React from 'react'

const ProtectedRoute = ({ children, isAuthenticated }) => {
  return isAuthenticated ? children : null
}

export default ProtectedRoute
