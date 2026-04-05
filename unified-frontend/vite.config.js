/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            '@': path.resolve(__dirname, './src'),
        },
    },
    test: {
        globals: true,
        environment: 'jsdom',
        setupFiles: ['./src/test/setup.ts'],
    },
    server: {
        host: '0.0.0.0',
        port: 3000,
        proxy: {
            // Agent/Copilot API - port 8009 (dedicated copilot server with SSE)
            '/api/copilot': {
                target: 'http://localhost:8009',
                changeOrigin: true,
                rewrite: function (path) { return path.replace(/^\/api\/copilot/, '/api/agent'); },
                configure: function (proxy) {
                    proxy.on('proxyRes', function (proxyRes) {
                        var _a;
                        if ((_a = proxyRes.headers['content-type']) === null || _a === void 0 ? void 0 : _a.includes('text/event-stream')) {
                            proxyRes.headers['cache-control'] = 'no-cache';
                            proxyRes.headers['x-accel-buffering'] = 'no';
                        }
                    });
                },
            },
            // All other API requests go through API Gateway (port 8000)
            // API Gateway handles routing to all microservices
            '/api': {
                target: 'http://localhost:8000',
                changeOrigin: true,
            },
        },
    },
    build: {
        outDir: 'dist',
        sourcemap: false,
        minify: 'esbuild',
        chunkSizeWarningLimit: 1000,
        rollupOptions: {
            output: {
                manualChunks: {
                    'react-vendor': ['react', 'react-dom', 'react-router-dom'],
                    'ui-vendor': ['@radix-ui/react-avatar', '@radix-ui/react-dropdown-menu', '@radix-ui/react-tooltip'],
                },
            },
        },
    },
});
