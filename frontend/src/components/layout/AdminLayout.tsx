/**
 * 管理后台布局组件
 * 根据docs/frontend.md规范设计
 */

import React, { useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  Layout,
  Menu,
  Button,
  Dropdown,
  Avatar,
  Space,
  Typography,
  theme,
  Breadcrumb,
  Badge,
  Tooltip,
  Divider,
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
  SearchOutlined,
  CustomerServiceOutlined,
  DatabaseOutlined,
  BarChartOutlined,
  QuestionCircleOutlined,
  HomeOutlined,
  CloudOutlined,
} from '@ant-design/icons';
import { useAuth } from '@/store/auth';
import { ROUTES } from '@/utils/constants';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

interface MenuItem {
  key: string;
  label: string;
  icon: React.ReactNode;
  path: string;
  children?: MenuItem[];
}

// 菜单配置
const menuItems: MenuItem[] = [
  {
    key: 'dashboard',
    label: '仪表盘',
    icon: <DashboardOutlined />,
    path: ROUTES.DASHBOARD,
  },
  {
    key: 'admin',
    label: '管理中心',
    icon: <SettingOutlined />,
    path: ROUTES.ADMIN,
    children: [
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
      {
        key: 'suppliers',
        label: '供应商管理',
        icon: <CloudOutlined />,
        path: ROUTES.ADMIN_SUPPLIERS,
      },
      {
        key: 'analytics',
        label: '数据统计',
        icon: <BarChartOutlined />,
        path: ROUTES.ADMIN_ANALYTICS,
      },
    ],
  },
  {
    key: 'chat',
    label: 'AI聊天',
    icon: <CustomerServiceOutlined />,
    path: ROUTES.CHAT,
  },
  {
    key: 'conversations',
    label: '对话历史',
    icon: <DatabaseOutlined />,
    path: ROUTES.CONVERSATIONS,
  },
  {
    key: 'memory',
    label: '记忆管理',
    icon: <DatabaseOutlined />,
    path: ROUTES.MEMORY,
  },
];

const AdminLayout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const { user, logout, isAdmin } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const { token } = theme.useToken();

  // 计算当前选中的菜单项
  const getSelectedKeys = () => {
    const currentPath = location.pathname;
    for (const item of menuItems) {
      if (item.path === currentPath) {
        return [item.key];
      }
      if (item.children) {
        for (const child of item.children) {
          if (child.path === currentPath) {
            return [child.key];
          }
        }
      }
    }
    return [];
  };

  // 计算当前展开的菜单项
  const getOpenKeys = () => {
    const currentPath = location.pathname;
    for (const item of menuItems) {
      if (item.children) {
        for (const child of item.children) {
          if (child.path === currentPath) {
            return [item.key];
          }
        }
      }
    }
    return [];
  };

  // 生成面包屑数据
  const generateBreadcrumbs = () => {
    const pathSegments = location.pathname.split('/').filter(Boolean);
    const breadcrumbs = [{ title: <HomeOutlined />, path: '/' }];

    let currentPath = '';
    for (const segment of pathSegments) {
      currentPath += `/${segment}`;
      
      // 查找对应的菜单项
      const findMenuItem = (items: MenuItem[], path: string): MenuItem | undefined => {
        for (const item of items) {
          if (item.path === path) {
            return item;
          }
          if (item.children) {
            const found = findMenuItem(item.children, path);
            if (found) return found;
          }
        }
        return undefined;
      };

      const menuItem = findMenuItem(menuItems, currentPath);
      if (menuItem) {
        breadcrumbs.push({
          title: menuItem.label,
          path: menuItem.path,
        });
      }
    }

    return breadcrumbs;
  };

  // 菜单点击事件
  const handleMenuClick = ({ key }: { key: string }) => {
    const findMenuItem = (items: MenuItem[], menuKey: string): MenuItem | undefined => {
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

    const menuItem = findMenuItem(menuItems, key);
    if (menuItem) {
      navigate(menuItem.path);
    }
  };

  // 用户下拉菜单
  const userDropdownItems = [
    {
      key: 'profile',
      label: '个人中心',
      icon: <UserOutlined />,
      onClick: () => navigate(ROUTES.PROFILE),
    },
    {
      key: 'settings',
      label: '设置',
      icon: <SettingOutlined />,
      onClick: () => navigate(ROUTES.SETTINGS),
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      label: '退出登录',
      icon: <LogoutOutlined />,
      onClick: logout,
    },
  ];

  // 过滤菜单项（根据用户权限）
  const filterMenuItems = (items: MenuItem[]): MenuItem[] => {
    return items.filter(item => {
      // 非管理员不能访问管理中心
      if (item.key === 'admin' && !isAdmin) {
        return false;
      }
      return true;
    });
  };

  // 转换为 Ant Design Menu 的数据结构
  const convertToMenuItems = (items: MenuItem[]) => {
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

  const filteredMenuItems = filterMenuItems(menuItems);
  const antdMenuItems = convertToMenuItems(filteredMenuItems);

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* 侧边栏 */}
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        theme="dark"
        width={240}
        style={{
          background: token.colorBgLayout,
          borderRight: `1px solid ${token.colorBorder}`,
        }}
      >
        {/* Logo 区域 */}
        <div
          style={{
            height: 64,
            margin: 16,
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'flex-start',
          }}
        >
          <div
            style={{
              width: 32,
              height: 32,
              backgroundColor: token.colorPrimary,
              borderRadius: 6,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              fontSize: 16,
              fontWeight: 'bold',
            }}
          >
            L
          </div>
          {!collapsed && (
            <Text
              style={{
                marginLeft: 12,
                color: token.colorTextLightSolid,
                fontSize: 16,
                fontWeight: 'bold',
              }}
            >
              Lyss AI
            </Text>
          )}
        </div>

        {/* 导航菜单 */}
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={getSelectedKeys()}
          defaultOpenKeys={getOpenKeys()}
          items={antdMenuItems}
          onClick={handleMenuClick}
          style={{
            border: 'none',
            backgroundColor: 'transparent',
          }}
        />
      </Sider>

      {/* 主内容区域 */}
      <Layout>
        {/* 顶部导航栏 */}
        <Header
          style={{
            padding: '0 16px',
            backgroundColor: token.colorBgContainer,
            borderBottom: `1px solid ${token.colorBorder}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center' }}>
            {/* 折叠按钮 */}
            <Button
              type="text"
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setCollapsed(!collapsed)}
              style={{
                fontSize: '16px',
                width: 64,
                height: 64,
              }}
            />

            {/* 面包屑导航 */}
            <Breadcrumb
              style={{ marginLeft: 16 }}
              items={generateBreadcrumbs().map((item, index) => ({
                title: index === 0 ? item.title : (
                  <a onClick={() => navigate(item.path)}>
                    {item.title}
                  </a>
                ),
              }))}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center' }}>
            {/* 搜索按钮 */}
            <Tooltip title="搜索">
              <Button
                type="text"
                icon={<SearchOutlined />}
                style={{ marginRight: 8 }}
              />
            </Tooltip>

            {/* 通知按钮 */}
            <Tooltip title="通知">
              <Badge count={0} size="small">
                <Button
                  type="text"
                  icon={<BellOutlined />}
                  style={{ marginRight: 8 }}
                />
              </Badge>
            </Tooltip>

            {/* 帮助按钮 */}
            <Tooltip title="帮助">
              <Button
                type="text"
                icon={<QuestionCircleOutlined />}
                style={{ marginRight: 16 }}
              />
            </Tooltip>

            <Divider type="vertical" />

            {/* 用户信息 */}
            <Dropdown menu={{ items: userDropdownItems }} placement="bottomRight">
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  cursor: 'pointer',
                  padding: '8px 12px',
                  borderRadius: 6,
                  transition: 'background-color 0.2s',
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.backgroundColor = token.colorBgTextHover;
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
                    marginRight: 8,
                  }}
                >
                  {user?.name?.charAt(0)?.toUpperCase()}
                </Avatar>
                <Space direction="vertical" size={0}>
                  <Text style={{ fontSize: 14, fontWeight: 500 }}>
                    {user?.name}
                  </Text>
                  <Text style={{ fontSize: 12, color: token.colorTextTertiary }}>
                    {user?.role === 'admin' ? '管理员' : '用户'}
                  </Text>
                </Space>
              </div>
            </Dropdown>
          </div>
        </Header>

        {/* 主内容区域 */}
        <Content
          style={{
            margin: '16px',
            padding: '24px',
            backgroundColor: token.colorBgContainer,
            borderRadius: token.borderRadius,
            minHeight: 'calc(100vh - 112px)',
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default AdminLayout;