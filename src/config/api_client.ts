// 🚀 Fish Feeder HTTP API Client
// Connects to Flask API Server (http://localhost:5000)

export interface ApiResponse<T> {
  status: 'success' | 'error';
  message?: string;
  data?: T;
  timestamp?: number;
}

export interface SensorData {
  DS18B20_WATER_TEMP?: { values: Array<{ value: number; unit: string; type: string }> };
  BATTERY_STATUS?: { values: Array<{ value: number; unit: string; type: string }> };
  LOAD_VOLTAGE?: { values: Array<{ value: number; unit: string; type: string }> };
  LOAD_CURRENT?: { values: Array<{ value: number; unit: string; type: string }> };
  SOIL_MOISTURE?: { values: Array<{ value: number; unit: string; type: string }> };
  HX711_SCALE_1?: { values: Array<{ value: number; unit: string; type: string }> };
}

export interface RelayStatus {
  led: boolean;
  fan: boolean;
}

export interface SystemHealth {
  status: 'healthy' | 'error';
  uptime: string;
  firebase_connected: boolean;
  serial_connected: boolean;
  response_time_ms: number;
}

export class FishFeederApiClient {
  protected baseUrl: string;
  private timeout: number;

  constructor(baseUrl: string = 'http://localhost:5000', timeout: number = 5000) {
    this.baseUrl = baseUrl;
    this.timeout = timeout;
  }

  // Generic API request with timeout
  protected async apiRequest<T>(
    endpoint: string, 
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      return data as ApiResponse<T>;
    } catch (error) {
      clearTimeout(timeoutId);
      
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error('Request timeout');
      }
      
      throw error;
    }
  }

  // Health check
  async getHealth(): Promise<ApiResponse<SystemHealth>> {
    return this.apiRequest<SystemHealth>('/health');
  }

  // Get all sensor data
  async getSensors(): Promise<ApiResponse<SensorData>> {
    return this.apiRequest<SensorData>('/api/sensors');
  }

  // Get specific sensor
  async getSensor(name: string): Promise<ApiResponse<any>> {
    return this.apiRequest<any>(`/api/sensors/${name}`);
  }

  // Get relay status
  async getRelayStatus(): Promise<ApiResponse<{ relay_status: RelayStatus }>> {
    return this.apiRequest<{ relay_status: RelayStatus }>('/api/relay/status');
  }

  // Control LED
  async controlLED(action: 'on' | 'off' | 'toggle' = 'toggle'): Promise<ApiResponse<{ relay_status: RelayStatus }>> {
    return this.apiRequest<{ relay_status: RelayStatus }>('/api/relay/led', {
      method: 'POST',
      body: JSON.stringify({ action }),
    });
  }

  // Control Fan
  async controlFan(action: 'on' | 'off' | 'toggle' = 'toggle'): Promise<ApiResponse<{ relay_status: RelayStatus }>> {
    return this.apiRequest<{ relay_status: RelayStatus }>('/api/relay/fan', {
      method: 'POST',
      body: JSON.stringify({ action }),
    });
  }

  // Ultra fast control
  async ultraControl(relay_id: number): Promise<ApiResponse<any>> {
    return this.apiRequest<any>('/api/control/ultra', {
      method: 'POST',
      body: JSON.stringify({ relay_id }),
    });
  }

  // Direct command
  async directControl(command: string): Promise<ApiResponse<any>> {
    return this.apiRequest<any>('/api/control/direct', {
      method: 'POST',
      body: JSON.stringify({ command }),
    });
  }

  // Sync sensors manually
  async syncSensors(): Promise<ApiResponse<any>> {
    return this.apiRequest<any>('/api/sensors/sync', {
      method: 'POST',
    });
  }

  // Check if API is reachable
  async ping(): Promise<boolean> {
    try {
      const response = await this.getHealth();
      return response.status === 'success';
    } catch {
      return false;
    }
  }
}

// Export singleton instance
export const apiClient = new FishFeederApiClient();

// Auto-detect API server
export const detectApiServer = async (): Promise<string> => {
  const servers = [
    'http://localhost:5000',
    'http://127.0.0.1:5000',
    'http://192.168.1.100:5000', // Common Pi IP
    'http://192.168.0.100:5000',
  ];

  for (const server of servers) {
    try {
      const client = new FishFeederApiClient(server, 2000);
      const isReachable = await client.ping();
      if (isReachable) {
        console.log(`🎯 API Server detected: ${server}`);
        return server;
      }
    } catch {
      // Continue trying
    }
  }

  console.warn('⚠️ No API server detected, using default');
  return 'http://localhost:5000';
};

// Enhanced API client with auto-detection
export class EnhancedApiClient extends FishFeederApiClient {
  private isAutoDetected = false;

  async autoConnect(): Promise<boolean> {
    if (this.isAutoDetected) return true;

    try {
      const detectedUrl = await detectApiServer();
      this.baseUrl = detectedUrl;
      this.isAutoDetected = true;
      return true;
    } catch {
      return false;
    }
  }

  // Override apiRequest to auto-connect first
  protected async apiRequest<T>(endpoint: string, options: RequestInit = {}): Promise<ApiResponse<T>> {
    if (!this.isAutoDetected) {
      await this.autoConnect();
    }
    return super.apiRequest(endpoint, options);
  }
}

// Export enhanced client as default
export const enhancedApiClient = new EnhancedApiClient();
export default enhancedApiClient; 