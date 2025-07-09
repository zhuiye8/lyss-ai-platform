/**
 * Lyss AI Platform - 应用入口文件
 * 功能描述: React应用的主入口，配置全局提供者
 * 作者: Claude AI Assistant
 * 创建时间: 2025-07-09
 * 最后更新: 2025-07-09
 */

import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import dayjs from 'dayjs'
import 'dayjs/locale/zh-cn'

import App from './App'
import './index.css'

// 配置dayjs中文语言
dayjs.locale('zh-cn')

// 创建React Query客户端
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 3,
      staleTime: 5 * 60 * 1000, // 5分钟缓存时间
      gcTime: 10 * 60 * 1000, // 10分钟垃圾回收时间
      refetchOnWindowFocus: false, // 禁用窗口聚焦时重新获取
    },
    mutations: {
      retry: 1, // 变更操作重试1次
    },
  },
})

// 渲染应用
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)