/**
 * 登录页面
 * 根据docs/frontend.md规范实现用户认证界面
 */

import React, { useState, useEffect } from 'react';
import { Form, Input, Button, Card, message, Divider, Typography, Space } from 'antd';
import { UserOutlined, LockOutlined, EyeInvisibleOutlined, EyeTwoTone } from '@ant-design/icons';
import { Navigate } from 'react-router-dom';
import { useAuth } from '@/store/auth';
import { LoginCredentials } from '@/types/user';
import { ROUTES, APP_CONFIG, VALIDATION_RULES } from '@/utils/constants';
import './Login.module.css';

const { Title, Text, Link } = Typography;

const LoginPage: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const { isAuthenticated, login, error, clearError } = useAuth();

  // 如果已经登录，重定向到仪表板
  if (isAuthenticated) {
    return <Navigate to={ROUTES.DASHBOARD} replace />;
  }

  // 清除错误状态
  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => {
        clearError();
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [error, clearError]);

  /**
   * 处理登录表单提交
   */
  const handleLogin = async (values: LoginCredentials) => {
    setLoading(true);
    
    try {
      await login(values);
      message.success('登录成功');
    } catch (error) {
      console.error('登录失败:', error);
      // 错误已在store中处理并显示
    } finally {
      setLoading(false);
    }
  };

  /**
   * 处理忘记密码
   */
  const handleForgotPassword = () => {
    message.info('请联系系统管理员重置密码');
    // TODO: 实现忘记密码功能
  };

  return (
    <div className="login-container">
      <div className="login-content">
        {/* Logo和标题 */}
        <div className="login-header">
          <div className="logo">
            <img 
              src="/logo.svg" 
              alt={APP_CONFIG.NAME}
              onError={(e) => {
                // 如果logo不存在，显示文字
                (e.target as HTMLImageElement).style.display = 'none';
              }}
            />
            <Title level={2} style={{ margin: 0, color: '#1890ff' }}>
              {APP_CONFIG.NAME}
            </Title>
          </div>
          <Text type="secondary" style={{ fontSize: 16 }}>
            {APP_CONFIG.DESCRIPTION}
          </Text>
        </div>

        {/* 登录卡片 */}
        <Card 
          className="login-card"
          title={
            <div style={{ textAlign: 'center' }}>
              <Title level={3} style={{ margin: 0 }}>
                用户登录
              </Title>
            </div>
          }
          bordered={false}
        >
          {/* 错误提示 */}
          {error && (
            <div className="error-alert">
              <Text type="danger">{error}</Text>
            </div>
          )}

          {/* 登录表单 */}
          <Form
            form={form}
            name="login"
            layout="vertical"
            size="large"
            onFinish={handleLogin}
            autoComplete="off"
            style={{ marginTop: 16 }}
          >
            {/* 邮箱输入 */}
            <Form.Item
              name="email"
              label="邮箱地址"
              rules={[
                VALIDATION_RULES.REQUIRED,
                VALIDATION_RULES.EMAIL,
              ]}
            >
              <Input
                prefix={<UserOutlined className="input-icon" />}
                placeholder="请输入您的邮箱地址"
                autoComplete="email"
              />
            </Form.Item>

            {/* 密码输入 */}
            <Form.Item
              name="password"
              label="密码"
              rules={[
                VALIDATION_RULES.REQUIRED,
                {
                  min: 6,
                  message: '密码至少需要6个字符',
                },
              ]}
            >
              <Input.Password
                prefix={<LockOutlined className="input-icon" />}
                placeholder="请输入您的密码"
                autoComplete="current-password"
                iconRender={(visible) => 
                  visible ? <EyeTwoTone /> : <EyeInvisibleOutlined />
                }
              />
            </Form.Item>

            {/* 记住我和忘记密码 */}
            <Form.Item style={{ marginBottom: 16 }}>
              <div className="login-options">
                <Form.Item name="remember_me" valuePropName="checked" noStyle>
                  {/* TODO: 实现记住我功能 */}
                </Form.Item>
                <Link onClick={handleForgotPassword}>
                  忘记密码？
                </Link>
              </div>
            </Form.Item>

            {/* 登录按钮 */}
            <Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                block
                size="large"
                style={{ height: 48 }}
              >
                {loading ? '登录中...' : '登录'}
              </Button>
            </Form.Item>
          </Form>

          <Divider>或</Divider>

          {/* 其他登录方式 */}
          <div className="alternative-login">
            <Text type="secondary">
              还没有账户？
              <Link onClick={() => message.info('请联系系统管理员创建账户')}>
                联系管理员
              </Link>
            </Text>
          </div>
        </Card>

        {/* 底部信息 */}
        <div className="login-footer">
          <Space direction="vertical" align="center">
            <Text type="secondary" style={{ fontSize: 12 }}>
              版本 {APP_CONFIG.VERSION}
            </Text>
            <Text type="secondary" style={{ fontSize: 12 }}>
              © 2025 Lyss AI Platform. All rights reserved.
            </Text>
          </Space>
        </div>
      </div>

      {/* 背景装饰 */}
      <div className="login-background">
        <div className="bg-shapes">
          <div className="shape shape-1"></div>
          <div className="shape shape-2"></div>
          <div className="shape shape-3"></div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;