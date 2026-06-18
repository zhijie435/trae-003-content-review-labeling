import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from 'antd';
import AppLayout from './components/Layout';
import Dashboard from './pages/Dashboard';
import TextAnnotation from './pages/TextAnnotation';
import ImageAnnotation from './pages/ImageAnnotation';
import QualityCheck from './pages/QualityCheck';

const { Content } = Layout;

const App: React.FC = () => {
  return (
    <AppLayout>
      <Content style={{ padding: '24px', minHeight: 'calc(100vh - 64px)' }}>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/text-annotation" element={<TextAnnotation />} />
          <Route path="/image-annotation" element={<ImageAnnotation />} />
          <Route path="/quality-check" element={<QualityCheck />} />
        </Routes>
      </Content>
    </AppLayout>
  );
};

export default App;
