/**
 * 应用程序入口
 * React应用的启动点
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

// 确保DOM元素存在
const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error('未找到根元素，请确保HTML中存在id为"root"的元素');
}

// 创建React根节点并渲染应用
const root = ReactDOM.createRoot(rootElement);

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);