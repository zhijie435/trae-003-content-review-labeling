import React, { useState } from 'react';
import { Layout, Menu, theme } from 'antd';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  DashboardOutlined,
  FileTextOutlined,
  PictureOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';

const { Header, Sider } = Layout;

interface AppLayoutProps {
  children: React.ReactNode;
}

const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const {
    token: { colorBgContainer },
  } = theme.useToken();

  const menuItems = [
    {
      key: '/dashboard',
      icon: <DashboardOutlined />,
      label: '数据概览',
    },
    {
      key: '/text-annotation',
      icon: <FileTextOutlined />,
      label: '文本标注',
    },
    {
      key: '/image-annotation',
      icon: <PictureOutlined />,
      label: '图片标注',
    },
    {
      key: '/quality-check',
      icon: <CheckCircleOutlined />,
      label: '质检中心',
    },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed}>
        <div style={{ height: 64, margin: 16, background: 'rgba(255, 255, 255, 0.2)', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontSize: collapsed ? 12 : 18, fontWeight: 'bold' }}>
          {collapsed ? '标注' : '内容审核标注'}
        </div>
        <Menu
          theme="dark"
          selectedKeys={[location.pathname]}
          mode="inline"
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{ padding: '0 24px', background: colorBgContainer, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h2 style={{ margin: 0 }}>
            {menuItems.find(item => item.key === location.pathname)?.label || '内容审核标注平台'}
          </h2>
          <div style={{ color: '#666' }}>标注员</div>
        </Header>
        {children}
      </Layout>
    </Layout>
  );
};

export default AppLayout;
