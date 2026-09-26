import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

// Backend address for the dev server. In Docker, nginx proxies the requests.
const backendUrl = process.env.VITE_BACKEND_URL ?? 'http://localhost:5000'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  // cubing.js generates scrambles in a module worker, and that worker loads the
  // cubing chunks. Vite wraps dynamic imports in its preload helper, which by
  // default lands in the main app chunk and uses `document`. Inside a worker that
  // means executing the whole app and failing on `document`, so:
  // 1. the helper gets its own chunk, and cubing chunks never import the app;
  // 2. cubing chunks are named `cubing-*`, and their dynamic imports get no
  //    preload list, so the helper does not touch `document` in the worker.
  build: {
    modulePreload: {
      resolveDependencies: (_file, deps, { hostId }) =>
        hostId.includes('/cubing-') ? [] : deps,
    },
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [{ name: 'preload-helper', test: /vite\/preload-helper/ }],
        },
        chunkFileNames: (chunk) =>
          chunk.moduleIds.some((id) => id.includes('/node_modules/cubing/'))
            ? 'assets/cubing-[name]-[hash].js'
            : 'assets/[name]-[hash].js',
      },
    },
  },
  server: {
    proxy: {
      '/api': {
        target: backendUrl,
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'node',
  },
})
