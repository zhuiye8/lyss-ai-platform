/**
 * Lyss AI Platform - 登录页面
 * 功能描述: 用户登录界面
 * 作者: Claude AI Assistant
 * 创建时间: 2025-07-09
 * 最后更新: 2025-07-09
 */

import React, { useState } from 'react'
import { Form, Input, Button, Card, Checkbox, Divider, message } from 'antd'
import { UserOutlined, LockOutlined, EyeInvisibleOutlined, EyeTwoTone } from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { LoginRequest } from '@/types'

/**
 * 登录页面组件
 */
const LoginPage: React.FC = () => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { login } = useAuth()

  // 获取重定向URL
  const from = location.state?.from?.pathname || '/dashboard'

  /**
   * 处理登录表单提交
   */
  const handleSubmit = async (values: LoginRequest) => {
    setLoading(true)
    
    try {
      const success = await login(values)
      
      if (success) {
        message.success('登录成功，正在跳转...')
        // 延迟跳转，让用户看到成功消息
        setTimeout(() => {
          navigate(from, { replace: true })
        }, 1000)
      }
    } catch (error) {
      console.error('登录失败:', error)
      // 错误消息已经在认证store中处理了
    } finally {
      setLoading(false)
    }
  }

  /**
   * 处理注册跳转
   */
  const handleRegister = () => {
    // TODO: 实现注册功能
    message.info('注册功能即将开放，请联系管理员获取账户')
  }

  /**
   * 处理忘记密码
   */
  const handleForgotPassword = () => {
    // TODO: 实现忘记密码功能
    message.info('忘记密码功能即将开放，请联系管理员重置密码')
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo和标题 */}
        <div className="text-center mb-8">
          <div className="text-4xl font-bold text-blue-600 mb-2">
            Lyss AI
          </div>
          <div className="text-lg text-gray-600 mb-1">
            企业级AI服务聚合平台
          </div>
          <div className="text-sm text-gray-500">
            智能对话 · 多模型集成 · 企业管理
          </div>
        </div>

        {/* 登录卡片 */}
        <Card 
          title="用户登录" 
          className="shadow-lg border-0"
          headStyle={{ 
            textAlign: 'center', 
            borderBottom: '1px solid #f0f0f0',
            fontSize: '18px',
            fontWeight: 'bold'
          }}
        >
          <Form
            form={form}
            name="login"
            onFinish={handleSubmit}
            layout="vertical"
            requiredMark={false}
            size="large"
          >
            {/* 邮箱输入 */}
            <Form.Item
              name="email"
              rules={[
                { required: true, message: '请输入邮箱地址' },
                { type: 'email', message: '请输入有效的邮箱地址' }
              ]}
            >
              <Input
                prefix={<UserOutlined className="text-gray-400" />}
                placeholder="邮箱地址"
                autoComplete="email"
              />
            </Form.Item>

            {/* 密码输入 */}
            <Form.Item
              name="password"
              rules={[
                { required: true, message: '请输入密码' },
                { min: 6, message: '密码长度至少6位' }
              ]}
            >
              <Input.Password
                prefix={<LockOutlined className="text-gray-400" />}
                placeholder="密码"
                autoComplete="current-password"
                iconRender={(visible) => (visible ? <EyeTwoTone /> : <EyeInvisibleOutlined />)}
              />
            </Form.Item>

            {/* 记住我和忘记密码 */}
            <Form.Item className="mb-4">
              <div className="flex justify-between items-center">
                <Form.Item name="remember_me" valuePropName="checked" noStyle>
                  <Checkbox>记住我</Checkbox>
                </Form.Item>
                <Button 
                  type="link" 
                  className="p-0 h-auto text-blue-600 hover:text-blue-800"
                  onClick={handleForgotPassword}
                >
                  忘记密码？
                </Button>
              </div>
            </Form.Item>

            {/* 登录按钮 */}
            <Form.Item className="mb-4">
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                block
                className="h-12 text-base font-medium"
              >
                {loading ? '登录中...' : '登录'}
              </Button>
            </Form.Item>

            {/* 分隔线 */}
            <Divider className="text-gray-400">
              <span className="text-sm">或者</span>
            </Divider>

            {/* 注册链接 */}
            <div className="text-center">
              <span className="text-gray-600">还没有账户？</span>
              <Button 
                type="link" 
                className="p-0 ml-1 text-blue-600 hover:text-blue-800"
                onClick={handleRegister}
              >
                立即注册
              </Button>
            </div>
          </Form>
        </Card>

        {/* 帮助信息 */}
        <div className="mt-8 text-center text-sm text-gray-500">
          <p>使用过程中遇到问题？</p>
          <p>
            联系我们: 
            <a href="mailto:support@lyss.ai" className="text-blue-600 hover:text-blue-800 ml-1">
              support@lyss.ai
            </a>
          </p>
        </div>

        {/* 版权信息 */}
        <div className="mt-8 text-center text-xs text-gray-400">
          <p>© 2025 Lyss AI Platform. All rights reserved.</p>
          <p>由 Claude AI Assistant 构建</p>
        </div>
      </div>
    </div>
  )
}

export default LoginPage