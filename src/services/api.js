import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:3000/api';

const axiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests if available
axiosInstance.interceptors.request.use((config) => {
  const token = localStorage.getItem('authToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => Promise.reject(error));

export default axiosInstance;

// Auth APIs
export const authAPI = {
  login: (email, password) => axiosInstance.post('/auth/login', { email, password }),
  logout: () => axiosInstance.post('/auth/logout'),
};

// Admin APIs
export const adminAPI = {
  getProfile: () => axiosInstance.get('/admins/profile'),
  updateProfile: (data) => axiosInstance.put('/admins/profile', data),
};

// Students APIs
export const studentAPI = {
  getAllStudents: (classId) => axiosInstance.get('/students', { params: { classId } }),
  getStudent: (id) => axiosInstance.get(`/students/${id}`),
  createStudent: (data) => axiosInstance.post('/students', data),
  updateStudent: (id, data) => axiosInstance.put(`/students/${id}`, data),
};

// Enrollment APIs
export const enrollmentAPI = {
  getEnrollments: () => axiosInstance.get('/enrollments'),
  getEnrollment: (id) => axiosInstance.get(`/enrollments/${id}`),
  createEnrollment: (data) => axiosInstance.post('/enrollments', data),
  updateEnrollmentStatus: (id, status) => axiosInstance.patch(`/enrollments/${id}/status`, { status }),
  uploadStudentImage: (enrollmentId, formData) => 
    axiosInstance.post(`/enrollments/${enrollmentId}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }),
};

// Attendance APIs
export const attendanceAPI = {
  getTodayAttendance: (classId) => axiosInstance.get('/attendance/today', { params: { classId } }),
  getAttendanceHistory: (studentId, startDate, endDate) => 
    axiosInstance.get(`/attendance/history`, { params: { studentId, startDate, endDate } }),
  getClassAttendance: (classId, date) => 
    axiosInstance.get('/attendance/class', { params: { classId, date } }),
  markAttendance: (data) => axiosInstance.post('/attendance', data),
  overrideAttendance: (id, data) => axiosInstance.patch(`/attendance/${id}/override`, data),
};

// Classes APIs
export const classAPI = {
  getClasses: () => axiosInstance.get('/classes'),
  getClass: (id) => axiosInstance.get(`/classes/${id}`),
  getClassStudents: (classId) => axiosInstance.get(`/classes/${classId}/students`),
};
