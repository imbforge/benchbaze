import { defineConfig } from "vite"; // Add this import
import react from "@vitejs/plugin-react";

export default defineConfig({
  // Wrap with defineConfig
  base: "./",
  plugins: [react()],
  build: {
    outDir: "dist",
    // OVE/editor bundles are large by nature; keep warnings useful by raising this threshold.
    chunkSizeWarningLimit: 3000,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("@teselagen/ove")) {
            return "ove";
          }
          if (id.includes("@teselagen/bio-parsers")) {
            return "bio-parsers";
          }
          if (id.includes("@blueprintjs") || id.includes("@teselagen/ui")) {
            return "ui-vendor";
          }
          if (id.includes("node_modules")) {
            return "vendor";
          }
        }
      }
    }
  },
  optimizeDeps: {
    esbuildOptions: {
      loader: {
        ".js": "jsx"
      }
    }
  },
  define: {
    // By default, Vite doesn't include shims for NodeJS/
    // necessary for segment analytics lib to work
    // global: {},
  }
});
