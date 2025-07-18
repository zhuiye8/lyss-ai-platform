import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

// Vite配置 - 根据docs/frontend.md规范
export default defineConfig({
  plugins: [react()],
  
  // 路径别名配置
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      '@/components': resolve(__dirname, 'src/components'),
      '@/pages': resolve(__dirname, 'src/pages'),
      '@/services': resolve(__dirname, 'src/services'),
      '@/types': resolve(__dirname, 'src/types'),
      '@/utils': resolve(__dirname, 'src/utils'),
      '@/store': resolve(__dirname, 'src/store'),
      '@/hooks': resolve(__dirname, 'src/hooks'),
      '@/assets': resolve(__dirname, 'src/assets'),
      '@/styles': resolve(__dirname, 'src/styles'),
    },
  },
  
  // 开发服务器配置
  server: {
    host: '0.0.0.0',
    port: 3000,
    open: false,
    
    // API代理到Backend API Gateway
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api/, '/api'), // 保持原路径
      },
    },
  },
  
  // 构建配置
  build: {
    target: 'es2015',
    outDir: 'dist',
    sourcemap: true,
    minify: 'terser',
    
    // 代码分割优化
    rollupOptions: {
      output: {
        manualChunks: {
          // React相关
          vendor: ['react', 'react-dom'],
          // Ant Design相关
          antd: ['antd', '@ant-design/icons', '@ant-design/x'],
          // 路由相关
          router: ['react-router-dom'],
          // 状态管理
          store: ['zustand'],
          // 工具库
          utils: ['axios', 'dayjs', 'lodash-es'],
        },
        // 资源命名
        chunkFileNames: 'assets/js/[name]-[hash].js',
        entryFileNames: 'assets/js/[name]-[hash].js',
        assetFileNames: 'assets/[ext]/[name]-[hash].[ext]',
      },
    },
    
    // 警告阈值
    chunkSizeWarningLimit: 1000,
  },
  
  // CSS配置
  css: {
    modules: {
      localsConvention: 'camelCase',
    },
    preprocessorOptions: {
      less: {
        javascriptEnabled: true,
      },
    },
  },
  
  // 环境变量前缀
  envPrefix: 'VITE_',
  
  // 定义全局常量
  define: {
    __APP_VERSION__: JSON.stringify(process.env.npm_package_version),
    __BUILD_TIME__: JSON.stringify(new Date().toISOString()),
  },
});