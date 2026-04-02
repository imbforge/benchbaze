import { defineConfig } from "vite"; // Add this import
import react from "@vitejs/plugin-react";

export default defineConfig({ // Wrap with defineConfig
  base: "./",
  plugins: [react()],
  build: {
    outDir: "dist"
  },
  optimizeDeps: {
    esbuildOptions: {
      loader: {
        ".js": "jsx",
      },
    },
  },
  define: {
    // By default, Vite doesn't include shims for NodeJS/
    // necessary for segment analytics lib to work
    // global: {},
  },
});
