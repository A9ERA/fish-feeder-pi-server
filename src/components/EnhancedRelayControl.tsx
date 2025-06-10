import React, { useState, useCallback, useEffect, useRef } from 'react';
import { FaLightbulb, FaFan, FaRocket, FaWifi, FaServer } from 'react-icons/fa';
import { BsLightningFill, BsSpeedometer2 } from 'react-icons/bs';
import { MdNetworkCheck } from 'react-icons/md';

// Import both clients
import { firebaseClient, FirebaseStatus, FirebaseRelayStatus } from '../config/firebase';
import { enhancedApiClient, RelayStatus } from '../config/api_client';

interface EnhancedRelayControlProps {
  className?: string;
}

type ConnectionMode = 'firebase' | 'http' | 'auto';

const EnhancedRelayControl: React.FC<EnhancedRelayControlProps> = ({ className = '' }) => {
  const [relayStatus, setRelayStatus] = useState<RelayStatus>({ led: false, fan: false });
  const [loading, setLoading] = useState<{ led: boolean; fan: boolean }>({ led: false, fan: false });
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<number>(0);
  
  // Connection status
  const [connectionMode, setConnectionMode] = useState<ConnectionMode>('auto');
  const [firebaseOnline, setFirebaseOnline] = useState<boolean>(false);
  const [httpOnline, setHttpOnline] = useState<boolean>(false);
  const [responseTime, setResponseTime] = useState<string>('~100');
  
  // Prevent double-submit
  const isSubmittingRef = useRef<{ led: boolean; fan: boolean }>({ led: false, fan: false });
  const unsubscribeRef = useRef<(() => void) | null>(null);

  // Auto-detect best connection method
  const detectConnection = useCallback(async () => {
    console.log('🔍 Detecting best connection method...');
    
    try {
      // Test HTTP API
      const httpReachable = await enhancedApiClient.ping();
      setHttpOnline(httpReachable);
      
      if (httpReachable) {
        console.log('✅ HTTP API detected and working');
        setConnectionMode('http');
        return 'http';
      }
    } catch {
      setHttpOnline(false);
    }

    try {
      // Test Firebase
      const firebaseReachable = await firebaseClient.isSystemOnline();
      setFirebaseOnline(firebaseReachable);
      
      if (firebaseReachable) {
        console.log('✅ Firebase detected and working');
        setConnectionMode('firebase');
        return 'firebase';
      }
    } catch {
      setFirebaseOnline(false);
    }

    console.warn('⚠️ No connection method available');
    setConnectionMode('firebase'); // Default fallback
    return null;
  }, []);

  // Setup Firebase listener
  const setupFirebaseListener = useCallback(() => {
    if (unsubscribeRef.current) {
      unsubscribeRef.current();
    }

    unsubscribeRef.current = firebaseClient.getStatus((status: FirebaseStatus | null) => {
      if (status?.relay) {
        setRelayStatus(status.relay);
        setLastUpdate(Date.now());
        setFirebaseOnline(status.online || false);
        setResponseTime(status.response_time_ms || '~100');
        setError(null);
      } else {
        setFirebaseOnline(false);
      }
    });
  }, []);

  // HTTP Status polling
  const pollHttpStatus = useCallback(async () => {
    try {
      const response = await enhancedApiClient.getRelayStatus();
      if (response.status === 'success' && response.data?.relay_status) {
        setRelayStatus(response.data.relay_status);
        setLastUpdate(Date.now());
        setHttpOnline(true);
        setError(null);
      }
    } catch (err) {
      setHttpOnline(false);
      console.error('HTTP polling failed:', err);
    }
  }, []);

  // Universal relay control - uses best available method
  const controlRelay = useCallback(async (
    type: 'led' | 'fan',
    action: 'on' | 'off' | 'toggle' = 'toggle'
  ) => {
    if (isSubmittingRef.current[type]) {
      console.log(`⚠️ ${type.toUpperCase()} control already in progress`);
      return;
    }

    try {
      isSubmittingRef.current[type] = true;
      setLoading(prev => ({ ...prev, [type]: true }));
      setError(null);

      const startTime = Date.now();
      let success = false;

      // Try HTTP first (faster)
      if (httpOnline && (connectionMode === 'http' || connectionMode === 'auto')) {
        try {
          console.log(`🚀 HTTP controlling ${type.toUpperCase()}: ${action}`);
          const response = type === 'led'
            ? await enhancedApiClient.controlLED(action)
            : await enhancedApiClient.controlFan(action);
          
          if (response.status === 'success' && response.data?.relay_status) {
            setRelayStatus(response.data.relay_status);
            success = true;
            const elapsed = Date.now() - startTime;
            setResponseTime(`${elapsed}`);
            console.log(`✅ HTTP ${type.toUpperCase()} control success (${elapsed}ms)`);
          }
        } catch (httpErr) {
          console.warn(`⚠️ HTTP failed, trying Firebase...`);
          setHttpOnline(false);
        }
      }

      // Fallback to Firebase
      if (!success && (connectionMode === 'firebase' || connectionMode === 'auto')) {
        try {
          console.log(`🔥 Firebase controlling ${type.toUpperCase()}: ${action}`);
          const firebaseSuccess = type === 'led'
            ? await firebaseClient.controlLED(action)
            : await firebaseClient.controlFan(action);
          
          if (firebaseSuccess) {
            success = true;
            const elapsed = Date.now() - startTime;
            setResponseTime(`~${elapsed}`);
            console.log(`✅ Firebase ${type.toUpperCase()} control success (~${elapsed}ms)`);
          }
        } catch (firebaseErr) {
          console.error(`❌ Firebase ${type.toUpperCase()} control failed:`, firebaseErr);
          setFirebaseOnline(false);
        }
      }

      if (!success) {
        throw new Error(`All control methods failed for ${type}`);
      }

    } catch (err) {
      console.error(`❌ ${type.toUpperCase()} control failed:`, err);
      setError(err instanceof Error ? err.message : `${type} control failed`);
    } finally {
      setLoading(prev => ({ ...prev, [type]: false }));
      isSubmittingRef.current[type] = false;
    }
  }, [connectionMode, httpOnline, firebaseOnline]);

  // Emergency shutdown
  const emergencyShutdown = useCallback(async () => {
    try {
      setLoading({ led: true, fan: true });
      setError(null);
      console.log('🚨 Emergency shutdown initiated');

      let success = false;

      // Try HTTP first
      if (httpOnline) {
        try {
          await enhancedApiClient.directControl('R:0');
          success = true;
          console.log('✅ HTTP emergency shutdown successful');
        } catch {
          console.warn('⚠️ HTTP emergency failed, trying Firebase...');
        }
      }

      // Fallback to Firebase
      if (!success) {
        success = await firebaseClient.turnOffAll();
        if (success) {
          console.log('✅ Firebase emergency shutdown successful');
        }
      }

      if (!success) {
        throw new Error('Emergency shutdown failed on all methods');
      }

    } catch (err) {
      console.error('❌ Emergency shutdown failed:', err);
      setError(err instanceof Error ? err.message : 'Emergency shutdown failed');
    } finally {
      setLoading({ led: false, fan: false });
    }
  }, [httpOnline]);

  // Quick control handlers
  const handleLEDToggle = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    controlRelay('led', 'toggle');
  }, [controlRelay]);

  const handleFanToggle = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    controlRelay('fan', 'toggle');
  }, [controlRelay]);

  const handleLEDOn = useCallback(() => controlRelay('led', 'on'), [controlRelay]);
  const handleLEDOff = useCallback(() => controlRelay('led', 'off'), [controlRelay]);
  const handleFanOn = useCallback(() => controlRelay('fan', 'on'), [controlRelay]);
  const handleFanOff = useCallback(() => controlRelay('fan', 'off'), [controlRelay]);

  // Ultra-fast control (HTTP only)
  const ultraControl = useCallback(async (relayId: number) => {
    if (!httpOnline) {
      setError('Ultra control requires HTTP API');
      return;
    }

    try {
      setError(null);
      console.log(`⚡ Ultra control: R:${relayId}`);
      const response = await enhancedApiClient.ultraControl(relayId);
      
      if (response.status === 'success') {
        console.log(`✅ Ultra control success: ${response.message}`);
        // Poll status after ultra control
        setTimeout(pollHttpStatus, 100);
      }
    } catch (err) {
      console.error('❌ Ultra control failed:', err);
      setError('Ultra control failed');
    }
  }, [httpOnline, pollHttpStatus]);

  // Initialize connections
  useEffect(() => {
    detectConnection().then((mode) => {
      if (mode === 'firebase') {
        setupFirebaseListener();
      } else if (mode === 'http') {
        pollHttpStatus();
        // Poll every 2 seconds for HTTP
        const interval = setInterval(pollHttpStatus, 2000);
        return () => clearInterval(interval);
      }
    });

    return () => {
      if (unsubscribeRef.current) {
        unsubscribeRef.current();
      }
    };
  }, [detectConnection, setupFirebaseListener, pollHttpStatus]);

  const formatLastUpdate = () => {
    if (!lastUpdate) return 'Never';
    const seconds = Math.floor((Date.now() - lastUpdate) / 1000);
    if (seconds < 60) return `${seconds}s ago`;
    return `${Math.floor(seconds / 60)}m ago`;
  };

  const isOnline = httpOnline || firebaseOnline;
  const activeConnection = httpOnline ? 'HTTP API' : firebaseOnline ? 'Firebase' : 'Offline';

  return (
    <div className={`bg-white rounded-lg shadow-lg border-2 p-6 ${className}`}>
      {/* Enhanced Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-bold flex items-center">
          <BsLightningFill className="mr-2 text-yellow-500" />
          🚀 Enhanced Relay Control
        </h3>
        <div className="text-right text-xs space-y-1">
          <div className={`font-semibold flex items-center gap-2 ${isOnline ? 'text-green-600' : 'text-red-600'}`}>
            <div className={`w-3 h-3 rounded-full ${isOnline ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
            {activeConnection}
          </div>
          <div className="text-gray-500">{formatLastUpdate()}</div>
          <div className="text-blue-600 font-mono">{responseTime}ms</div>
        </div>
      </div>

      {/* Connection Status */}
      <div className="grid grid-cols-2 gap-2 mb-6">
        <div className={`p-3 rounded-lg border-2 ${httpOnline ? 'bg-green-50 border-green-200' : 'bg-gray-50 border-gray-200'}`}>
          <div className="flex items-center text-sm">
            <FaServer className={`mr-2 ${httpOnline ? 'text-green-600' : 'text-gray-400'}`} />
            <span className={httpOnline ? 'text-green-800 font-medium' : 'text-gray-600'}>
              HTTP API {httpOnline ? '✅' : '❌'}
            </span>
          </div>
        </div>
        <div className={`p-3 rounded-lg border-2 ${firebaseOnline ? 'bg-blue-50 border-blue-200' : 'bg-gray-50 border-gray-200'}`}>
          <div className="flex items-center text-sm">
            <FaWifi className={`mr-2 ${firebaseOnline ? 'text-blue-600' : 'text-gray-400'}`} />
            <span className={firebaseOnline ? 'text-blue-800 font-medium' : 'text-gray-600'}>
              Firebase {firebaseOnline ? '✅' : '❌'}
            </span>
          </div>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border-2 border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800 text-sm font-medium">⚠️ {error}</p>
        </div>
      )}

      {/* Performance Indicator */}
      <div className="bg-gradient-to-r from-purple-50 to-blue-50 rounded-lg p-4 mb-6 border-2 border-purple-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center text-purple-700">
            <BsSpeedometer2 className="mr-2" />
            <span className="font-semibold">Performance Mode</span>
          </div>
          <div className="text-blue-700 font-mono text-sm">
            {responseTime}ms • {activeConnection}
          </div>
        </div>
      </div>

      {/* LED Control */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center">
            <FaLightbulb className={`mr-3 text-2xl ${relayStatus.led ? 'text-yellow-500' : 'text-gray-400'}`} />
            <div>
              <span className="font-semibold text-lg">LED Light</span>
              <div className="text-sm text-gray-500">R:1 Command</div>
            </div>
          </div>
          <div className={`px-3 py-1 rounded-full text-sm font-bold ${
            relayStatus.led
              ? 'bg-yellow-100 text-yellow-800 shadow-md'
              : 'bg-gray-100 text-gray-600'
          }`}>
            {relayStatus.led ? '💡 ON' : '⚫ OFF'}
          </div>
        </div>

        <div className="grid grid-cols-4 gap-2">
          <button
            onClick={handleLEDToggle}
            disabled={loading.led || !isOnline}
            className={`px-4 py-3 rounded-xl font-bold text-sm transition-all duration-200 transform hover:scale-105 ${
              relayStatus.led
                ? 'bg-yellow-500 hover:bg-yellow-600 text-white shadow-lg'
                : 'bg-gray-200 hover:bg-gray-300 text-gray-700'
            } disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none`}
          >
            {loading.led ? (
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mx-auto" />
            ) : (
              'TOGGLE'
            )}
          </button>

          <button
            onClick={handleLEDOn}
            disabled={loading.led || !isOnline}
            className="bg-green-500 hover:bg-green-600 disabled:opacity-50 text-white px-4 py-3 rounded-xl font-bold text-sm transition-all duration-200 transform hover:scale-105 disabled:transform-none shadow-md"
          >
            🟢 ON
          </button>

          <button
            onClick={handleLEDOff}
            disabled={loading.led || !isOnline}
            className="bg-red-500 hover:bg-red-600 disabled:opacity-50 text-white px-4 py-3 rounded-xl font-bold text-sm transition-all duration-200 transform hover:scale-105 disabled:transform-none shadow-md"
          >
            🔴 OFF
          </button>

          <button
            onClick={() => ultraControl(1)}
            disabled={!httpOnline}
            className="bg-purple-500 hover:bg-purple-600 disabled:opacity-50 text-white px-4 py-3 rounded-xl font-bold text-sm transition-all duration-200 transform hover:scale-105 disabled:transform-none shadow-md"
          >
            ⚡ ULTRA
          </button>
        </div>
      </div>

      {/* Fan Control */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center">
            <FaFan className={`mr-3 text-2xl ${relayStatus.fan ? 'text-blue-500 animate-spin' : 'text-gray-400'}`} />
            <div>
              <span className="font-semibold text-lg">Cooling Fan</span>
              <div className="text-sm text-gray-500">R:2 Command</div>
            </div>
          </div>
          <div className={`px-3 py-1 rounded-full text-sm font-bold ${
            relayStatus.fan
              ? 'bg-blue-100 text-blue-800 shadow-md'
              : 'bg-gray-100 text-gray-600'
          }`}>
            {relayStatus.fan ? '🌀 ON' : '⚫ OFF'}
          </div>
        </div>

        <div className="grid grid-cols-4 gap-2">
          <button
            onClick={handleFanToggle}
            disabled={loading.fan || !isOnline}
            className={`px-4 py-3 rounded-xl font-bold text-sm transition-all duration-200 transform hover:scale-105 ${
              relayStatus.fan
                ? 'bg-blue-500 hover:bg-blue-600 text-white shadow-lg'
                : 'bg-gray-200 hover:bg-gray-300 text-gray-700'
            } disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none`}
          >
            {loading.fan ? (
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mx-auto" />
            ) : (
              'TOGGLE'
            )}
          </button>

          <button
            onClick={handleFanOn}
            disabled={loading.fan || !isOnline}
            className="bg-green-500 hover:bg-green-600 disabled:opacity-50 text-white px-4 py-3 rounded-xl font-bold text-sm transition-all duration-200 transform hover:scale-105 disabled:transform-none shadow-md"
          >
            🟢 ON
          </button>

          <button
            onClick={handleFanOff}
            disabled={loading.fan || !isOnline}
            className="bg-red-500 hover:bg-red-600 disabled:opacity-50 text-white px-4 py-3 rounded-xl font-bold text-sm transition-all duration-200 transform hover:scale-105 disabled:transform-none shadow-md"
          >
            🔴 OFF
          </button>

          <button
            onClick={() => ultraControl(2)}
            disabled={!httpOnline}
            className="bg-purple-500 hover:bg-purple-600 disabled:opacity-50 text-white px-4 py-3 rounded-xl font-bold text-sm transition-all duration-200 transform hover:scale-105 disabled:transform-none shadow-md"
          >
            ⚡ ULTRA
          </button>
        </div>
      </div>

      {/* Emergency & Advanced Controls */}
      <div className="pt-6 border-t-2 border-gray-200">
        <h4 className="text-sm font-bold text-gray-700 mb-4 flex items-center">
          <FaRocket className="mr-2" />
          🚨 Emergency & Advanced Controls
        </h4>
        <div className="grid grid-cols-2 gap-3">
          <button
            onClick={emergencyShutdown}
            disabled={loading.led || loading.fan || !isOnline}
            className="bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white px-4 py-3 rounded-xl font-bold text-sm transition-all duration-200 transform hover:scale-105 disabled:transform-none shadow-lg flex items-center justify-center"
          >
            {(loading.led || loading.fan) ? (
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
            ) : (
              <span className="mr-2">🛑</span>
            )}
            EMERGENCY STOP
          </button>

          <button
            onClick={() => ultraControl(0)}
            disabled={!httpOnline}
            className="bg-orange-500 hover:bg-orange-600 disabled:opacity-50 text-white px-4 py-3 rounded-xl font-bold text-sm transition-all duration-200 transform hover:scale-105 disabled:transform-none shadow-lg flex items-center justify-center"
          >
            <span className="mr-2">⚡</span>
            ULTRA ALL OFF
          </button>
        </div>
      </div>

      {/* Connection Info */}
      <div className="mt-6 pt-4 border-t border-gray-200">
        <div className="text-xs text-gray-500 space-y-1">
          <div className="flex justify-between">
            <span>Primary:</span>
            <span className="font-mono">{activeConnection}</span>
          </div>
          <div className="flex justify-between">
            <span>Response:</span>
            <span className="font-mono">{responseTime}ms</span>
          </div>
          <div className="flex justify-between">
            <span>Last Update:</span>
            <span>{formatLastUpdate()}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EnhancedRelayControl; 