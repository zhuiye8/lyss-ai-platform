/**
 * Lyss AI Platform - 加载页面
 * 功能描述: 全屏加载页面组件
 * 作者: Claude AI Assistant
 * 创建时间: 2025-07-09
 * 最后更新: 2025-07-09
 */

import React from 'react'
import { Spin } from 'antd'

interface LoadingPageProps {
  tip?: string
  size?: 'small' | 'default' | 'large'
}

/**
 * 全屏加载页面
 */
const LoadingPage: React.FC<LoadingPageProps> = ({ 
  tip = '系统初始化中...', 
  size = 'large' 
}) => {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-50">
      {/* Logo */}
      <div className="mb-8">
        <div className="text-3xl font-bold text-blue-600 mb-2">
          Lyss AI Platform
        </div>
        <div className="text-sm text-gray-500 text-center">
          企业级AI服务聚合与管理平台
        </div>
      </div>

      {/* 加载指示器 */}
      <Spin size={size} tip={tip} />

      {/* 版权信息 */}
      <div className="mt-16 text-xs text-gray-400 text-center">
        <p>© 2025 Lyss AI Platform. All rights reserved.</p>
        <p>Powered by Claude AI Assistant</p>
      </div>
    </div>
  )
}

export default LoadingPage