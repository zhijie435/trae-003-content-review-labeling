import React, { useEffect, useState } from 'react';
import { Table, Tag, Card, Tabs, Image, Descriptions, Button, Modal, Form, Radio, Input, InputNumber, Space, Statistic, Row, Col } from 'antd';
import { CheckCircleOutlined, EyeOutlined, ExperimentOutlined } from '@ant-design/icons';
import { annotationApi } from '../services/api';
import { Annotation, AnnotationType, AnnotationResult, AnnotationStatus } from '../types';
import {
  ANNOTATION_TYPE_MAP,
  ANNOTATION_RESULT_MAP,
  ANNOTATION_RESULT_COLOR,
  ANNOTATION_STATUS_MAP,
  ANNOTATION_STATUS_COLOR,
} from '../utils/enumMaps';
import dayjs from 'dayjs';

const QualityCheck: React.FC = () => {
  const [data, setData] = useState<Annotation[]>([]);
  const [loading, setLoading] = useState(false);
  const [sampleData, setSampleData] = useState<Annotation[]>([]);
  const [sampleLoading, setSampleLoading] = useState(false);
  const [sampleCount, setSampleCount] = useState(5);
  const [sampleTotal, setSampleTotal] = useState(0);
  const [sampleSampled, setSampleSampled] = useState(0);
  const [detailVisible, setDetailVisible] = useState(false);
  const [currentRecord, setCurrentRecord] = useState<Annotation | null>(null);
  const [reviewVisible, setReviewVisible] = useState(false);
  const [form] = Form.useForm();

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await annotationApi.getReviewList();
      setData(res.data);
    } catch (e) {
      message.error('获取数据失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleViewDetail = (record: Annotation) => {
    setCurrentRecord(record);
    setDetailVisible(true);
  };

  const handleReview = (record: Annotation) => {
    setCurrentRecord(record);
    form.resetFields();
    setReviewVisible(true);
  };

  const handleReviewSubmit = async () => {
    if (!currentRecord) return;
    try {
      const values = await form.validateFields();
      await annotationApi.update(currentRecord.id, {
        reviewer: '质检员A',
        remark: values.remark,
      });
      message.success('质检完成');
      setReviewVisible(false);
      fetchData();
    } catch (e) {
      console.error(e);
    }
  };

  const handleSample = async () => {
    setSampleLoading(true);
    try {
      const res = await annotationApi.getReviewSample(sampleCount);
      setSampleData(res.data.samples);
      setSampleTotal(res.data.total);
      setSampleSampled(res.data.sampled);
      message.success(`已抽取 ${res.data.sampled} 条样本（共 ${res.data.total} 条待检）`);
    } catch (e) {
      message.error('抽样失败');
    } finally {
      setSampleLoading(false);
    }
  };

  const textColumns = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 80,
    },
    {
      title: '文本内容',
      dataIndex: 'content',
      ellipsis: true,
      render: (text: string) => <div style={{ maxWidth: 400 }}>{text}</div>,
    },
    {
      title: '标注结果',
      dataIndex: 'result',
      width: 120,
      render: (result?: AnnotationResult) =>
        result ? (
          <Tag color={ANNOTATION_RESULT_COLOR[result]}>
            {ANNOTATION_RESULT_MAP[result]}
          </Tag>
        ) : (
          <Tag color="default">未标注</Tag>
        ),
    },
    {
      title: '标签',
      dataIndex: 'tags',
      width: 150,
      render: (tags?: string) => tags || '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (status: AnnotationStatus) => (
        <Tag color={ANNOTATION_STATUS_COLOR[status]}>
          {ANNOTATION_STATUS_MAP[status]}
        </Tag>
      ),
    },
    {
      title: '标注员',
      dataIndex: 'annotator',
      width: 100,
      render: (a?: string) => a || '-',
    },
    {
      title: '标注时间',
      dataIndex: 'updatedAt',
      width: 180,
      render: (t: string) => dayjs(t).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '操作',
      key: 'action',
      width: 160,
      render: (_: any, record: Annotation) => (
        <span>
          <Button type="link" icon={<EyeOutlined />} onClick={() => handleViewDetail(record)}>
            查看
          </Button>
          <Button
            type="link"
            icon={<CheckCircleOutlined />}
            onClick={() => handleReview(record)}
          >
            质检
          </Button>
        </span>
      ),
    },
  ];

  const imageColumns = [
    ...textColumns.filter(c => c.dataIndex !== 'content'),
    {
      title: '图片',
      dataIndex: 'imageUrl',
      width: 140,
      render: (url: string) => (
        <Image width={100} height={80} src={url} style={{ objectFit: 'cover' }} />
      ),
    },
  ].map(c => {
    if (c.dataIndex === 'id') return { ...c, title: 'ID' };
    return c;
  });

  const imageColumnsFixed = [
    { title: 'ID', dataIndex: 'id', width: 80 },
    {
      title: '图片',
      dataIndex: 'imageUrl',
      width: 140,
      render: (url: string) => (
        <Image width={100} height={80} src={url} style={{ objectFit: 'cover' }} />
      ),
    },
    { title: '图片描述', dataIndex: 'content', render: (t?: string) => t || '-' },
    {
      title: '标注结果',
      dataIndex: 'result',
      width: 120,
      render: (result?: AnnotationResult) =>
        result ? (
          <Tag color={ANNOTATION_RESULT_COLOR[result]}>
            {ANNOTATION_RESULT_MAP[result]}
          </Tag>
        ) : (
          <Tag color="default">未标注</Tag>
        ),
    },
    { title: '标签', dataIndex: 'tags', width: 150, render: (t?: string) => t || '-' },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (status: AnnotationStatus) => (
        <Tag color={ANNOTATION_STATUS_COLOR[status]}>
          {ANNOTATION_STATUS_MAP[status]}
        </Tag>
      ),
    },
    { title: '标注员', dataIndex: 'annotator', width: 100, render: (a?: string) => a || '-' },
    {
      title: '标注时间',
      dataIndex: 'updatedAt',
      width: 180,
      render: (t: string) => dayjs(t).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '操作',
      key: 'action',
      width: 160,
      render: (_: any, record: Annotation) => (
        <span>
          <Button type="link" icon={<EyeOutlined />} onClick={() => handleViewDetail(record)}>
            查看
          </Button>
          <Button
            type="link"
            icon={<CheckCircleOutlined />}
            onClick={() => handleReview(record)}
          >
            质检
          </Button>
        </span>
      ),
    },
  ];

  const textData = data.filter(d => d.type === AnnotationType.TEXT);
  const imageData = data.filter(d => d.type === AnnotationType.IMAGE);

  const tabItems = [
    {
      key: 'sample',
      label: '抽样质检',
      children: (
        <Card>
          <Card size="small" style={{ marginBottom: 16 }}>
            <Space wrap>
              <span>抽样数量：</span>
              <InputNumber
                min={1}
                max={100}
                value={sampleCount}
                onChange={(val) => setSampleCount(val || 5)}
              />
              <Button
                type="primary"
                icon={<ExperimentOutlined />}
                onClick={handleSample}
                loading={sampleLoading}
              >
                开始抽样
              </Button>
              {sampleTotal > 0 && (
                <span style={{ marginLeft: 16 }}>
                  <Tag color="blue">待检总数：{sampleTotal}</Tag>
                  <Tag color="green">已抽样：{sampleSampled}</Tag>
                </span>
              )}
            </Space>
          </Card>
          <Table
            rowKey="id"
            columns={[
              { title: 'ID', dataIndex: 'id', width: 80 },
              {
                title: '类型',
                dataIndex: 'type',
                width: 100,
                render: (t: AnnotationType) => (
                  <Tag color={t === AnnotationType.TEXT ? 'blue' : 'green'}>
                    {ANNOTATION_TYPE_MAP[t]}
                  </Tag>
                ),
              },
              {
                title: '内容',
                dataIndex: 'content',
                render: (_: any, r: Annotation) =>
                  r.type === AnnotationType.TEXT ? (
                    <div style={{ maxWidth: 300 }}>{r.content}</div>
                  ) : (
                    r.imageUrl && <Image width={80} height={60} src={r.imageUrl} style={{ objectFit: 'cover' }} />
                  ),
              },
              {
                title: '标注结果',
                dataIndex: 'result',
                width: 120,
                render: (result?: AnnotationResult) =>
                  result ? (
                    <Tag color={ANNOTATION_RESULT_COLOR[result]}>
                      {ANNOTATION_RESULT_MAP[result]}
                    </Tag>
                  ) : (
                    <Tag color="default">未标注</Tag>
                  ),
              },
              {
                title: '状态',
                dataIndex: 'status',
                width: 100,
                render: (status: AnnotationStatus) => (
                  <Tag color={ANNOTATION_STATUS_COLOR[status]}>
                    {ANNOTATION_STATUS_MAP[status]}
                  </Tag>
                ),
              },
              { title: '标注员', dataIndex: 'annotator', width: 100, render: (a?: string) => a || '-' },
              {
                title: '标注时间',
                dataIndex: 'updatedAt',
                width: 180,
                render: (t: string) => dayjs(t).format('YYYY-MM-DD HH:mm:ss'),
              },
              {
                title: '操作',
                key: 'action',
                width: 160,
                render: (_: any, record: Annotation) => (
                  <span>
                    <Button type="link" icon={<EyeOutlined />} onClick={() => handleViewDetail(record)}>
                      查看
                    </Button>
                    <Button
                      type="link"
                      icon={<CheckCircleOutlined />}
                      onClick={() => handleReview(record)}
                    >
                      质检
                    </Button>
                  </span>
                ),
              },
            ]}
            dataSource={sampleData}
            loading={sampleLoading}
            pagination={{ pageSize: 10 }}
            locale={{ emptyText: '请点击"开始抽样"抽取质检样本' }}
          />
        </Card>
      ),
    },
    {
      key: 'all',
      label: `全部 (${data.length})`,
      children: (
        <Card>
          <div style={{ marginBottom: 16 }}>
            <Tag color="blue">文本: {textData.length}</Tag>
            <Tag color="green">图片: {imageData.length}</Tag>
          </div>
          <Table
            rowKey="id"
            columns={[
              { title: 'ID', dataIndex: 'id', width: 80 },
              {
                title: '类型',
                dataIndex: 'type',
                width: 100,
                render: (t: AnnotationType) => (
                  <Tag color={t === AnnotationType.TEXT ? 'blue' : 'green'}>
                    {ANNOTATION_TYPE_MAP[t]}
                  </Tag>
                ),
              },
              {
                title: '内容',
                dataIndex: 'content',
                render: (_: any, r: Annotation) =>
                  r.type === AnnotationType.TEXT ? (
                    <div style={{ maxWidth: 300 }}>{r.content}</div>
                  ) : (
                    r.imageUrl && <Image width={80} height={60} src={r.imageUrl} style={{ objectFit: 'cover' }} />
                  ),
              },
              {
                title: '标注结果',
                dataIndex: 'result',
                width: 120,
                render: (result?: AnnotationResult) =>
                  result ? (
                    <Tag color={ANNOTATION_RESULT_COLOR[result]}>
                      {ANNOTATION_RESULT_MAP[result]}
                    </Tag>
                  ) : (
                    <Tag color="default">未标注</Tag>
                  ),
              },
              {
                title: '状态',
                dataIndex: 'status',
                width: 100,
                render: (status: AnnotationStatus) => (
                  <Tag color={ANNOTATION_STATUS_COLOR[status]}>
                    {ANNOTATION_STATUS_MAP[status]}
                  </Tag>
                ),
              },
              { title: '标注员', dataIndex: 'annotator', width: 100, render: (a?: string) => a || '-' },
              {
                title: '标注时间',
                dataIndex: 'updatedAt',
                width: 180,
                render: (t: string) => dayjs(t).format('YYYY-MM-DD HH:mm:ss'),
              },
              {
                title: '操作',
                key: 'action',
                width: 160,
                render: (_: any, record: Annotation) => (
                  <span>
                    <Button type="link" icon={<EyeOutlined />} onClick={() => handleViewDetail(record)}>
                      查看
                    </Button>
                    <Button
                      type="link"
                      icon={<CheckCircleOutlined />}
                      onClick={() => handleReview(record)}
                    >
                      质检
                    </Button>
                  </span>
                ),
              },
            ]}
            dataSource={data}
            loading={loading}
            pagination={{ pageSize: 10 }}
          />
        </Card>
      ),
    },
    {
      key: 'text',
      label: `文本标注 (${textData.length})`,
      children: (
        <Card>
          <Table
            rowKey="id"
            columns={textColumns}
            dataSource={textData}
            loading={loading}
            pagination={{ pageSize: 10 }}
          />
        </Card>
      ),
    },
    {
      key: 'image',
      label: `图片标注 (${imageData.length})`,
      children: (
        <Card>
          <Table
            rowKey="id"
            columns={imageColumnsFixed}
            dataSource={imageData}
            loading={loading}
            pagination={{ pageSize: 10 }}
          />
        </Card>
      ),
    },
  ];

  return (
    <div>
      <Card title="质检中心" extra={<Button onClick={fetchData}>刷新</Button>}>
        <Tabs items={tabItems} />
      </Card>

      <Modal
        title="标注详情"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailVisible(false)}>
            关闭
          </Button>,
        ]}
        width={600}
      >
        {currentRecord && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="ID">{currentRecord.id}</Descriptions.Item>
            <Descriptions.Item label="类型">
              <Tag color={currentRecord.type === AnnotationType.TEXT ? 'blue' : 'green'}>
                {ANNOTATION_TYPE_MAP[currentRecord.type]}
              </Tag>
            </Descriptions.Item>
            {currentRecord.type === AnnotationType.IMAGE && currentRecord.imageUrl && (
              <Descriptions.Item label="图片">
                <Image width={300} src={currentRecord.imageUrl} />
              </Descriptions.Item>
            )}
            <Descriptions.Item label="内容">
              {currentRecord.content || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="标注结果">
              {currentRecord.result ? (
                <Tag color={ANNOTATION_RESULT_COLOR[currentRecord.result]}>
                  {ANNOTATION_RESULT_MAP[currentRecord.result]}
                </Tag>
              ) : (
                '-'
              )}
            </Descriptions.Item>
            <Descriptions.Item label="标签">{currentRecord.tags || '-'}</Descriptions.Item>
            <Descriptions.Item label="备注">{currentRecord.remark || '-'}</Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={ANNOTATION_STATUS_COLOR[currentRecord.status]}>
                {ANNOTATION_STATUS_MAP[currentRecord.status]}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="标注员">{currentRecord.annotator || '-'}</Descriptions.Item>
            <Descriptions.Item label="质检员">{currentRecord.reviewer || '-'}</Descriptions.Item>
            <Descriptions.Item label="创建时间">
              {dayjs(currentRecord.createdAt).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
            <Descriptions.Item label="更新时间">
              {dayjs(currentRecord.updatedAt).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>

      <Modal
        title="质检审核"
        open={reviewVisible}
        onOk={handleReviewSubmit}
        onCancel={() => setReviewVisible(false)}
        width={600}
        destroyOnClose
      >
        {currentRecord && (
          <div>
            <Descriptions column={1} bordered size="small" style={{ marginBottom: 16 }}>
              <Descriptions.Item label="类型">
                {ANNOTATION_TYPE_MAP[currentRecord.type]}
              </Descriptions.Item>
              <Descriptions.Item label="标注结果">
                {currentRecord.result ? (
                  <Tag color={ANNOTATION_RESULT_COLOR[currentRecord.result]}>
                    {ANNOTATION_RESULT_MAP[currentRecord.result]}
                  </Tag>
                ) : (
                  '-'
                )}
              </Descriptions.Item>
              <Descriptions.Item label="标注员">
                {currentRecord.annotator || '-'}
              </Descriptions.Item>
            </Descriptions>
            <Form form={form} layout="vertical">
              <Form.Item
                name="reviewResult"
                label="质检结论"
                rules={[{ required: true, message: '请选择质检结论' }]}
              >
                <Radio.Group>
                  <Radio value="pass">质检通过</Radio>
                  <Radio value="reject">需重新标注</Radio>
                </Radio.Group>
              </Form.Item>
              <Form.Item name="remark" label="质检备注">
                <Input.TextArea rows={3} placeholder="请输入质检备注" />
              </Form.Item>
            </Form>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default QualityCheck;
