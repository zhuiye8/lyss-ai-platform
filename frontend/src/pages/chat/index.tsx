/**
 * AI聊天界面
 * 根据docs/frontend.md规范，集成Ant Design X组件
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  Row,
  Col,
  Card,
  Button,
  Space,
  Select,
  Tooltip,
  Modal,
  Form,
  Input,
  Slider,
  Switch,
  message,
  Typography,
  Badge,
  Avatar,
  Tag,
} from 'antd';
import {
  SendOutlined,
  SettingOutlined,
  HistoryOutlined,
  PlusOutlined,
  DeleteOutlined,
  RobotOutlined,
  UserOutlined,
  CopyOutlined,
  RedoOutlined,
} from '@ant-design/icons';
import { Conversations, Bubble, Sender } from '@ant-design/x';
import dayjs from 'dayjs';

import { ChatService } from '@/services/chat';
import { ConversationService } from '@/services/conversation';
import { useAuth } from '@/store/auth';
import { SUPPLIER_CONFIG } from '@/utils/constants';
import { handleApiError, handleStreamError, withErrorHandling } from '@/utils/errorHandler';

const { Title, Text } = Typography;
const { Option } = Select;

// 消息类型
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
  
  const [chatConfig, setChatConfig] = useState<ChatConfig>({
    model: 'gpt-3.5-turbo',
    supplier: 'openai',
    temperature: 0.7,
    max_tokens: 2000,
    stream: true,
    memory_enabled: true,
  });

  const { user } = useAuth();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [form] = Form.useForm();

  /**
   * 滚动到底部
   */
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

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
      
      if (response.success) {
        setConversations(response.data.items);
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
   * 发送消息
   */
  const handleSendMessage = async (content: string) => {
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
      if (chatConfig.stream) {
        // 流式响应
        await handleStreamingResponse(content);
      } else {
        // 普通响应
        await handleNormalResponse(content);
      }
    } catch (error) {
      handleApiError(error);
      
      // 根据错误类型添加不同的错误消息
      let errorContent = '抱歉，发生了错误，请稍后重试。';
      
      if (error.code === 'NETWORK_ERROR') {
        errorContent = '网络连接失败，请检查网络后重试。';
      } else if (error.response?.status === 429) {
        errorContent = '请求过于频繁，请稍后再试。';
      } else if (error.response?.status === 401) {
        errorContent = '认证失效，请重新登录。';
      } else if (error.response?.status >= 500) {
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
    } finally {
      setLoading(false);
      setStreaming(false);
    }
  };

  /**
   * 处理流式响应
   */
  const handleStreamingResponse = async (content: string) => {
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
              }
            } catch (e) {
              console.warn('解析流式数据失败:', e);
            }
          }
        }
      }
    } catch (error) {
      console.error('流式聊天失败:', error);
      throw error;
    }
  };

  /**
   * 处理普通响应
   */
  const handleNormalResponse = async (content: string) => {
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

      if (response.success) {
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

        setMessages(prev => [...prev, assistantMessage]);

        // 更新当前对话
        if (response.data.conversation_id) {
          setCurrentConversation(prev => prev ? {
            ...prev,
            id: response.data.conversation_id,
            updated_at: new Date().toISOString(),
          } : null);
        }
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
      if (response.success) {
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

  /**
   * 复制消息内容
   */
  const handleCopyMessage = (content: string) => {
    navigator.clipboard.writeText(content);
    message.success('已复制到剪贴板');
  };

  /**
   * 重新生成回答
   */
  const handleRegenerateResponse = async (messageIndex: number) => {
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
    <div className="chat-container" style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* 头部工具栏 */}
      <Card 
        className="chat-toolbar"
        size="small" 
        style={{ 
          borderBottom: '1px solid #f0f0f0',
          borderRadius: 0,
          marginBottom: 0,
        }}
      >
        <Row justify="space-between" align="middle">
          <Col xs={12} sm={12} md={16} lg={16}>
            <Space>
              <Title level={4} style={{ margin: 0 }}>
                AI 对话
              </Title>
              {currentConversation && (
                <Tag className="desktop-only">{currentConversation.title}</Tag>
              )}
            </Space>
          </Col>
          <Col xs={12} sm={12} md={8} lg={8}>
            <Space>
              <Tooltip title="对话历史">
                <Button
                  icon={<HistoryOutlined />}
                  onClick={() => setConversationsVisible(true)}
                  size="small"
                />
              </Tooltip>
              <Tooltip title="新建对话">
                <Button
                  icon={<PlusOutlined />}
                  onClick={handleNewConversation}
                  size="small"
                />
              </Tooltip>
              <Tooltip title="设置">
                <Button
                  icon={<SettingOutlined />}
                  onClick={() => setSettingsVisible(true)}
                  size="small"
                />
              </Tooltip>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 聊天区域 */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* 消息列表 */}
        <div 
          className="chat-message-list"
          style={{ 
            flex: 1, 
            overflow: 'auto', 
            padding: '16px 24px',
            background: '#fafafa'
          }}
        >
          {messages.length === 0 ? (
            <div style={{ 
              textAlign: 'center', 
              padding: '80px 0',
              color: '#999'
            }}>
              <RobotOutlined style={{ fontSize: 48, marginBottom: 16 }} />
              <div>
                <Text type="secondary">开始与AI对话吧</Text>
              </div>
              <div style={{ marginTop: 16 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  当前模型: {chatConfig.model} | 供应商: {
                    SUPPLIER_CONFIG[chatConfig.supplier.toUpperCase() as keyof typeof SUPPLIER_CONFIG]?.name || chatConfig.supplier
                  }
                </Text>
              </div>
            </div>
          ) : (
            <div>
              {messages.map((message, index) => (
                <div key={message.id} style={{ marginBottom: 16 }}>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                    {message.role === 'assistant' && (
                      <Avatar 
                        style={{ backgroundColor: '#1890ff' }}
                        icon={<RobotOutlined />}
                      />
                    )}
                    <div style={{ flex: 1 }}>
                      <Bubble
                        content={message.content}
                        placement={message.role === 'user' ? 'end' : 'start'}
                        typing={streaming && index === messages.length - 1}
                        variant={message.metadata?.isError ? 'filled' : undefined}
                        style={message.metadata?.isError ? { 
                          backgroundColor: '#fff2f0',
                          borderColor: '#ffccc7',
                          color: '#cf1322'
                        } : undefined}
                      />
                      {message.role === 'assistant' && (
                        <div style={{ marginTop: 4 }}>
                          <Space size="small">
                            <Tooltip title="复制">
                              <Button
                                type="text"
                                size="small"
                                icon={<CopyOutlined />}
                                onClick={() => handleCopyMessage(message.content)}
                              />
                            </Tooltip>
                            <Tooltip title="重新生成">
                              <Button
                                type="text"
                                size="small"
                                icon={<RedoOutlined />}
                                onClick={() => handleRegenerateResponse(index)}
                                loading={loading}
                              />
                            </Tooltip>
                          </Space>
                        </div>
                      )}
                      {message.tokens && (
                        <div style={{ marginTop: 4 }}>
                          <Text type="secondary" style={{ fontSize: 10 }}>
                            模型: {message.model} | 
                            输入: {message.tokens.input} | 
                            输出: {message.tokens.output} | 
                            总计: {message.tokens.total} tokens
                          </Text>
                        </div>
                      )}
                    </div>
                    {message.role === 'user' && (
                      <Avatar src={user?.avatar} icon={<UserOutlined />} />
                    )}
                  </div>
                  <div style={{ 
                    textAlign: message.role === 'user' ? 'right' : 'left',
                    marginTop: 4
                  }}>
                    <Text type="secondary" style={{ fontSize: 10 }}>
                      {dayjs(message.timestamp).format('HH:mm:ss')}
                    </Text>
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* 输入区域 */}
        <div 
          className="chat-input-area"
          style={{ 
            padding: '16px 24px',
            borderTop: '1px solid #f0f0f0',
            background: '#fff'
          }}
        >
          <Sender
            onSubmit={handleSendMessage}
            loading={loading || streaming}
            placeholder="输入消息..."
            style={{ width: '100%' }}
            disabled={loading || streaming}
          />
          
          <div style={{ 
            marginTop: 8,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <Space size="small">
              <Text type="secondary" style={{ fontSize: 11 }}>
                模型: {chatConfig.model}
              </Text>
              <Text type="secondary" style={{ fontSize: 11 }}>
                温度: {chatConfig.temperature}
              </Text>
              {chatConfig.memory_enabled && (
                <Badge status="success" text="记忆已启用" />
              )}
            </Space>
            
            <Space size="small">
              <Text type="secondary" style={{ fontSize: 11 }}>
                {streaming ? '正在生成...' : loading ? '发送中...' : '准备就绪'}
              </Text>
            </Space>
          </div>
        </div>
      </div>

      {/* 设置模态框 */}
      <Modal
        title="聊天设置"
        open={settingsVisible}
        onCancel={() => setSettingsVisible(false)}
        footer={null}
        width="90%"
        style={{ maxWidth: 600 }}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={chatConfig}
          onFinish={handleSaveSettings}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="AI供应商"
                name="supplier"
                rules={[{ required: true, message: '请选择供应商' }]}
              >
                <Select>
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
            </Col>
            <Col span={12}>
              <Form.Item
                label="模型"
                name="model"
                rules={[{ required: true, message: '请选择模型' }]}
              >
                <Select>
                  <Option value="gpt-3.5-turbo">GPT-3.5 Turbo</Option>
                  <Option value="gpt-4">GPT-4</Option>
                  <Option value="gpt-4-turbo">GPT-4 Turbo</Option>
                  <Option value="claude-3-haiku">Claude 3 Haiku</Option>
                  <Option value="claude-3-sonnet">Claude 3 Sonnet</Option>
                  <Option value="claude-3-opus">Claude 3 Opus</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
          
          <Form.Item
            label={`温度 (${form.getFieldValue('temperature') || 0.7})`}
            name="temperature"
          >
            <Slider
              min={0}
              max={2}
              step={0.1}
              marks={{
                0: '精确',
                1: '平衡',
                2: '创造'
              }}
            />
          </Form.Item>
          
          <Form.Item
            label="最大输出长度"
            name="max_tokens"
          >
            <Slider
              min={100}
              max={4000}
              step={100}
              marks={{
                100: '100',
                2000: '2000',
                4000: '4000'
              }}
            />
          </Form.Item>
          
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="流式响应"
                name="stream"
                valuePropName="checked"
              >
                <Switch checkedChildren="开启" unCheckedChildren="关闭" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="启用记忆"
                name="memory_enabled"
                valuePropName="checked"
              >
                <Switch checkedChildren="开启" unCheckedChildren="关闭" />
              </Form.Item>
            </Col>
          </Row>
          
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                保存设置
              </Button>
              <Button onClick={() => setSettingsVisible(false)}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 对话历史侧边栏 */}
      <Modal
        title="对话历史"
        open={conversationsVisible}
        onCancel={() => setConversationsVisible(false)}
        footer={null}
        width="95%"
        style={{ maxWidth: 800 }}
      >
        <div style={{ maxHeight: 400, overflow: 'auto' }}>
          {conversations.map(conv => (
            <div
              key={conv.id}
              style={{
                padding: '12px 16px',
                borderBottom: '1px solid #f0f0f0',
                cursor: 'pointer',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
              onClick={() => {
                handleSelectConversation(conv);
                setConversationsVisible(false);
              }}
            >
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 500, marginBottom: 4 }}>
                  {conv.title}
                </div>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {dayjs(conv.updated_at).fromNow()}
                </Text>
              </div>
              <Tooltip title="删除">
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
                      onOk: () => handleDeleteConversation(conv.id),
                    });
                  }}
                />
              </Tooltip>
            </div>
          ))}
          {conversations.length === 0 && (
            <div style={{ textAlign: 'center', padding: '40px 20px', color: '#999' }}>
              暂无对话历史
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
};

export default ChatPage;