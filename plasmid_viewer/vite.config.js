import react from "@vitejs/plugin-react";

export default {
  base: "./",
  plugins: [react()],
  build: {
    outDir: "./build"
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
};
