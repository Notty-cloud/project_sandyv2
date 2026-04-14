import React from 'react'

const Alert = ({ type = 'info', message, onClose }) => {
  const bgColorMap = {
    success: 'bg-green-50',
    error: 'bg-red-50',
    info: 'bg-blue-50',
    warning: 'bg-yellow-50',
  }

  const borderColorMap = {
    success: 'border-green-200',
    error: 'border-red-200',
    info: 'border-blue-200',
    warning: 'border-yellow-200',
  }

  const textColorMap = {
    success: 'text-green-800',
    error: 'text-red-800',
    info: 'text-blue-800',
    warning: 'text-yellow-800',
  }

  return (
    <div className={`${bgColorMap[type]} border ${borderColorMap[type]} rounded-lg p-4 flex justify-between items-center`}>
      <span className={`${textColorMap[type]} font-medium`}>{message}</span>
      {onClose && (
        <button
          onClick={onClose}
          className={`${textColorMap[type]} hover:opacity-70 transition`}
        >
          ✕
        </button>
      )}
    </div>
  )
}

export default Alert
