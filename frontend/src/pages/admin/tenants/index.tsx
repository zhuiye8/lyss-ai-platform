/**
 * 租户管理页面
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
  Popconfirm,
  message,
  Drawer,
  Descriptions,
  Statistic,
  Row,
  Col,
  Tooltip,
  Badge,
  Alert,
  Typography,
  Progress,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ExportOutlined,
  ReloadOutlined,
  EyeOutlined,
  UserOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import { TenantService } from '@/services/tenant';
import { Tenant, CreateTenantRequest, UpdateTenantRequest } from '@/types/tenant';
import { PAGINATION } from '@/utils/constants';
import { handleApiError } from '@/utils/errorHandler';

const { Search } = Input;
const { Title, Text } = Typography;
const { Option } = Select;

interface TenantStats {
  user_count: number;
  api_calls_count: number;
  storage_usage: number;
  last_active_at: string;
}

// 扩展Tenant类型以包含页面所需的额外字段
interface ExtendedTenant extends Tenant {
  status: 'active' | 'inactive' | 'pending';
  is_default?: boolean;
  user_count?: number;
  max_users?: number;
  max_storage?: number;
  last_active_at?: string;
}

interface TableParams {
  page?: number;
  page_size?: number;
  search?: string;
  status?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

const TenantsPage: React.FC = () => {
  const [tenants, setTenants] = useState<ExtendedTenant[]>([]);
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
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  
  // Modal 状态
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false);
  const [currentTenant, setCurrentTenant] = useState<ExtendedTenant | null>(null);
  const [tenantStats, setTenantStats] = useState<TenantStats | null>(null);
  
  // Form 实例
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();
  

  /**
   * 加载租户数据
   */
  const loadTenants = async (params: TableParams = {}) => {
    setLoading(true);
    try {
      const response = await TenantService.getTenants({
        page: params.page || pagination.current,
        page_size: params.page_size || pagination.pageSize,
        search: params.search || searchText,
        status: params.status || statusFilter,
        sort_by: params.sort_by,
        sort_order: params.sort_order,
      });
      
      if (response.success && response.data) {
        const data = response.data;
        setTenants(data.items as ExtendedTenant[]);
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
    loadTenants();
  }, []);

  /**
   * 表格列定义
   */
  const columns: ColumnsType<ExtendedTenant> = [
    {
      title: '租户名称',
      dataIndex: 'name',
      key: 'name',
      sorter: true,
      render: (text: string, record: ExtendedTenant) => (
        <Space>
          <strong>{text}</strong>
          {record.is_default && <Tag color="gold">默认</Tag>}
        </Space>
      ),
    },
    {
      title: '租户标识',
      dataIndex: 'slug',
      key: 'slug',
      render: (text: string) => <Text code>{text}</Text>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      filters: [
        { text: '正常', value: 'active' },
        { text: '禁用', value: 'inactive' },
        { text: '待审核', value: 'pending' },
      ],
      render: (status: string) => {
        const config = {
          active: { color: 'green', text: '正常' },
          inactive: { color: 'red', text: '禁用' },
          pending: { color: 'orange', text: '待审核' },
        }[status] || { color: 'gray', text: '未知' };
        
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '用户数',
      dataIndex: 'user_count',
      key: 'user_count',
      sorter: true,
      render: (count: number) => (
        <Badge count={count} showZero color="#1890ff" />
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
      title: '最后活动',
      dataIndex: 'last_active_at',
      key: 'last_active_at',
      sorter: true,
      render: (date: string) => (
        date ? (
          <Tooltip title={dayjs(date).format('YYYY-MM-DD HH:mm:ss')}>
            {dayjs(date).fromNow()}
          </Tooltip>
        ) : (
          <Text type="secondary">未活动</Text>
        )
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_, record: ExtendedTenant) => (
        <Space size="middle">
          <Tooltip title="查看详情">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => handleViewTenant(record)}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEditTenant(record)}
            />
          </Tooltip>
          <Tooltip title="删除">
            <Popconfirm
              title="确定删除该租户吗？"
              description="删除后将无法恢复，且所有相关数据都将被清空。"
              onConfirm={() => handleDeleteTenant(record.id)}
              okText="确定"
              cancelText="取消"
            >
              <Button
                type="text"
                danger
                icon={<DeleteOutlined />}
                disabled={record.is_default}
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
      status: filters.status?.[0],
    };
    
    if (sorter.field) {
      params.sort_by = sorter.field;
      params.sort_order = sorter.order === 'ascend' ? 'asc' : 'desc';
    }
    
    loadTenants(params);
  };

  /**
   * 搜索处理
   */
  const handleSearch = (value: string) => {
    setSearchText(value);
    loadTenants({ search: value, page: 1 });
  };

  /**
   * 状态筛选处理
   */
  const handleStatusFilter = (value: string | undefined) => {
    setStatusFilter(value);
    loadTenants({ status: value, page: 1 });
  };

  /**
   * 查看租户详情
   */
  const handleViewTenant = async (tenant: ExtendedTenant) => {
    setCurrentTenant(tenant);
    setDetailDrawerVisible(true);
    
    // 加载统计信息
    try {
      const response = await TenantService.getTenantStats(tenant.id);
      if (response.success && response.data) {
        setTenantStats(response.data);
      }
    } catch (error) {
      console.error('加载租户统计信息失败:', error);
    }
  };

  /**
   * 创建租户
   */
  const handleCreateTenant = () => {
    setCreateModalVisible(true);
  };

  /**
   * 编辑租户
   */
  const handleEditTenant = (tenant: ExtendedTenant) => {
    setCurrentTenant(tenant);
    editForm.setFieldsValue({
      name: tenant.name,
      slug: tenant.slug,
      description: tenant.description,
      status: tenant.status,
      max_users: tenant.max_users,
      max_storage: tenant.max_storage,
    });
    setEditModalVisible(true);
  };

  /**
   * 删除租户
   */
  const handleDeleteTenant = async (id: string) => {
    try {
      const response = await TenantService.deleteTenant(id);
      if (response.success) {
        message.success('删除成功');
        loadTenants();
      }
    } catch (error) {
      handleApiError(error);
    }
  };

  /**
   * 提交创建表单
   */
  const handleCreateSubmit = async (values: CreateTenantRequest) => {
    try {
      const response = await TenantService.createTenant(values);
      if (response.success) {
        message.success('创建成功');
        setCreateModalVisible(false);
        createForm.resetFields();
        loadTenants();
      }
    } catch (error) {
      handleApiError(error);
    }
  };

  /**
   * 提交编辑表单
   */
  const handleEditSubmit = async (values: UpdateTenantRequest) => {
    if (!currentTenant) return;
    
    try {
      const response = await TenantService.updateTenant(currentTenant.id, values);
      if (response.success) {
        message.success('更新成功');
        setEditModalVisible(false);
        editForm.resetFields();
        setCurrentTenant(null);
        loadTenants();
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
      message.warning('请选择要操作的租户');
      return;
    }
    
    try {
      const response = await TenantService.batchUpdateTenants(
        selectedRowKeys as string[],
        action
      );
      if (response.success) {
        message.success(`批量${action === 'enable' ? '启用' : '禁用'}成功`);
        setSelectedRowKeys([]);
        loadTenants();
      }
    } catch (error) {
      handleApiError(error);
    }
  };

  /**
   * 导出数据
   */
  const handleExport = async () => {
    try {
      const blob = await TenantService.exportTenants({
        format: 'xlsx',
        filters: {
          search: searchText,
          status: statusFilter,
        },
      });
      
      // 创建下载链接
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = `租户数据_${dayjs().format('YYYY-MM-DD')}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      message.success('导出成功');
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
    getCheckboxProps: (record: ExtendedTenant) => ({
      disabled: record.is_default, // 默认租户不允许选择
    }),
  };

  return (
    <div>
      {/* 页面标题 */}
      <div style={{ marginBottom: 16 }}>
        <Title level={2} style={{ margin: 0 }}>租户管理</Title>
        <Text type="secondary">管理系统中的所有租户账户和权限</Text>
      </div>

      {/* 操作栏 */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]} align="middle">
          <Col flex={1}>
            <Space size="middle">
              <Search
                placeholder="搜索租户名称或标识"
                allowClear
                style={{ width: 300 }}
                onSearch={handleSearch}
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
              />
              <Select
                placeholder="筛选状态"
                allowClear
                style={{ width: 120 }}
                value={statusFilter}
                onChange={handleStatusFilter}
              >
                <Option value="active">正常</Option>
                <Option value="inactive">禁用</Option>
                <Option value="pending">待审核</Option>
              </Select>
            </Space>
          </Col>
          <Col>
            <Space>
              <Button
                icon={<ReloadOutlined />}
                onClick={() => loadTenants()}
                loading={loading}
              >
                刷新
              </Button>
              <Button
                icon={<ExportOutlined />}
                onClick={handleExport}
              >
                导出
              </Button>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleCreateTenant}
              >
                新建租户
              </Button>
            </Space>
          </Col>
        </Row>
        
        {/* 批量操作 */}
        {selectedRowKeys.length > 0 && (
          <Row style={{ marginTop: 16 }}>
            <Col span={24}>
              <Alert
                message={`已选择 ${selectedRowKeys.length} 个租户`}
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
          dataSource={tenants}
          rowKey="id"
          pagination={pagination}
          loading={loading}
          onChange={handleTableChange}
          scroll={{ x: 'max-content' }}
          size="middle"
        />
      </Card>

      {/* 创建租户模态框 */}
      <Modal
        title="创建租户"
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
          <Form.Item
            label="租户名称"
            name="name"
            rules={[{ required: true, message: '请输入租户名称' }]}
          >
            <Input placeholder="请输入租户名称" />
          </Form.Item>
          
          <Form.Item
            label="租户标识"
            name="slug"
            rules={[
              { required: true, message: '请输入租户标识' },
              { pattern: /^[a-z0-9-_]+$/, message: '只允许小写字母、数字、中划线和下划线' },
            ]}
          >
            <Input placeholder="请输入租户标识（用于 URL）" />
          </Form.Item>
          
          <Form.Item
            label="描述"
            name="description"
          >
            <Input.TextArea
              placeholder="请输入租户描述"
              rows={3}
            />
          </Form.Item>
          
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="最大用户数"
                name="max_users"
                initialValue={100}
              >
                <Input type="number" placeholder="最大用户数" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="最大存储空间(GB)"
                name="max_storage"
                initialValue={10}
              >
                <Input type="number" placeholder="最大存储空间" />
              </Form.Item>
            </Col>
          </Row>
          
          <Form.Item
            label="状态"
            name="status"
            initialValue="active"
          >
            <Select>
              <Option value="active">正常</Option>
              <Option value="inactive">禁用</Option>
              <Option value="pending">待审核</Option>
            </Select>
          </Form.Item>
          
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

      {/* 编辑租户模态框 */}
      <Modal
        title="编辑租户"
        open={editModalVisible}
        onCancel={() => {
          setEditModalVisible(false);
          editForm.resetFields();
          setCurrentTenant(null);
        }}
        footer={null}
        width={600}
      >
        <Form
          form={editForm}
          layout="vertical"
          onFinish={handleEditSubmit}
        >
          <Form.Item
            label="租户名称"
            name="name"
            rules={[{ required: true, message: '请输入租户名称' }]}
          >
            <Input placeholder="请输入租户名称" />
          </Form.Item>
          
          <Form.Item
            label="租户标识"
            name="slug"
            rules={[
              { required: true, message: '请输入租户标识' },
              { pattern: /^[a-z0-9-_]+$/, message: '只允许小写字母、数字、中划线和下划线' },
            ]}
          >
            <Input placeholder="请输入租户标识（用于 URL）" />
          </Form.Item>
          
          <Form.Item
            label="描述"
            name="description"
          >
            <Input.TextArea
              placeholder="请输入租户描述"
              rows={3}
            />
          </Form.Item>
          
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="最大用户数"
                name="max_users"
              >
                <Input type="number" placeholder="最大用户数" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="最大存储空间(GB)"
                name="max_storage"
              >
                <Input type="number" placeholder="最大存储空间" />
              </Form.Item>
            </Col>
          </Row>
          
          <Form.Item
            label="状态"
            name="status"
          >
            <Select>
              <Option value="active">正常</Option>
              <Option value="inactive">禁用</Option>
              <Option value="pending">待审核</Option>
            </Select>
          </Form.Item>
          
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                更新
              </Button>
              <Button onClick={() => {
                setEditModalVisible(false);
                editForm.resetFields();
                setCurrentTenant(null);
              }}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 租户详情抽屉 */}
      <Drawer
        title="租户详情"
        width={600}
        open={detailDrawerVisible}
        onClose={() => {
          setDetailDrawerVisible(false);
          setCurrentTenant(null);
          setTenantStats(null);
        }}
      >
        {currentTenant && (
          <div>
            {/* 基本信息 */}
            <Descriptions
              title="基本信息"
              bordered
              column={1}
              style={{ marginBottom: 24 }}
            >
              <Descriptions.Item label="租户名称">
                {currentTenant.name}
                {currentTenant.is_default && (
                  <Tag color="gold" style={{ marginLeft: 8 }}>默认</Tag>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="租户标识">
                <Text code>{currentTenant.slug}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="描述">
                {currentTenant.description || '无'}
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={
                  currentTenant.status === 'active' ? 'green' :
                  currentTenant.status === 'inactive' ? 'red' : 'orange'
                }>
                  {currentTenant.status === 'active' ? '正常' :
                   currentTenant.status === 'inactive' ? '禁用' : '待审核'}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {dayjs(currentTenant.created_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="最后更新">
                {dayjs(currentTenant.updated_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
            </Descriptions>

            {/* 统计信息 */}
            {tenantStats && (
              <div>
                <Title level={4}>使用统计</Title>
                <Row gutter={16} style={{ marginBottom: 24 }}>
                  <Col span={8}>
                    <Card size="small">
                      <Statistic
                        title="用户数量"
                        value={tenantStats.user_count}
                        prefix={<UserOutlined />}
                        suffix={`/ ${currentTenant.max_users || '无限'}`}
                      />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card size="small">
                      <Statistic
                        title="API调用次数"
                        value={tenantStats.api_calls_count}
                        prefix={<DatabaseOutlined />}
                      />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card size="small">
                      <Statistic
                        title="存储使用量"
                        value={(tenantStats.storage_usage / 1024 / 1024 / 1024).toFixed(2)}
                        prefix={<DatabaseOutlined />}
                        suffix={`GB / ${currentTenant.max_storage || '无限'}GB`}
                      />
                    </Card>
                  </Col>
                </Row>
                
                {/* 存储使用率 */}
                {currentTenant.max_storage && (
                  <div style={{ marginBottom: 16 }}>
                    <Text strong>存储使用率</Text>
                    <Progress
                      percent={Math.round((tenantStats.storage_usage / 1024 / 1024 / 1024) / currentTenant.max_storage * 100)}
                      status={tenantStats.storage_usage / 1024 / 1024 / 1024 > currentTenant.max_storage * 0.8 ? 'exception' : 'normal'}
                    />
                  </div>
                )}
                
                <Descriptions bordered column={1}>
                  <Descriptions.Item label="最后活动时间">
                    {tenantStats.last_active_at ? 
                      dayjs(tenantStats.last_active_at).format('YYYY-MM-DD HH:mm:ss') : 
                      '未活动'
                    }
                  </Descriptions.Item>
                </Descriptions>
              </div>
            )}
          </div>
        )}
      </Drawer>
    </div>
  );
};

export default TenantsPage;