import { defineConfig } from 'vite'

// A relative base keeps the built app working under the project sub-path GitHub Pages serves it from
// (https://<user>.github.io/visualsimplex/) without hardcoding that path here.
export default defineConfig({
  base: './',
  build: {
    outDir: 'dist',
    target: 'es2022',
  },
})
