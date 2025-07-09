/**
 * Lyss AI Platform - 仪表盘页面
 * 功能描述: 系统主要数据展示和快速操作
 * 作者: Claude AI Assistant
 * 创建时间: 2025-07-09
 * 最后更新: 2025-07-09
 */

import React, { useState, useEffect } from 'react'
import { 
  Card, 
  Row, 
  Col, 
  Statistic, 
  Button, 
  List, 
  Avatar,
  Typography,
  Divider,
  Space,
  Tag,
  Progress
} from 'antd'
import {
  MessageOutlined,
  RobotOutlined,
  DollarOutlined,
  TeamOutlined,
  PlusOutlined,
  HistoryOutlined,
  TrendingUpOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { get } from '@/utils/request'
import type { Conversation, UsageStats } from '@/types'

const { Title, Text } = Typography

/**
 * 仪表盘页面组件
 */
const DashboardPage: React.FC = () => {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [loading, setLoading] = useState(true)
  const [recentConversations, setRecentConversations] = useState<Conversation[]>([])
  const [usageStats, setUsageStats] = useState<any>(null)

  // 页面初始化时加载数据
  useEffect(() => {
    loadDashboardData()
  }, [])

  /**
   * 加载仪表盘数据
   */
  const loadDashboardData = async () => {
    setLoading(true)
    try {
      // 并行加载数据
      const [conversationsRes, statsRes] = await Promise.all([
        get('/api/v1/conversations?page=1&page_size=5&sort_by=updated_at&sort_order=desc'),
        get('/api/v1/conversations/statistics')
      ])

      if (conversationsRes.data.success) {
        setRecentConversations(conversationsRes.data.data.conversations || [])
      }

      if (statsRes.data.success) {
        setUsageStats(statsRes.data.data)
      }
    } catch (error) {
      console.error('加载仪表盘数据失败:', error)
    } finally {
      setLoading(false)
    }
  }

  /**
   * 创建新对话
   */
  const handleCreateConversation = () => {
    navigate('/conversations/new')
  }

  /**
   * 跳转到对话详情
   */
  const handleViewConversation = (conversationId: string) => {
    navigate(`/conversations/${conversationId}`)
  }

  /**
   * 格式化时间
   */
  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMins / 60)
    const diffDays = Math.floor(diffHours / 24)

    if (diffMins < 1) return '刚刚'
    if (diffMins < 60) return `${diffMins}分钟前`
    if (diffHours < 24) return `${diffHours}小时前`
    if (diffDays < 7) return `${diffDays}天前`
    return date.toLocaleDateString()
  }

  /**
   * 获取状态标签颜色
   */
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'green'
      case 'archived': return 'orange'
      case 'deleted': return 'red'
      default: return 'default'
    }
  }

  return (
    <div className="p-6 space-y-6">
      {/* 页面标题 */}
      <div className="flex justify-between items-center">
        <div>
          <Title level={2} className="mb-1">
            欢迎回来，{user?.first_name || user?.username || '用户'}！
          </Title>
          <Text type="secondary">
            这里是您的AI平台控制台，可以查看最新数据和快速开始对话
          </Text>
        </div>
        <Button 
          type="primary" 
          size="large" 
          icon={<PlusOutlined />}
          onClick={handleCreateConversation}
        >
          新建对话
        </Button>
      </div>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="总对话数"
              value={usageStats?.total_conversations || 0}
              prefix={<MessageOutlined className="text-blue-500" />}
              loading={loading}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="总消息数"
              value={usageStats?.total_messages || 0}
              prefix={<RobotOutlined className="text-green-500" />}
              loading={loading}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="今日消息"
              value={usageStats?.today_messages || 0}
              prefix={<TrendingUpOutlined className="text-orange-500" />}
              loading={loading}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="活跃对话"
              value={usageStats?.active_conversations || 0}
              prefix={<TeamOutlined className="text-purple-500" />}
              loading={loading}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        {/* 最近对话 */}
        <Col xs={24} lg={14}>
          <Card 
            title={
              <Space>
                <HistoryOutlined />
                最近对话
              </Space>
            }
            extra={
              <Button type="link" onClick={() => navigate('/conversations')}>
                查看全部
              </Button>
            }
            loading={loading}
          >
            {recentConversations.length > 0 ? (
              <List
                dataSource={recentConversations}
                renderItem={(conversation) => (
                  <List.Item
                    actions={[
                      <Button 
                        type="link" 
                        size="small"
                        onClick={() => handleViewConversation(conversation.conversation_id)}
                      >
                        打开
                      </Button>
                    ]}
                  >
                    <List.Item.Meta
                      avatar={
                        <Avatar 
                          icon={<MessageOutlined />} 
                          className="bg-blue-500"
                        />
                      }
                      title={
                        <div className="flex items-center justify-between">
                          <Text className="font-medium">
                            {conversation.title || '未命名对话'}
                          </Text>
                          <Tag 
                            color={getStatusColor(conversation.status)}
                            size="small"
                          >
                            {conversation.status === 'active' ? '活跃' : 
                             conversation.status === 'archived' ? '已归档' : '已删除'}
                          </Tag>
                        </div>
                      }
                      description={
                        <div className="space-y-1">
                          <Text type="secondary" className="text-sm">
                            {conversation.summary || '暂无摘要'}
                          </Text>
                          <div className="flex items-center justify-between text-xs text-gray-500">
                            <span>{conversation.message_count} 条消息</span>
                            <span>{formatTimeAgo(conversation.updated_at)}</span>
                          </div>
                        </div>
                      }
                    />
                  </List.Item>
                )}
              />
            ) : (
              <div className="text-center py-8 text-gray-500">
                <MessageOutlined className="text-4xl mb-4 text-gray-300" />
                <p>暂无对话记录</p>
                <Button 
                  type="primary" 
                  ghost 
                  className="mt-2"
                  onClick={handleCreateConversation}
                >
                  开始第一个对话
                </Button>
              </div>
            )}
          </Card>
        </Col>

        {/* 快速操作和统计 */}
        <Col xs={24} lg={10}>
          <Space direction="vertical" size="middle" className="w-full">
            {/* 快速操作 */}
            <Card title="快速操作">
              <Space direction="vertical" className="w-full">
                <Button 
                  type="primary" 
                  block 
                  icon={<PlusOutlined />}
                  onClick={handleCreateConversation}
                >
                  新建对话
                </Button>
                <Button 
                  block 
                  icon={<MessageOutlined />}
                  onClick={() => navigate('/conversations')}
                >
                  对话管理
                </Button>
                <Button 
                  block 
                  icon={<TeamOutlined />}
                  onClick={() => navigate('/settings')}
                >
                  系统设置
                </Button>
              </Space>
            </Card>

            {/* 使用情况 */}
            <Card title="今日使用情况">
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <Text>对话活跃度</Text>
                    <Text type="secondary">
                      {usageStats?.today_messages || 0} / 1000
                    </Text>
                  </div>
                  <Progress 
                    percent={Math.min(((usageStats?.today_messages || 0) / 1000) * 100, 100)}
                    showInfo={false}
                    strokeColor="#52c41a"
                  />
                </div>
                
                <Divider className="my-3" />
                
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <Text type="secondary">活跃对话:</Text>
                    <Text>{usageStats?.active_conversations || 0}</Text>
                  </div>
                  <div className="flex justify-between">
                    <Text type="secondary">归档对话:</Text>
                    <Text>{usageStats?.archived_conversations || 0}</Text>
                  </div>
                  <div className="flex justify-between">
                    <Text type="secondary">总消息数:</Text>
                    <Text>{usageStats?.total_messages || 0}</Text>
                  </div>
                </div>
              </div>
            </Card>
          </Space>
        </Col>
      </Row>
    </div>
  )
}

export default DashboardPage