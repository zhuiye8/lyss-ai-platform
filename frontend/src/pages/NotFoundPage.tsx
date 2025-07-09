/**
 * Lyss AI Platform - 404页面
 * 功能描述: 页面未找到的错误页面
 * 作者: Claude AI Assistant
 * 创建时间: 2025-07-09
 * 最后更新: 2025-07-09
 */

import React from 'react'
import { Result, Button } from 'antd'
import { useNavigate } from 'react-router-dom'

/**
 * 404错误页面
 */
const NotFoundPage: React.FC = () => {
  const navigate = useNavigate()

  const handleGoHome = () => {
    navigate('/dashboard')
  }

  const handleGoBack = () => {
    navigate(-1)
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <Result
        status="404"
        title="404"
        subTitle="抱歉，您访问的页面不存在。"
        extra={
          <div className="space-x-4">
            <Button type="primary" onClick={handleGoHome}>
              返回首页
            </Button>
            <Button onClick={handleGoBack}>
              返回上页
            </Button>
          </div>
        }
      />
    </div>
  )
}

export default NotFoundPage