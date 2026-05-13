import {
  CloudUploadOutlined,
  DownloadOutlined,
  FileDoneOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import { PageContainer } from '@ant-design/pro-components';
import { Button, Progress, Space, Typography, Upload, message, theme } from 'antd';
import type { UploadProps } from 'antd';
import { useEffect, useRef, useState } from 'react';
import { getNeatTask, uploadNeatYaml, type NeatTaskStatus } from '@/services/kubeneat';
import './style.less';

const { Dragger } = Upload;
const { Text, Title } = Typography;

const isDone = (status?: string) => status === 'SUCCESS' || status === 'FAILURE';

const KubeneatPage = () => {
  const { token } = theme.useToken();
  const [task, setTask] = useState<NeatTaskStatus>();
  const [uploading, setUploading] = useState(false);
  const timerRef = useRef<number>();

  const stopPolling = () => {
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = undefined;
    }
  };

  const pollTask = (taskId: string) => {
    stopPolling();
    timerRef.current = window.setInterval(async () => {
      const latest = await getNeatTask(taskId);
      setTask(latest);
      if (isDone(latest.status)) {
        stopPolling();
      }
    }, 1200);
  };

  useEffect(() => stopPolling, []);

  const handleUpload: UploadProps['customRequest'] = async (options) => {
    const file = options.file as File;
    setUploading(true);
    setTask(undefined);

    try {
      const created = await uploadNeatYaml(file);
      const firstState = await getNeatTask(created.task_id);
      setTask(firstState);
      pollTask(created.task_id);
      options.onSuccess?.(created);
    } catch (error) {
      message.error('上传或创建任务失败');
      options.onError?.(error as Error);
    } finally {
      setUploading(false);
    }
  };

  const progressPercent = task?.progress
    ? Math.round((task.progress.current / task.progress.total) * 100)
    : task?.status === 'SUCCESS'
      ? 100
      : task?.status === 'FAILURE'
        ? 100
        : task
          ? 8
          : 0;

  return (
    <PageContainer title="kubectl-neat YAML 精简">
      <div className="kubeneat-shell">
        <section className="kubeneat-uploader">
          <Title level={3}>上传 Kubernetes YAML</Title>
          <Text type="secondary">
            支持包含多个资源的 YAML 文档流，后端会按 <Text code>---</Text> 拆分后逐个精简。
          </Text>
          <Dragger
            accept=".yaml,.yml"
            maxCount={1}
            customRequest={handleUpload}
            showUploadList={false}
            disabled={uploading || (!!task && !isDone(task.status))}
            className="kubeneat-dropzone"
          >
            <CloudUploadOutlined className="kubeneat-upload-icon" style={{ color: token.colorPrimary }} />
            <p className="ant-upload-text">点击或拖拽 YAML 文件到此处</p>
            <p className="ant-upload-hint">上传后将立即创建 Celery 后台任务</p>
          </Dragger>
        </section>

        <section className="kubeneat-status-panel">
          <Space direction="vertical" size={16} className="kubeneat-status-content">
            <Space>
              {task?.status === 'SUCCESS' ? (
                <FileDoneOutlined style={{ color: token.colorSuccess }} />
              ) : (
                <LoadingOutlined spin={!!task && !isDone(task.status)} />
              )}
              <Text strong>{task ? `任务状态：${task.status}` : '等待上传文件'}</Text>
            </Space>

            <Progress
              percent={progressPercent}
              status={task?.status === 'FAILURE' ? 'exception' : task?.status === 'SUCCESS' ? 'success' : 'active'}
            />

            {task?.progress && <Text>{task.progress.message}</Text>}
            {task?.error && <Text type="danger">{task.error}</Text>}

            {task?.result && (
              <Space direction="vertical">
                <Text>资源数量：{task.result.resource_count}</Text>
                <Text>结果文件：{task.result.result_filename}</Text>
                <Button type="primary" icon={<DownloadOutlined />} href={task.result.download_url}>
                  下载精简结果
                </Button>
              </Space>
            )}
          </Space>
        </section>
      </div>
    </PageContainer>
  );
};

export default KubeneatPage;
