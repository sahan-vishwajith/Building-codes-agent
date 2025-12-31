# Render Deployment Guide for EEBC Advisor

This document walks you through deploying your Flask + React app to Render.

## What's Been Set Up

✅ **Backend (Flask)** — Configured for Render as a Python Web Service
- Gunicorn start command configured
- Environment-aware index loading (can skip expensive rebuild on deploy)
- Health check endpoint at `/health`
- Bind to 0.0.0.0:$PORT (Render's PORT env var)

✅ **Frontend (React + Vite)** — Configured for Render as a Static Site
- npm build command ready
- dist folder will be served as static files

✅ **Files Created/Modified:**
- `render.yaml` — Infrastructure as Code (defines both services)
- `eebc-advisor/backend/app.py` — Updated to read env vars (HOST, PORT, FLASK_DEBUG, SKIP_INDEX_BUILD)
- `eebc-advisor/backend/requirements.txt` — Added gunicorn
- `eebc-advisor/backend/Procfile` — Alternative start command definition
- `eebc-advisor/backend/runtime.txt` — Python version pinned to 3.11.8

---

## Deployment Steps

### Step 1: Verify Your Git Repository

Make sure your repo is set up and all files are committed:

```powershell
cd C:\Users\sahan\PycharmProjects\Building-2
git status
```

If it's not a git repo yet:
```powershell
git init
git add .
git commit -m "Initial commit with Render deployment config"
git remote add origin <your-github-repo-url>
git push -u origin main
```

### Step 2: Commit Render Deployment Files

```powershell
git add render.yaml eebc-advisor/backend/app.py eebc-advisor/backend/requirements.txt eebc-advisor/backend/Procfile eebc-advisor/backend/runtime.txt
git commit -m "Add Render deployment configuration"
git push
```

### Step 3: Connect Your Repository to Render

1. Go to [https://render.com](https://render.com)
2. Sign up or log in with your GitHub account
3. In the dashboard, click **"New +"** → **"Web Service"** (or **"Blueprint"** to use render.yaml)
4. If using **Blueprint** (recommended):
   - Select your GitHub repository
   - Render will automatically detect and create both services from `render.yaml`
5. If creating services manually:
   - Create a **Web Service** for the backend (root: `eebc-advisor/backend`)
   - Create a **Static Site** for the frontend (root: `eebc-advisor/frontend`)

### Step 4: Set Environment Variables / Secrets

In the Render dashboard, go to your backend service's **Settings** → **Environment**:

**Required Secret:**
- Key: `GROQ_API_KEY`
- Value: `<your-groq-api-key>` (get from [https://console.groq.com](https://console.groq.com))

**Optional Environment Variables:**
- `FLASK_ENV` = `production` (already set in render.yaml)
- `SKIP_INDEX_BUILD` = `true` (already set in render.yaml to avoid long startup)

### Step 5: Handle Index Files

Since `SKIP_INDEX_BUILD=true`, the app expects `index.faiss` and `chunks.json` to already exist:

**Option A: Commit to Repository (Simple)**
```powershell
# If the files don't exist yet, the app will build them on first run
# To build locally and commit:
cd eebc-advisor/backend
python app.py  # This will build the index
git add data/index.faiss data/chunks.json
git commit -m "Add pre-built FAISS index"
git push
```

**Option B: Upload to Render Persistent Disk (For Large Files)**
- Contact Render support if the files are too large to commit
- Or build the index on first deploy by temporarily setting `SKIP_INDEX_BUILD=false`

### Step 6: Deploy

Once you've connected your repo:
1. Render will automatically deploy when you push to your branch
2. Monitor the deployment in the Render dashboard
3. Check the logs if there are any issues

### Step 7: Test Your Deployment

After deployment completes:

**Backend health check:**
```powershell
curl https://<your-backend-url>.onrender.com/health
# Should return: {"ok": true}
```

**Frontend:**
Open `https://<your-frontend-url>.onrender.com` in your browser

---

## Troubleshooting

### Build Fails: "ModuleNotFoundError"
- Make sure `requirements.txt` is in `eebc-advisor/backend/` ✓
- Make sure all Python imports are correct

### App Starts but Returns 502 Bad Gateway
- Check health check path in Render service settings
- Verify GROQ_API_KEY is set as a secret
- Check logs in Render dashboard

### Index Files Not Found
- If you set `SKIP_INDEX_BUILD=true` but didn't provide index files:
  - Either commit the pre-built files to repo, or
  - Temporarily set `SKIP_INDEX_BUILD=false` in Render to build on first deploy
- Monitor the startup time if building (may take several minutes)

### Frontend Not Deployed
- Ensure the Static Site build command is: `npm ci && npm run build`
- Verify `dist` folder is the publish directory
- Check `eebc-advisor/frontend/package.json` has `build` script ✓

---

## Service URLs After Deployment

Once deployed, you'll have:
- **Backend API:** `https://eebc-advisor-backend.onrender.com`
- **Frontend:** `https://eebc-advisor-frontend.onrender.com`

Update your frontend React code to point to the backend API URL. In your frontend React app (e.g., `src/App.jsx`), replace any `localhost:5000` with the Render backend URL.

---

## Local Testing (Optional)

Before deploying, you can test locally:

### Test Frontend Build
```powershell
cd eebc-advisor/frontend
npm ci
npm run build
```

### Test Backend with Gunicorn
```powershell
cd eebc-advisor/backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:GROQ_API_KEY="your_key_here"
gunicorn --bind 0.0.0.0:5000 --workers 2 --threads 4 --timeout 120 app:app
```

Then visit `http://localhost:5000/health` in your browser.

---

## Summary

- ✅ Files are configured for Render
- ✅ render.yaml defines both services
- ✅ app.py reads environment variables
- ✅ gunicorn added to requirements
- 📋 Next: Push to GitHub, connect repo to Render, set GROQ_API_KEY secret, deploy!

For more info: [Render Docs](https://render.com/docs)

