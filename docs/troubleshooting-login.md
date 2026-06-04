# Login Troubleshooting — "Something went wrong"

Follow these steps in order on the affected machine.

---

## Step 1 — Apply migrations

```powershell
python manage.py migrate
```

---

## Step 2 — Start the backend on the correct port

```powershell
python manage.py runserver 3000
```

The port `3000` is required. Omitting it starts Django on `8000` and the frontend won't find it.

---

## Step 3 — Install frontend dependencies (if not done yet)

```powershell
npm install
```

---

## Step 4 — Start the frontend

```powershell
npm run dev
```

---

## Step 5 — Verify both servers are up before logging in

Open a browser and confirm both URLs respond:

- `http://localhost:3000/api/` — should return 403 (not "connection refused")
- `http://localhost:5173/` — should show the sign-in page

---

## Step 6 — If login still fails, check the browser Network tab

1. Open DevTools (`F12`) → **Network** tab
2. Attempt to sign in
3. Click the `login` request and check the status:

| Status | Meaning | Fix |
|--------|---------|-----|
| `(failed)` / `ERR_CONNECTION_REFUSED` | Django not running or on wrong port | Repeat Step 2 |
| `500` | Django crashed | Check the terminal running `runserver` for the traceback |
| `400` / `401` | Credentials don't match the database | Verify you are using the correct username and password for the copied database |
