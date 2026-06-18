import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Button, message } from 'antd';
import { FileTextOutlined, PictureOutlined, CheckCircleOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { annotationApi } from '../services/api';
import { Annotation, AnnotationStatus, AnnotationType } from '../types';

const Dashboard: React.FC = () => {
  const [data, setData] = useState<Annotation[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await annotationApi.getList();
      setData(res.data);
    } catch (e) {
      message.error('获取数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSeed = async () => {
    try {
      const res = await annotationApi.seed();
      message.success(`已初始化 ${res.data.text} 条文本和 ${res.data.image} 条图片示例数据`);
      fetchData();
    } catch (e) {
      message.error('初始化数据失败');
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const total = data.length;
  const textCount = data.filter(d => d.type === AnnotationType.TEXT).length;
  const imageCount = data.filter(d => d.type === AnnotationType.IMAGE).length;
  const pendingCount = data.filter(d => d.status === AnnotationStatus.PENDING).length;
  const annotatedCount = data.filter(d => d.status === AnnotationStatus.ANNOTATED || d.status === AnnotationStatus.REVIEWED).length;

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Button type="primary" onClick={handleSeed} loading={loading}>
          初始化示例数据
        </Button>
      </div>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={6}>
          <Card loading={loading}>
            <Statistic title="总任务数" value={total} prefix={<FileTextOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card loading={loading}>
            <Statistic title="文本标注" value={textCount} prefix={<FileTextOutlined />} valueStyle={{ color: '#1890ff' }} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card loading={loading}>
            <Statistic title="图片标注" value={imageCount} prefix={<PictureOutlined />} valueStyle={{ color: '#52c41a' }} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card loading={loading}>
            <Statistic title="待标注" value={pendingCount} prefix={<ClockCircleOutlined />} valueStyle={{ color: '#faad14' }} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card loading={loading}>
            <Statistic title="已标注" value={annotatedCount} prefix={<CheckCircleOutlined />} valueStyle={{ color: '#52c41a' }} />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
