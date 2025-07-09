/**
 * Lyss AI Platform - 对话管理页面
 * 功能描述: 对话列表管理和聊天界面
 * 作者: Claude AI Assistant
 * 创建时间: 2025-07-09
 * 最后更新: 2025-07-09
 */

import React, { useState, useEffect } from 'react'
import { Routes, Route, useNavigate, useParams } from 'react-router-dom'
import { Layout, Card, Empty, Button } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import ConversationList from '@/components/conversations/ConversationList'
import ChatInterface from '@/components/conversations/ChatInterface'
import { get } from '@/utils/request'
import type { Conversation, Message } from '@/types'

const { Sider, Content } = Layout

/**
 * 对话管理页面组件
 */
const ConversationsPage: React.FC = () => {
  const navigate = useNavigate()
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [messagesLoading, setMessagesLoading] = useState(false)

  // 初始化加载对话列表
  useEffect(() => {
    loadConversations()
  }, [])

  /**
   * 加载对话列表
   */
  const loadConversations = async () => {
    setLoading(true)
    try {
      const response = await get('/api/v1/conversations?page=1&page_size=50&sort_by=updated_at&sort_order=desc')
      if (response.data.success) {
        setConversations(response.data.data.conversations || [])
      }
    } catch (error) {
      console.error('加载对话列表失败:', error)
    } finally {
      setLoading(false)
    }
  }

  /**
   * 选择对话
   */
  const handleSelectConversation = async (conversationId: string) => {
    // 找到对话对象
    const conversation = conversations.find(c => c.conversation_id === conversationId)
    if (!conversation) return

    setSelectedConversation(conversation)
    navigate(`/conversations/${conversationId}`)

    // 加载消息
    await loadMessages(conversationId)
  }

  /**
   * 加载对话消息
   */
  const loadMessages = async (conversationId: string) => {
    setMessagesLoading(true)
    try {
      const response = await get(`/api/v1/conversations/${conversationId}/messages?page=1&page_size=100&sort_order=asc`)
      if (response.data.success) {
        setMessages(response.data.data.messages || [])
      }
    } catch (error) {
      console.error('加载消息失败:', error)
      setMessages([])
    } finally {
      setMessagesLoading(false)
    }
  }

  /**
   * 创建新对话
   */
  const handleCreateConversation = async () => {
    try {
      const response = await get('/api/v1/conversations', {
        method: 'POST',
        data: {
          title: '新对话',
          metadata: {}
        }
      })
      
      if (response.data.success) {
        const newConversation = response.data.data
        setConversations(prev => [newConversation, ...prev])
        await handleSelectConversation(newConversation.conversation_id)
      }
    } catch (error) {
      console.error('创建对话失败:', error)
    }
  }

  /**
   * 发送消息
   */
  const handleSendMessage = async (content: string) => {
    if (!selectedConversation) return

    try {
      // 先添加用户消息到界面
      const userMessage: Message = {
        message_id: `temp_${Date.now()}`,
        conversation_id: selectedConversation.conversation_id,
        tenant_id: selectedConversation.tenant_id,
        role: 'user',
        content,
        content_type: 'text',
        metadata: {},
        attachments: [],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }

      setMessages(prev => [...prev, userMessage])

      // 发送到后端
      const response = await get(`/api/v1/conversations/${selectedConversation.conversation_id}/messages`, {
        method: 'POST',
        data: {
          content,
          content_type: 'text',
          metadata: {}
        }
      })

      if (response.data.success) {
        // 重新加载消息列表获取真实的消息ID
        await loadMessages(selectedConversation.conversation_id)
        
        // 更新对话列表中的最后消息时间
        await loadConversations()
      }
    } catch (error) {
      console.error('发送消息失败:', error)
      // 发送失败，移除临时消息
      setMessages(prev => prev.filter(msg => !msg.message_id.startsWith('temp_')))
    }
  }

  return (
    <div className="h-screen flex flex-col">
      <Layout className="flex-1">
        {/* 左侧对话列表 */}
        <Sider 
          width={320} 
          className="bg-white border-r border-gray-200"
          theme="light"
        >
          <div className="h-full flex flex-col">
            {/* 标题和新建按钮 */}
            <div className="p-4 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">对话列表</h3>
                <Button 
                  type="primary" 
                  size="small" 
                  icon={<PlusOutlined />}
                  onClick={handleCreateConversation}
                >
                  新建
                </Button>
              </div>
            </div>

            {/* 对话列表 */}
            <div className="flex-1 overflow-hidden">
              <ConversationList
                conversations={conversations}
                selectedConversationId={selectedConversation?.conversation_id}
                onSelectConversation={handleSelectConversation}
                onCreateConversation={handleCreateConversation}
                loading={loading}
              />
            </div>
          </div>
        </Sider>

        {/* 右侧聊天界面 */}
        <Content className="bg-gray-50">
          <Routes>
            <Route 
              path="/" 
              element={<ConversationWelcome onCreateConversation={handleCreateConversation} />} 
            />
            <Route 
              path="/:conversationId" 
              element={
                <ConversationDetailWrapper 
                  conversation={selectedConversation}
                  messages={messages}
                  loading={messagesLoading}
                  onSendMessage={handleSendMessage}
                />
              } 
            />
          </Routes>
        </Content>
      </Layout>
    </div>
  )
}

/**
 * 对话详情包装组件
 */
interface ConversationDetailWrapperProps {
  conversation: Conversation | null
  messages: Message[]
  loading: boolean
  onSendMessage: (content: string) => void
}

const ConversationDetailWrapper: React.FC<ConversationDetailWrapperProps> = ({
  conversation,
  messages,
  loading,
  onSendMessage
}) => {
  const { conversationId } = useParams<{ conversationId: string }>()

  if (!conversation && conversationId) {
    return (
      <div className="h-full flex items-center justify-center">
        <Card className="text-center">
          <Empty 
            description="对话不存在或已被删除"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        </Card>
      </div>
    )
  }

  return (
    <ChatInterface
      conversation={conversation}
      messages={messages}
      onSendMessage={onSendMessage}
      loading={loading}
    />
  )
}

/**
 * 欢迎页面组件
 */
interface ConversationWelcomeProps {
  onCreateConversation: () => void
}

const ConversationWelcome: React.FC<ConversationWelcomeProps> = ({ onCreateConversation }) => {
  return (
    <div className="h-full flex items-center justify-center">
      <Card className="text-center max-w-md">
        <div className="mb-6">
          <div className="text-6xl mb-4">💬</div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            欢迎使用 Lyss AI
          </h2>
          <p className="text-gray-600">
            选择一个对话开始聊天，或者创建新的对话体验智能AI助手
          </p>
        </div>
        
        <Button 
          type="primary" 
          size="large" 
          icon={<PlusOutlined />}
          onClick={onCreateConversation}
        >
          开始新对话
        </Button>
        
        <div className="mt-6 text-sm text-gray-500">
          <p>✨ 支持多种AI模型</p>
          <p>🔒 企业级安全保护</p>
          <p>💾 对话历史永久保存</p>
        </div>
      </Card>
    </div>
  )
}

export default ConversationsPage