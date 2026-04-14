# Facial Recognition Attendance System - Presentation Layer

This is the React + Vite + Tailwind CSS presentation layer for a facial recognition-based school attendance system. The application provides 5 main dashboards for managing student attendance.

## 📋 Features

### 1. **Sign-in Portal** (`/signin`)
- Teacher/Admin authentication
- Email and password-based login
- Secure session management
- Role-based access control

### 2. **Central Navigation Dashboard** (`/`)
- Quick overview of system statistics
- Navigation to all major features
- Active classes listing
- System status overview

### 3. **Class Attendance View** (`/attendance`)
- View attendance records by class and date
- Real-time attendance status (Present, Absent, Late)
- Confidence scores from AI recognition
- Manual override indicators
- Filter and search capabilities

### 4. **Enrollment Hub** (`/enrollment`)
- Student facial embedding registration
- Image upload and processing
- Enrollment status tracking (Pending, Processing, Completed, Failed)
- Quality score monitoring
- Re-enrollment for failed captures

### 5. **Manual Override Interface** (`/override`)
- Handle failed AI recognition cases
- Manual attendance adjustment with audit trail
- Low confidence flag handling
- Override reason documentation
- Comprehensive filtering and statistics

## 🛠️ Tech Stack

- **Framework:** React 18.2
- **Build Tool:** Vite 5.0
- **Styling:** Tailwind CSS 3.4
- **HTTP Client:** Axios 1.6
- **Routing:** React Router 6.20
- **Node:** 16+ (Recommended: 18+)

## 📦 Installation

### 1. Install Dependencies
```bash
npm install
```

### 2. Environment Setup
Copy the example environment file and configure for your backend:
```bash
cp .env.example .env
```

Edit `.env` with your API endpoint:
```
VITE_API_BASE_URL=http://localhost:3000/api
```

### 3. Create `.env.local` for Development
```bash
# .env.local
VITE_API_BASE_URL=http://localhost:3000/api
```

## 🚀 Running the Application

### Development Mode
```bash
npm run dev
```
The app will be available at `http://localhost:5173`

### Production Build
```bash
npm run build
```

### Preview Production Build
```bash
npm run preview
```

## 📁 Project Structure

```
src/
├── components/
│   ├── Header.jsx          # Main header with logout
│   ├── Navigation.jsx      # Sidebar navigation
│   ├── Alert.jsx           # Alert component
│   └── ProtectedRoute.jsx  # Route protection
├── pages/
│   ├── SignIn.jsx          # Login dashboard
│   ├── Dashboard.jsx       # Central navigation
│   ├── AttendanceView.jsx  # Attendance records
│   ├── EnrollmentHub.jsx   # Student enrollment
│   └── ManualOverride.jsx  # Override failed records
├── services/
│   ├── api.js              # Axios API client & endpoints
│   ├── auth.js             # Authentication utilities
├── App.jsx                 # Main app with routing
├── main.jsx                # React entry point
└── index.css               # Global styles

public/
└── vite.svg

Configuration Files:
├── package.json            # Dependencies
├── vite.config.js          # Vite configuration
├── tailwind.config.js      # Tailwind configuration
├── postcss.config.js       # PostCSS configuration
└── index.html              # HTML entry point
```

## 🔑 Key Components

### API Service Layer (`src/services/api.js`)
Comprehensive API client with endpoints for:
- **/auth** - Login/Logout
- **/admins** - Admin profile management
- **/students** - Student data
- **/enrollments** - Enrollment management
- **/attendance** - Attendance tracking
- **/classes** - Class management

### Authentication Service (`src/services/auth.js`)
- Token storage and retrieval
- User session management
- Login/Logout handling

### Navigation System
- Protected routes that redirect unauthenticated users to `/signin`
- Dynamic navigation based on current page
- Logout functionality

## 🔐 Authentication Flow

1. User navigates to `/signin`
2. Enters email and password
3. System calls `/api/auth/login`
4. Token and user data stored in localStorage
5. User redirected to dashboard (`/`)
6. Routes check authentication before rendering
7. Logout clears session and redirects to signin

## 📊 Database Schema Integration

The application integrates with the following tables:

### `students`
- Student ID, Name, Grade, Section
- Active status

### `student_embeddings`
- 512-d ArcFace facial embeddings
- Quality scores, Version tracking

### `classes`
- Class name, Grade, Section
- Teacher assignment

### `enrollments`
- Student enrollment records
- Status: pending, processing, completed, failed, re_enroll
- Quality scores and embedding status

### `student_attendance`
- Attendance records with timestamp
- Confidence scores from AI
- Manual override flags and reasons
- Location tracking

### `admins`
- User accounts (Teachers/Admins)
- Role-based access control
- Password authentication

## 🎨 UI/UX Features

- **Responsive Design:** Works on desktop, tablet, and mobile
- **Tailwind CSS:** Utility-first styling with custom theme
- **Real-time Updates:** Live attendance and enrollment status
- **Visual Indicators:** Status badges, progress bars, alerts
- **Modal Dialogs:** For confirmations and detailed actions
- **Data Tables:** Sortable, filterable records
- **Error Handling:** User-friendly error messages
- **Loading States:** Visual feedback during async operations

## 📝 Usage Examples

### View Today's Attendance
1. Navigate to **Attendance** section
2. Select a class from dropdown
3. Choose today's date
4. View all student attendance records

### Enroll a New Student
1. Go to **Enrollment Hub**
2. Select the class and student
3. Click "Upload Image"
4. Select a clear frontal face photo
5. System processes facial embedding

### Override Failed Recognition
1. Go to **Manual Override**
2. Select class and date
3. Review records with low confidence
4. Click "Override" button
5. Select new status and provide reason
6. Confirm override (audit trail recorded)

## 🔗 API Integration

The application expects a backend API at `http://localhost:3000/api` with the following endpoints:

### Authentication
```
POST   /auth/login
POST   /auth/logout
```

### Admin
```
GET    /admins/profile
PUT    /admins/profile
```

### Students
```
GET    /students?classId={id}
GET    /students/{id}
POST   /students
PUT    /students/{id}
```

### Enrollment
```
GET    /enrollments
GET    /enrollments/{id}
POST   /enrollments
PATCH  /enrollments/{id}/status
POST   /enrollments/{id}/upload
```

### Attendance
```
GET    /attendance/today?classId={id}
GET    /attendance/history?studentId={id}&startDate={date}&endDate={date}
GET    /attendance/class?classId={id}&date={date}
POST   /attendance
PATCH  /attendance/{id}/override
```

### Classes
```
GET    /classes
GET    /classes/{id}
GET    /classes/{id}/students
```

## 🌐 Environment Variables

```
VITE_API_BASE_URL    # Backend API base URL
VITE_APP_NAME        # Application display name
```

## 🚨 Error Handling

The application includes:
- Network error handling with user-friendly messages
- Form validation
- Token expiration handling
- API error responses display
- Loading and error states

## 📱 Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## 🔐 Security Features

- JWT token-based authentication
- Local storage for secure token management
- HTTPS support
- CORS configuration
- Protected routes

## 📈 Performance

- Lazy loading for routes
- Optimized re-renders with React
- CSS minification with Tailwind
- Code splitting with Vite

## 🐛 Known Limitations

- Requires backend API running separately
- LocalStorage browser support required
- HTTPS recommended for production

## 📄 License

All rights reserved © 2026 Cybernations Project

## 👥 Support

For issues or questions regarding the presentation layer:
1. Check API connectivity
2. Verify environment variables
3. Review browser console for errors
4. Check backend API logs

## 🎯 Next Steps

1. Set up backend API server
2. Configure environment variables
3. Run `npm install`
4. Start development server with `npm run dev`
5. Test all 5 dashboards with sample data

---

**Happy Attendance Tracking! 📚👨‍🎓**
