import {
  ClearOutlined,
  CloudUploadOutlined,
  CopyOutlined,
  DownloadOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { DiffEditor, Editor } from '@monaco-editor/react';
import type { Monaco } from '@monaco-editor/react';
import { PageContainer } from '@ant-design/pro-components';
import { Button, Input, Modal, Progress, Segmented, Space, Typography, Upload, message, notification } from 'antd';
import type { UploadFile, UploadProps } from 'antd';
import type { RcFile } from 'antd/es/upload';
import { configureMonacoYaml } from 'monaco-yaml';
import { useEffect, useRef, useState } from 'react';
import { getNeatTask, submitNeatYaml, uploadNeatYaml, type NeatTaskStatus } from '@/services/kubeneat';
import './style.less';

const { Dragger } = Upload;
const { Text, Title } = Typography;

const isDone = (status?: string) => status === 'SUCCESS' || status === 'FAILURE';

type SubmitMode = 'upload' | 'manual';

const editorOptions = {
  automaticLayout: true,
  fontSize: 13,
  lineNumbersMinChars: 3,
  minimap: { enabled: false },
  padding: { top: 16, bottom: 16 },
  scrollBeyondLastLine: false,
  tabSize: 2,
  wordWrap: 'on' as const,
};

const diffEditorOptions = {
  ...editorOptions,
  enableSplitViewResizing: true,
  originalEditable: false,
  readOnly: true,
  renderSideBySide: true,
};

let yamlConfigured = false;

const setupMonacoYaml = (monaco: Monaco) => {
  if (yamlConfigured) {
    return;
  }

  configureMonacoYaml(monaco, {
    completion: true,
    enableSchemaRequest: false,
    format: {},
    hover: true,
    schemas: [],
    validate: true,
  });

  yamlConfigured = true;
};

const KubeneatPage = () => {
  const [notificationApi, notificationContextHolder] = notification.useNotification();
  const [mode, setMode] = useState<SubmitMode>('upload');
  const [task, setTask] = useState<NeatTaskStatus | undefined>(undefined);
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<UploadFile | undefined>();
  const [selectedRawFile, setSelectedRawFile] = useState<RcFile | undefined>();
  const [selectedYaml, setSelectedYaml] = useState('');
  const [manualFilename, setManualFilename] = useState('manual-input.yaml');
  const [manualYaml, setManualYaml] = useState('');
  const timerRef = useRef<number | undefined>(undefined);
  const notifiedTaskKeyRef = useRef<string | undefined>(undefined);

  const hasResult = !!task?.result?.result_content;
  const busy = uploading || (!!task && !isDone(task.status));
  const canClear = !!task || !!manualYaml.trim() || !!selectedFile;
  const originalYaml = mode === 'manual'
    ? manualYaml
    : selectedYaml || task?.result?.original_content || '';
  const resultYaml = task?.result?.result_content || '';

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

  useEffect(() => {
    if (!task || !isDone(task.status)) {
      return;
    }

    const notificationKey = `${task.task_id}:${task.status}`;
    if (notifiedTaskKeyRef.current === notificationKey) {
      return;
    }
    notifiedTaskKeyRef.current = notificationKey;

    if (task.status === 'SUCCESS' && task.result) {
      notificationApi.success({
        key: notificationKey,
        message: 'YAML cleanup completed',
        duration: 6,
        description: (
          <Space direction="vertical" size={4}>
            <Text>{`Original file: ${task.result.original_filename}`}</Text>
            <Text>{`Resource count: ${task.result.resource_count}`}</Text>
            <Text>{`Result file: ${task.result.result_filename}`}</Text>
          </Space>
        ),
        btn: (
          <Button size="small" type="primary" icon={<DownloadOutlined />} href={task.result.download_url}>
            Download
          </Button>
        ),
      });
      return;
    }

    if (task.status === 'FAILURE') {
      notificationApi.error({
        key: notificationKey,
        message: 'YAML cleanup failed',
        duration: 6,
        description: task.error || 'The background task finished with an error.',
      });
    }
  }, [notificationApi, task]);

  const startTaskTracking = async (taskId: string) => {
    const firstState = await getNeatTask(taskId);
    setTask(firstState);
    pollTask(taskId);
  };

  const normalizeFilename = (filename: string) => {
    const trimmed = filename.trim() || 'manual-input.yaml';
    return /\.(yaml|yml)$/i.test(trimmed) ? trimmed : `${trimmed}.yaml`;
  };

  const clearWorkspaceState = () => {
    stopPolling();
    setUploading(false);
    setTask(undefined);
    notifiedTaskKeyRef.current = undefined;
    setSelectedFile(undefined);
    setSelectedRawFile(undefined);
    setSelectedYaml('');
    setManualFilename('manual-input.yaml');
    setManualYaml('');
  };

  const handleClearWorkspace = () => {
    clearWorkspaceState();
    message.success('已清空，可以重新粘贴或上传 YAML。');
  };

  const handleModeChange = (nextMode: SubmitMode) => {
    if (nextMode === mode) {
      return;
    }

    if (!hasResult) {
      setMode(nextMode);
      return;
    }

    Modal.confirm({
      title: '切换会造成当前页面数据丢失',
      content: '当前 YAML 精简结果和对比内容会被清空，确认要切换吗？',
      okText: '确认切换',
      cancelText: '取消',
      onOk: () => {
        clearWorkspaceState();
        setMode(nextMode);
      },
    });
  };

  const handleSubmitFile = async () => {
    const file = selectedRawFile;
    if (!file) {
      message.warning('Select a YAML file first.');
      return;
    }

    setUploading(true);
    setTask(undefined);
    notifiedTaskKeyRef.current = undefined;

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
    notifiedTaskKeyRef.current = undefined;

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

  const handleCopyResult = async () => {
    const resultContent = task?.result?.result_content;
    if (!resultContent) {
      return;
    }

    await navigator.clipboard.writeText(resultContent);
    message.success('Result YAML copied.');
  };

  const uploadProps: UploadProps = {
    accept: '.yaml,.yml',
    maxCount: 1,
    beforeUpload: (file) => {
      setSelectedRawFile(file);
      void file.text().then((content) => setSelectedYaml(content));
      setSelectedFile({
        uid: file.uid,
        name: file.name,
        size: file.size,
        type: file.type,
        status: 'done',
        originFileObj: file,
      });
      return false;
    },
    onRemove: () => {
      setSelectedFile(undefined);
      setSelectedRawFile(undefined);
      setSelectedYaml('');
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

  const renderResultCompare = (inputTitle: string) => (
    <div className="kubeneat-compare-pane">
      <div className="kubeneat-compare-pane__header">
        <Text strong>{inputTitle} / Cleaned YAML diff</Text>
        <Space>
          <Button type="primary" icon={<DownloadOutlined />} href={task?.result?.download_url}>
            Download file
          </Button>
          <Button icon={<CopyOutlined />} onClick={handleCopyResult}>
            Copy result
          </Button>
          <Button icon={<ClearOutlined />} onClick={handleClearWorkspace} disabled={uploading}>
            清空
          </Button>
        </Space>
      </div>
      <div className="monaco-shell">
        <DiffEditor
          beforeMount={setupMonacoYaml}
          height="560px"
          original={originalYaml}
          modified={resultYaml}
          language="yaml"
          theme="vs-dark"
          options={diffEditorOptions}
        />
      </div>
    </div>
  );

  return (
    <>
      {notificationContextHolder}
      <PageContainer title="在线 kubectl-neat YAML 清理">
        <section className="kubeneat-workspace">
          <Space direction="vertical" size={20} className="kubeneat-form-stack">
            <div>
              <Title level={3}>提交你的 Kubernetes 资源 YAML,请删除敏感信息如域名,AK SK明文</Title>
              <Text type="secondary">
                上传或者粘贴符合k8s的部署yaml,将会自动调用kube-neat进行清理,支持多个以 --- 分割的部署文件。
              </Text>
              <text>可自行下载本地部署使用,可以自己替换已经有的kubeneat的二进制文件,源代码链接:</text>
              <a>https://github.com/EITSxiaozhai/fastapi_kubeneat</a>
            </div>

            <Segmented<SubmitMode>
              block
              value={mode}
              onChange={handleModeChange}
              options={[
                { label: 'File upload', value: 'upload' },
                { label: 'Manual input', value: 'manual' },
              ]}
            />

            {mode === 'upload' ? (
              <Space direction="vertical" size={16} className="kubeneat-form-stack">
                <Dragger {...uploadProps} className="kubeneat-dropzone">
                  <CloudUploadOutlined className="kubeneat-upload-icon" />
                  <p className="ant-upload-text">Click or drag a YAML file here</p>
                  <p className="ant-upload-hint">Selecting a file does not submit it. Use the button below to start.</p>
                </Dragger>

                <Space size={12} wrap>
                  <Button
                    type="primary"
                    size="large"
                    onClick={handleSubmitFile}
                    loading={uploading && mode === 'upload'}
                    disabled={busy || !selectedFile}
                  >
                    Submit file
                  </Button>
                  <Button
                    size="large"
                    icon={<ClearOutlined />}
                    onClick={handleClearWorkspace}
                    disabled={uploading || !canClear}
                  >
                    清空
                  </Button>
                </Space>

                {hasResult && (
                  <div className="kubeneat-compare-grid">{renderResultCompare('Original YAML')}</div>
                )}
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
                <div className="kubeneat-compare-grid">
                  {hasResult ? renderResultCompare('Input YAML') : (
                    <div className="kubeneat-compare-pane">
                      <div className="kubeneat-compare-pane__header">
                        <Text strong>Input YAML</Text>
                      </div>
                      <div className="monaco-shell monaco-shell--input">
                        <Editor
                          beforeMount={setupMonacoYaml}
                          height="420px"
                          defaultLanguage="yaml"
                          language="yaml"
                          theme="vs-dark"
                          value={manualYaml}
                          options={{
                            ...editorOptions,
                            readOnly: busy,
                          }}
                          onChange={(value) => setManualYaml(value ?? '')}
                        />
                      </div>
                    </div>
                  )}
                </div>
                <Space size={12} wrap>
                  <Button
                    type="primary"
                    size="large"
                    onClick={handleSubmitManualYaml}
                    loading={uploading && mode === 'manual'}
                    disabled={busy || !manualYaml.trim()}
                  >
                    Submit YAML
                  </Button>
                  <Button
                    size="large"
                    icon={<ClearOutlined />}
                    onClick={handleClearWorkspace}
                    disabled={uploading || !canClear}
                  >
                    清空
                  </Button>
                </Space>
              </Space>
            )}

            {!!task && (
              <div className="kubeneat-inline-status">
                <Space direction="vertical" size={10} className="kubeneat-form-stack">
                  <Text strong>{`Task status: ${task.status}`}</Text>
                  <Progress
                    percent={progressPercent}
                    status={task.status === 'FAILURE' ? 'exception' : task.status === 'SUCCESS' ? 'success' : 'active'}
                  />
                  {task.progress && <Text>{task.progress.message}</Text>}
                  {task.error && <Text type="danger">{task.error}</Text>}
                </Space>
              </div>
            )}

          </Space>
        </section>
      </PageContainer>
    </>
  );
};

export default KubeneatPage;
