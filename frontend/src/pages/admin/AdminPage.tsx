/**
 * Lyss AI Platform - 管理页面
 * 功能描述: 系统管理和租户管理
 * 作者: Claude AI Assistant
 * 创建时间: 2025-07-09
 * 最后更新: 2025-07-09
 */

import React from 'react'
import { Card, Typography } from 'antd'

const { Title } = Typography

/**
 * 管理页面组件
 */
const AdminPage: React.FC = () => {
  return (
    <div className="p-6">
      <Title level={2} className="mb-6">
        系统管理
      </Title>
      
      <Card>
        <div className="text-center py-8 text-gray-500">
          <div className="text-4xl mb-4">👥</div>
          <p>管理功能正在开发中...</p>
          <p className="text-sm mt-2">即将支持用户管理、租户管理、系统监控等功能</p>
        </div>
      </Card>
    </div>
  )
}

export default AdminPage