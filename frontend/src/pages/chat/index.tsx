/**
 * 现代化AI对话界面
 * 使用Ant Design X组件实现一屏展示设计，优化用户体验和布局
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Button,
  Space,
  Select,
  Tooltip,
  Modal,
  Form,
  Slider,
  Switch,
  message,
  Typography,
  Badge,
  Tag,
  Drawer,
  Flex,
  theme,
  Divider,
  Row,
  Col,
} from 'antd';
import {
  SettingOutlined,
  HistoryOutlined,
  PlusOutlined,
  DeleteOutlined,
  RobotOutlined,
  UserOutlined,
  CopyOutlined,
  RedoOutlined,
  MessageOutlined,
  ClockCircleOutlined,
  ThunderboltOutlined,
  BulbOutlined,
  SendOutlined,
  ClearOutlined,
} from '@ant-design/icons';
import { Bubble, Sender, Conversations, useXAgent } from '@ant-design/x';
import dayjs from 'dayjs';

import { ChatService } from '@/services/chat';
import { ConversationService } from '@/services/conversation';
import { useAuth } from '@/store/auth';
import { SUPPLIER_CONFIG } from '@/utils/constants';
import { handleApiError } from '@/utils/errorHandler';

const { Title, Text } = Typography;
const { Option } = Select;

// 消息类型 - 适配Ant Design X格式
interface ChatMessage {
  id: string;
  content: string;
  role: 'user' | 'assistant' | 'system';
  timestamp: Date;
  model?: string;
  tokens?: {
    input: number;
    output: number;
    total: number;
  };
  metadata?: Record<string, any>;
}

// 对话类型
interface Conversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  model: string;
  supplier: string;
  created_at: string;
  updated_at: string;
}

// 聊天配置
interface ChatConfig {
  model: string;
  supplier: string;
  temperature: number;
  max_tokens: number;
  stream: boolean;
  memory_enabled: boolean;
}

const ChatPage: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null);
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [settingsVisible, setSettingsVisible] = useState(false);
  const [conversationsVisible, setConversationsVisible] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  
  const [chatConfig, setChatConfig] = useState<ChatConfig>({
    model: 'gpt-3.5-turbo',
    supplier: 'openai',
    temperature: 0.7,
    max_tokens: 2000,
    stream: true,
    memory_enabled: true,
  });

  const { user } = useAuth();
  const { token } = theme.useToken();
  const [form] = Form.useForm();
  
  // Ant Design X的agent状态管理（留待后续实现）
  // const [agent] = useXAgent({
  //   request: async (info, callbacks) => {
  //     const { message } = info;
  //     return await handleSendMessage(message || '', callbacks);
  //   },
  // });
  
  // 转换消息格式为Ant Design X兼容格式
  const convertToXChatMessages = (msgs: ChatMessage[]) => {
    return msgs.map(msg => ({
      id: msg.id,
      message: msg.content,
      status: 'success' as const,
      createdAt: msg.timestamp.getTime(),
      role: msg.role,
      meta: {
        avatar: msg.role === 'user' ? user?.avatar : '/ai-avatar.png',
        title: msg.role === 'user' ? user?.name || '用户' : 'Lyss AI',
        ...(msg.tokens && { tokens: msg.tokens }),
        ...(msg.model && { model: msg.model }),
        ...(msg.metadata && msg.metadata),
      },
    }));
  };

  // 响应式断点检测
  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < 768);
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Ant Design X自动处理滚动，无需手动实现

  /**
   * 加载对话历史
   */
  const loadConversations = async () => {
    try {
      const response = await ConversationService.getConversations({
        page: 1,
        page_size: 50,
        sort_by: 'updated_at',
        sort_order: 'desc',
      });
      
      if (response.success && response.data) {
        setConversations(response.data.items.map((item: any) => ({
          ...item,
          messages: [] // 添加缺失的messages字段
        })));
      }
    } catch (error) {
      handleApiError(error);
    }
  };

  /**
   * 初始化加载
   */
  useEffect(() => {
    loadConversations();
  }, []);

  /**
   * 发送消息 - 适配Ant Design X的useXAgent
   */
  const handleSendMessage = useCallback(async (content: string, callbacks?: any) => {
    if (!content.trim() || loading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      content: content.trim(),
      role: 'user',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setLoading(true);

    try {
      let assistantMessage: ChatMessage;
      
      if (chatConfig.stream) {
        // 流式响应
        assistantMessage = await handleStreamingResponse(content, callbacks);
      } else {
        // 普通响应
        assistantMessage = await handleNormalResponse(content);
      }
      
      setMessages(prev => [...prev, assistantMessage]);
      return assistantMessage.content;
    } catch (error) {
      handleApiError(error);
      
      // 根据错误类型添加不同的错误消息
      let errorContent = '抱歉，发生了错误，请稍后重试。';
      
      if ((error as any).code === 'NETWORK_ERROR') {
        errorContent = '网络连接失败，请检查网络后重试。';
      } else if ((error as any).response?.status === 429) {
        errorContent = '请求过于频繁，请稍后再试。';
      } else if ((error as any).response?.status === 401) {
        errorContent = '认证失效，请重新登录。';
      } else if ((error as any).response?.status >= 500) {
        errorContent = '服务器暂时不可用，请稍后重试。';
      }
      
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        content: errorContent,
        role: 'assistant',
        timestamp: new Date(),
        metadata: { isError: true },
      };
      setMessages(prev => [...prev, errorMessage]);
      throw error;
    } finally {
      setLoading(false);
      setStreaming(false);
    }
  }, [loading, chatConfig]);

  /**
   * 处理流式响应 - 支持Ant Design X的callbacks
   */
  const handleStreamingResponse = async (content: string, callbacks?: any): Promise<ChatMessage> => {
    setStreaming(true);
    
    const assistantMessage: ChatMessage = {
      id: (Date.now() + 1).toString(),
      content: '',
      role: 'assistant',
      timestamp: new Date(),
      model: chatConfig.model,
    };

    setMessages(prev => [...prev, assistantMessage]);

    try {
      const response = await ChatService.streamChat({
        message: content,
        conversation_id: currentConversation?.id,
        model: chatConfig.model,
        supplier: chatConfig.supplier,
        config: {
          temperature: chatConfig.temperature,
          max_tokens: chatConfig.max_tokens,
          memory_enabled: chatConfig.memory_enabled,
        },
      });

      // 处理流式数据
      const reader = response.getReader();
      let accumulated = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = new TextDecoder().decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') {
              break;
            }

            try {
              const parsed = JSON.parse(data);
              if (parsed.type === 'chunk' && parsed.content) {
                accumulated += parsed.content;
                
                // 更新消息内容
                setMessages(prev => 
                  prev.map(msg => 
                    msg.id === assistantMessage.id 
                      ? { ...msg, content: accumulated }
                      : msg
                  )
                );
                
                // 调用callbacks传递给Ant Design X
                if (callbacks?.onUpdate) {
                  callbacks.onUpdate(accumulated);
                }
              }
            } catch (e) {
              console.warn('解析流式数据失败:', e);
            }
          }
        }
      }
      
      // 返回最终的消息
      const finalMessage = { ...assistantMessage, content: accumulated };
      return finalMessage;
    } catch (error) {
      console.error('流式聊天失败:', error);
      throw error;
    }
  };

  /**
   * 处理普通响应
   */
  const handleNormalResponse = async (content: string): Promise<ChatMessage> => {
    try {
      const response = await ChatService.sendMessage({
        message: content,
        conversation_id: currentConversation?.id,
        model: chatConfig.model,
        supplier: chatConfig.supplier,
        config: {
          temperature: chatConfig.temperature,
          max_tokens: chatConfig.max_tokens,
          memory_enabled: chatConfig.memory_enabled,
        },
      });

      if (response.success && response.data) {
        const assistantMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          content: response.data.content,
          role: 'assistant',
          timestamp: new Date(),
          model: response.data.model,
          tokens: response.data.usage ? {
            input: response.data.usage.input_tokens,
            output: response.data.usage.output_tokens,
            total: response.data.usage.total_tokens,
          } : undefined,
        };

        // 更新当前对话
        if (response.data.conversation_id) {
          setCurrentConversation(prev => prev ? {
            ...prev,
            id: response.data.conversation_id,
            updated_at: new Date().toISOString(),
          } : null);
        }
        
        return assistantMessage;
      } else {
        throw new Error('服务器响应失败');
      }
    } catch (error) {
      console.error('发送消息失败:', error);
      throw error;
    }
  };

  /**
   * 新建对话
   */
  const handleNewConversation = () => {
    setCurrentConversation(null);
    setMessages([]);
  };

  /**
   * 选择对话
   */
  const handleSelectConversation = async (conversation: Conversation) => {
    try {
      const response = await ConversationService.getConversationMessages(conversation.id);
      if (response.success && response.data) {
        setCurrentConversation(conversation);
        setMessages(response.data.items.map((msg: any) => ({
          id: msg.id,
          content: msg.content,
          role: msg.role as 'user' | 'assistant',
          timestamp: new Date(msg.created_at),
          model: msg.model,
          tokens: msg.tokens,
        })));
      }
    } catch (error) {
      handleApiError(error);
    }
  };

  /**
   * 删除对话
   */
  const handleDeleteConversation = async (conversationId: string) => {
    try {
      const response = await ConversationService.deleteConversation(conversationId);
      if (response.success) {
        message.success('对话删除成功');
        setConversations(prev => prev.filter(c => c.id !== conversationId));
        
        if (currentConversation?.id === conversationId) {
          handleNewConversation();
        }
      }
    } catch (error) {
      handleApiError(error);
    }
  };

  // 复制消息内容功能已移动到Bubble组件中

  // 重新生成回答功能已移动到handleRegenerateMessage函数中

  /**
   * 重新生成消息 - 适配Ant Design X的Bubble组件
   */
  const handleRegenerateMessage = async (messageId: string) => {
    const messageIndex = messages.findIndex(msg => msg.id === messageId);
    if (messageIndex === -1) return;
    
    const userMessage = messages[messageIndex - 1];
    if (!userMessage || userMessage.role !== 'user') return;

    // 移除当前回答及之后的消息
    const newMessages = messages.slice(0, messageIndex);
    setMessages(newMessages);

    // 重新发送用户消息
    await handleSendMessage(userMessage.content);
  };

  /**
   * 保存聊天配置
   */
  const handleSaveSettings = async (values: any) => {
    setChatConfig(prev => ({ ...prev, ...values }));
    setSettingsVisible(false);
    message.success('设置已保存');
  };

  return (
    <div 
      style={{ 
        height: 'calc(100vh - 152px)', // 减去AdminLayout的头部和边距
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: 'transparent',
        overflow: 'hidden',
      }}
    >
      {/* 现代化顶部工具栏 */}
      <div
        style={{
          padding: '16px 24px',
          backgroundColor: token.colorBgContainer,
          borderBottom: `1px solid ${token.colorBorderSecondary}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexShrink: 0,
        }}
      >
        <Flex align="center" gap={16}>
          <div>
            <Title 
              level={4} 
              style={{ 
                margin: 0, 
                color: token.colorTextBase,
                fontWeight: 600,
              }}
            >
              <MessageOutlined style={{ marginRight: 8, color: token.colorPrimary }} />
              AI 对话
            </Title>
            {currentConversation && !isMobile && (
              <Text 
                type="secondary" 
                style={{ 
                  fontSize: 12,
                  marginTop: 2,
                  display: 'block',
                }}
              >
                {currentConversation.title}
              </Text>
            )}
          </div>
          
          {/* 状态指示器 */}
          <div>
            {streaming && (
              <Badge 
                status="processing" 
                text={
                  <Text style={{ fontSize: 12, color: token.colorTextSecondary }}>
                    AI正在思考中...
                  </Text>
                } 
              />
            )}
            {loading && !streaming && (
              <Badge 
                status="warning" 
                text={
                  <Text style={{ fontSize: 12, color: token.colorTextSecondary }}>
                    发送中...
                  </Text>
                } 
              />
            )}
          </div>
        </Flex>

        <Flex align="center" gap={8}>
          {/* 快捷配置显示 */}
          {!isMobile && (
            <Space size={4}>
              <Tag 
                color="blue" 
                style={{ 
                  margin: 0,
                  fontSize: 11,
                  padding: '2px 6px',
                }}
              >
                {chatConfig.model}
              </Tag>
              <Tag 
                color="green" 
                style={{ 
                  margin: 0,
                  fontSize: 11,
                  padding: '2px 6px',
                }}
              >
                温度 {chatConfig.temperature}
              </Tag>
              {chatConfig.memory_enabled && (
                <Tag 
                  color="purple" 
                  style={{ 
                    margin: 0,
                    fontSize: 11,
                    padding: '2px 6px',
                  }}
                >
                  记忆开启
                </Tag>
              )}
            </Space>
          )}

          {/* 操作按钮组 */}
          <Space size={4}>
            <Tooltip title="对话历史">
              <Button
                type="text"
                icon={<HistoryOutlined />}
                onClick={() => setConversationsVisible(true)}
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: 8,
                  color: token.colorTextSecondary,
                }}
              />
            </Tooltip>
            
            <Tooltip title="新建对话">
              <Button
                type="text"
                icon={<PlusOutlined />}
                onClick={handleNewConversation}
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: 8,
                  color: token.colorTextSecondary,
                }}
              />
            </Tooltip>
            
            <Tooltip title="对话设置">
              <Button
                type="text"
                icon={<SettingOutlined />}
                onClick={() => setSettingsVisible(true)}
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: 8,
                  color: token.colorTextSecondary,
                }}
              />
            </Tooltip>
          </Space>
        </Flex>
      </div>

      {/* 现代化聊天区域 */}
      <div 
        style={{ 
          flex: 1, 
          display: 'flex', 
          flexDirection: 'column', 
          overflow: 'hidden',
          backgroundColor: token.colorBgSpotlight,
        }}
      >
        {/* 消息列表容器 */}
        <div 
          style={{ 
            flex: 1, 
            overflow: 'auto', 
            padding: isMobile ? '16px' : '24px',
            background: `linear-gradient(180deg, ${token.colorBgSpotlight} 0%, ${token.colorBgLayout} 100%)`,
            position: 'relative',
          }}
        >
          {messages.length === 0 ? (
            /* 欢迎页面 */
            <div 
              style={{ 
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                minHeight: '400px',
                textAlign: 'center',
                padding: '40px 20px',
              }}
            >
              {/* AI机器人图标 */}
              <div
                style={{
                  width: 80,
                  height: 80,
                  borderRadius: '50%',
                  background: `linear-gradient(135deg, ${token.colorPrimary} 0%, #3b82f6 100%)`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: 24,
                  boxShadow: '0 8px 24px rgba(37, 99, 235, 0.15)',
                }}
              >
                <RobotOutlined 
                  style={{ 
                    fontSize: 36, 
                    color: 'white',
                  }} 
                />
              </div>

              {/* 欢迎文字 */}
              <Title 
                level={3} 
                style={{ 
                  margin: '0 0 8px 0',
                  color: token.colorTextBase,
                  fontWeight: 600,
                }}
              >
                欢迎使用 AI 对话
              </Title>
              
              <Text 
                style={{ 
                  fontSize: 16,
                  color: token.colorTextSecondary,
                  marginBottom: 24,
                  lineHeight: 1.6,
                }}
              >
                我是您的AI助手，可以回答问题、协助创作、分析问题等
              </Text>

              {/* 快速开始卡片 */}
              <div 
                style={{ 
                  display: 'grid',
                  gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fit, minmax(200px, 1fr))',
                  gap: 16,
                  maxWidth: 600,
                  width: '100%',
                }}
              >
                {[
                  { icon: <BulbOutlined />, title: '创意写作', desc: '帮助您创作文章、故事' },
                  { icon: <ThunderboltOutlined />, title: '问题解答', desc: '回答各种知识性问题' },
                  { icon: <ClockCircleOutlined />, title: '效率助手', desc: '提升工作学习效率' },
                ].map((item, index) => (
                  <Card
                    key={index}
                    size="small"
                    hoverable
                    style={{
                      borderRadius: 12,
                      border: `1px solid ${token.colorBorderSecondary}`,
                      background: token.colorBgContainer,
                      cursor: 'default',
                    }}
                    bodyStyle={{ padding: 16, textAlign: 'center' }}
                  >
                    <div style={{ 
                      color: token.colorPrimary, 
                      fontSize: 24, 
                      marginBottom: 8 
                    }}>
                      {item.icon}
                    </div>
                    <Text 
                      strong 
                      style={{ 
                        display: 'block', 
                        marginBottom: 4,
                        color: token.colorTextBase,
                      }}
                    >
                      {item.title}
                    </Text>
                    <Text 
                      type="secondary" 
                      style={{ fontSize: 12 }}
                    >
                      {item.desc}
                    </Text>
                  </Card>
                ))}
              </div>

              {/* 当前配置信息 */}
              <div style={{ marginTop: 32 }}>
                <Space split={<Divider type="vertical" />} size="small">
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    模型: {chatConfig.model}
                  </Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    供应商: {SUPPLIER_CONFIG[chatConfig.supplier.toUpperCase() as keyof typeof SUPPLIER_CONFIG]?.name || chatConfig.supplier}
                  </Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    温度: {chatConfig.temperature}
                  </Text>
                </Space>
              </div>
            </div>
          ) : (
            /* 使用Ant Design X的Bubble组件显示消息列表 */
            <div style={{ maxWidth: 800, margin: '0 auto', width: '100%' }}>
              {messages.map((msg, index) => {
                const isUser = msg.role === 'user';
                return (
                  <div key={msg.id} style={{ marginBottom: 24 }}>
                    <Bubble
                      content={msg.content}
                      avatar={{
                        src: isUser ? user?.avatar : undefined,
                        icon: isUser ? <UserOutlined /> : <RobotOutlined />,
                        style: {
                          backgroundColor: isUser ? token.colorPrimary : '#52c41a',
                        },
                      }}
                      placement={isUser ? 'end' : 'start'}
                      typing={streaming && index === messages.length - 1 && !isUser}
                      style={{
                        maxWidth: isMobile ? '85%' : '70%',
                      }}
                    />
                    
                    {/* 消息底部信息和操作 */}
                    <div style={{ 
                      fontSize: 11, 
                      color: token.colorTextQuaternary,
                      marginTop: 8,
                      textAlign: isUser ? 'right' : 'left',
                      display: 'flex',
                      justifyContent: isUser ? 'flex-end' : 'flex-start',
                      alignItems: 'center',
                      gap: 8,
                    }}>
                      <span>
                        {dayjs(msg.timestamp).format('HH:mm')}
                      </span>
                      
                      {/* 显示tokens和模型信息 */}
                      {msg.tokens && (
                        <span>• {msg.tokens.total} tokens</span>
                      )}
                      {msg.model && (
                        <span>• {msg.model}</span>
                      )}
                      
                      {/* 操作按钮（仅AI消息） */}
                      {!isUser && (
                        <Space size={4}>
                          <Tooltip title="复制">
                            <Button
                              type="text"
                              size="small"
                              icon={<CopyOutlined />}
                              style={{
                                fontSize: 10,
                                padding: '0 4px',
                                height: 16,
                                minWidth: 16,
                                opacity: 0.6,
                              }}
                              onClick={() => {
                                navigator.clipboard.writeText(msg.content);
                                message.success('已复制到剪贴板');
                              }}
                            />
                          </Tooltip>
                          
                          <Tooltip title="重新生成">
                            <Button
                              type="text"
                              size="small"
                              icon={<RedoOutlined />}
                              style={{
                                fontSize: 10,
                                padding: '0 4px',
                                height: 16,
                                minWidth: 16,
                                opacity: 0.6,
                              }}
                              onClick={() => handleRegenerateMessage(msg.id)}
                            />
                          </Tooltip>
                        </Space>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* 现代化输入区域 */}
        <div 
          style={{ 
            padding: isMobile ? '16px' : '20px 24px',
            backgroundColor: token.colorBgContainer,
            borderTop: `1px solid ${token.colorBorderSecondary}`,
            flexShrink: 0,
          }}
        >
          {/* 输入框容器 */}
          <div 
            style={{ 
              maxWidth: 800, 
              margin: '0 auto',
              position: 'relative',
            }}
          >
            <Sender
              onSubmit={(text: string) => {
                if (text.trim()) {
                  handleSendMessage(text.trim());
                }
              }}
              loading={loading || streaming}
              placeholder={
                loading ? '正在发送...' :
                streaming ? 'AI正在回复中...' :
                '输入消息... (Shift + Enter 换行，Enter 发送)'
              }
              style={{ 
                width: '100%',
              }}
              styles={{
                input: {
                  borderRadius: 16,
                  padding: '12px 16px',
                  fontSize: 14,
                  border: `1px solid ${token.colorBorderSecondary}`,
                  transition: 'all 0.3s ease',
                },
              }}
              disabled={loading || streaming}
              autoSize={{ minRows: 1, maxRows: 6 }}
              prefix={<SendOutlined />}
              // 其他配置属性
            />
          </div>
          
          {/* 状态栏 */}
          <div 
            style={{ 
              marginTop: 12,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              maxWidth: 800,
              margin: '12px auto 0',
              padding: '0 4px',
            }}
          >
            {/* 左侧：配置信息 */}
            <Space size="small" wrap>
              <Text 
                type="secondary" 
                style={{ 
                  fontSize: 11,
                  opacity: 0.8,
                }}
              >
                {chatConfig.model}
              </Text>
              
              {!isMobile && (
                <>
                  <Text 
                    type="secondary" 
                    style={{ 
                      fontSize: 11,
                      opacity: 0.6,
                    }}
                  >
                    •
                  </Text>
                  
                  <Text 
                    type="secondary" 
                    style={{ 
                      fontSize: 11,
                      opacity: 0.8,
                    }}
                  >
                    温度 {chatConfig.temperature}
                  </Text>
                  
                  {chatConfig.memory_enabled && (
                    <>
                      <Text 
                        type="secondary" 
                        style={{ 
                          fontSize: 11,
                          opacity: 0.6,
                        }}
                      >
                        •
                      </Text>
                      
                      <Badge 
                        status="success" 
                        style={{ fontSize: 10 }}
                        text={
                          <Text 
                            style={{ 
                              fontSize: 11,
                              color: token.colorSuccess,
                            }}
                          >
                            记忆开启
                          </Text>
                        } 
                      />
                    </>
                  )}
                </>
              )}
            </Space>
            
            {/* 右侧：状态指示 */}
            <Space size="small">
              {(loading || streaming) && (
                <Badge 
                  status={streaming ? "processing" : "warning"}
                  text={
                    <Text 
                      style={{ 
                        fontSize: 11,
                        color: streaming ? token.colorPrimary : token.colorWarning,
                      }}
                    >
                      {streaming ? 'AI思考中' : '发送中'}
                    </Text>
                  } 
                />
              )}
              
              {!loading && !streaming && (
                <Text 
                  type="secondary" 
                  style={{ 
                    fontSize: 11,
                    opacity: 0.6,
                  }}
                >
                  Ready
                </Text>
              )}
            </Space>
          </div>
        </div>
      </div>

      {/* 现代化设置抽屉 */}
      <Drawer
        title={
          <Flex align="center" gap={8}>
            <SettingOutlined style={{ color: token.colorPrimary }} />
            <span>对话设置</span>
          </Flex>
        }
        open={settingsVisible}
        onClose={() => setSettingsVisible(false)}
        width={isMobile ? '100%' : 480}
        placement="right"
        styles={{
          header: {
            paddingBottom: 16,
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
          },
          body: {
            padding: 24,
          },
        }}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={chatConfig}
          onFinish={handleSaveSettings}
          style={{ height: '100%' }}
        >
          {/* 供应商和模型选择 */}
          <Card 
            title="模型配置" 
            size="small" 
            style={{ marginBottom: 24 }}
            bodyStyle={{ padding: 16 }}
          >
            <Form.Item
              label="AI供应商"
              name="supplier"
              rules={[{ required: true, message: '请选择供应商' }]}
              style={{ marginBottom: 16 }}
            >
              <Select size="large" placeholder="选择AI供应商">
                {Object.entries(SUPPLIER_CONFIG).map(([key, config]) => (
                  <Option key={key} value={key.toLowerCase()}>
                    <Space>
                      <span>{config.icon}</span>
                      {config.name}
                    </Space>
                  </Option>
                ))}
              </Select>
            </Form.Item>
            
            <Form.Item
              label="模型"
              name="model"
              rules={[{ required: true, message: '请选择模型' }]}
              style={{ marginBottom: 0 }}
            >
              <Select size="large" placeholder="选择AI模型">
                <Option value="gpt-3.5-turbo">GPT-3.5 Turbo</Option>
                <Option value="gpt-4">GPT-4</Option>
                <Option value="gpt-4-turbo">GPT-4 Turbo</Option>
                <Option value="claude-3-haiku">Claude 3 Haiku</Option>
                <Option value="claude-3-sonnet">Claude 3 Sonnet</Option>
                <Option value="claude-3-opus">Claude 3 Opus</Option>
              </Select>
            </Form.Item>
          </Card>

          {/* 参数配置 */}
          <Card 
            title="参数调节" 
            size="small" 
            style={{ marginBottom: 24 }}
            bodyStyle={{ padding: 16 }}
          >
            <Form.Item
              label="创造性温度"
              name="temperature"
              style={{ marginBottom: 20 }}
            >
              <Slider
                min={0}
                max={2}
                step={0.1}
                marks={{
                  0: { label: '精确', style: { fontSize: 12 } },
                  1: { label: '平衡', style: { fontSize: 12 } },
                  2: { label: '创造', style: { fontSize: 12 } }
                }}
                tooltip={{ 
                  formatter: (value?: number) => value ? `${value} - ${
                    value < 0.3 ? '严谨精确' :
                    value < 0.7 ? '平衡适中' :
                    value < 1.2 ? '富有创意' : '高度创造'
                  }` : ''
                }}
              />
            </Form.Item>
            
            <Form.Item
              label="最大输出长度"
              name="max_tokens"
              style={{ marginBottom: 0 }}
            >
              <Slider
                min={100}
                max={4000}
                step={100}
                marks={{
                  100: { label: '100', style: { fontSize: 12 } },
                  2000: { label: '2K', style: { fontSize: 12 } },
                  4000: { label: '4K', style: { fontSize: 12 } }
                }}
                tooltip={{ 
                  formatter: (value?: number) => value ? `${value} tokens (约${Math.floor(value * 0.75)}字)` : ''
                }}
              />
            </Form.Item>
          </Card>
          
          {/* 功能开关 */}
          <Card 
            title="功能设置" 
            size="small" 
            style={{ marginBottom: 32 }}
            bodyStyle={{ padding: 16 }}
          >
            <Row gutter={[16, 16]}>
              <Col span={24}>
                <Form.Item
                  name="stream"
                  valuePropName="checked"
                  style={{ marginBottom: 12 }}
                >
                  <Flex justify="space-between" align="center">
                    <div>
                      <Text strong>流式响应</Text>
                      <br />
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        实时显示AI回复过程，提升交互体验
                      </Text>
                    </div>
                    <Switch 
                      checkedChildren="开启" 
                      unCheckedChildren="关闭"
                      size="default"
                    />
                  </Flex>
                </Form.Item>
              </Col>
              
              <Col span={24}>
                <Form.Item
                  name="memory_enabled"
                  valuePropName="checked"
                  style={{ marginBottom: 0 }}
                >
                  <Flex justify="space-between" align="center">
                    <div>
                      <Text strong>对话记忆</Text>
                      <br />
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        AI将记住之前的对话内容，保持上下文连贯性
                      </Text>
                    </div>
                    <Switch 
                      checkedChildren="开启" 
                      unCheckedChildren="关闭"
                      size="default"
                    />
                  </Flex>
                </Form.Item>
              </Col>
            </Row>
          </Card>
          
          {/* 操作按钮 */}
          <div style={{ position: 'sticky', bottom: 0, backgroundColor: token.colorBgContainer, padding: '16px 0' }}>
            <Space style={{ width: '100%', justifyContent: 'center' }}>
              <Button 
                type="primary" 
                htmlType="submit"
                size="large"
                style={{ minWidth: 120 }}
              >
                保存设置
              </Button>
              <Button 
                onClick={() => setSettingsVisible(false)}
                size="large"
                style={{ minWidth: 120 }}
              >
                取消
              </Button>
            </Space>
          </div>
        </Form>
      </Drawer>

      {/* 现代化对话历史抽屉 */}
      <Drawer
        title={
          <Flex align="center" gap={8}>
            <HistoryOutlined style={{ color: token.colorPrimary }} />
            <span>对话历史</span>
            <Badge count={conversations.length} showZero style={{ marginLeft: 8 }} />
          </Flex>
        }
        open={conversationsVisible}
        onClose={() => setConversationsVisible(false)}
        width={isMobile ? '100%' : 400}
        placement="left"
        styles={{
          header: {
            paddingBottom: 16,
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
          },
          body: {
            padding: 0,
          },
        }}
      >
        {/* 新建对话按钮 */}
        <div style={{ padding: '16px 24px', borderBottom: `1px solid ${token.colorBorderSecondary}` }}>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              handleNewConversation();
              setConversationsVisible(false);
            }}
            block
            size="large"
          >
            新建对话
          </Button>
        </div>

        {/* 对话列表 */}
        <div style={{ height: 'calc(100vh - 200px)', overflowY: 'auto' }}>
          {conversations.length === 0 ? (
            <div 
              style={{ 
                textAlign: 'center', 
                padding: '60px 20px',
                color: token.colorTextTertiary,
              }}
            >
              <HistoryOutlined style={{ fontSize: 48, marginBottom: 16, opacity: 0.5 }} />
              <div>
                <Text type="secondary">暂无对话历史</Text>
              </div>
              <div style={{ marginTop: 8 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  开始新对话后，历史记录将显示在这里
                </Text>
              </div>
            </div>
          ) : (
            conversations.map((conv, index) => (
              <div
                key={conv.id}
                style={{
                  padding: '16px 24px',
                  borderBottom: index === conversations.length - 1 ? 'none' : `1px solid ${token.colorBorderSecondary}`,
                  cursor: 'pointer',
                  transition: 'background-color 0.2s ease',
                  backgroundColor: currentConversation?.id === conv.id 
                    ? token.colorBgSpotlight 
                    : 'transparent',
                }}
                onMouseEnter={(e) => {
                  if (currentConversation?.id !== conv.id) {
                    e.currentTarget.style.backgroundColor = token.colorBgSpotlight;
                  }
                }}
                onMouseLeave={(e) => {
                  if (currentConversation?.id !== conv.id) {
                    e.currentTarget.style.backgroundColor = 'transparent';
                  }
                }}
                onClick={() => {
                  handleSelectConversation(conv);
                  setConversationsVisible(false);
                }}
              >
                <Flex justify="space-between" align="start">
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div 
                      style={{ 
                        fontWeight: currentConversation?.id === conv.id ? 600 : 500,
                        marginBottom: 4,
                        color: currentConversation?.id === conv.id 
                          ? token.colorPrimary 
                          : token.colorTextBase,
                        fontSize: 14,
                        lineHeight: 1.4,
                      }}
                    >
                      {conv.title}
                    </div>
                    
                    <Space split={<span style={{ color: token.colorTextQuaternary }}>•</span>} size="small">
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {dayjs(conv.updated_at).fromNow()}
                      </Text>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {conv.model}
                      </Text>
                    </Space>
                  </div>
                  
                  <Tooltip title="删除对话">
                    <Button
                      type="text"
                      size="small"
                      danger
                      icon={<DeleteOutlined />}
                      onClick={(e) => {
                        e.stopPropagation();
                        Modal.confirm({
                          title: '确认删除',
                          content: '删除后无法恢复，确定要删除这个对话吗？',
                          okText: '确认删除',
                          cancelText: '取消',
                          okType: 'danger',
                          onOk: () => handleDeleteConversation(conv.id),
                        });
                      }}
                      style={{
                        opacity: 0.6,
                        marginLeft: 8,
                        flexShrink: 0,
                      }}
                    />
                  </Tooltip>
                </Flex>
              </div>
            ))
          )}
        </div>
      </Drawer>
    </div>
  );
};

export default ChatPage;