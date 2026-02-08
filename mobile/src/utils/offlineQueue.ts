/**
 * Offline queue for mutations when network is unavailable
 * Queues API calls and syncs when connection is restored
 */
import AsyncStorage from '@react-native-async-storage/async-storage';
import NetInfo from '@react-native-community/netinfo';
import {apiClient} from '../api/client';

const QUEUE_STORAGE_KEY = '@offline_queue';

interface QueuedRequest {
  id: string;
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  url: string;
  data?: any;
  timestamp: number;
}

class OfflineQueue {
  private queue: QueuedRequest[] = [];
  private isSyncing = false;
  private isOnline = true;

  constructor() {
    this.initialize();
  }

  private async initialize() {
    // Load queue from storage
    await this.loadQueue();

    // Monitor network status
    NetInfo.addEventListener(state => {
      const wasOffline = !this.isOnline;
      this.isOnline = state.isConnected ?? false;

      // If we just came back online, sync the queue
      if (wasOffline && this.isOnline) {
        this.syncQueue();
      }
    });
  }

  private async loadQueue() {
    try {
      const queueJson = await AsyncStorage.getItem(QUEUE_STORAGE_KEY);
      if (queueJson) {
        this.queue = JSON.parse(queueJson);
      }
    } catch (error) {
      console.error('Failed to load offline queue:', error);
    }
  }

  private async saveQueue() {
    try {
      await AsyncStorage.setItem(QUEUE_STORAGE_KEY, JSON.stringify(this.queue));
    } catch (error) {
      console.error('Failed to save offline queue:', error);
    }
  }

  async addToQueue(
    method: QueuedRequest['method'],
    url: string,
    data?: any
  ): Promise<void> {
    const request: QueuedRequest = {
      id: `${Date.now()}_${Math.random()}`,
      method,
      url,
      data,
      timestamp: Date.now(),
    };

    this.queue.push(request);
    await this.saveQueue();
  }

  async syncQueue(): Promise<void> {
    if (this.isSyncing || !this.isOnline || this.queue.length === 0) {
      return;
    }

    this.isSyncing = true;

    try {
      const failedRequests: QueuedRequest[] = [];

      for (const request of this.queue) {
        try {
          await this.executeRequest(request);
        } catch (error) {
          console.error('Failed to sync request:', error);
          failedRequests.push(request);
        }
      }

      // Keep only failed requests in queue
      this.queue = failedRequests;
      await this.saveQueue();
    } finally {
      this.isSyncing = false;
    }
  }

  private async executeRequest(request: QueuedRequest): Promise<void> {
    switch (request.method) {
      case 'GET':
        await apiClient.get(request.url);
        break;
      case 'POST':
        await apiClient.post(request.url, request.data);
        break;
      case 'PUT':
        await apiClient.put(request.url, request.data);
        break;
      case 'PATCH':
        await apiClient.patch(request.url, request.data);
        break;
      case 'DELETE':
        await apiClient.delete(request.url);
        break;
    }
  }

  getQueueSize(): number {
    return this.queue.length;
  }

  isNetworkOnline(): boolean {
    return this.isOnline;
  }

  async clearQueue(): Promise<void> {
    this.queue = [];
    await this.saveQueue();
  }
}

export const offlineQueue = new OfflineQueue();
