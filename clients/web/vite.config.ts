import { defineConfig, type Plugin } from "vite";

// Dev: proxy all API traffic to the single gateway entry point on :8000.
// The gateway routes /api/<service>/<path> to the right upstream.
export default defineConfig({
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  plugins: [cspPlugin()],
});

// Inject a Content-Security-Policy only for production builds (Vite dev
// relies on inline scripts/eval that a strict CSP would break).
function cspPlugin(): Plugin {
  const csp = [
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self'",
    "img-src 'self' data: blob:",
    "media-src 'self' blob: https:",
    "connect-src 'self' https: ws:",
    "font-src 'self' data:",
    "object-src 'none'",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ].join("; ");
  return {
    name: "inject-csp",
    apply: "build",
    transformIndexHtml(html: string) {
      const meta = `<meta http-equiv="Content-Security-Policy" content="${csp}" />`;
      return html.replace("</head>", `${meta}</head>`);
    },
  };
}