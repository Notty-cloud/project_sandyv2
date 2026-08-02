import axios from 'axios';

// VITE_* values are inlined at build time. In the container image the frontend
// is built without one, so production must fall back to a same-origin relative
// path — Django serves the SPA and the API from the same host. An absolute
// localhost default would send deployed users' browsers to their own machines.
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.DEV ? 'http://localhost:3000/api' : '/api');

const axiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests if available (skip auth endpoints — stale tokens block login)
axiosInstance.interceptors.request.use((config) => {
  const isAuthEndpoint = config.url?.includes('/auth/login');
  const token = localStorage.getItem('authToken');
  if (token && !isAuthEndpoint) {
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
  getAllStudents: (params) => axiosInstance.get('/students/', { params }),
  getStudent: (id) => axiosInstance.get(`/students/${id}/`),
  createStudent: (data) => axiosInstance.post('/students/', data),
  updateStudent: (id, data) => axiosInstance.put(`/students/${id}/`, data),
  identifyStudent: (formData) => axiosInstance.post('/students/identify/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  identifyGroup: (formData) => axiosInstance.post('/students/identify-group/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  importStudentsCsv: (formData) => axiosInstance.post('/students/import-csv/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
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
  getClassAttendance: (classId, date) => axiosInstance.get('/attendance/', { params: { class_ref: classId, date } }),
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
  getClasses: (params) => axiosInstance.get('/classes/', { params }),
  getClass: (id) => axiosInstance.get(`/classes/${id}/`),
  getClassStudents: (classId) => axiosInstance.get(`/classes/${classId}/`),
  createClass: (data) => axiosInstance.post('/classes/', data),
  updateClass: (id, data) => axiosInstance.patch(`/classes/${id}/`, data),
  deleteClass: (id) => axiosInstance.delete(`/classes/${id}/`),
};
