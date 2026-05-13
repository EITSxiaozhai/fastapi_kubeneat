import { request } from '@umijs/max';

export type NeatTaskStatus = {
  task_id: string;
  status: 'PENDING' | 'STARTED' | 'PROGRESS' | 'SUCCESS' | 'FAILURE' | string;
  progress?: {
    current: number;
    total: number;
    message: string;
  };
  result?: {
    original_filename: string;
    resource_count: number;
    result_filename: string;
    download_url: string;
    message: string;
  };
  error?: string;
};

export async function uploadNeatYaml(file: File) {
  const formData = new FormData();
  formData.append('file', file);

  return request<{ task_id: string; status: string }>('/api/neat/upload', {
    method: 'POST',
    data: formData,
  });
}

export async function getNeatTask(taskId: string) {
  return request<NeatTaskStatus>(`/api/neat/tasks/${taskId}`, {
    method: 'GET',
  });
}
