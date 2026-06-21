import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// 挂件开发服务器：端口 5174，避开后端 8000 与管理端 8001。
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    host: '127.0.0.1',
  },
});
