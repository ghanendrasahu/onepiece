import { defineConfig } from "vite";

const services: Record<string, number> = {
  identity: 8001,
  catalog: 8002,
  streaming: 8003,
  "ai-guide": 8004,
};

const proxy = Object.fromEntries(
  Object.entries(services).map(([name, port]) => [
    `/api/${name}`,
    {
      target: `http://localhost:${port}`,
      changeOrigin: true,
      rewrite: (path: string) => path.replace(/^\/api\/[^/]+/, ""),
    },
  ]),
);

export default defineConfig({
  server: {
    port: 5173,
    proxy,
  },
});
