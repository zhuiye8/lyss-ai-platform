/**
 * 供应商选择器组件
 * 支持树形结构展示供应商和模型信息
 */

import React, { useState, useEffect } from 'react';
import { Select, TreeSelect, Typography, Tag, Space } from 'antd';
import { ApiOutlined, RobotOutlined, GlobalOutlined } from '@ant-design/icons';
import { SupplierService } from '@/services/supplier';
import { ProviderTreeNode } from '@/types/supplier';

const { Text } = Typography;

interface ProviderSelectorProps {
  value?: string;
  onChange?: (value: string, providerInfo?: ProviderTreeNode) => void;
  placeholder?: string;
  disabled?: boolean;
  allowClear?: boolean;
  showModels?: boolean; // 是否显示模型信息
  style?: React.CSSProperties;
}

interface TreeSelectOption {
  value: string;
  title: React.ReactNode;
  children?: TreeSelectOption[];
  selectable?: boolean;
  disabled?: boolean;
}

export const ProviderSelector: React.FC<ProviderSelectorProps> = ({
  value,
  onChange,
  placeholder = '请选择供应商',
  disabled = false,
  allowClear = true,
  showModels = false,
  style,
}) => {
  const [loading, setLoading] = useState(false);
  const [providers, setProviders] = useState<ProviderTreeNode[]>([]);
  const [treeData, setTreeData] = useState<TreeSelectOption[]>([]);

  // 获取供应商树形数据
  useEffect(() => {
    const fetchProviders = async () => {
      setLoading(true);
      try {
        const response = await SupplierService.getAvailableProviders();
        if (response.success && response.data) {
          setProviders(response.data.providers);
          setTreeData(buildTreeData(response.data.providers));
        }
      } catch (error) {
        console.error('获取供应商列表失败:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchProviders();
  }, []);

  // 构建树形选择器数据
  const buildTreeData = (providers: ProviderTreeNode[]): TreeSelectOption[] => {
    return providers.map(provider => {
      const option: TreeSelectOption = {
        value: provider.provider_name,
        title: (
          <Space>
            <ApiOutlined style={{ color: '#1890ff' }} />
            <Text strong>{provider.display_name}</Text>
            <Text type="secondary" style={{ fontSize: '12px' }}>
              {provider.description}
            </Text>
          </Space>
        ),
        selectable: true,
      };

      // 如果需要显示模型信息，添加子节点
      if (showModels && provider.models.length > 0) {
        option.children = provider.models.map(model => ({
          value: `${provider.provider_name}::${model.model_id}`,
          title: (
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <Space>
                <RobotOutlined style={{ color: '#52c41a' }} />
                <Text>{model.display_name}</Text>
                <Tag color="blue">{model.type}</Tag>
              </Space>
              <Text type="secondary" style={{ fontSize: '11px', marginLeft: '20px' }}>
                {model.description}
              </Text>
              <Space style={{ marginLeft: '20px' }}>
                <Tag color="orange">
                  上下文: {model.context_window.toLocaleString()}
                </Tag>
                <Tag color="green">
                  输入: ${model.price_per_1k_tokens.input}/1K
                </Tag>
                <Tag color="purple">
                  输出: ${model.price_per_1k_tokens.output}/1K
                </Tag>
              </Space>
            </Space>
          ),
          selectable: false, // 模型节点不可选择，仅作展示
        }));
      }

      return option;
    });
  };

  // 处理选择变化
  const handleChange = (selectedValue: string) => {
    const selectedProvider = providers.find(p => p.provider_name === selectedValue);
    onChange?.(selectedValue, selectedProvider);
  };

  // 自定义下拉框渲染
  const dropdownRender = (menu: React.ReactElement) => (
    <div>
      {menu}
      <div style={{ 
        padding: '8px 12px', 
        borderTop: '1px solid #f0f0f0',
        backgroundColor: '#fafafa',
        fontSize: '12px',
        color: '#666'
      }}>
        <Space>
          <GlobalOutlined />
          <Text type="secondary">
            共 {providers.length} 个供应商可用
          </Text>
        </Space>
      </div>
    </div>
  );

  if (showModels) {
    // 树形选择器模式，显示供应商和模型
    return (
      <TreeSelect
        value={value}
        onChange={handleChange}
        treeData={treeData}
        placeholder={placeholder}
        disabled={disabled}
        allowClear={allowClear}
        loading={loading}
        style={style}
        showSearch
        treeDefaultExpandAll={false}
        treeExpandedKeys={[]} // 默认不展开
        dropdownStyle={{ maxHeight: 400, overflow: 'auto' }}
        filterTreeNode={(input, node) => {
          const title = typeof node.title === 'string' ? node.title : '';
          return title.toLowerCase().includes(input.toLowerCase());
        }}
        dropdownRender={dropdownRender}
      />
    );
  }

  // 简单选择器模式，仅显示供应商
  const selectOptions = providers.map(provider => ({
    value: provider.provider_name,
    label: (
      <Space>
        <ApiOutlined style={{ color: '#1890ff' }} />
        <Text>{provider.display_name}</Text>
        <Text type="secondary" style={{ fontSize: '12px' }}>
          {provider.description}
        </Text>
      </Space>
    ),
  }));

  return (
    <Select
      value={value}
      onChange={handleChange}
      options={selectOptions}
      placeholder={placeholder}
      disabled={disabled}
      allowClear={allowClear}
      loading={loading}
      style={style}
      showSearch
      filterOption={(input, option) => {
        return String(option?.label || '').toLowerCase().includes(input.toLowerCase());
      }}
      dropdownRender={dropdownRender}
    />
  );
};

export default ProviderSelector;