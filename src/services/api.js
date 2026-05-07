import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000/api';

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

// Redirect to sign-in on expired/invalid token
axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('authToken');
      localStorage.removeItem('userData');
      window.location.replace('/signin');
    }
    return Promise.reject(error);
  }
);

export default axiosInstance;

// Auth APIs
export const authAPI = {
  login: (adminName, password) => axiosInstance.post('/auth/login/', { admin_name: adminName, password }),
  logout: () => axiosInstance.post('/auth/logout/'),
};

// Admin APIs
export const adminAPI = {
  getProfile: () => axiosInstance.get('/admins/'),
  updateProfile: (data) => axiosInstance.put('/admins/', data),
};

// Students APIs
export const studentAPI = {
  getAllStudents: (classId) => axiosInstance.get('/students/', { params: { classId } }),
  getStudent: (id) => axiosInstance.get(`/students/${id}/`),
  createStudent: (data) => axiosInstance.post('/students/', data),
  updateStudent: (id, data) => axiosInstance.put(`/students/${id}/`, data),
};

// Enrollment APIs
export const enrollmentAPI = {
  getEnrollments: () => axiosInstance.get('/enrollments/'),
  getEnrollment: (id) => axiosInstance.get(`/enrollments/${id}/`),
  createEnrollment: (data) => axiosInstance.post('/enrollments/', data),
  updateEnrollmentStatus: (id, status) => axiosInstance.patch(`/enrollments/${id}/`, { status }),
  uploadStudentImage: (enrollmentId, formData) =>
    axiosInstance.post(`/students/${enrollmentId}/enroll/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }),
};

// Attendance APIs
export const attendanceAPI = {
  getAttendance: (params) => axiosInstance.get('/attendance/', { params }),
  markAttendanceByFace: (formData) => axiosInstance.post('/attendance/mark-by-face/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  overrideAttendance: (id, data) => axiosInstance.patch(`/attendance/${id}/override/`, data),
};

// Admin Management APIs (level-3 admins only)
export const adminManagementAPI = {
  getAdmins: (params) => axiosInstance.get('/admins/', { params }),
  createAdmin: (data) => axiosInstance.post('/admins/', data),
  updateAdmin: (id, data) => axiosInstance.patch(`/admins/${id}/`, data),
  deleteAdmin: (id) => axiosInstance.delete(`/admins/${id}/`),
  unlockAdmin: (id) => axiosInstance.post(`/admin/${id}/unlock/`),
};

// Classes APIs
export const classAPI = {
  getClasses: () => axiosInstance.get('/classes/'),
  getClass: (id) => axiosInstance.get(`/classes/${id}/`),
  getClassStudents: (classId) => axiosInstance.get(`/classes/${classId}/`),
};
