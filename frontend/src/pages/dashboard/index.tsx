/**
 * 用户仪表板页面
 * 显示用户基本信息和平台使用统计
 */

import React from 'react';
import { Layout, Card, Row, Col, Statistic, Typography, Button, Space, Avatar } from 'antd';
import { UserOutlined, LogoutOutlined, SettingOutlined } from '@ant-design/icons';
import { useAuth } from '@/store/auth';
import { ROUTES } from '@/utils/constants';

const { Header, Content } = Layout;
const { Title, Text } = Typography;

const DashboardPage: React.FC = () => {
  const { user, logout, isAdmin } = useAuth();

  const handleLogout = async () => {
    try {
      await logout();
    } catch (error) {
      console.error('登出失败:', error);
    }
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* 页面头部 */}
      <Header style={{ 
        background: '#fff', 
        padding: '0 24px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        borderBottom: '1px solid #f0f0f0'
      }}>
        <Title level={3} style={{ margin: 0, color: '#1890ff' }}>
          Lyss AI Platform
        </Title>
        
        <Space>
          <Avatar 
            size={40} 
            icon={<UserOutlined />} 
            src={user?.avatar}
          />
          <div>
            <div style={{ fontWeight: 500 }}>{user?.name}</div>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {user?.role === 'admin' ? '管理员' : '用户'}
            </Text>
          </div>
          <Button 
            type="text" 
            icon={<SettingOutlined />}
            onClick={() => window.location.href = ROUTES.SETTINGS}
          >
            设置
          </Button>
          <Button 
            type="text" 
            icon={<LogoutOutlined />}
            onClick={handleLogout}
          >
            登出
          </Button>
        </Space>
      </Header>

      {/* 页面内容 */}
      <Content style={{ padding: '24px' }}>
        <div style={{ maxWidth: 1200, margin: '0 auto' }}>
          {/* 欢迎信息 */}
          <Card style={{ marginBottom: 24 }}>
            <Row>
              <Col span={24}>
                <Title level={2} style={{ marginBottom: 8 }}>
                  欢迎回来，{user?.name}！
                </Title>
                <Text type="secondary">
                  这是您的个人仪表板，您可以在这里查看平台使用情况和管理您的账户。
                </Text>
              </Col>
            </Row>
          </Card>

          {/* 统计卡片 */}
          <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="今日对话"
                  value={0}
                  valueStyle={{ color: '#3f8600' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="本月API调用"
                  value={0}
                  valueStyle={{ color: '#1890ff' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="存储使用"
                  value={0}
                  suffix="MB"
                  valueStyle={{ color: '#cf1322' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="活跃天数"
                  value={1}
                  valueStyle={{ color: '#722ed1' }}
                />
              </Card>
            </Col>
          </Row>

          {/* 快速操作 */}
          <Card title="快速操作" style={{ marginBottom: 24 }}>
            <Row gutter={[16, 16]}>
              <Col xs={24} sm={12} md={8}>
                <Card 
                  hoverable
                  style={{ textAlign: 'center' }}
                  onClick={() => window.location.href = ROUTES.CHAT}
                >
                  <div style={{ fontSize: 32, marginBottom: 16 }}>💬</div>
                  <Title level={4}>开始对话</Title>
                  <Text type="secondary">与AI助手开始新的对话</Text>
                </Card>
              </Col>
              
              {isAdmin && (
                <>
                  <Col xs={24} sm={12} md={8}>
                    <Card 
                      hoverable
                      style={{ textAlign: 'center' }}
                      onClick={() => window.location.href = ROUTES.ADMIN_USERS}
                    >
                      <div style={{ fontSize: 32, marginBottom: 16 }}>👥</div>
                      <Title level={4}>用户管理</Title>
                      <Text type="secondary">管理平台用户和权限</Text>
                    </Card>
                  </Col>
                  
                  <Col xs={24} sm={12} md={8}>
                    <Card 
                      hoverable
                      style={{ textAlign: 'center' }}
                      onClick={() => window.location.href = ROUTES.ADMIN_SUPPLIERS}
                    >
                      <div style={{ fontSize: 32, marginBottom: 16 }}>🔧</div>
                      <Title level={4}>供应商配置</Title>
                      <Text type="secondary">配置AI服务供应商</Text>
                    </Card>
                  </Col>
                </>
              )}
            </Row>
          </Card>

          {/* 用户信息 */}
          <Card title="账户信息">
            <Row gutter={[16, 16]}>
              <Col xs={24} md={12}>
                <div style={{ marginBottom: 16 }}>
                  <Text strong>邮箱地址：</Text>
                  <div>{user?.email}</div>
                </div>
                <div style={{ marginBottom: 16 }}>
                  <Text strong>用户角色：</Text>
                  <div>{user?.role === 'admin' ? '管理员' : '普通用户'}</div>
                </div>
                <div style={{ marginBottom: 16 }}>
                  <Text strong>账户状态：</Text>
                  <div style={{ color: user?.is_active ? '#52c41a' : '#f5222d' }}>
                    {user?.is_active ? '正常' : '已禁用'}
                  </div>
                </div>
              </Col>
              <Col xs={24} md={12}>
                <div style={{ marginBottom: 16 }}>
                  <Text strong>租户ID：</Text>
                  <div style={{ fontFamily: 'monospace', fontSize: 12 }}>
                    {user?.tenant_id}
                  </div>
                </div>
                <div style={{ marginBottom: 16 }}>
                  <Text strong>最后登录：</Text>
                  <div>
                    {user?.last_login_at ? 
                      new Date(user.last_login_at).toLocaleString('zh-CN') : 
                      '首次登录'
                    }
                  </div>
                </div>
                <div style={{ marginBottom: 16 }}>
                  <Text strong>注册时间：</Text>
                  <div>
                    {user?.created_at ? 
                      new Date(user.created_at).toLocaleString('zh-CN') : 
                      '未知'
                    }
                  </div>
                </div>
              </Col>
            </Row>
          </Card>
        </div>
      </Content>
    </Layout>
  );
};

export default DashboardPage;