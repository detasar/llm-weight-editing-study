import { defineConfig } from 'vite';
export default defineConfig({publicDir:'delivery-public',base: process.env.PAGES ? '/llm-weight-editing-study/' : './',build:{chunkSizeWarningLimit:6500}});
