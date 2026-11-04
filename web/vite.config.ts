import { defineConfig } from 'vite';
export default defineConfig({base: process.env.PAGES ? '/llm-weight-editing-study/' : './',build:{chunkSizeWarningLimit:6500}});
