/**
 * Lyss AI Platform - 聊天界面组件
 * 功能描述: 对话聊天的主界面
 * 作者: Claude AI Assistant
 * 创建时间: 2025-07-09
 * 最后更新: 2025-07-09
 */

import React, { useState, useRef, useEffect } from 'react'
import { 
  Input, 
  Button, 
  Card, 
  Avatar, 
  Typography, 
  Spin, 
  Divider,
  Space,
  Tag,
  Tooltip
} from 'antd'
import { 
  SendOutlined, 
  UserOutlined, 
  RobotOutlined,
  ClockCircleOutlined,
  FileTextOutlined
} from '@ant-design/icons'
import { useAuth } from '@/hooks/useAuth'
import type { ChatInterfaceProps, Message } from '@/types'

const { TextArea } = Input
const { Text, Title } = Typography

/**
 * 聊天界面组件
 */
const ChatInterface: React.FC<ChatInterfaceProps> = ({
  conversation,
  messages,
  onSendMessage,
  loading = false
}) => {
  const [inputValue, setInputValue] = useState('')
  const [sending, setSending] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { user } = useAuth()

  // 自动滚动到底部
  useEffect(() => {
    scrollToBottom()
  }, [messages])

  /**
   * 滚动到消息底部
   */
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  /**
   * 处理发送消息
   */
  const handleSendMessage = async () => {
    const content = inputValue.trim()
    if (!content || sending) return

    setSending(true)
    setInputValue('')

    try {
      await onSendMessage(content)
    } catch (error) {
      console.error('发送消息失败:', error)
      // 发送失败，恢复输入内容
      setInputValue(content)
    } finally {
      setSending(false)
    }
  }

  /**
   * 处理按键事件
   */
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  /**
   * 格式化时间显示
   */
  const formatMessageTime = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const isToday = date.toDateString() === now.toDateString()
    
    if (isToday) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    } else {
      return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  }

  /**
   * 消息气泡组件
   */
  const MessageBubble: React.FC<{ message: Message }> = ({ message }) => {
    const isUser = message.role === 'user'
    const isSystem = message.role === 'system'

    if (isSystem) {
      return (
        <div className="flex justify-center my-4">
          <div className="bg-gray-100 text-gray-600 px-3 py-1 rounded-full text-sm">
            <FileTextOutlined className="mr-1" />
            {message.content}
          </div>
        </div>
      )
    }

    return (
      <div className={`flex mb-4 ${isUser ? 'justify-end' : 'justify-start'}`}>
        <div className={`flex max-w-[70%] ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
          {/* 头像 */}
          <Avatar 
            size={32}
            icon={isUser ? <UserOutlined /> : <RobotOutlined />}
            className={`${isUser ? 'ml-2 bg-blue-500' : 'mr-2 bg-green-500'} flex-shrink-0`}
            src={isUser ? user?.profile_picture : undefined}
          />

          {/* 消息内容 */}
          <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
            {/* 发送者信息 */}
            <div className={`flex items-center mb-1 text-xs text-gray-500 ${
              isUser ? 'flex-row-reverse' : 'flex-row'
            }`}>
              <span className={isUser ? 'mr-2' : 'ml-2'}>
                {isUser ? (user?.first_name || user?.username || '我') : 'AI助手'}
              </span>
              <Tooltip title={formatMessageTime(message.created_at)}>
                <ClockCircleOutlined className="text-xs" />
              </Tooltip>
            </div>

            {/* 消息气泡 */}
            <div
              className={`px-4 py-2 rounded-lg ${
                isUser
                  ? 'bg-blue-500 text-white rounded-br-sm'
                  : 'bg-white text-gray-900 border border-gray-200 rounded-bl-sm shadow-sm'
              }`}
            >
              <div className="whitespace-pre-wrap break-words">
                {message.content}
              </div>
              
              {/* 消息元数据 */}
              {message.metadata && Object.keys(message.metadata).length > 0 && (
                <div className="mt-2 pt-2 border-t border-gray-200 opacity-75">
                  <div className="text-xs space-x-2">
                    {message.metadata.model && (
                      <Tag size="small">模型: {message.metadata.model}</Tag>
                    )}
                    {message.metadata.tokens && (
                      <Tag size="small">Token: {message.metadata.tokens}</Tag>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (!conversation) {
    return (
      <div className="h-full flex items-center justify-center bg-gray-50">
        <Card className="text-center">
          <div className="text-4xl mb-4">💬</div>
          <Title level={4}>请选择一个对话</Title>
          <Text type="secondary">从左侧选择对话开始聊天</Text>
        </Card>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col bg-white">
      {/* 对话头部 */}
      <div className="flex-shrink-0 px-6 py-4 border-b border-gray-200 bg-white">
        <div className="flex items-center justify-between">
          <div>
            <Title level={4} className="mb-1">
              {conversation.title || '未命名对话'}
            </Title>
            <Space size="small">
              <Tag color="blue">{conversation.message_count} 条消息</Tag>
              <Tag color={conversation.status === 'active' ? 'green' : 'orange'}>
                {conversation.status === 'active' ? '活跃' : '已归档'}
              </Tag>
              <Text type="secondary" className="text-sm">
                最后更新: {new Date(conversation.updated_at).toLocaleString()}
              </Text>
            </Space>
          </div>
        </div>
      </div>

      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto px-6 py-4 bg-gray-50">
        {loading ? (
          <div className="h-full flex items-center justify-center">
            <Spin size="large" tip="加载消息中..." />
          </div>
        ) : messages.length > 0 ? (
          <div className="space-y-2">
            {messages.map((message) => (
              <MessageBubble key={message.message_id} message={message} />
            ))}
            {sending && (
              <div className="flex justify-start">
                <div className="flex items-center max-w-[70%]">
                  <Avatar 
                    size={32}
                    icon={<RobotOutlined />}
                    className="mr-2 bg-green-500"
                  />
                  <div className="bg-white border border-gray-200 rounded-lg px-4 py-2 shadow-sm">
                    <div className="flex items-center space-x-2">
                      <Spin size="small" />
                      <Text type="secondary">AI正在思考中...</Text>
                    </div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        ) : (
          <div className="h-full flex items-center justify-center">
            <Card className="text-center">
              <div className="text-4xl mb-4">🤖</div>
              <Title level={4}>开始对话</Title>
              <Text type="secondary">发送第一条消息开始与AI助手对话</Text>
            </Card>
          </div>
        )}
      </div>

      {/* 输入区域 */}
      <div className="flex-shrink-0 border-t border-gray-200 bg-white">
        <div className="p-4">
          <div className="flex space-x-3">
            <div className="flex-1">
              <TextArea
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onPressEnter={handleKeyPress}
                placeholder="输入消息... (Enter发送，Shift+Enter换行)"
                autoSize={{ minRows: 1, maxRows: 4 }}
                disabled={sending}
                className="resize-none"
              />
            </div>
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleSendMessage}
              loading={sending}
              disabled={!inputValue.trim() || sending}
              className="self-end"
            >
              发送
            </Button>
          </div>
          
          {/* 提示信息 */}
          <div className="mt-2 text-xs text-gray-500 text-center">
            AI助手将基于您的输入提供智能回复。请注意保护个人隐私信息。
          </div>
        </div>
      </div>
    </div>
  )
}

export default ChatInterface