import React, { useEffect, useState } from 'react';
import { Table, Button, Modal, Form, Input, Radio, Tag, message, Card, Image, Space } from 'antd';
import { PlusOutlined, EditOutlined } from '@ant-design/icons';
import { annotationApi } from '../services/api';
import { Annotation, AnnotationType, AnnotationResult, AnnotationStatus } from '../types';
import { ANNOTATION_RESULT_MAP, ANNOTATION_RESULT_COLOR, ANNOTATION_STATUS_MAP, ANNOTATION_STATUS_COLOR } from '../utils/enumMaps';
import dayjs from 'dayjs';

const ImageAnnotation: React.FC = () => {
  const [data, setData] = useState<Annotation[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRecord, setEditingRecord] = useState<Annotation | null>(null);
  const [form] = Form.useForm();

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await annotationApi.getList(AnnotationType.IMAGE);
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

  const handleAdd = () => {
    setEditingRecord(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (record: Annotation) => {
    setEditingRecord(record);
    form.setFieldsValue({
      imageUrl: record.imageUrl,
      content: record.content,
      result: record.result,
      tags: record.tags,
      remark: record.remark,
    });
    setModalVisible(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editingRecord) {
        await annotationApi.update(editingRecord.id, {
          result: values.result,
          tags: values.tags,
          remark: values.remark,
          annotator: '标注员A',
        });
        message.success('更新成功');
      } else {
        await annotationApi.createImage({
          type: AnnotationType.IMAGE,
          imageUrl: values.imageUrl,
          content: values.content,
          result: values.result,
          tags: values.tags,
          remark: values.remark,
          annotator: '标注员A',
        });
        message.success('保存成功');
      }
      setModalVisible(false);
      fetchData();
    } catch (e) {
      console.error(e);
    }
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 80,
    },
    {
      title: '图片',
      dataIndex: 'imageUrl',
      width: 140,
      render: (url: string) => (
        <Image width={100} height={80} src={url} style={{ objectFit: 'cover' }} />
      ),
    },
    {
      title: '图片描述',
      dataIndex: 'content',
      ellipsis: true,
      render: (text?: string) => text || '-',
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
      title: '标注时间',
      dataIndex: 'updatedAt',
      width: 180,
      render: (t: string) => dayjs(t).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_: any, record: Annotation) => (
        <Button type="link" icon={<EditOutlined />} onClick={() => handleEdit(record)}>
          标注
        </Button>
      ),
    },
  ];

  return (
    <div>
      <Card
        title="图片标注任务"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            新建图片任务
          </Button>
        }
      >
        <Table
          rowKey="id"
          columns={columns}
          dataSource={data}
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <Modal
        title={editingRecord ? '编辑图片标注' : '新建图片标注任务'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        width={600}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          {editingRecord && editingRecord.remark && editingRecord.reviewer && (
            <div style={{ marginBottom: 16, padding: 12, backgroundColor: '#fff7e6', border: '1px solid #ffd591', borderRadius: 4 }}>
              <div style={{ fontWeight: 'bold', color: '#d46b08', marginBottom: 4 }}>
                质检驳回原因：
              </div>
              <div style={{ color: '#873800' }}>{editingRecord.remark}</div>
            </div>
          )}
          {editingRecord && editingRecord.imageUrl && (
            <Form.Item label="当前图片">
              <Image width={200} src={editingRecord.imageUrl} />
            </Form.Item>
          )}
          <Form.Item
            name="imageUrl"
            label="图片 URL"
            rules={[
              { required: !editingRecord, message: '请输入图片 URL' },
              { type: 'url', message: '请输入有效的 URL' },
            ]}
          >
            <Input
              placeholder="请输入图片 URL，如：https://example.com/image.jpg"
              disabled={!!editingRecord}
            />
          </Form.Item>
          <Form.Item name="content" label="图片描述">
            <Input placeholder="请输入图片描述（可选）" disabled={!!editingRecord} />
          </Form.Item>
          <Form.Item
            name="result"
            label="标注结果"
            rules={[{ required: true, message: '请选择标注结果' }]}
          >
            <Radio.Group>
              <Radio value={AnnotationResult.PASS}>通过</Radio>
              <Radio value={AnnotationResult.SUSPICIOUS}>疑似违规</Radio>
              <Radio value={AnnotationResult.VIOLATION}>违规</Radio>
            </Radio.Group>
          </Form.Item>
          <Form.Item name="tags" label="标签">
            <Input placeholder="多个标签用逗号分隔，如：色情,暴力" />
          </Form.Item>
          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={2} placeholder="请输入备注信息" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ImageAnnotation;
