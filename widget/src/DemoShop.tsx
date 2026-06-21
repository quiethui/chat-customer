/** 演示宿主页：模拟电商商品详情页，右下角嵌入 AI 客服挂件。 */

import type { CSSProperties } from 'react';
import { ChatWidget } from './widget/ChatWidget';

const page: CSSProperties = {
  minHeight: '100vh',
  background: '#f5f6f8',
  fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', sans-serif",
  color: '#1f2937',
};

const nav: CSSProperties = {
  height: 56,
  background: '#fff',
  borderBottom: '1px solid #eee',
  display: 'flex',
  alignItems: 'center',
  padding: '0 32px',
  fontWeight: 700,
  fontSize: 18,
  color: '#2f6bff',
};

const main: CSSProperties = {
  maxWidth: 960,
  margin: '24px auto',
  background: '#fff',
  borderRadius: 12,
  padding: 24,
  display: 'flex',
  gap: 24,
  boxShadow: '0 2px 12px rgba(0,0,0,0.05)',
};

const gallery: CSSProperties = {
  width: 360,
  height: 360,
  borderRadius: 12,
  background: 'linear-gradient(135deg, #e0ecff, #f0f5ff)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontSize: 96,
};

const price: CSSProperties = { color: '#fa5151', fontSize: 28, fontWeight: 700, margin: '12px 0' };
const buy: CSSProperties = {
  marginTop: 24,
  background: '#fa5151',
  color: '#fff',
  border: 'none',
  borderRadius: 24,
  padding: '12px 40px',
  fontSize: 16,
  cursor: 'pointer',
};

export function DemoShop() {
  return (
    <div style={page}>
      <div style={nav}>云市集</div>
      <div style={main}>
        <div style={gallery}>🎧</div>
        <div style={{ flex: 1 }}>
          <h1 style={{ fontSize: 22, margin: 0 }}>无线降噪耳机</h1>
          <p style={{ color: '#888', marginTop: 8 }}>主动降噪 · 蓝牙 5.3 · 单次续航 8 小时 · 充电盒总续航 30 小时</p>
          <div style={price}>¥599.00</div>
          <ul style={{ color: '#555', lineHeight: 2, paddingLeft: 18 }}>
            <li>SKU：HEADSET-NC-002</li>
            <li>库存：充足，48 小时内发货</li>
            <li>支持 7 天无理由退换</li>
          </ul>
          <button type="button" style={buy}>
            立即购买
          </button>
        </div>
      </div>
      <p style={{ textAlign: 'center', color: '#aab', fontSize: 13 }}>
        ↘ 右下角点开「在线客服」，体验匿名问答 · 转人工 · 满意度评分
      </p>

      <ChatWidget />
    </div>
  );
}
