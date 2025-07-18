/**
 * 主布局组件 - 参考Ant Design Pro最佳实践
 * 统一的布局设计，适用于所有用户角色
 * 采用现代化对话历史侧边栏 + 顶部导航栏的设计
 */

import React, { useState, useEffect } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  Layout as AntLayout,
  Button,
  Dropdown,
  Avatar,
  Space,
  Typography,
  theme,
  Badge,
  Tooltip,
  Divider,
  Flex,
  Input,
  Empty,
  Modal,
  message,
  Menu,
  List,
  Breadcrumb,
} from 'antd';
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  DashboardOutlined,
  TeamOutlined,
  UserOutlined,
  SettingOutlined,
  LogoutOutlined,
  BellOutlined,
  QuestionCircleOutlined,
  CloudOutlined,
  MessageOutlined,
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  MoreOutlined,
  HomeOutlined,
  CommentOutlined,
} from '@ant-design/icons';
import { useAuth } from '@/store/auth';
import { ROUTES } from '@/utils/constants';
import { ConversationService } from '@/services/conversation';
import { handleApiError } from '@/utils/errorHandler';
import dayjs from 'dayjs';

const { Header, Sider, Content } = AntLayout;
const { Text } = Typography;
const { Search } = Input;

// 对话数据接口
interface Conversation {
  id: string;
  title: string;
  model: string;
  supplier: string;
  last_message: string;
  message_count: number;
  created_at: string;
  updated_at: string;
  is_pinned?: boolean;
  summary?: string;
}

// 主导航菜单配置 - 参考Ant Design Pro顶部导航设计
const mainMenuItems = [
  {
    key: 'dashboard',
    label: '工作台',
    icon: <DashboardOutlined />,
    path: ROUTES.DASHBOARD,
  },
  {
    key: 'chat',
    label: 'AI对话',
    icon: <MessageOutlined />,
    path: '/chat',
  },
  {
    key: 'admin',
    label: '管理中心',
    icon: <SettingOutlined />,
    children: [
      {
        key: 'suppliers',
        label: '供应商配置',
        icon: <CloudOutlined />,
        path: ROUTES.ADMIN_SUPPLIERS,
      },
      {
        key: 'tenants',
        label: '租户管理',
        icon: <TeamOutlined />,
        path: ROUTES.ADMIN_TENANTS,
      },
      {
        key: 'users',
        label: '用户管理',
        icon: <UserOutlined />,
        path: ROUTES.ADMIN_USERS,
      },
    ],
  },
];

const Layout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [searchValue, setSearchValue] = useState('');
  const [conversationLoading, setConversationLoading] = useState(false);
  const { user, logout, isAdmin } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const { token } = theme.useToken();

  // 响应式断点检测
  useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth;
      setIsMobile(width < 768);
      // 在移动端自动折叠侧边栏
      if (width < 768) {
        setCollapsed(true);
      }
    };

    // 初始检测
    handleResize();
    
    // 监听窗口大小变化
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // 加载对话历史
  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = async () => {
    setConversationLoading(true);
    try {
      const response = await ConversationService.getConversations();
      setConversations(response.data || []);
    } catch (error) {
      handleApiError(error);
    } finally {
      setConversationLoading(false);
    }
  };

  // 创建新对话
  const createNewConversation = async () => {
    try {
      const response = await ConversationService.createConversation({
        title: '新对话',
        model: 'gpt-3.5-turbo',
        supplier: 'openai',
      });
      setConversations(prev => [response.data, ...prev]);
      navigate(`/chat/${response.data.id}`);
    } catch (error) {
      handleApiError(error);
    }
  };

  // 删除对话
  const deleteConversation = async (conversationId: string) => {
    try {
      await ConversationService.deleteConversation(conversationId);
      setConversations(prev => prev.filter(conv => conv.id !== conversationId));
      message.success('对话已删除');
    } catch (error) {
      handleApiError(error);
    }
  };

  // 过滤对话
  const filteredConversations = conversations.filter(conv => 
    conv.title.toLowerCase().includes(searchValue.toLowerCase()) ||
    conv.last_message.toLowerCase().includes(searchValue.toLowerCase())
  );

  // 生成面包屑数据
  const generateBreadcrumbs = (): Array<{ title: React.ReactNode; path: string }> => {
    const pathSegments = location.pathname.split('/').filter(Boolean);
    const breadcrumbs: Array<{ title: React.ReactNode; path: string }> = [{ title: <HomeOutlined />, path: '/' }];

    // 简化面包屑逻辑，基于路径生成
    const pathMap: Record<string, string> = {
      'dashboard': '工作台',
      'chat': 'AI对话',
      'admin': '管理中心',
      'suppliers': '供应商配置',
      'tenants': '租户管理',
      'users': '用户管理',
    };

    let currentPath = '';
    for (const segment of pathSegments) {
      currentPath += `/${segment}`;
      const title = pathMap[segment] || segment;
      breadcrumbs.push({
        title,
        path: currentPath,
      });
    }

    return breadcrumbs;
  };

  // 主导航菜单点击事件
  const handleMainMenuClick = ({ key }: { key: string }) => {
    const findMenuItem = (items: typeof mainMenuItems, menuKey: string): any => {
      for (const item of items) {
        if (item.key === menuKey) {
          return item;
        }
        if (item.children) {
          const found = findMenuItem(item.children, menuKey);
          if (found) return found;
        }
      }
      return undefined;
    };

    const menuItem = findMenuItem(mainMenuItems, key);
    if (menuItem) {
      navigate(menuItem.path);
    }
  };

  // 对话点击事件
  const handleConversationClick = (conversationId: string) => {
    navigate(`/chat/${conversationId}`);
  };

  // 用户下拉菜单
  const userDropdownItems = [
    {
      key: 'profile',
      label: '个人中心',
      icon: <UserOutlined />,
      onClick: () => navigate('/profile'),
    },
    {
      key: 'settings',
      label: '设置',
      icon: <SettingOutlined />,
      onClick: () => navigate('/settings'),
    },
    {
      type: 'divider' as const,
    },
    {
      key: 'logout',
      label: '退出登录',
      icon: <LogoutOutlined />,
      onClick: logout,
    },
  ];

  // 过滤主导航菜单项（根据用户权限）
  const filterMainMenuItems = (items: typeof mainMenuItems) => {
    return items.filter(item => {
      // 非管理员不能访问管理中心
      if (item.key === 'admin' && !isAdmin) {
        return false;
      }
      return true;
    });
  };

  // 转换为 Ant Design Menu 的数据结构
  const convertToMenuItems = (items: typeof mainMenuItems): any[] => {
    return items.map(item => {
      if (item.children) {
        return {
          key: item.key,
          label: item.label,
          icon: item.icon,
          children: convertToMenuItems(item.children),
        };
      }
      return {
        key: item.key,
        label: item.label,
        icon: item.icon,
      };
    });
  };

  const filteredMainMenuItems = filterMainMenuItems(mainMenuItems);
  const antdMenuItems = convertToMenuItems(filteredMainMenuItems);

  return (
    <AntLayout style={{ minHeight: '100vh', backgroundColor: token.colorBgLayout }}>
      {/* 现代化对话历史侧边栏 */}
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        theme="light"
        width={280}
        collapsedWidth={isMobile ? 0 : 80}
        breakpoint="lg"
        style={{
          backgroundColor: token.colorBgContainer,
          borderRight: `1px solid ${token.colorBorderSecondary}`,
          boxShadow: isMobile ? 'none' : '2px 0 8px 0 rgba(29, 35, 41, 0.05)',
          position: isMobile ? 'fixed' : 'relative',
          height: '100vh',
          left: 0,
          top: 0,
          zIndex: 1001,
          overflow: 'hidden',
        }}
      >
        {/* 现代化Logo区域 */}
        <div
          style={{
            height: 64,
            padding: '12px 16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'flex-start',
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
            backgroundColor: token.colorBgContainer,
          }}
        >
          <div
            style={{
              width: 40,
              height: 40,
              background: `linear-gradient(135deg, ${token.colorPrimary} 0%, #3b82f6 100%)`,
              borderRadius: 12,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              fontSize: 18,
              fontWeight: '600',
              boxShadow: '0 4px 12px rgba(37, 99, 235, 0.15)',
            }}
          >
            L
          </div>
          {!collapsed && (
            <div style={{ marginLeft: 12 }}>
              <Text
                style={{
                  fontSize: 16,
                  fontWeight: '600',
                  color: token.colorTextBase,
                  lineHeight: 1.2,
                }}
              >
                Lyss AI
              </Text>
            </div>
          )}
        </div>

        {/* 新建对话按钮 */}
        {!collapsed && (
          <div style={{ padding: '16px 16px 8px 16px' }}>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              block
              size="large"
              onClick={createNewConversation}
              style={{
                borderRadius: 8,
                height: 40,
                fontSize: 14,
                fontWeight: 500,
              }}
            >
              新建对话
            </Button>
          </div>
        )}

        {/* 对话搜索 */}
        {!collapsed && (
          <div style={{ padding: '8px 16px' }}>
            <Search
              placeholder="搜索对话..."
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
              style={{
                borderRadius: 8,
              }}
            />
          </div>
        )}

        {/* 对话历史列表 */}
        <div
          style={{
            flex: 1,
            overflow: 'auto',
            padding: !collapsed ? '8px 16px' : '8px 12px',
          }}
        >
          {!collapsed ? (
            <List
              loading={conversationLoading}
              dataSource={filteredConversations}
              locale={{
                emptyText: (
                  <Empty
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                    description="暂无对话记录"
                    style={{ margin: '20px 0' }}
                  />
                ),
              }}
              renderItem={(conversation) => (
                <List.Item
                  style={{
                    padding: '8px 12px',
                    borderRadius: 8,
                    cursor: 'pointer',
                    marginBottom: 4,
                    backgroundColor: location.pathname.includes(conversation.id) ? token.colorPrimaryBg : 'transparent',
                    border: location.pathname.includes(conversation.id) ? `1px solid ${token.colorPrimary}` : '1px solid transparent',
                    transition: 'all 0.2s ease',
                  }}
                  onClick={() => handleConversationClick(conversation.id)}
                  onMouseEnter={(e) => {
                    if (!location.pathname.includes(conversation.id)) {
                      e.currentTarget.style.backgroundColor = token.colorBgSpotlight;
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!location.pathname.includes(conversation.id)) {
                      e.currentTarget.style.backgroundColor = 'transparent';
                    }
                  }}
                >
                  <div style={{ width: '100%' }}>
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'flex-start',
                        marginBottom: 4,
                      }}
                    >
                      <Text
                        style={{
                          fontSize: 13,
                          fontWeight: 500,
                          color: token.colorTextBase,
                          lineHeight: 1.2,
                        }}
                        ellipsis
                      >
                        {conversation.title}
                      </Text>
                      <Dropdown
                        menu={{
                          items: [
                            {
                              key: 'edit',
                              label: '重命名',
                              icon: <EditOutlined />,
                            },
                            {
                              key: 'delete',
                              label: '删除',
                              icon: <DeleteOutlined />,
                              danger: true,
                              onClick: () => {
                                Modal.confirm({
                                  title: '确认删除',
                                  content: `确定要删除对话 "${conversation.title}" 吗？`,
                                  onOk: () => deleteConversation(conversation.id),
                                });
                              },
                            },
                          ],
                        }}
                        trigger={['click']}
                      >
                        <Button
                          type="text"
                          icon={<MoreOutlined />}
                          size="small"
                          style={{
                            width: 20,
                            height: 20,
                            padding: 0,
                            minWidth: 20,
                          }}
                          onClick={(e) => e.stopPropagation()}
                        />
                      </Dropdown>
                    </div>
                    <Text
                      style={{
                        fontSize: 11,
                        color: token.colorTextTertiary,
                        lineHeight: 1.2,
                      }}
                      ellipsis
                    >
                      {conversation.last_message}
                    </Text>
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginTop: 4,
                      }}
                    >
                      <Text
                        style={{
                          fontSize: 10,
                          color: token.colorTextTertiary,
                        }}
                      >
                        {dayjs(conversation.updated_at).format('MM/DD')}
                      </Text>
                      <Text
                        style={{
                          fontSize: 10,
                          color: token.colorTextTertiary,
                        }}
                      >
                        {conversation.message_count} 消息
                      </Text>
                    </div>
                  </div>
                </List.Item>
              )}
            />
          ) : (
            // 折叠状态下的简化图标
            <div style={{ textAlign: 'center', padding: '16px 0' }}>
              <Button
                type="text"
                icon={<MessageOutlined />}
                size="large"
                onClick={createNewConversation}
                style={{
                  width: 56,
                  height: 56,
                  borderRadius: 12,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 20,
                  color: token.colorPrimary,
                }}
              />
            </div>
          )}
        </div>
      </Sider>

      {/* 主内容区域 */}
      <AntLayout style={{ marginLeft: isMobile && !collapsed ? 0 : 0 }}>
        {/* 现代化顶部导航栏 - 参考Ant Design Pro设计 */}
        <Header
          style={{
            padding: '0 24px',
            backgroundColor: token.colorBgContainer,
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            height: 64,
            zIndex: 1000,
            boxShadow: '0 1px 4px 0 rgba(0, 0, 0, 0.02)',
          }}
        >
          <Flex align="center" gap={16}>
            {/* 现代化折叠按钮 */}
            <Button
              type="text"
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setCollapsed(!collapsed)}
              style={{
                fontSize: 16,
                width: 40,
                height: 40,
                borderRadius: 8,
                color: token.colorText,
                transition: 'all 0.2s ease',
              }}
            />

            {/* 主导航菜单 - 参考Ant Design Pro最佳实践 */}
            <Menu
              theme="light"
              mode="horizontal"
              selectedKeys={[location.pathname.split('/')[1] || 'dashboard']}
              items={antdMenuItems}
              onClick={handleMainMenuClick}
              style={{
                backgroundColor: 'transparent',
                border: 'none',
                flex: 1,
                minWidth: 0,
                fontSize: 14,
                fontWeight: 500,
              }}
            />
          </Flex>

          <Flex align="center" gap={8}>
            {/* 右侧工具栏 */}
            <Tooltip title="通知消息">
              <Badge count={0} size="small">
                <Button
                  type="text"
                  icon={<BellOutlined />}
                  style={{
                    width: 40,
                    height: 40,
                    borderRadius: 8,
                    color: token.colorTextSecondary,
                  }}
                />
              </Badge>
            </Tooltip>

            <Tooltip title="帮助文档">
              <Button
                type="text"
                icon={<QuestionCircleOutlined />}
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: 8,
                  color: token.colorTextSecondary,
                }}
              />
            </Tooltip>

            <Divider 
              type="vertical" 
              style={{ 
                height: 24,
                borderColor: token.colorBorderSecondary,
                margin: '0 8px',
              }} 
            />

            {/* 用户头像菜单 - 只保留右上角一个 */}
            <Dropdown 
              menu={{ items: userDropdownItems }} 
              placement="bottomRight"
              trigger={['click']}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  cursor: 'pointer',
                  padding: '6px 12px',
                  borderRadius: 8,
                  transition: 'background-color 0.2s ease',
                  backgroundColor: 'transparent',
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.backgroundColor = token.colorBgSpotlight;
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.backgroundColor = 'transparent';
                }}
              >
                <Avatar
                  size={32}
                  src={user?.avatar}
                  style={{
                    backgroundColor: token.colorPrimary,
                    marginRight: !isMobile ? 8 : 0,
                    border: `2px solid ${token.colorBgContainer}`,
                    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
                  }}
                >
                  {user?.name?.charAt(0)?.toUpperCase()}
                </Avatar>
                {!isMobile && (
                  <Space direction="vertical" size={0}>
                    <Text 
                      style={{ 
                        fontSize: 14, 
                        fontWeight: 500,
                        color: token.colorTextBase,
                        lineHeight: 1.2,
                      }}
                    >
                      {user?.name}
                    </Text>
                    <Text 
                      style={{ 
                        fontSize: 12, 
                        color: token.colorTextTertiary,
                        lineHeight: 1,
                      }}
                    >
                      {user?.role === 'admin' ? '管理员' : '用户'}
                    </Text>
                  </Space>
                )}
              </div>
            </Dropdown>
          </Flex>
        </Header>

        {/* 现代化主内容区域 - 移除冗余标头容器 */}
        <Content
          style={{
            padding: 0,
            margin: 0,
            minHeight: 'calc(100vh - 64px)',
            backgroundColor: token.colorBgContainer,
            overflow: 'hidden',
          }}
        >
          <Outlet />
        </Content>
      </AntLayout>

      {/* 移动端遮罩层 */}
      {isMobile && !collapsed && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.45)',
            zIndex: 1000,
          }}
          onClick={() => setCollapsed(true)}
        />
      )}
    </AntLayout>
  );
};

export default Layout;