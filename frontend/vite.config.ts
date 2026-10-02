import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Route-based code splitting: every page except the Catalog is loaded via
// React.lazy(), so the initial bundle stays small. Vendor libraries are split
// into their own chunks so they can be cached independently of app code.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          "react-vendor": ["react", "react-dom", "react-router-dom"],
          "axios-vendor": ["axios"],
          "markdown-vendor": ["react-markdown"],
        },
      },
    },
  },
});
