# Getting Started - Quick Setup Guide

## 🚀 Prerequisites

Before you begin, ensure you have:
- ✅ Node.js 16+ installed ([Download](https://nodejs.org/))
- ✅ npm 8+ (comes with Node.js)
- ✅ Git (optional, for version control)
- ✅ A code editor (VS Code recommended)

Check your versions:
```bash
node --version
npm --version
```

---

## 📦 Installation Steps

### Step 1: Install Dependencies
Navigate to the project directory and install all required packages:

```bash
cd project_sandy_presentation_layer
npm install
```

This installs:
- React 18
- React Router 6
- Axios
- Tailwind CSS
- Vite build tools

**⏱️ Time: ~2-3 minutes** (depends on internet speed)

---

### Step 2: Configure Environment

#### Create `.env.local` file in the project root:

```bash
VITE_API_BASE_URL=http://localhost:3000/api
```

**Environment Variables:**
- `VITE_API_BASE_URL` - Your backend API endpoint
- Default: `http://localhost:3000/api`
- For production: Update to your production URL

#### Example for different environments:

**Development (.env.local):**
```
VITE_API_BASE_URL=http://localhost:3000/api
```

**Production (.env.production):**
```
VITE_API_BASE_URL=https://api.yourdomain.com
```

---

## 🎮 Running the Application

### Development Mode (Recommended for Development)

Start the development server:
```bash
npm run dev
```

**Output:**
```
  VITE v5.0.0  ready in 245 ms

  ➜  Local:   http://localhost:5173/
  ➜  press h to show help
```

Open your browser to `http://localhost:5173/`

**Features:**
- ⚡ Hot Module Replacement (HMR) - See changes instantly
- 🔧 Developer tools
- 📊 Vite dashboard

### Production Build

Build optimized version:
```bash
npm run build
```

**Output:**
```
dist/
├── index.html
├── assets/
│   ├── main-xxxxx.js
│   └── style-xxxxx.css
```

Preview build locally:
```bash
npm run preview
```

---

## 🎯 First Time Setup Walkthrough

### 1. **Complete Installation**
```bash
npm install
```

### 2. **Create Environment File**
Create `.env.local`:
```
VITE_API_BASE_URL=http://localhost:3000/api
```

### 3. **Start Development Server**
```bash
npm run dev
```

### 4. **Open in Browser**
Navigate to: `http://localhost:5173/`

### 5. **See Login Page**
You should see the Sign-in dashboard with:
- School icon 🎓
- Email input field
- Password input field
- Login button
- Demo credentials info

### 6. **Prepare Test Data**
Ensure your backend API has:
- Sample admin account (for login)
- Sample classes
- Sample students
- Sample enrollment records

---

## ✅ Verification Checklist

After setup, verify everything works:

- [ ] `npm install` completed without errors
- [ ] `.env.local` file created
- [ ] `npm run dev` starts without errors
- [ ] Browser opens to `http://localhost:5173/`
- [ ] Sign-in page displays correctly
- [ ] Tailwind styles load (colors and layout look good)
- [ ] Backend API is running (if testing login)

---

## 🧪 Testing the Dashboards

### Test Each Dashboard:

**1. Sign-In Dashboard**
- Try logging in with test credentials
- Verify error handling with wrong password
- Check loading states

**2. Central Navigation**
After login:
- Verify dashboard loads
- Click each navigation card
- Check statistics display

**3. Attendance View**
- Select a class from dropdown
- Change date
- Filter by status
- Verify table displays

**4. Enrollment Hub**
- Select class
- Filter by status
- Try upload modal (no backend needed)

**5. Manual Override**
- Select class and date
- Review failed records
- Test override modal

---

## 🐛 Troubleshooting

### Issue: Port 5173 already in use

**Solution 1:** Kill the process on that port
```bash
# Windows PowerShell
netstat -ano | findstr :5173
taskkill /PID <PID> /F

# Mac/Linux
lsof -i :5173
kill -9 <PID>
```

**Solution 2:** Use a different port
```bash
npm run dev -- --port 5174
```

---

### Issue: "Cannot GET /" when opening in browser

**Possible Causes:**
- Vite dev server not running
- Using wrong URL
- Browser cached old version

**Solutions:**
- Make sure `npm run dev` is running
- Check terminal output for the correct URL
- Hard refresh browser (Ctrl+Shift+R or Cmd+Shift+R)
- Clear browser cache

---

### Issue: Styles not loading (no Tailwind CSS)

**Possible Causes:**
- PostCSS not processing
- Tailwind config not found
- Branch selection issue

**Solutions:**
```bash
# Clear node_modules and reinstall
rm -r node_modules
npm install

# Clear npm cache
npm cache clean --force
npm install
```

---

### Issue: API calls fail (Network Error)

**Possible Causes:**
- Backend API not running
- Wrong API URL in `.env.local`
- CORS issues

**Solutions:**
1. Start your backend API server
2. Verify `VITE_API_BASE_URL` in `.env.local`
3. Check backend is accessible:
   ```bash
   curl http://localhost:3000/api
   ```

---

### Issue: "Cannot find module" errors

**Solution:**
```bash
rm -r node_modules package-lock.json
npm install
```

---

## 📚 Useful Commands

```bash
# Development
npm run dev              # Start dev server

# Building
npm run build            # Build for production
npm run preview          # Preview production build locally

# Maintenance
npm list                 # List installed packages
npm outdated             # Check for outdated packages
npm update               # Update packages
npm install <package>    # Install new package

# Cleaning
npm cache clean --force  # Clear npm cache
rm -r node_modules       # Delete node_modules folder
```

---

## 🗂️ File Organization After Installation

```
project_sandy_presentation_layer/
├── node_modules/              # Installed packages
├── src/
│   ├── components/            # Reusable components
│   ├── pages/                 # Dashboard pages
│   ├── services/              # API & auth services
│   ├── App.jsx                # Main app component
│   ├── main.jsx               # Entry point
│   └── index.css              # Global styles
├── public/                    # Static assets
├── dist/                      # Build output (after npm run build)
├── .env.local                 # Local environment variables
├── .env.example               # Example environment
├── package.json               # Dependencies & scripts
├── vite.config.js             # Vite configuration
├── tailwind.config.js         # Tailwind configuration
├── index.html                 # HTML template
├── README.md                  # Full documentation
└── README_QUICK_START.md      # This file
```

---

## 🎨 Development Tips

### Hot Reload (Auto-Refresh)
Changes to `.jsx` and `.css` files automatically refresh in browser - no manual reload needed!

### Browser DevTools
Press `F12` to open Developer Tools:
- **Console:** See logs and errors
- **Network:** Check API calls
- **Components:** Inspect React component tree (React DevTools extension)

### VSCode Extensions to Install
```
- ES7+ React/Redux/React-Native snippets
- Tailwind CSS IntelliSense
- Prettier (Code formatter)
- REST Client (for testing API endpoints)
```

---

## 📱 Testing on Different Devices

### Mobile Testing
```bash
# Find your computer's local IP
# Windows: ipconfig
# Mac/Linux: ifconfig

# Access from phone on same network:
# http://<YOUR_IP>:5173/
```

Example:
```
Your IP: 192.168.1.100
Mobile URL: http://192.168.1.100:5173/
```

Make sure phone is on same WiFi network!

---

## 🚀 Next Steps After Setup

1. **Explore the Code**
   - Read `PROJECT_MANIFEST.md` for detailed structure
   - Review each `.jsx` file to understand components
   - Check API endpoints in `services/api.js`

2. **Connect Backend**
   - Set up your Node/Express backend API
   - Implement the endpoints from README.md
   - Test API connections

3. **Add Test Data**
   - Create sample admin account
   - Add test students and classes
   - Create sample enrollment records

4. **Customize**
   - Update colors in `tailwind.config.js`
   - Modify logo/branding
   - Add company logo to header
   - Customize theme colors

5. **Deploy**
   - Build project: `npm run build`
   - Deploy `dist/` folder to hosting service
   - Configure production environment variables

---

## 📞 Getting Help

If you encounter issues:

1. **Check the Logs**
   - Terminal output for build errors
   - Browser console (DevTools) for runtime errors

2. **Review Documentation**
   - [Vite Docs](https://vitejs.dev/)
   - [React Docs](https://react.dev/)
   - [Tailwind Docs](https://tailwindcss.com/docs)
   - [React Router Docs](https://reactrouter.com/)

3. **Common Issues**
   - See **Troubleshooting** section above

---

## ✨ You're Ready!

Your React + Vite + Tailwind facial recognition attendance system is now set up!

**Happy coding! 🎉**

---

**Questions?** Refer to:
- `README.md` - Full documentation
- `PROJECT_MANIFEST.md` - Architecture overview
- `AI SCHEMA CONTEXT.txt` - Database schema
