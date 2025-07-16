/**
 * 模型选择器组件
 * 基于选择的供应商动态加载并展示模型信息
 */

import React, { useState, useEffect } from 'react';
import { Select, Card, Row, Col, Typography, Tag, Space, Spin, Empty } from 'antd';
import { RobotOutlined, ClockCircleOutlined, DollarOutlined, DatabaseOutlined } from '@ant-design/icons';
import { SupplierService } from '@/services/supplier';
import { ProviderModelInfo } from '@/types/supplier';

const { Text } = Typography;
const { Option } = Select;

interface ModelSelectorProps {
  providerName?: string; // 选择的供应商名称
  value?: string; // 选择的模型ID
  onChange?: (modelId: string, modelInfo?: ProviderModelInfo) => void;
  placeholder?: string;
  disabled?: boolean;
  allowClear?: boolean;
  showDetails?: boolean; // 是否显示模型详细信息卡片
  mode?: 'select' | 'cards'; // 显示模式：下拉选择 或 卡片选择
  style?: React.CSSProperties;
}

export const ModelSelector: React.FC<ModelSelectorProps> = ({
  providerName,
  value,
  onChange,
  placeholder = '请先选择供应商',
  disabled = false,
  allowClear = true,
  showDetails = true,
  mode = 'select',
  style,
}) => {
  const [loading, setLoading] = useState(false);
  const [models, setModels] = useState<ProviderModelInfo[]>([]);
  const [selectedModel, setSelectedModel] = useState<ProviderModelInfo | null>(null);

  // 当供应商变化时，获取模型列表
  useEffect(() => {
    if (providerName) {
      fetchModels();
    } else {
      setModels([]);
      setSelectedModel(null);
    }
  }, [providerName]);

  // 当value变化时，更新选中的模型信息
  useEffect(() => {
    if (value && models.length > 0) {
      const model = models.find(m => m.model_id === value);
      setSelectedModel(model || null);
    } else {
      setSelectedModel(null);
    }
  }, [value, models]);

  // 获取指定供应商的模型列表
  const fetchModels = async () => {
    if (!providerName) return;
    
    setLoading(true);
    try {
      const response = await SupplierService.getProviderModelsByName(providerName);
      if (response.success && response.data) {
        setModels(response.data.models);
      }
    } catch (error) {
      console.error('获取模型列表失败:', error);
      setModels([]);
    } finally {
      setLoading(false);
    }
  };

  // 处理模型选择
  const handleModelChange = (modelId: string) => {
    const modelInfo = models.find(m => m.model_id === modelId);
    setSelectedModel(modelInfo || null);
    onChange?.(modelId, modelInfo);
  };

  // 获取模型类型标签颜色
  const getModelTypeColor = (type: string) => {
    const colorMap: Record<string, string> = {
      chat: 'blue',
      completion: 'green',
      embedding: 'orange',
      image: 'purple',
      audio: 'red',
      multimodal: 'cyan',
    };
    return colorMap[type] || 'default';
  };

  // 格式化价格显示
  const formatPrice = (price: number) => {
    return price < 0.001 ? price.toFixed(6) : price.toFixed(3);
  };

  // 渲染模型详情卡片
  const renderModelDetails = (model: ProviderModelInfo) => (
    <Card 
      size="small" 
      style={{ marginTop: 8 }}
      title={
        <Space>
          <RobotOutlined />
          <Text strong>{model.display_name}</Text>
          <Tag color={getModelTypeColor(model.type)}>{model.type}</Tag>
        </Space>
      }
    >
      <Row gutter={[16, 8]}>
        <Col span={24}>
          <Text type="secondary">{model.description}</Text>
        </Col>
        <Col span={8}>
          <Space direction="vertical" size="small">
            <Text strong>
              <DatabaseOutlined /> 上下文窗口
            </Text>
            <Text>{model.context_window.toLocaleString()} tokens</Text>
          </Space>
        </Col>
        <Col span={8}>
          <Space direction="vertical" size="small">
            <Text strong>
              <ClockCircleOutlined /> 最大输出
            </Text>
            <Text>{model.max_tokens.toLocaleString()} tokens</Text>
          </Space>
        </Col>
        <Col span={8}>
          <Space direction="vertical" size="small">
            <Text strong>
              <DollarOutlined /> 价格 (每1K tokens)
            </Text>
            <Space direction="vertical" size="small">
              <Text>输入: ${formatPrice(model.price_per_1k_tokens.input)}</Text>
              <Text>输出: ${formatPrice(model.price_per_1k_tokens.output)}</Text>
            </Space>
          </Space>
        </Col>
        {model.features.length > 0 && (
          <Col span={24}>
            <Space direction="vertical" size="small">
              <Text strong>特性支持</Text>
              <Space wrap>
                {model.features.map((feature, index) => (
                  <Tag key={index} color="processing">{feature}</Tag>
                ))}
              </Space>
            </Space>
          </Col>
        )}
      </Row>
    </Card>
  );

  // 如果没有选择供应商
  if (!providerName) {
    return (
      <div style={style}>
        <Select
          placeholder={placeholder}
          disabled
          style={{ width: '100%' }}
        />
        {showDetails && (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="请先选择供应商"
            style={{ marginTop: 16, padding: 16 }}
          />
        )}
      </div>
    );
  }

  // 卡片选择模式
  if (mode === 'cards') {
    return (
      <div style={style}>
        <Spin spinning={loading}>
          {models.length === 0 ? (
            <Empty description="该供应商暂无可用模型" />
          ) : (
            <Row gutter={[16, 16]}>
              {models.map(model => (
                <Col span={12} key={model.model_id}>
                  <Card
                    hoverable
                    size="small"
                    className={value === model.model_id ? 'selected-model-card' : ''}
                    onClick={() => handleModelChange(model.model_id)}
                    style={{
                      border: value === model.model_id ? '2px solid #1890ff' : '1px solid #d9d9d9'
                    }}
                  >
                    <Space direction="vertical" size="small" style={{ width: '100%' }}>
                      <Space>
                        <RobotOutlined style={{ color: '#1890ff' }} />
                        <Text strong>{model.display_name}</Text>
                        <Tag color={getModelTypeColor(model.type)}>
                          {model.type}
                        </Tag>
                      </Space>
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        {model.description}
                      </Text>
                      <Space>
                        <Tag>
                          上下文: {(model.context_window / 1000).toFixed(0)}K
                        </Tag>
                        <Tag color="green">
                          ${formatPrice(model.price_per_1k_tokens.input)}/1K
                        </Tag>
                      </Space>
                    </Space>
                  </Card>
                </Col>
              ))}
            </Row>
          )}
        </Spin>
      </div>
    );
  }

  // 下拉选择模式
  return (
    <div style={style}>
      <Select
        value={value}
        onChange={handleModelChange}
        placeholder={loading ? '加载中...' : '请选择模型'}
        disabled={disabled || loading}
        allowClear={allowClear}
        loading={loading}
        style={{ width: '100%' }}
        showSearch
        filterOption={(input, option) => {
          return String(option?.children || '').toLowerCase().includes(input.toLowerCase());
        }}
      >
        {models.map(model => (
          <Option key={model.model_id} value={model.model_id}>
            <Space>
              <RobotOutlined style={{ color: '#1890ff' }} />
              <Text>{model.display_name}</Text>
              <Tag color={getModelTypeColor(model.type)}>
                {model.type}
              </Tag>
              <Text type="secondary" style={{ fontSize: '12px' }}>
                ${formatPrice(model.price_per_1k_tokens.input)}/1K
              </Text>
            </Space>
          </Option>
        ))}
      </Select>
      
      {showDetails && selectedModel && renderModelDetails(selectedModel)}
    </div>
  );
};

export default ModelSelector;