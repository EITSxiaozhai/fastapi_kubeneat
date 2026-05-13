import { DownloadOutlined, ReloadOutlined } from '@ant-design/icons';
import { PageContainer } from '@ant-design/pro-components';
import { useQuery } from '@tanstack/react-query';
import { Button, Card, Space, Table, Tag, Tooltip, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import { listNeatTasks, type NeatTaskStatus } from '@/services/kubeneat';

dayjs.extend(relativeTime);

const { Text } = Typography;

const statusColorMap: Record<string, string> = {
  PENDING: 'gold',
  STARTED: 'blue',
  PROGRESS: 'processing',
  SUCCESS: 'success',
  FAILURE: 'error',
};

const columns: ColumnsType<NeatTaskStatus> = [
  {
    title: 'Task ID',
    dataIndex: 'task_id',
    key: 'task_id',
    width: 360,
    render: (value: string) => (
      <Text
        code
        copyable
        style={{ wordBreak: 'break-all', whiteSpace: 'normal', display: 'inline-block' }}
      >
        {value}
      </Text>
    ),
  },
  {
    title: 'Source file',
    dataIndex: 'original_filename',
    key: 'original_filename',
    ellipsis: true,
    render: (value?: string) => value || '-',
  },
  {
    title: 'Submit type',
    dataIndex: 'submission_type',
    key: 'submission_type',
    width: 160,
    render: (value?: string) => {
      if (value === 'manual') {
        return <Tag color="purple">Manual paste</Tag>;
      }
      if (value === 'file') {
        return <Tag color="cyan">File upload</Tag>;
      }
      return <Text type="secondary">Unknown</Text>;
    },
  },
  {
    title: 'Status',
    dataIndex: 'status',
    key: 'status',
    width: 130,
    render: (value: string) => <Tag color={statusColorMap[value] || 'default'}>{value}</Tag>,
  },
  {
    title: 'Progress',
    key: 'progress',
    width: 220,
    render: (_, record) => {
      if (record.progress) {
        return `${record.progress.current}/${record.progress.total} ${record.progress.message}`;
      }
      if (record.error) {
        return (
          <Tooltip title={record.error}>
            <Text type="danger" ellipsis>
              {record.error}
            </Text>
          </Tooltip>
        );
      }
      if (record.result?.message) {
        return record.result.message;
      }
      return '-';
    },
  },
  {
    title: 'Created',
    dataIndex: 'created_at',
    key: 'created_at',
    width: 180,
    render: (value?: string) => (value ? dayjs(value).format('YYYY-MM-DD HH:mm:ss') : '-'),
  },
  {
    title: 'Actions',
    key: 'actions',
    width: 150,
    render: (_, record) =>
      record.result?.download_url ? (
        <Button type="link" icon={<DownloadOutlined />} href={record.result.download_url}>
          Download
        </Button>
      ) : (
        <Text type="secondary">Unavailable</Text>
      ),
  },
];

const DashboardTasksPage = () => {
  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['neat-task-list'],
    queryFn: listNeatTasks,
    refetchInterval: 3000,
  });

  return (
    <PageContainer
      title="Task Center"
      extra={[
        <Button key="refresh" icon={<ReloadOutlined />} loading={isFetching} onClick={() => refetch()}>
          Refresh
        </Button>,
      ]}
    >
      <Card bordered={false}>
        <Space direction="vertical" size={16} style={{ width: '100%' }}>
          <Text type="secondary">
            Review all submitted YAML cleanup tasks, track execution status, and download completed outputs.
          </Text>

          <Table<NeatTaskStatus>
            rowKey="task_id"
            columns={columns}
            dataSource={data?.items || []}
            loading={isLoading}
            pagination={{
              pageSize: 10,
              showSizeChanger: false,
              showTotal: (total) => `Total ${total} tasks`,
            }}
            scroll={{ x: 1320 }}
          />
        </Space>
      </Card>
    </PageContainer>
  );
};

export default DashboardTasksPage;
