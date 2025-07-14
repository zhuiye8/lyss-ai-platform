/**
 * 用户管理页面
 * 根据docs/frontend.md规范设计
 */

import React, { useState, useEffect } from 'react';
import {
  Table,
  Card,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  Switch,
  Popconfirm,
  message,
  Drawer,
  Descriptions,
  Avatar,
  Row,
  Col,
  Typography,
  Alert,
  Tooltip,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
  EyeOutlined,
  UserOutlined,
  MailOutlined,
  LockOutlined,
  UnlockOutlined,
  KeyOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import { UserService } from '@/services/user';
import { User, CreateUserRequest, UpdateUserRequest } from '@/types/user';
import { PAGINATION, USER_ROLES, USER_STATUS } from '@/utils/constants';
import { handleApiError } from '@/utils/errorHandler';
import { useAuth } from '@/store/auth';

const { Search } = Input;
const { Title, Text } = Typography;
const { Option } = Select;
const { Password } = Input;

interface TableParams {
  page?: number;
  page_size?: number;
  search?: string;
  role?: string;
  status?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

const UsersPage: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: PAGINATION.DEFAULT_PAGE_SIZE,
    total: 0,
    showSizeChanger: true,
    showQuickJumper: true,
    showTotal: (total: number, range: [number, number]) => 
      `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
  });
  const [searchText, setSearchText] = useState('');
  const [roleFilter, setRoleFilter] = useState<string | undefined>();
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  
  // Modal 状态
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false);
  const [resetPasswordModalVisible, setResetPasswordModalVisible] = useState(false);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  
  // Form 实例
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();
  const [resetPasswordForm] = Form.useForm();
  
  const { user: currentAuthUser } = useAuth();

  /**
   * 加载用户数据
   */
  const loadUsers = async (params: TableParams = {}) => {
    setLoading(true);
    try {
      const response = await UserService.getUsers({
        page: params.page || pagination.current,
        page_size: params.page_size || pagination.pageSize,
        search: params.search || searchText,
        role: params.role || roleFilter,
        status: params.status || statusFilter,
        sort_by: params.sort_by,
        sort_order: params.sort_order,
      });
      
      if (response.success && response.data) {
        const data = response.data;
        setUsers(data.items);
        setPagination(prev => ({
          ...prev,
          current: data.pagination.page,
          pageSize: data.pagination.page_size,
          total: data.pagination.total_items,
        }));
      }
    } catch (error) {
      handleApiError(error);
    } finally {
      setLoading(false);
    }
  };

  /**
   * 初始化加载
   */
  useEffect(() => {
    loadUsers();
  }, []);

  /**
   * 表格列定义
   */
  const columns: ColumnsType<User> = [
    {
      title: '用户',
      key: 'user',
      width: 200,
      render: (_, record: User) => (
        <Space>
          <Avatar 
            src={record.avatar} 
            icon={!record.avatar && <UserOutlined />}
            size="default"
          />
          <div>
            <div>
              <strong>{record.name}</strong>
              {record.id === currentAuthUser?.id && (
                <Tag color="blue" style={{ marginLeft: 4, fontSize: '12px' }}>
                  当前用户
                </Tag>
              )}
            </div>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {record.username || record.email}
            </Text>
          </div>
        </Space>
      ),
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      key: 'email',
      ellipsis: true,
      render: (email: string, record: User) => (
        <Space>
          <MailOutlined style={{ color: '#1890ff' }} />
          <span>{email}</span>
          {record.is_verified && (
            <Tag color="green" style={{ fontSize: '12px' }}>已验证</Tag>
          )}
        </Space>
      ),
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      filters: Object.entries(USER_ROLES).map(([key, value]) => ({
        text: value.label,
        value: key,
      })),
      render: (role: string) => {
        const roleConfig = USER_ROLES[role as keyof typeof USER_ROLES] || USER_ROLES.user;
        return (
          <Tag color={roleConfig.color}>
            {roleConfig.label}
          </Tag>
        );
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      filters: Object.entries(USER_STATUS).map(([key, value]) => ({
        text: value.label,
        value: key,
      })),
      render: (status: string, record: User) => {
        // 使用is_active字段来确定状态
        const actualStatus = record.is_active ? 'active' : 'inactive';
        const statusConfig = USER_STATUS[actualStatus] || USER_STATUS.inactive;
        return (
          <Space>
            <Tag color={statusConfig.color}>
              {statusConfig.label}
            </Tag>
            {!record.is_active && (
              <Tag color="red" style={{ fontSize: '12px' }}>禁用</Tag>
            )}
          </Space>
        );
      },
    },
    {
      title: '最后登录',
      dataIndex: 'last_login_at',
      key: 'last_login_at',
      sorter: true,
      render: (date: string) => (
        date ? (
          <Tooltip title={dayjs(date).format('YYYY-MM-DD HH:mm:ss')}>
            {dayjs(date).fromNow()}
          </Tooltip>
        ) : (
          <Text type="secondary">从未登录</Text>
        )
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      sorter: true,
      render: (date: string) => (
        <Tooltip title={dayjs(date).format('YYYY-MM-DD HH:mm:ss')}>
          {dayjs(date).fromNow()}
        </Tooltip>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_, record: User) => (
        <Space size="small">
          <Tooltip title="查看详情">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => handleViewUser(record)}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEditUser(record)}
              disabled={record.id === currentAuthUser?.id}
            />
          </Tooltip>
          <Tooltip title="重置密码">
            <Button
              type="text"
              icon={<KeyOutlined />}
              onClick={() => handleResetPassword(record)}
              disabled={record.id === currentAuthUser?.id}
            />
          </Tooltip>
          <Tooltip title={record.is_active ? '禁用' : '启用'}>
            <Button
              type="text"
              icon={record.is_active ? <LockOutlined /> : <UnlockOutlined />}
              onClick={() => handleToggleUserStatus(record)}
              disabled={record.id === currentAuthUser?.id}
            />
          </Tooltip>
          <Tooltip title="删除">
            <Popconfirm
              title="确定删除该用户吗？"
              description="删除后将无法恢复，且所有相关数据都将被清空。"
              onConfirm={() => handleDeleteUser(record.id)}
              okText="确定"
              cancelText="取消"
            >
              <Button
                type="text"
                danger
                icon={<DeleteOutlined />}
                disabled={record.id === currentAuthUser?.id}
              />
            </Popconfirm>
          </Tooltip>
        </Space>
      ),
    },
  ];

  /**
   * 表格变化处理
   */
  const handleTableChange = (paginationConfig: any, filters: any, sorter: any) => {
    const params: TableParams = {
      page: paginationConfig.current,
      page_size: paginationConfig.pageSize,
      role: filters.role?.[0],
      status: filters.status?.[0],
    };
    
    if (sorter.field) {
      params.sort_by = sorter.field;
      params.sort_order = sorter.order === 'ascend' ? 'asc' : 'desc';
    }
    
    loadUsers(params);
  };

  /**
   * 搜索处理
   */
  const handleSearch = (value: string) => {
    setSearchText(value);
    loadUsers({ search: value, page: 1 });
  };

  /**
   * 查看用户详情
   */
  const handleViewUser = (user: User) => {
    setCurrentUser(user);
    setDetailDrawerVisible(true);
  };

  /**
   * 创建用户
   */
  const handleCreateUser = () => {
    setCreateModalVisible(true);
  };

  /**
   * 编辑用户
   */
  const handleEditUser = (user: User) => {
    setCurrentUser(user);
    editForm.setFieldsValue({
      name: user.name,
      username: user.username,
      email: user.email,
      phone: user.phone,
      role: user.role,
      is_active: user.is_active,
    });
    setEditModalVisible(true);
  };

  /**
   * 删除用户
   */
  const handleDeleteUser = async (id: string) => {
    try {
      const response = await UserService.deleteUser(id);
      if (response.success) {
        message.success('删除成功');
        loadUsers();
      }
    } catch (error) {
      handleApiError(error);
    }
  };

  /**
   * 切换用户状态
   */
  const handleToggleUserStatus = async (user: User) => {
    try {
      const response = await UserService.updateUser(user.id, {
        is_active: !user.is_active,
      });
      if (response.success) {
        message.success(`${user.is_active ? '禁用' : '启用'}成功`);
        loadUsers();
      }
    } catch (error) {
      handleApiError(error);
    }
  };

  /**
   * 重置密码
   */
  const handleResetPassword = (user: User) => {
    setCurrentUser(user);
    setResetPasswordModalVisible(true);
  };

  /**
   * 提交创建表单
   */
  const handleCreateSubmit = async (values: CreateUserRequest) => {
    try {
      const response = await UserService.createUser(values);
      if (response.success) {
        message.success('创建成功');
        setCreateModalVisible(false);
        createForm.resetFields();
        loadUsers();
      }
    } catch (error) {
      handleApiError(error);
    }
  };

  /**
   * 提交编辑表单
   */
  const handleEditSubmit = async (values: UpdateUserRequest) => {
    if (!currentUser) return;
    
    try {
      const response = await UserService.updateUser(currentUser.id, values);
      if (response.success) {
        message.success('更新成功');
        setEditModalVisible(false);
        editForm.resetFields();
        setCurrentUser(null);
        loadUsers();
      }
    } catch (error) {
      handleApiError(error);
    }
  };

  /**
   * 提交重置密码表单
   */
  const handleResetPasswordSubmit = async (values: { new_password: string }) => {
    if (!currentUser) return;
    
    try {
      const response = await UserService.resetUserPassword(currentUser.id, values.new_password);
      if (response.success) {
        message.success('密码重置成功');
        setResetPasswordModalVisible(false);
        resetPasswordForm.resetFields();
        setCurrentUser(null);
      }
    } catch (error) {
      handleApiError(error);
    }
  };

  /**
   * 批量操作
   */
  const handleBatchAction = async (action: 'enable' | 'disable') => {
    if (selectedRowKeys.length === 0) {
      message.warning('请选择要操作的用户');
      return;
    }
    
    try {
      const response = await UserService.batchUpdateUsers(
        selectedRowKeys as string[],
        action
      );
      if (response.success) {
        message.success(`批量${action === 'enable' ? '启用' : '禁用'}成功`);
        setSelectedRowKeys([]);
        loadUsers();
      }
    } catch (error) {
      handleApiError(error);
    }
  };

  /**
   * 行选择配置
   */
  const rowSelection = {
    selectedRowKeys,
    onChange: (newSelectedRowKeys: React.Key[]) => {
      setSelectedRowKeys(newSelectedRowKeys);
    },
    getCheckboxProps: (record: User) => ({
      disabled: record.id === currentAuthUser?.id, // 当前用户不允许选择
    }),
  };

  return (
    <div>
      {/* 页面标题 */}
      <div style={{ marginBottom: 16 }}>
        <Title level={2} style={{ margin: 0 }}>用户管理</Title>
        <Text type="secondary">管理租户下的所有用户账户和权限</Text>
      </div>

      {/* 操作栏 */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]} align="middle">
          <Col flex={1}>
            <Space size="middle">
              <Search
                placeholder="搜索用户名、邮箱或手机号"
                allowClear
                style={{ width: 300 }}
                onSearch={handleSearch}
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
              />
              <Select
                placeholder="筛选角色"
                allowClear
                style={{ width: 120 }}
                value={roleFilter}
                onChange={setRoleFilter}
              >
                {Object.entries(USER_ROLES).map(([key, value]) => (
                  <Option key={key} value={key}>{value.label}</Option>
                ))}
              </Select>
              <Select
                placeholder="筛选状态"
                allowClear
                style={{ width: 120 }}
                value={statusFilter}
                onChange={setStatusFilter}
              >
                {Object.entries(USER_STATUS).map(([key, value]) => (
                  <Option key={key} value={key}>{value.label}</Option>
                ))}
              </Select>
            </Space>
          </Col>
          <Col>
            <Space>
              <Button
                icon={<ReloadOutlined />}
                onClick={() => loadUsers()}
                loading={loading}
              >
                刷新
              </Button>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleCreateUser}
              >
                新建用户
              </Button>
            </Space>
          </Col>
        </Row>
        
        {/* 批量操作 */}
        {selectedRowKeys.length > 0 && (
          <Row style={{ marginTop: 16 }}>
            <Col span={24}>
              <Alert
                message={`已选择 ${selectedRowKeys.length} 个用户`}
                type="info"
                showIcon
                action={
                  <Space>
                    <Button
                      size="small"
                      onClick={() => handleBatchAction('enable')}
                    >
                      批量启用
                    </Button>
                    <Button
                      size="small"
                      onClick={() => handleBatchAction('disable')}
                    >
                      批量禁用
                    </Button>
                    <Button
                      size="small"
                      onClick={() => setSelectedRowKeys([])}
                    >
                      取消选择
                    </Button>
                  </Space>
                }
              />
            </Col>
          </Row>
        )}
      </Card>

      {/* 数据表格 */}
      <Card>
        <Table
          rowSelection={rowSelection}
          columns={columns}
          dataSource={users}
          rowKey="id"
          pagination={pagination}
          loading={loading}
          onChange={handleTableChange}
          scroll={{ x: 'max-content' }}
          size="middle"
        />
      </Card>

      {/* 创建用户模态框 */}
      <Modal
        title="创建用户"
        open={createModalVisible}
        onCancel={() => {
          setCreateModalVisible(false);
          createForm.resetFields();
        }}
        footer={null}
        width={600}
      >
        <Form
          form={createForm}
          layout="vertical"
          onFinish={handleCreateSubmit}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="用户名"
                name="name"
                rules={[{ required: true, message: '请输入用户名' }]}
              >
                <Input placeholder="请输入用户名" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="登录名"
                name="username"
              >
                <Input placeholder="请输入登录名（可选）" />
              </Form.Item>
            </Col>
          </Row>
          
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="邮箱"
                name="email"
                rules={[
                  { required: true, message: '请输入邮箱' },
                  { type: 'email', message: '请输入有效的邮箱地址' },
                ]}
              >
                <Input placeholder="请输入邮箱" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="手机号"
                name="phone"
              >
                <Input placeholder="请输入手机号（可选）" />
              </Form.Item>
            </Col>
          </Row>
          
          <Form.Item
            label="密码"
            name="password"
            rules={[
              { required: true, message: '请输入密码' },
              { min: 6, message: '密码至少6位' },
            ]}
          >
            <Password placeholder="请输入密码" />
          </Form.Item>
          
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="角色"
                name="role"
                initialValue="user"
                rules={[{ required: true, message: '请选择角色' }]}
              >
                <Select>
                  {Object.entries(USER_ROLES).map(([key, value]) => (
                    <Option key={key} value={key}>{value.label}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="状态"
                name="is_active"
                initialValue={true}
                valuePropName="checked"
              >
                <Switch checkedChildren="启用" unCheckedChildren="禁用" />
              </Form.Item>
            </Col>
          </Row>
          
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                创建
              </Button>
              <Button onClick={() => {
                setCreateModalVisible(false);
                createForm.resetFields();
              }}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑用户模态框 */}
      <Modal
        title="编辑用户"
        open={editModalVisible}
        onCancel={() => {
          setEditModalVisible(false);
          editForm.resetFields();
          setCurrentUser(null);
        }}
        footer={null}
        width={600}
      >
        <Form
          form={editForm}
          layout="vertical"
          onFinish={handleEditSubmit}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="用户名"
                name="name"
                rules={[{ required: true, message: '请输入用户名' }]}
              >
                <Input placeholder="请输入用户名" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="登录名"
                name="username"
              >
                <Input placeholder="请输入登录名（可选）" />
              </Form.Item>
            </Col>
          </Row>
          
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="邮箱"
                name="email"
                rules={[
                  { required: true, message: '请输入邮箱' },
                  { type: 'email', message: '请输入有效的邮箱地址' },
                ]}
              >
                <Input placeholder="请输入邮箱" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="手机号"
                name="phone"
              >
                <Input placeholder="请输入手机号（可选）" />
              </Form.Item>
            </Col>
          </Row>
          
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="角色"
                name="role"
                rules={[{ required: true, message: '请选择角色' }]}
              >
                <Select>
                  {Object.entries(USER_ROLES).map(([key, value]) => (
                    <Option key={key} value={key}>{value.label}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="状态"
                name="is_active"
                valuePropName="checked"
              >
                <Switch checkedChildren="启用" unCheckedChildren="禁用" />
              </Form.Item>
            </Col>
          </Row>
          
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                更新
              </Button>
              <Button onClick={() => {
                setEditModalVisible(false);
                editForm.resetFields();
                setCurrentUser(null);
              }}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 重置密码模态框 */}
      <Modal
        title="重置密码"
        open={resetPasswordModalVisible}
        onCancel={() => {
          setResetPasswordModalVisible(false);
          resetPasswordForm.resetFields();
          setCurrentUser(null);
        }}
        footer={null}
        width={400}
      >
        <Form
          form={resetPasswordForm}
          layout="vertical"
          onFinish={handleResetPasswordSubmit}
        >
          <Form.Item>
            <Alert
              message={`正在为用户 "${currentUser?.name}" 重置密码`}
              type="warning"
              showIcon
              style={{ marginBottom: 16 }}
            />
          </Form.Item>
          
          <Form.Item
            label="新密码"
            name="new_password"
            rules={[
              { required: true, message: '请输入新密码' },
              { min: 6, message: '密码至少6位' },
            ]}
          >
            <Password placeholder="请输入新密码" />
          </Form.Item>
          
          <Form.Item
            label="确认密码"
            name="confirm_password"
            dependencies={['new_password']}
            rules={[
              { required: true, message: '请确认新密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('new_password') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('两次输入的密码不一致'));
                },
              }),
            ]}
          >
            <Password placeholder="请确认新密码" />
          </Form.Item>
          
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                重置密码
              </Button>
              <Button onClick={() => {
                setResetPasswordModalVisible(false);
                resetPasswordForm.resetFields();
                setCurrentUser(null);
              }}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 用户详情抽屉 */}
      <Drawer
        title="用户详情"
        width={600}
        open={detailDrawerVisible}
        onClose={() => {
          setDetailDrawerVisible(false);
          setCurrentUser(null);
        }}
      >
        {currentUser && (
          <div>
            {/* 基本信息 */}
            <Descriptions
              title="基本信息"
              bordered
              column={1}
              style={{ marginBottom: 24 }}
            >
              <Descriptions.Item label="头像">
                <Avatar 
                  src={currentUser.avatar} 
                  icon={!currentUser.avatar && <UserOutlined />}
                  size="large"
                />
              </Descriptions.Item>
              <Descriptions.Item label="用户名">
                {currentUser.name}
                {currentUser.id === currentAuthUser?.id && (
                  <Tag color="blue" style={{ marginLeft: 8 }}>当前用户</Tag>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="登录名">
                {currentUser.username || '未设置'}
              </Descriptions.Item>
              <Descriptions.Item label="邮箱">
                <Space>
                  {currentUser.email}
                  {currentUser.is_verified && (
                    <Tag color="green" style={{ fontSize: '12px' }}>已验证</Tag>
                  )}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="手机号">
                {currentUser.phone || '未设置'}
              </Descriptions.Item>
              <Descriptions.Item label="角色">
                <Tag color={USER_ROLES[currentUser.role]?.color || 'default'}>
                  {USER_ROLES[currentUser.role]?.label || currentUser.role}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Space>
                  <Tag color={currentUser.is_active ? 'green' : 'red'}>
                    {currentUser.is_active ? '正常' : '禁用'}
                  </Tag>
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {dayjs(currentUser.created_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="最后更新">
                {dayjs(currentUser.updated_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="最后登录">
                {currentUser.last_login_at ? 
                  dayjs(currentUser.last_login_at).format('YYYY-MM-DD HH:mm:ss') : 
                  '从未登录'
                }
              </Descriptions.Item>
            </Descriptions>
          </div>
        )}
      </Drawer>
    </div>
  );
};

export default UsersPage;