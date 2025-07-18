/**
 * 401未认证错误页面
 */

import React from 'react';
import { Result, Button } from 'antd';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '@/utils/constants';

const UnauthorizedPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <Result
      status="warning"
      title="认证已过期"
      subTitle="您的登录状态已过期，请重新登录。"
      extra={
        <Button type="primary" onClick={() => navigate(ROUTES.LOGIN)}>
          重新登录
        </Button>
      }
    />
  );
};

export default UnauthorizedPage;