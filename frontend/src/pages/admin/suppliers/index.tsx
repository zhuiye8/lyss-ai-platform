/**
 * 供应商凭证管理页面
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
  Row,
  Col,
  Typography,
  Alert,
  Tooltip,
  Progress,
  Badge,
  Divider,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
  SearchOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ApiOutlined,
  KeyOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import { SupplierService } from '@/services/supplier';
import { SupplierCredential, CreateSupplierCredentialRequest, UpdateSupplierCredentialRequest } from '@/types/supplier';
import { PaginationResponse } from '@/types/api';
import { PAGINATION, SUPPLIER_CONFIG } from '@/utils/constants';
import { handleApiError } from '@/utils/errorHandler';
import { useAuth } from '@/store/auth';

const { Search } = Input;
const { Title, Text } = Typography;
const { Option } = Select;
const { TextArea } = Input;

interface TableParams {
  page?: number;
  page_size?: number;
  search?: string;
  provider?: string;
  status?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

const SuppliersPage: React.FC = () => {
  const [suppliers, setSuppliers] = useState<SupplierCredential[]>([]);
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
  const [providerFilter, setProviderFilter] = useState<string | undefined>();
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  
  // Modal 状态
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false);
  const [testConnectionModalVisible, setTestConnectionModalVisible] = useState(false);
  const [currentSupplier, setCurrentSupplier] = useState<SupplierCredential | null>(null);
  const [showApiKey, setShowApiKey] = useState<{ [key: string]: boolean }>({});
  
  // Form 实例
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();
  
  const { user } = useAuth();

  /**
   * 加载供应商凭证数据
   */
  const loadSuppliers = async (params: TableParams = {}) => {
    setLoading(true);
    try {
      const response = await SupplierService.getSupplierCredentials({
        page: params.page || pagination.current,
        page_size: params.page_size || pagination.pageSize,
        search: params.search || searchText,
        provider: params.provider || providerFilter,
        status: params.status || statusFilter,
        sort_by: params.sort_by,
        sort_order: params.sort_order,
      });
      
      if (response.success) {
        setSuppliers(response.data.items);
        setPagination(prev => ({
          ...prev,
          current: response.data.pagination.page,
          pageSize: response.data.pagination.page_size,
          total: response.data.pagination.total_items,
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
    loadSuppliers();
  }, []);

  /**
   * 表格列定义
   */
  const columns: ColumnsType<SupplierCredential> = [
    {
      title: '供应商',
      key: 'provider',
      width: 150,
      render: (_, record: SupplierCredential) => {
        const config = SUPPLIER_CONFIG[record.provider as keyof typeof SUPPLIER_CONFIG] || {
          name: record.provider,
          icon: '🔧',
          color: '#666666'
        };
        
        return (
          <Space>
            <span style={{ fontSize: 18 }}>{config.icon}</span>
            <div>
              <div><strong>{config.name}</strong></div>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {record.provider}
              </Text>
            </div>
          </Space>
        );
      },
    },
    {
      title: '凭证名称',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      render: (text: string, record: SupplierCredential) => (
        <div>
          <strong>{text}</strong>
          {record.is_default && (
            <Tag color="gold" size="small" style={{ marginLeft: 4 }}>
              默认
            </Tag>
          )}
        </div>
      ),
    },
    {
      title: 'API密钥',
      dataIndex: 'api_key_preview',
      key: 'api_key_preview',
      width: 200,
      render: (preview: string, record: SupplierCredential) => (
        <Space>
          <Text code style={{ fontSize: 12 }}>
            {showApiKey[record.id] ? record.api_key_full : preview}
          </Text>
          <Button
            type="text"
            size="small"
            icon={showApiKey[record.id] ? <EyeInvisibleOutlined /> : <EyeOutlined />}
            onClick={() => toggleApiKeyVisibility(record.id)}
          />
        </Space>
      ),
    },
    {
      title: '端点地址',
      dataIndex: 'api_endpoint',
      key: 'api_endpoint',
      ellipsis: true,
      render: (endpoint: string) => (
        endpoint ? (
          <Tooltip title={endpoint}>
            <Text code style={{ fontSize: 12 }}>{endpoint}</Text>
          </Tooltip>
        ) : (
          <Text type="secondary">默认</Text>
        )
      ),
    },
    {
      title: '状态',
      key: 'status',
      width: 120,
      render: (_, record: SupplierCredential) => (
        <Space direction="vertical" size="small">
          <Tag color={record.is_active ? 'green' : 'red'}>
            {record.is_active ? '启用' : '禁用'}
          </Tag>
          {record.connection_status && (
            <Badge
              status={record.connection_status === 'connected' ? 'success' : 'error'}
              text={record.connection_status === 'connected' ? '已连接' : '连接失败'}
            />
          )}
        </Space>
      ),
    },
    {
      title: '最后测试',
      dataIndex: 'last_tested_at',
      key: 'last_tested_at',
      sorter: true,
      render: (date: string) => (
        date ? (
          <Tooltip title={dayjs(date).format('YYYY-MM-DD HH:mm:ss')}>
            {dayjs(date).fromNow()}
          </Tooltip>
        ) : (
          <Text type="secondary">未测试</Text>
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
      render: (_, record: SupplierCredential) => (
        <Space size="small">
          <Tooltip title="查看详情">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => handleViewSupplier(record)}
            />
          </Tooltip>
          <Tooltip title="测试连接">
            <Button
              type="text"
              icon={<ApiOutlined />}
              onClick={() => handleTestConnection(record)}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEditSupplier(record)}
            />
          </Tooltip>
          <Tooltip title="删除">
            <Popconfirm
              title="确定删除该供应商凭证吗？"
              description="删除后将无法恢复，相关配置也将失效。"
              onConfirm={() => handleDeleteSupplier(record.id)}
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
    };
    
    if (sorter.field) {
      params.sort_by = sorter.field;
      params.sort_order = sorter.order === 'ascend' ? 'asc' : 'desc';
    }
    
    loadSuppliers(params);
  };

  /**
   * 搜索处理
   */
  const handleSearch = (value: string) => {
    setSearchText(value);
    loadSuppliers({ search: value, page: 1 });
  };

  /**
   * 切换API密钥显示
   */
  const toggleApiKeyVisibility = async (id: string) => {
    if (!showApiKey[id]) {
      // 首次显示时获取完整密钥
      try {
        const response = await SupplierService.getSupplierCredentialDetail(id, { include_api_key: true });
        if (response.success) {
          const supplier = suppliers.find(s => s.id === id);
          if (supplier) {
            supplier.api_key_full = response.data.api_key;
          }
        }
      } catch (error) {
        handleApiError(error);
        return;
      }
    }
    
    setShowApiKey(prev => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  /**
   * 查看供应商详情
   */
  const handleViewSupplier = (supplier: SupplierCredential) => {
    setCurrentSupplier(supplier);
    setDetailDrawerVisible(true);
  };

  /**
   * 创建供应商凭证
   */
  const handleCreateSupplier = () => {
    setCreateModalVisible(true);
  };

  /**
   * 编辑供应商凭证
   */
  const handleEditSupplier = (supplier: SupplierCredential) => {
    setCurrentSupplier(supplier);
    editForm.setFieldsValue({
      name: supplier.name,
      provider: supplier.provider,
      api_endpoint: supplier.api_endpoint,
      model_config: supplier.model_config ? JSON.stringify(supplier.model_config, null, 2) : '',
      is_active: supplier.is_active,
    });
    setEditModalVisible(true);
  };

  /**
   * 删除供应商凭证
   */
  const handleDeleteSupplier = async (id: string) => {
    try {
      const response = await SupplierService.deleteSupplierCredential(id);
      if (response.success) {
        message.success('删除成功');
        loadSuppliers();
      }
    } catch (error) {
      handleApiError(error);
    }
  };

  /**
   * 测试连接
   */
  const handleTestConnection = async (supplier: SupplierCredential) => {
    try {
      setLoading(true);
      const response = await SupplierService.testConnection(supplier.id);
      if (response.success) {
        message.success('连接测试成功');
        loadSuppliers(); // 刷新状态
      }
    } catch (error) {
      handleApiError(error);
    } finally {
      setLoading(false);
    }
  };

  /**
   * 提交创建表单
   */
  const handleCreateSubmit = async (values: CreateSupplierCredentialRequest & { model_config_text?: string }) => {
    try {
      const submitData = { ...values };
      
      // 处理模型配置JSON
      if (values.model_config_text) {
        try {
          submitData.model_config = JSON.parse(values.model_config_text);
        } catch (error) {
          message.error('模型配置JSON格式无效');
          return;
        }
      }
      delete submitData.model_config_text;
      
      const response = await SupplierService.createSupplierCredential(submitData);
      if (response.success) {
        message.success('创建成功');
        setCreateModalVisible(false);
        createForm.resetFields();
        loadSuppliers();
      }
    } catch (error) {
      handleApiError(error);
    }
  };

  /**
   * 提交编辑表单
   */
  const handleEditSubmit = async (values: UpdateSupplierCredentialRequest & { model_config_text?: string }) => {
    if (!currentSupplier) return;
    
    try {
      const submitData = { ...values };
      
      // 处理模型配置JSON
      if (values.model_config_text) {
        try {
          submitData.model_config = JSON.parse(values.model_config_text);
        } catch (error) {
          message.error('模型配置JSON格式无效');
          return;
        }
      }
      delete submitData.model_config_text;
      
      const response = await SupplierService.updateSupplierCredential(currentSupplier.id, submitData);
      if (response.success) {
        message.success('更新成功');
        setEditModalVisible(false);
        editForm.resetFields();
        setCurrentSupplier(null);
        loadSuppliers();
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
    getCheckboxProps: (record: SupplierCredential) => ({
      disabled: record.is_default, // 默认凭证不允许选择
    }),
  };

  return (
    <div>
      {/* 页面标题 */}
      <div style={{ marginBottom: 16 }}>
        <Title level={2} style={{ margin: 0 }}>供应商凭证管理</Title>
        <Text type="secondary">管理AI服务供应商的API凭证和配置</Text>
      </div>

      {/* 操作栏 */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]} align="middle">
          <Col flex={1}>
            <Space size="middle">
              <Search
                placeholder="搜索凭证名称或供应商"
                allowClear
                style={{ width: 300 }}
                onSearch={handleSearch}
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
              />
              <Select
                placeholder="筛选供应商"
                allowClear
                style={{ width: 150 }}
                value={providerFilter}
                onChange={setProviderFilter}
              >
                {Object.entries(SUPPLIER_CONFIG).map(([key, config]) => (
                  <Option key={key} value={key.toLowerCase()}>
                    <Space>
                      <span>{config.icon}</span>
                      {config.name}
                    </Space>
                  </Option>
                ))}
              </Select>
              <Select
                placeholder="筛选状态"
                allowClear
                style={{ width: 120 }}
                value={statusFilter}
                onChange={setStatusFilter}
              >
                <Option value="active">启用</Option>
                <Option value="inactive">禁用</Option>
              </Select>
            </Space>
          </Col>
          <Col>
            <Space>
              <Button
                icon={<ReloadOutlined />}
                onClick={() => loadSuppliers()}
                loading={loading}
              >
                刷新
              </Button>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleCreateSupplier}
              >
                添加凭证
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 数据表格 */}
      <Card>
        <Table
          columns={columns}
          dataSource={suppliers}
          rowKey="id"
          pagination={pagination}
          loading={loading}
          onChange={handleTableChange}
          scroll={{ x: 'max-content' }}
          size="middle"
        />
      </Card>

      {/* 创建供应商凭证模态框 */}
      <Modal
        title="添加供应商凭证"
        open={createModalVisible}
        onCancel={() => {
          setCreateModalVisible(false);
          createForm.resetFields();
        }}
        footer={null}
        width={700}
      >
        <Form
          form={createForm}
          layout="vertical"
          onFinish={handleCreateSubmit}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="供应商"
                name="provider"
                rules={[{ required: true, message: '请选择供应商' }]}
              >
                <Select placeholder="请选择供应商">
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
                label="凭证名称"
                name="name"
                rules={[{ required: true, message: '请输入凭证名称' }]}
              >
                <Input placeholder="请输入凭证名称" />
              </Form.Item>
            </Col>
          </Row>
          
          <Form.Item
            label="API密钥"
            name="api_key"
            rules={[{ required: true, message: '请输入API密钥' }]}
          >
            <Input.Password placeholder="请输入API密钥" />
          </Form.Item>
          
          <Form.Item
            label="API端点"
            name="api_endpoint"
            extra="留空将使用默认端点"
          >
            <Input placeholder="https://api.example.com/v1" />
          </Form.Item>
          
          <Form.Item
            label="模型配置"
            name="model_config_text"
            extra="可选的JSON格式配置，用于自定义模型参数"
          >
            <TextArea
              rows={6}
              placeholder='{"model": "gpt-4", "temperature": 0.7, "max_tokens": 2000}'
            />
          </Form.Item>
          
          <Form.Item
            label="状态"
            name="is_active"
            initialValue={true}
            valuePropName="checked"
          >
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
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

      {/* 编辑供应商凭证模态框 */}
      <Modal
        title="编辑供应商凭证"
        open={editModalVisible}
        onCancel={() => {
          setEditModalVisible(false);
          editForm.resetFields();
          setCurrentSupplier(null);
        }}
        footer={null}
        width={700}
      >
        <Form
          form={editForm}
          layout="vertical"
          onFinish={handleEditSubmit}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="供应商"
                name="provider"
                rules={[{ required: true, message: '请选择供应商' }]}
              >
                <Select placeholder="请选择供应商">
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
                label="凭证名称"
                name="name"
                rules={[{ required: true, message: '请输入凭证名称' }]}
              >
                <Input placeholder="请输入凭证名称" />
              </Form.Item>
            </Col>
          </Row>
          
          <Form.Item
            label="API密钥"
            name="api_key"
            extra="留空表示不修改现有密钥"
          >
            <Input.Password placeholder="请输入新的API密钥（可选）" />
          </Form.Item>
          
          <Form.Item
            label="API端点"
            name="api_endpoint"
            extra="留空将使用默认端点"
          >
            <Input placeholder="https://api.example.com/v1" />
          </Form.Item>
          
          <Form.Item
            label="模型配置"
            name="model_config_text"
            extra="可选的JSON格式配置，用于自定义模型参数"
          >
            <TextArea
              rows={6}
              placeholder='{"model": "gpt-4", "temperature": 0.7, "max_tokens": 2000}'
            />
          </Form.Item>
          
          <Form.Item
            label="状态"
            name="is_active"
            valuePropName="checked"
          >
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
          
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                更新
              </Button>
              <Button onClick={() => {
                setEditModalVisible(false);
                editForm.resetFields();
                setCurrentSupplier(null);
              }}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 供应商详情抽屉 */}
      <Drawer
        title="供应商凭证详情"
        width={600}
        open={detailDrawerVisible}
        onClose={() => {
          setDetailDrawerVisible(false);
          setCurrentSupplier(null);
        }}
      >
        {currentSupplier && (
          <div>
            {/* 基本信息 */}
            <Descriptions
              title="基本信息"
              bordered
              column={1}
              style={{ marginBottom: 24 }}
            >
              <Descriptions.Item label="供应商">
                <Space>
                  <span style={{ fontSize: 16 }}>
                    {SUPPLIER_CONFIG[currentSupplier.provider as keyof typeof SUPPLIER_CONFIG]?.icon || '🔧'}
                  </span>
                  <strong>
                    {SUPPLIER_CONFIG[currentSupplier.provider as keyof typeof SUPPLIER_CONFIG]?.name || currentSupplier.provider}
                  </strong>
                  <Text type="secondary">({currentSupplier.provider})</Text>
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="凭证名称">
                {currentSupplier.name}
                {currentSupplier.is_default && (
                  <Tag color="gold" style={{ marginLeft: 8 }}>默认</Tag>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="API端点">
                {currentSupplier.api_endpoint ? (
                  <Text code>{currentSupplier.api_endpoint}</Text>
                ) : (
                  <Text type="secondary">使用默认端点</Text>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Space>
                  <Tag color={currentSupplier.is_active ? 'green' : 'red'}>
                    {currentSupplier.is_active ? '启用' : '禁用'}
                  </Tag>
                  {currentSupplier.connection_status && (
                    <Badge
                      status={currentSupplier.connection_status === 'connected' ? 'success' : 'error'}
                      text={currentSupplier.connection_status === 'connected' ? '连接正常' : '连接异常'}
                    />
                  )}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {dayjs(currentSupplier.created_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="最后更新">
                {dayjs(currentSupplier.updated_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="最后测试">
                {currentSupplier.last_tested_at ? 
                  dayjs(currentSupplier.last_tested_at).format('YYYY-MM-DD HH:mm:ss') : 
                  '未测试'
                }
              </Descriptions.Item>
            </Descriptions>

            {/* 模型配置 */}
            {currentSupplier.model_config && (
              <div>
                <Divider>模型配置</Divider>
                <pre style={{ 
                  background: '#f5f5f5', 
                  padding: 16, 
                  borderRadius: 6,
                  fontSize: 12,
                  overflow: 'auto'
                }}>
                  {JSON.stringify(currentSupplier.model_config, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </Drawer>
    </div>
  );
};

export default SuppliersPage;