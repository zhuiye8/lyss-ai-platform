/**
 * Lyss AI Platform - 对话列表组件
 * 功能描述: 显示用户的对话列表
 * 作者: Claude AI Assistant
 * 创建时间: 2025-07-09
 * 最后更新: 2025-07-09
 */

import React, { useState } from 'react'
import { 
  List, 
  Avatar, 
  Typography, 
  Input, 
  Select, 
  Button, 
  Dropdown, 
  Menu, 
  Tag, 
  Empty,
  Spin
} from 'antd'
import { 
  MessageOutlined, 
  SearchOutlined, 
  MoreOutlined,
  EditOutlined,
  DeleteOutlined,
  ArchiveOutlined,
  ExportOutlined
} from '@ant-design/icons'
import type { Conversation, ConversationListProps } from '@/types'

const { Text } = Typography
const { Search } = Input
const { Option } = Select

interface ExtendedConversationListProps extends ConversationListProps {
  loading?: boolean
}

/**
 * 对话列表组件
 */
const ConversationList: React.FC<ExtendedConversationListProps> = ({
  conversations,
  selectedConversationId,
  onSelectConversation,
  onCreateConversation,
  loading = false
}) => {
  const [searchText, setSearchText] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [sortBy, setSortBy] = useState<string>('updated_at')

  /**
   * 过滤和排序对话
   */
  const filteredConversations = React.useMemo(() => {
    let filtered = [...conversations]

    // 搜索过滤
    if (searchText.trim()) {
      const searchLower = searchText.toLowerCase()
      filtered = filtered.filter(conv => 
        conv.title?.toLowerCase().includes(searchLower) ||
        conv.summary?.toLowerCase().includes(searchLower)
      )
    }

    // 状态过滤
    if (statusFilter !== 'all') {
      filtered = filtered.filter(conv => conv.status === statusFilter)
    }

    // 排序
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'title':
          return (a.title || '').localeCompare(b.title || '')
        case 'created_at':
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        case 'message_count':
          return b.message_count - a.message_count
        case 'updated_at':
        default:
          return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      }
    })

    return filtered
  }, [conversations, searchText, statusFilter, sortBy])

  /**
   * 格式化时间显示
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

  /**
   * 获取状态显示文本
   */
  const getStatusText = (status: string) => {
    switch (status) {
      case 'active': return '活跃'
      case 'archived': return '已归档'
      case 'deleted': return '已删除'
      default: return status
    }
  }

  /**
   * 处理对话操作菜单
   */
  const getConversationMenu = (conversation: Conversation) => (
    <Menu>
      <Menu.Item key="edit" icon={<EditOutlined />}>
        编辑对话
      </Menu.Item>
      <Menu.Item key="archive" icon={<ArchiveOutlined />}>
        {conversation.status === 'archived' ? '取消归档' : '归档对话'}
      </Menu.Item>
      <Menu.Item key="export" icon={<ExportOutlined />}>
        导出对话
      </Menu.Item>
      <Menu.Divider />
      <Menu.Item key="delete" icon={<DeleteOutlined />} danger>
        删除对话
      </Menu.Item>
    </Menu>
  )

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Spin size="large" tip="加载对话列表..." />
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* 搜索和过滤器 */}
      <div className="p-4 space-y-3 border-b border-gray-200">
        {/* 搜索框 */}
        <Search
          placeholder="搜索对话..."
          allowClear
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          prefix={<SearchOutlined />}
        />

        {/* 过滤器 */}
        <div className="flex space-x-2">
          <Select
            value={statusFilter}
            onChange={setStatusFilter}
            size="small"
            className="flex-1"
          >
            <Option value="all">全部状态</Option>
            <Option value="active">活跃</Option>
            <Option value="archived">已归档</Option>
          </Select>

          <Select
            value={sortBy}
            onChange={setSortBy}
            size="small"
            className="flex-1"
          >
            <Option value="updated_at">最近更新</Option>
            <Option value="created_at">创建时间</Option>
            <Option value="title">标题</Option>
            <Option value="message_count">消息数量</Option>
          </Select>
        </div>
      </div>

      {/* 对话列表 */}
      <div className="flex-1 overflow-y-auto">
        {filteredConversations.length > 0 ? (
          <List
            dataSource={filteredConversations}
            renderItem={(conversation) => (
              <List.Item
                className={`cursor-pointer hover:bg-gray-50 transition-colors px-4 py-3 border-none ${
                  selectedConversationId === conversation.conversation_id 
                    ? 'bg-blue-50 border-r-2 border-blue-500' 
                    : ''
                }`}
                onClick={() => onSelectConversation(conversation.conversation_id)}
                actions={[
                  <Dropdown 
                    overlay={getConversationMenu(conversation)} 
                    placement="bottomRight"
                    trigger={['click']}
                    key="more"
                  >
                    <Button 
                      type="text" 
                      size="small" 
                      icon={<MoreOutlined />}
                      onClick={(e) => e.stopPropagation()}
                    />
                  </Dropdown>
                ]}
              >
                <List.Item.Meta
                  avatar={
                    <Avatar 
                      icon={<MessageOutlined />} 
                      className="bg-blue-500"
                      size={40}
                    />
                  }
                  title={
                    <div className="flex items-center justify-between">
                      <Text 
                        className="font-medium text-gray-900" 
                        ellipsis={{ tooltip: conversation.title }}
                      >
                        {conversation.title || '未命名对话'}
                      </Text>
                      <Tag 
                        color={getStatusColor(conversation.status)} 
                        size="small"
                      >
                        {getStatusText(conversation.status)}
                      </Tag>
                    </div>
                  }
                  description={
                    <div className="space-y-1">
                      <Text 
                        type="secondary" 
                        className="text-sm"
                        ellipsis={{ tooltip: conversation.summary }}
                      >
                        {conversation.summary || '暂无摘要...'}
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
          <div className="h-full flex items-center justify-center p-8">
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description={
                searchText || statusFilter !== 'all' 
                  ? '没有找到匹配的对话' 
                  : '暂无对话记录'
              }
              className="text-gray-500"
            >
              {!searchText && statusFilter === 'all' && (
                <Button 
                  type="primary" 
                  ghost 
                  onClick={onCreateConversation}
                >
                  创建第一个对话
                </Button>
              )}
            </Empty>
          </div>
        )}
      </div>

      {/* 底部统计信息 */}
      {filteredConversations.length > 0 && (
        <div className="p-3 border-t border-gray-200 bg-gray-50 text-xs text-gray-500 text-center">
          显示 {filteredConversations.length} / {conversations.length} 个对话
        </div>
      )}
    </div>
  )
}

export default ConversationList