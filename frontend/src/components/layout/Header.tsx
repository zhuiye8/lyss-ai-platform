/**
 * 头部组件
 * 已在AdminLayout中集成，这里作为独立组件导出
 */

import React from 'react';
import { Layout, Button, Dropdown, Avatar, Space, Typography, Breadcrumb, Badge, Tooltip, Divider } from 'antd';
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  SearchOutlined,
  BellOutlined,
  QuestionCircleOutlined,
  UserOutlined,
  SettingOutlined,
  LogoutOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/store/auth';
import { ROUTES } from '@/utils/constants';

const { Header: AntdHeader } = Layout;
const { Text } = Typography;

interface HeaderProps {
  collapsed: boolean;
  onCollapse: (collapsed: boolean) => void;
  breadcrumbs?: Array<{ title: React.ReactNode; path: string }>;
}

const Header: React.FC<HeaderProps> = ({
  collapsed,
  onCollapse,
  breadcrumbs = [],
}) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

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
      type: 'divider' as const,
    },
    {
      key: 'logout',
      label: '退出登录',
      icon: <LogoutOutlined />,
      onClick: logout,
    },
  ];

  return (
    <AntdHeader
      style={{
        padding: '0 16px',
        backgroundColor: '#fff',
        borderBottom: '1px solid #f0f0f0',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: 64,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center' }}>
        {/* 折叠按钮 */}
        <Button
          type="text"
          icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          onClick={() => onCollapse(!collapsed)}
          style={{
            fontSize: '16px',
            width: 64,
            height: 64,
          }}
        />

        {/* 面包屑导航 */}
        <Breadcrumb
          style={{ marginLeft: 16 }}
          items={breadcrumbs.map((item, index) => ({
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
          >
            <Avatar
              size={32}
              src={user?.avatar}
              style={{
                backgroundColor: '#1890ff',
                marginRight: 8,
              }}
            >
              {user?.name?.charAt(0)?.toUpperCase()}
            </Avatar>
            <Space direction="vertical" size={0}>
              <Text style={{ fontSize: 14, fontWeight: 500 }}>
                {user?.name}
              </Text>
              <Text style={{ fontSize: 12, color: '#999' }}>
                {user?.role === 'admin' ? '管理员' : '用户'}
              </Text>
            </Space>
          </div>
        </Dropdown>
      </div>
    </AntdHeader>
  );
};

export default Header;