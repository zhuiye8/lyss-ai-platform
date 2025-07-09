/**
 * Lyss AI Platform - 设置页面
 * 功能描述: 用户设置和系统配置
 * 作者: Claude AI Assistant
 * 创建时间: 2025-07-09
 * 最后更新: 2025-07-09
 */

import React from 'react'
import { Card, Typography } from 'antd'

const { Title } = Typography

/**
 * 设置页面组件
 */
const SettingsPage: React.FC = () => {
  return (
    <div className="p-6">
      <Title level={2} className="mb-6">
        系统设置
      </Title>
      
      <Card>
        <div className="text-center py-8 text-gray-500">
          <div className="text-4xl mb-4">⚙️</div>
          <p>设置功能正在开发中...</p>
          <p className="text-sm mt-2">即将支持用户偏好、AI模型配置、通知设置等功能</p>
        </div>
      </Card>
    </div>
  )
}

export default SettingsPage