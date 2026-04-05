# Frontend Development - Quick Guide

## ⚡ Fast Development Mode (RECOMMENDED)

**Native Vite Dev Server with Hot Reload:**

```bash
# Start dev server (from project root)
cd public-frontend && ./dev.sh

# OR manually:
npm run dev -- --port 5174 --host 0.0.0.0
```

**Access:**
- Dev Server: http://localhost:5175 (Hot Reload enabled)
- Production: http://localhost:5173 (Docker container)

**Workflow:**
1. Edit files in `src/`
2. Save file
3. Browser auto-reloads (~200ms)
4. No Docker rebuild needed! ✅

---

## 🐳 Production Build (for final testing)

```bash
# From docker directory
cd ../docker
docker compose build public-frontend
docker compose up -d public-frontend

# Access: http://localhost:5173
```

---

## 🎯 Quick Commands

| Command | Purpose | Speed |
|---------|---------|-------|
| `./dev.sh` | Start dev server | ⚡ Instant |
| `npm run build` | Build for production | ~10s |
| `npm run preview` | Preview production build | Fast |

---

## 🔥 Hot Module Replacement (HMR)

Changes are applied **without page reload**:
- React components re-render instantly
- State is preserved
- CSS updates live
- TypeScript errors show in terminal + browser

---

## 🛑 Stop Dev Server

```bash
# Find process
ps aux | grep vite

# Kill by PID
kill <PID>

# Or kill all node processes (careful!)
pkill -f "vite"
```

---

## 📝 Notes

- Dev server runs **outside Docker** for speed
- Uses same `package.json` and dependencies
- Production Docker build still needed for deployment
- Both can run simultaneously (different ports)
