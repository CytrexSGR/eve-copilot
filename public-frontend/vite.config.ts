import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api/wormhole": {
        target: "http://localhost:8012",
        changeOrigin: true
      },
      "/api/powerbloc": {
        target: "http://localhost:8002",
        changeOrigin: true
      },
      "/api/war": {
        target: "http://localhost:8002",
        changeOrigin: true
      },
      "/api/auth": {
        target: "http://localhost:8010",
        changeOrigin: true
      },
      "/api/tier": {
        target: "http://localhost:8010",
        changeOrigin: true
      },
      "/api/settings": {
        target: "http://localhost:8010",
        changeOrigin: true
      },
      "/api/scheduler": {
        target: "http://localhost:8003",
        changeOrigin: true
      },
      "/api/jobs": {
        target: "http://localhost:8003",
        changeOrigin: true
      },
      "/api/market": {
        target: "http://localhost:8004",
        changeOrigin: true
      },
      "/api/production": {
        target: "http://localhost:8005",
        changeOrigin: true
      },
      "/api/shopping": {
        target: "http://localhost:8006",
        changeOrigin: true
      },
      "/api/character": {
        target: "http://localhost:8007",
        changeOrigin: true
      },
      "/api/fittings": {
        target: "http://localhost:8007",
        changeOrigin: true
      },
      "/api/mastery": {
        target: "http://localhost:8007",
        changeOrigin: true
      },
      "/api/skills": {
        target: "http://localhost:8007",
        changeOrigin: true
      },
      "/api/research": {
        target: "http://localhost:8007",
        changeOrigin: true
      },
      "/api/hunter": {
        target: "http://localhost:8004",
        changeOrigin: true
      },
      "/api/trading": {
        target: "http://localhost:8004",
        changeOrigin: true
      },
      "/api/alerts": {
        target: "http://localhost:8004",
        changeOrigin: true
      },
      "/api/goals": {
        target: "http://localhost:8004",
        changeOrigin: true
      },
      "/api/history": {
        target: "http://localhost:8004",
        changeOrigin: true
      },
      "/api/bookmarks": {
        target: "http://localhost:8004",
        changeOrigin: true
      },
      "/api/portfolio": {
        target: "http://localhost:8004",
        changeOrigin: true
      },
      "/api/items": {
        target: "http://localhost:8004",
        changeOrigin: true
      },
      "/api/materials": {
        target: "http://localhost:8004",
        changeOrigin: true
      },
      "/api/route": {
        target: "http://localhost:8004",
        changeOrigin: true
      },
      "/api/pi": {
        target: "http://localhost:8005",
        changeOrigin: true
      },
      "/api/mining": {
        target: "http://localhost:8005",
        changeOrigin: true
      },
      "/api/supply-chain": {
        target: "http://localhost:8005",
        changeOrigin: true
      },
      "/api/reactions": {
        target: "http://localhost:8005",
        changeOrigin: true
      },
      "/api/dps": {
        target: "http://localhost:8002",
        changeOrigin: true
      },
      "/api/risk": {
        target: "http://localhost:8002",
        changeOrigin: true
      },
      "/api/reports": {
        target: "http://localhost:8002",
        changeOrigin: true
      },
      "/api/fingerprints": {
        target: "http://localhost:8002",
        changeOrigin: true
      },
      "/api/alliances": {
        target: "http://localhost:8002",
        changeOrigin: true
      },
      "/api/intelligence": {
        target: "http://localhost:8002",
        changeOrigin: true
      },
      "/api/fleet": {
        target: "http://localhost:8002",
        changeOrigin: true
      },
      "/api/sovereignty": {
        target: "http://localhost:8002",
        changeOrigin: true
      },
      "/api/contracts": {
        target: "http://localhost:8002",
        changeOrigin: true
      },
      "/api/jump": {
        target: "http://localhost:8002",
        changeOrigin: true
      },
      "/api/timers": {
        target: "http://localhost:8002",
        changeOrigin: true
      },
      "/api/moon": {
        target: "http://localhost:8002",
        changeOrigin: true
      },
      "/api/fuel": {
        target: "http://localhost:8002",
        changeOrigin: true
      },
      "/api/wallet": {
        target: "http://localhost:8002",
        changeOrigin: true
      },
      "/api/corp-contracts": {
        target: "http://localhost:8002",
        changeOrigin: true
      },
      "/api/events": {
        target: "http://localhost:8002",
        changeOrigin: true
      },
      "/mcp": {
        target: "http://localhost:8008",
        changeOrigin: true
      },
      "/api/dashboard": {
        target: "http://localhost:8000",
        changeOrigin: true
      },
      "/ectmap": {
        target: "http://localhost:3001",
        changeOrigin: true
      },
      "/api/dotlan": {
        target: "http://localhost:8014",
        changeOrigin: true
      },
      "/api/finance": {
        target: "http://localhost:8016",
        changeOrigin: true
      },
      "/api/hr": {
        target: "http://localhost:8015",
        changeOrigin: true
      },
      "/api/sde": {
        target: "http://localhost:8007",
        changeOrigin: true
      },
      "/api/feedback": {
        target: "http://localhost:8000",
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: "dist",
    sourcemap: false,
    minify: "esbuild",
    chunkSizeWarningLimit: 500,
    rollupOptions: {
      output: {
        manualChunks: {
          "react-vendor": ["react", "react-dom"],
          "routing": ["react-router-dom"],
          "data": ["@tanstack/react-query", "axios"],
          "charts": ["chart.js", "react-chartjs-2"],
          "icons": ["lucide-react"]
        }
      }
    }
  }
});
