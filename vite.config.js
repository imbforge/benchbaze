import { defineConfig, transformWithEsbuild } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ command }) => ({
  // Use /ove_dev/ in dev so asset URLs stay under the proxied nginx location.
  // Keep relative base for production build output.
  base: command === "serve" ? "/ove_dev/" : "./",
  plugins: [
    // Rollup's acorn parser can't handle JSX. Pre-transform any .js files from
    // @teselagen/ove (which ships uncompiled JSX source) before Rollup sees them.
    {
      name: "transform-ove-jsx",
      enforce: "pre",
      async transform(code, id) {
        if (id.includes("@teselagen/ove") && id.endsWith(".js")) {
          return transformWithEsbuild(code, id, { loader: "jsx" });
        }
      }
    },
    react({
      include: [/\.jsx?$/, /\.tsx?$/]
    })
  ],
  build: {
    outDir: "dist",
    // OVE/editor bundles are large by nature; keep warnings useful by raising this threshold.
    chunkSizeWarningLimit: 3000
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
}));
