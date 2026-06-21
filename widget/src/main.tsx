import React from 'react';
import ReactDOM from 'react-dom/client';
import { DemoShop } from './DemoShop';
import './widget/styles.css';

const container = document.getElementById('root');
if (!container) {
  throw new Error('未找到挂载节点 #root');
}

ReactDOM.createRoot(container).render(
  <React.StrictMode>
    <DemoShop />
  </React.StrictMode>,
);
