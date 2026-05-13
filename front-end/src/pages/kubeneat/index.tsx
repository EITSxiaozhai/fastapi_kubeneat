import {
  CloudUploadOutlined,
  DownloadOutlined,
  FileDoneOutlined,
  FileTextOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import { PageContainer } from '@ant-design/pro-components';
import {
  Button,
  Input,
  Progress,
  Segmented,
  Space,
  Typography,
  Upload,
  message,
  theme,
} from 'antd';
import type { UploadFile, UploadProps } from 'antd';
import { useEffect, useRef, useState } from 'react';
import { getNeatTask, submitNeatYaml, uploadNeatYaml, type NeatTaskStatus } from '@/services/kubeneat';
import './style.less';

const { Dragger } = Upload;
const { Text, Title } = Typography;
const { TextArea } = Input;

const isDone = (status?: string) => status === 'SUCCESS' || status === 'FAILURE';

type SubmitMode = 'upload' | 'manual';

const KubeneatPage = () => {
  const { token } = theme.useToken();
  const [mode, setMode] = useState<SubmitMode>('upload');
  const [task, setTask] = useState<NeatTaskStatus>();
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<UploadFile | undefined>();
  const [manualFilename, setManualFilename] = useState('manual-input.yaml');
  const [manualYaml, setManualYaml] = useState('');
  const timerRef = useRef<number>();

  const hasStatusPanel = !!task;
  const busy = uploading || (!!task && !isDone(task.status));

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

  const startTaskTracking = async (taskId: string) => {
    const firstState = await getNeatTask(taskId);
    setTask(firstState);
    pollTask(taskId);
  };

  const normalizeFilename = (filename: string) => {
    const trimmed = filename.trim() || 'manual-input.yaml';
    return /\.(yaml|yml)$/i.test(trimmed) ? trimmed : `${trimmed}.yaml`;
  };

  const handleSubmitFile = async () => {
    const file = selectedFile?.originFileObj;
    if (!file) {
      message.warning('Select a YAML file first.');
      return;
    }

    setUploading(true);
    setTask(undefined);

    try {
      const created = await uploadNeatYaml(file);
      await startTaskTracking(created.task_id);
      message.success('File submitted. Processing has started.');
    } catch (error) {
      message.error('File submission failed.');
      setTask({
        task_id: '',
        status: 'FAILURE',
        error: (error as Error).message || 'File submission failed.',
      });
    } finally {
      setUploading(false);
    }
  };

  const handleSubmitManualYaml = async () => {
    if (!manualYaml.trim()) {
      message.warning('Paste YAML content first.');
      return;
    }

    setUploading(true);
    setTask(undefined);

    try {
      const created = await submitNeatYaml(manualYaml, normalizeFilename(manualFilename));
      await startTaskTracking(created.task_id);
      message.success('YAML content submitted. Processing has started.');
    } catch (error) {
      message.error('YAML submission failed.');
      setTask({
        task_id: '',
        status: 'FAILURE',
        error: (error as Error).message || 'YAML submission failed.',
      });
    } finally {
      setUploading(false);
    }
  };

  const uploadProps: UploadProps = {
    accept: '.yaml,.yml',
    maxCount: 1,
    beforeUpload: (file) => {
      setSelectedFile(file as UploadFile);
      return false;
    },
    onRemove: () => {
      setSelectedFile(undefined);
    },
    fileList: selectedFile ? [selectedFile] : [],
    showUploadList: true,
    disabled: busy,
  };

  const progressPercent = task?.progress
    ? Math.round((task.progress.current / task.progress.total) * 100)
    : task?.status === 'SUCCESS' || task?.status === 'FAILURE'
      ? 100
      : task
        ? 8
        : 0;

  return (
    <PageContainer title="kubectl-neat YAML cleanup">
      <div className={`kubeneat-shell${hasStatusPanel ? ' kubeneat-shell--with-status' : ''}`}>
        <section className="kubeneat-uploader">
          <Space direction="vertical" size={20} className="kubeneat-form-stack">
            <div>
              <Title level={3}>Submit Kubernetes YAML</Title>
              <Text type="secondary">
                Upload a YAML file or paste raw Kubernetes YAML. The task card stays hidden until a submission is sent.
              </Text>
            </div>

            <Segmented<SubmitMode>
              block
              value={mode}
              onChange={(value) => setMode(value)}
              options={[
                { label: 'File upload', value: 'upload' },
                { label: 'Manual input', value: 'manual' },
              ]}
            />

            {mode === 'upload' ? (
              <Space direction="vertical" size={16} className="kubeneat-form-stack">
                <Dragger {...uploadProps} className="kubeneat-dropzone">
                  <CloudUploadOutlined className="kubeneat-upload-icon" style={{ color: token.colorPrimary }} />
                  <p className="ant-upload-text">Click or drag a YAML file here</p>
                  <p className="ant-upload-hint">Selecting a file does not submit it. Use the button below to start.</p>
                </Dragger>

                <Button
                  type="primary"
                  size="large"
                  onClick={handleSubmitFile}
                  loading={uploading && mode === 'upload'}
                  disabled={busy || !selectedFile}
                >
                  Submit file
                </Button>
              </Space>
            ) : (
              <Space direction="vertical" size={16} className="kubeneat-form-stack">
                <Input
                  value={manualFilename}
                  onChange={(event) => setManualFilename(event.target.value)}
                  placeholder="Output filename, for example deployment.yaml"
                  prefix={<FileTextOutlined />}
                  disabled={busy}
                />
                <TextArea
                  value={manualYaml}
                  onChange={(event) => setManualYaml(event.target.value)}
                  placeholder="Paste Kubernetes YAML here"
                  autoSize={{ minRows: 14, maxRows: 22 }}
                  disabled={busy}
                />
                <Button
                  type="primary"
                  size="large"
                  onClick={handleSubmitManualYaml}
                  loading={uploading && mode === 'manual'}
                  disabled={busy || !manualYaml.trim()}
                >
                  Submit YAML
                </Button>
              </Space>
            )}
          </Space>
        </section>

        {hasStatusPanel && (
          <section className="kubeneat-status-panel">
            <Space direction="vertical" size={16} className="kubeneat-status-content">
              <Space>
                {task?.status === 'SUCCESS' ? (
                  <FileDoneOutlined style={{ color: token.colorSuccess }} />
                ) : (
                  <LoadingOutlined spin={!!task && !isDone(task.status)} />
                )}
                <Text strong>{`Task status: ${task.status}`}</Text>
              </Space>

              <Progress
                percent={progressPercent}
                status={task?.status === 'FAILURE' ? 'exception' : task?.status === 'SUCCESS' ? 'success' : 'active'}
              />

              {task?.progress && <Text>{task.progress.message}</Text>}
              {task?.error && <Text type="danger">{task.error}</Text>}

              {task?.result && (
                <Space direction="vertical">
                  <Text>{`Original file: ${task.result.original_filename}`}</Text>
                  <Text>{`Resource count: ${task.result.resource_count}`}</Text>
                  <Text>{`Result file: ${task.result.result_filename}`}</Text>
                  <Button type="primary" icon={<DownloadOutlined />} href={task.result.download_url}>
                    Download result
                  </Button>
                </Space>
              )}
            </Space>
          </section>
        )}
      </div>
    </PageContainer>
  );
};

export default KubeneatPage;
