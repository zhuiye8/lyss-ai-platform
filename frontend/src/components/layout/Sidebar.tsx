/**
 * 侧边栏组件
 * 已在AdminLayout中集成，这里作为独立组件导出
 */

import React from 'react';
import { Layout, Menu, Typography } from 'antd';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  DashboardOutlined,
  TeamOutlined,
  UserOutlined,
  SettingOutlined,
  CustomerServiceOutlined,
  DatabaseOutlined,
  BarChartOutlined,
  CloudOutlined,
} from '@ant-design/icons';
import { useAuth } from '@/store/auth';
import { ROUTES } from '@/utils/constants';

const { Sider } = Layout;
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

interface SidebarProps {
  collapsed: boolean;
}

const Sidebar: React.FC<SidebarProps> = ({ collapsed }) => {
  const { isAdmin } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

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
  const convertToMenuItems = (items: MenuItem[]): any[] => {
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
    <Sider
      trigger={null}
      collapsible
      collapsed={collapsed}
      theme="dark"
      width={240}
      style={{
        background: '#001529',
        borderRight: '1px solid #f0f0f0',
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
            backgroundColor: '#1890ff',
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
              color: 'white',
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
  );
};

export default Sidebar;