/**
 * Lyss AI Platform - 主布局组件
 * 功能描述: 应用主要布局，包含侧边栏、顶部导航等
 * 作者: Claude AI Assistant
 * 创建时间: 2025-07-09
 * 最后更新: 2025-07-09
 */

import React, { useState } from 'react'
import { Layout, Menu, Dropdown, Avatar, Button, Badge, Tooltip } from 'antd'
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  DashboardOutlined,
  MessageOutlined,
  SettingOutlined,
  UserOutlined,
  LogoutOutlined,
  BellOutlined,
  QuestionCircleOutlined,
  TeamOutlined
} from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth, usePermissions } from '@/hooks/useAuth'

const { Header, Sider, Content } = Layout

interface MainLayoutProps {
  children: React.ReactNode
}

/**
 * 主布局组件
 */
const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuth()
  const { isAdmin } = usePermissions()

  // 切换侧边栏
  const toggleSidebar = () => {
    setCollapsed(!collapsed)
  }

  // 处理菜单点击
  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key)
  }

  // 用户下拉菜单
  const userMenu = (
    <Menu>
      <Menu.Item key="profile" icon={<UserOutlined />}>
        <span onClick={() => navigate('/settings')}>个人设置</span>
      </Menu.Item>
      <Menu.Divider />
      <Menu.Item key="logout" icon={<LogoutOutlined />} onClick={logout}>
        退出登录
      </Menu.Item>
    </Menu>
  )

  // 侧边栏菜单项
  const menuItems = [
    {
      key: '/dashboard',
      icon: <DashboardOutlined />,
      label: '仪表盘'
    },
    {
      key: '/conversations',
      icon: <MessageOutlined />,
      label: '对话管理'
    },
    // 管理员菜单
    ...(isAdmin() ? [{
      key: '/admin',
      icon: <TeamOutlined />,
      label: '系统管理'
    }] : []),
    {
      key: '/settings',
      icon: <SettingOutlined />,
      label: '系统设置'
    }
  ]

  // 获取当前选中的菜单
  const getSelectedKey = () => {
    const pathname = location.pathname
    if (pathname.startsWith('/conversations')) return '/conversations'
    if (pathname.startsWith('/admin')) return '/admin'
    if (pathname.startsWith('/settings')) return '/settings'
    return pathname
  }

  return (
    <Layout className="min-h-screen">
      {/* 侧边栏 */}
      <Sider 
        trigger={null} 
        collapsible 
        collapsed={collapsed}
        className="shadow-lg"
        theme="light"
        width={240}
      >
        {/* Logo */}
        <div className={`flex items-center justify-center h-16 border-b border-gray-200 ${
          collapsed ? 'px-2' : 'px-6'
        }`}>
          {collapsed ? (
            <div className="text-xl font-bold text-blue-600">L</div>
          ) : (
            <div className="flex items-center space-x-2">
              <div className="text-xl font-bold text-blue-600">Lyss AI</div>
            </div>
          )}
        </div>

        {/* 菜单 */}
        <Menu
          mode="inline"
          selectedKeys={[getSelectedKey()]}
          className="border-0 h-full"
          items={menuItems}
          onClick={handleMenuClick}
        />
      </Sider>

      {/* 主内容区 */}
      <Layout>
        {/* 顶部导航 */}
        <Header className="bg-white shadow-sm border-b border-gray-200 px-4 flex items-center justify-between">
          {/* 左侧：折叠按钮 */}
          <div className="flex items-center space-x-4">
            <Button
              type="text"
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={toggleSidebar}
              className="text-lg"
            />
            
            {/* 面包屑导航可以在这里添加 */}
          </div>

          {/* 右侧：用户信息和操作 */}
          <div className="flex items-center space-x-4">
            {/* 通知 */}
            <Tooltip title="通知">
              <Badge count={0} size="small">
                <Button 
                  type="text" 
                  icon={<BellOutlined />} 
                  className="text-lg"
                />
              </Badge>
            </Tooltip>

            {/* 帮助 */}
            <Tooltip title="帮助">
              <Button 
                type="text" 
                icon={<QuestionCircleOutlined />} 
                className="text-lg"
              />
            </Tooltip>

            {/* 用户信息 */}
            <div className="flex items-center space-x-3 pl-4 border-l border-gray-200">
              <div className="text-right text-sm">
                <div className="font-medium text-gray-900">
                  {user?.first_name && user?.last_name 
                    ? `${user.first_name} ${user.last_name}` 
                    : user?.username || user?.email
                  }
                </div>
                <div className="text-gray-500 text-xs">
                  {user?.roles?.join(', ') || '用户'}
                </div>
              </div>
              
              <Dropdown overlay={userMenu} placement="bottomRight" trigger={['click']}>
                <div className="cursor-pointer">
                  <Avatar 
                    size={32}
                    src={user?.profile_picture}
                    icon={<UserOutlined />}
                  />
                </div>
              </Dropdown>
            </div>
          </div>
        </Header>

        {/* 内容区域 */}
        <Content className="bg-gray-50">
          {children}
        </Content>
      </Layout>
    </Layout>
  )
}

export default MainLayout