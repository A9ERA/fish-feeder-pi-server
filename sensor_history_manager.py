#!/usr/bin/env python3
"""
📊 SENSOR HISTORY MANAGER - NoSQL JSON Storage
==============================================
Complete sensor data storage and analytics system for 128GB Pi storage
+ Real-time data collection + Historical analysis + Energy monitoring
"""

import json
import os
import time
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import gzip
import shutil
from collections import defaultdict, deque

class SensorHistoryManager:
    """
    NoSQL JSON-based sensor history storage with advanced analytics
    Optimized for 128GB Pi storage with intelligent data management
    """
    
    def __init__(self, logger, storage_path="data/sensor_history"):
        self.logger = logger
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Performance optimizations - Enhanced for Li-ion battery
        self.memory_buffer = deque(maxlen=2000)  # Keep last 2000 readings in memory
        self.write_buffer = []
        self.buffer_lock = threading.Lock()
        self.last_write_time = time.time()
        self.write_interval = 15  # Write to disk every 15 seconds (faster for better performance)
        
        # Battery-specific performance tracking
        self.battery_specs = {
            'type': 'Lithium-ion',
            'voltage': 12,
            'capacity_ah': 12,
            'max_voltage': 12.6,
            'min_voltage': 8.4,
            'max_current': 25,
            'internal_resistance': 0.001,  # <1mΩ
            'cycle_life': 1000,
            'efficiency': 0.95  # Li-ion efficiency ~95%
        }
        
        # Storage configuration for 128GB
        self.max_storage_gb = 100  # Use 100GB max for sensor data
        self.retention_days = {
            'raw': 30,      # Raw data: 30 days
            'hourly': 365,  # Hourly summaries: 1 year  
            'daily': 1825,  # Daily summaries: 5 years
            'monthly': 3650 # Monthly summaries: 10 years
        }
        
        # Analytics cache
        self.analytics_cache = {}
        self.cache_expiry = 300  # 5 minutes cache
        
        # Start background services
        self._start_background_writer()
        self._start_analytics_updater()
        
        self.logger.info(f"📊 SensorHistoryManager initialized - Storage: {self.storage_path}")
    
    def save_sensor_data(self, sensor_data: Dict[str, Any]) -> bool:
        """
        Save sensor data to NoSQL JSON storage with performance optimization
        """
        try:
            timestamp = datetime.now()
            
            # Create standardized data record
            record = {
                'timestamp': timestamp.isoformat(),
                'unix_time': int(timestamp.timestamp()),
                'date': timestamp.strftime('%Y-%m-%d'),
                'time': timestamp.strftime('%H:%M:%S'),
                'hour': timestamp.hour,
                'minute': timestamp.minute,
                'data': self._normalize_sensor_data(sensor_data)
            }
            
            # Add to memory buffer for real-time access
            with self.buffer_lock:
                self.memory_buffer.append(record)
                self.write_buffer.append(record)
            
            # Trigger write if buffer is full or time elapsed
            if (len(self.write_buffer) >= 100 or 
                time.time() - self.last_write_time > self.write_interval):
                threading.Thread(target=self._flush_write_buffer, daemon=True).start()
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to save sensor data: {e}")
            return False
    
    def _normalize_sensor_data(self, sensor_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Normalize sensor data to consistent format
        """
        normalized = {}
        
        # Standard sensor mappings
        sensor_mappings = {
            'soil_moisture': ['soil_moisture', 'soil'],
            'battery_voltage': ['battery_voltage', 'load_voltage', 'battery'],
            'solar_voltage': ['solar_voltage', 'solar_v'],
            'solar_current': ['solar_current', 'solar_i'],
            'load_current': ['load_current', 'current'],
            'dht22_feed_temp': ['feed_temp', 'dht22_feed_temp', 'temp1'],
            'dht22_feed_humidity': ['feed_humidity', 'dht22_feed_humidity', 'humidity1'],
            'dht22_control_temp': ['control_temp', 'dht22_control_temp', 'temp2'],
            'dht22_control_humidity': ['control_humidity', 'dht22_control_humidity', 'humidity2'],
            'water_temp': ['water_temp', 'water_temperature'],
            'load_cell_weight': ['weight', 'load_cell_weight', 'food_weight'],
            'battery_percentage': ['battery_percentage', 'battery_pct']
        }
        
        # Extract and normalize values
        for standard_name, possible_keys in sensor_mappings.items():
            for key in possible_keys:
                if key in sensor_data:
                    try:
                        normalized[standard_name] = float(sensor_data[key])
                        break
                    except (ValueError, TypeError):
                        continue
        
        # Calculate derived values
        if 'solar_voltage' in normalized and 'solar_current' in normalized:
            normalized['solar_power'] = normalized['solar_voltage'] * normalized['solar_current']
        
        if 'battery_voltage' in normalized and 'load_current' in normalized:
            normalized['load_power'] = normalized['battery_voltage'] * normalized['load_current']
        
        # Enhanced energy efficiency calculation for Li-ion battery
        if 'solar_power' in normalized and 'load_power' in normalized:
            solar_power = normalized['solar_power']
            load_power = normalized['load_power']
            
            if load_power > 0:
                # Account for Li-ion battery efficiency and internal resistance
                battery_loss = normalized.get('load_current', 0) ** 2 * self.battery_specs['internal_resistance']
                effective_load = load_power + battery_loss
                
                # Include battery charging efficiency
                charging_efficiency = self.battery_specs['efficiency']
                system_efficiency = (solar_power * charging_efficiency) / effective_load * 100
                
                normalized['energy_efficiency'] = min(100, system_efficiency)
                normalized['battery_loss_watts'] = round(battery_loss, 3)
                normalized['system_efficiency'] = round(system_efficiency, 1)
            else:
                normalized['energy_efficiency'] = 100
                normalized['battery_loss_watts'] = 0
                normalized['system_efficiency'] = 100
        
        # Calculate battery state of charge (SOC) for Li-ion
        if 'battery_voltage' in normalized:
            voltage = normalized['battery_voltage']
            if voltage >= 12.5:
                soc = 100
            elif voltage >= 8.4:
                # Linear approximation for Li-ion SOC
                soc = ((voltage - 8.4) / (12.6 - 8.4)) * 100
            else:
                soc = 0
            normalized['battery_soc'] = round(soc, 1)
        
        return normalized
    
    def _flush_write_buffer(self):
        """
        Write buffered data to disk with compression
        """
        try:
            with self.buffer_lock:
                if not self.write_buffer:
                    return
                
                data_to_write = self.write_buffer.copy()
                self.write_buffer.clear()
                self.last_write_time = time.time()
            
            # Group by date for efficient file organization
            data_by_date = defaultdict(list)
            for record in data_to_write:
                data_by_date[record['date']].append(record)
            
            # Write each date's data
            for date, records in data_by_date.items():
                self._write_daily_data(date, records)
            
            self.logger.debug(f"📝 Flushed {len(data_to_write)} records to disk")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to flush write buffer: {e}")
    
    def _write_daily_data(self, date: str, records: List[Dict]):
        """
        Write daily data to compressed JSON files
        """
        try:
            daily_dir = self.storage_path / "raw" / date[:4] / date[5:7]  # YYYY/MM structure
            daily_dir.mkdir(parents=True, exist_ok=True)
            
            daily_file = daily_dir / f"{date}.json.gz"
            
            # Load existing data if file exists
            existing_data = []
            if daily_file.exists():
                try:
                    with gzip.open(daily_file, 'rt', encoding='utf-8') as f:
                        existing_data = json.load(f)
                except:
                    existing_data = []
            
            # Append new records
            existing_data.extend(records)
            
            # Sort by timestamp
            existing_data.sort(key=lambda x: x['unix_time'])
            
            # Write compressed data
            with gzip.open(daily_file, 'wt', encoding='utf-8') as f:
                json.dump(existing_data, f, separators=(',', ':'))
            
        except Exception as e:
            self.logger.error(f"❌ Failed to write daily data for {date}: {e}")
    
    def get_historical_data(self, start_date: str, end_date: str, 
                          sensors: List[str] = None, 
                          resolution: str = "raw") -> List[Dict]:
        """
        Get historical sensor data with flexible querying
        
        Args:
            start_date: YYYY-MM-DD format
            end_date: YYYY-MM-DD format  
            sensors: List of sensor names to include
            resolution: "raw", "hourly", "daily", "monthly"
        """
        try:
            cache_key = f"{start_date}:{end_date}:{resolution}:{','.join(sensors or [])}"
            
            # Check cache first
            if cache_key in self.analytics_cache:
                cache_time, data = self.analytics_cache[cache_key]
                if time.time() - cache_time < self.cache_expiry:
                    return data
            
            # Load data based on resolution
            if resolution == "raw":
                data = self._load_raw_data(start_date, end_date, sensors)
            elif resolution == "hourly":
                data = self._load_summary_data(start_date, end_date, sensors, "hourly")
            elif resolution == "daily":
                data = self._load_summary_data(start_date, end_date, sensors, "daily")
            elif resolution == "monthly":
                data = self._load_summary_data(start_date, end_date, sensors, "monthly")
            else:
                data = []
            
            # Cache result
            self.analytics_cache[cache_key] = (time.time(), data)
            
            return data
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get historical data: {e}")
            return []
    
    def _load_raw_data(self, start_date: str, end_date: str, sensors: List[str]) -> List[Dict]:
        """
        Load raw sensor data from compressed JSON files
        """
        data = []
        current_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
        
        while current_date <= end_date_obj:
            date_str = current_date.strftime('%Y-%m-%d')
            daily_file = (self.storage_path / "raw" / 
                         date_str[:4] / date_str[5:7] / f"{date_str}.json.gz")
            
            if daily_file.exists():
                try:
                    with gzip.open(daily_file, 'rt', encoding='utf-8') as f:
                        daily_data = json.load(f)
                        
                    # Filter sensors if specified
                    if sensors:
                        for record in daily_data:
                            filtered_data = {k: v for k, v in record['data'].items() if k in sensors}
                            if filtered_data:
                                record['data'] = filtered_data
                                data.append(record)
                    else:
                        data.extend(daily_data)
                        
                except Exception as e:
                    self.logger.error(f"❌ Failed to load data for {date_str}: {e}")
            
            current_date += timedelta(days=1)
        
        return data
    
    def get_energy_analytics(self, days: int = 7) -> Dict[str, Any]:
        """
        Get comprehensive energy analytics and usage summary
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Get historical data
            data = self.get_historical_data(
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d'),
                ['solar_power', 'load_power', 'battery_voltage', 'energy_efficiency']
            )
            
            if not data:
                return self._get_default_analytics()
            
            # Calculate analytics
            analytics = {
                'period': {
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'days': days,
                    'total_readings': len(data)
                },
                'energy_summary': self._calculate_energy_summary(data),
                'efficiency_analysis': self._calculate_efficiency_analysis(data),
                'power_trends': self._calculate_power_trends(data),
                'battery_health': self._calculate_battery_health(data),
                'daily_breakdown': self._calculate_daily_breakdown(data),
                'recommendations': self._generate_recommendations(data)
            }
            
            return analytics
            
        except Exception as e:
            self.logger.error(f"❌ Failed to calculate energy analytics: {e}")
            return self._get_default_analytics()
    
    def _calculate_energy_summary(self, data: List[Dict]) -> Dict[str, float]:
        """Calculate energy usage summary"""
        solar_powers = [r['data'].get('solar_power', 0) for r in data if 'solar_power' in r['data']]
        load_powers = [r['data'].get('load_power', 0) for r in data if 'load_power' in r['data']]
        
        if not solar_powers or not load_powers:
            return {'total_solar_kwh': 0, 'total_load_kwh': 0, 'net_energy': 0, 'self_sufficiency': 0}
        
        # Calculate energy in kWh (assuming 5-minute intervals)
        interval_hours = 5 / 60  # 5 minutes = 1/12 hour
        
        total_solar_kwh = sum(solar_powers) * interval_hours / 1000
        total_load_kwh = sum(load_powers) * interval_hours / 1000
        net_energy = total_solar_kwh - total_load_kwh
        self_sufficiency = min(100, (total_solar_kwh / total_load_kwh * 100)) if total_load_kwh > 0 else 100
        
        return {
            'total_solar_kwh': round(total_solar_kwh, 3),
            'total_load_kwh': round(total_load_kwh, 3),
            'net_energy': round(net_energy, 3),
            'self_sufficiency': round(self_sufficiency, 1),
            'avg_solar_power': round(sum(solar_powers) / len(solar_powers), 2),
            'avg_load_power': round(sum(load_powers) / len(load_powers), 2),
            'max_solar_power': round(max(solar_powers), 2),
            'max_load_power': round(max(load_powers), 2)
        }
    
    def _calculate_efficiency_analysis(self, data: List[Dict]) -> Dict[str, Any]:
        """Calculate energy efficiency analysis"""
        efficiencies = [r['data'].get('energy_efficiency', 0) for r in data if 'energy_efficiency' in r['data']]
        
        if not efficiencies:
            return {'avg_efficiency': 0, 'efficiency_trend': 'stable', 'peak_hours': []}
        
        avg_efficiency = sum(efficiencies) / len(efficiencies)
        
        # Calculate trend (simple linear regression)
        if len(efficiencies) > 10:
            n = len(efficiencies)
            x_avg = n / 2
            y_avg = avg_efficiency
            
            slope_num = sum((i - x_avg) * (eff - y_avg) for i, eff in enumerate(efficiencies))
            slope_den = sum((i - x_avg) ** 2 for i in range(n))
            
            trend = 'improving' if slope_num > 0 else 'declining' if slope_num < 0 else 'stable'
        else:
            trend = 'stable'
        
        # Find peak efficiency hours
        hourly_efficiency = defaultdict(list)
        for record in data:
            if 'energy_efficiency' in record['data']:
                hour = record['hour']
                hourly_efficiency[hour].append(record['data']['energy_efficiency'])
        
        avg_hourly = {hour: sum(effs) / len(effs) for hour, effs in hourly_efficiency.items()}
        peak_hours = sorted(avg_hourly.keys(), key=avg_hourly.get, reverse=True)[:3]
        
        return {
            'avg_efficiency': round(avg_efficiency, 1),
            'max_efficiency': round(max(efficiencies), 1),
            'min_efficiency': round(min(efficiencies), 1),
            'efficiency_trend': trend,
            'peak_hours': peak_hours,
            'efficiency_distribution': self._calculate_distribution(efficiencies)
        }
    
    def _calculate_power_trends(self, data: List[Dict]) -> Dict[str, List]:
        """Calculate power generation and consumption trends"""
        hourly_solar = defaultdict(list)
        hourly_load = defaultdict(list)
        
        for record in data:
            hour = record['hour']
            if 'solar_power' in record['data']:
                hourly_solar[hour].append(record['data']['solar_power'])
            if 'load_power' in record['data']:
                hourly_load[hour].append(record['data']['load_power'])
        
        solar_trend = [
            {
                'hour': hour,
                'avg_power': round(sum(powers) / len(powers), 2),
                'max_power': round(max(powers), 2),
                'readings': len(powers)
            }
            for hour, powers in hourly_solar.items()
        ]
        
        load_trend = [
            {
                'hour': hour,
                'avg_power': round(sum(powers) / len(powers), 2),
                'max_power': round(max(powers), 2),
                'readings': len(powers)
            }
            for hour, powers in hourly_load.items()
        ]
        
        return {
            'solar_by_hour': sorted(solar_trend, key=lambda x: x['hour']),
            'load_by_hour': sorted(load_trend, key=lambda x: x['hour'])
        }
    
    def _calculate_battery_health(self, data: List[Dict]) -> Dict[str, Any]:
        """Calculate battery health metrics for Lithium-ion 12V 12AH battery"""
        voltages = [r['data'].get('battery_voltage', 0) for r in data if 'battery_voltage' in r['data']]
        currents = [r['data'].get('load_current', 0) for r in data if 'load_current' in r['data']]
        
        if not voltages:
            return {'status': 'unknown', 'avg_voltage': 0, 'health_score': 0, 'battery_type': 'Li-ion 12V 12AH'}
        
        avg_voltage = sum(voltages) / len(voltages)
        min_voltage = min(voltages)
        max_voltage = max(voltages)
        avg_current = sum(currents) / len(currents) if currents else 0
        
        # Lithium-ion 12V 12AH health scoring (8.4V-12.6V operating range)
        if avg_voltage >= 12.5:  # >99% charge
            status = 'excellent'
            health_score = 100
            charge_level = 100
        elif avg_voltage >= 12.2:  # 85-99% charge
            status = 'good'
            health_score = 90
            charge_level = int(85 + ((avg_voltage - 12.2) / 0.3) * 14)
        elif avg_voltage >= 11.8:  # 60-85% charge
            status = 'fair'
            health_score = 75
            charge_level = int(60 + ((avg_voltage - 11.8) / 0.4) * 25)
        elif avg_voltage >= 11.4:  # 30-60% charge
            status = 'low'
            health_score = 60
            charge_level = int(30 + ((avg_voltage - 11.4) / 0.4) * 30)
        elif avg_voltage >= 10.8:  # 10-30% charge
            status = 'very_low'
            health_score = 40
            charge_level = int(10 + ((avg_voltage - 10.8) / 0.6) * 20)
        elif avg_voltage >= 8.4:   # <10% charge (minimum safe voltage)
            status = 'critical'
            health_score = 20
            charge_level = int(max(0, ((avg_voltage - 8.4) / 2.4) * 10))
        else:
            status = 'damaged'
            health_score = 0
            charge_level = 0
        
        # Calculate capacity estimation (12AH battery)
        estimated_capacity_ah = 12 * (health_score / 100)
        
        # Calculate runtime estimate based on current load
        if avg_current > 0:
            estimated_runtime_hours = estimated_capacity_ah / avg_current
        else:
            estimated_runtime_hours = 999  # No load
        
        # Performance metrics
        voltage_stability = max_voltage - min_voltage
        performance_rating = 'excellent' if voltage_stability < 0.2 else 'good' if voltage_stability < 0.5 else 'poor'
        
        return {
            'battery_type': 'Lithium-ion 12V 12AH',
            'status': status,
            'health_score': health_score,
            'charge_level': charge_level,
            'avg_voltage': round(avg_voltage, 2),
            'min_voltage': round(min_voltage, 2),
            'max_voltage': round(max_voltage, 2),
            'voltage_stability': round(voltage_stability, 2),
            'performance_rating': performance_rating,
            'estimated_capacity_ah': round(estimated_capacity_ah, 1),
            'estimated_runtime_hours': round(min(estimated_runtime_hours, 999), 1),
            'avg_current_draw': round(avg_current, 2),
            'operating_specs': {
                'nominal_voltage': '12V',
                'capacity': '12AH',
                'operating_range': '8.4V - 12.6V',
                'max_charge_voltage': '12.6V',
                'max_current': '25A',
                'chemistry': 'Lithium-ion',
                'weight': '0.9kg',
                'dimensions': '15×6.4×9.5cm',
                'cycle_life': '≥1000 cycles',
                'temperature_range': '-20°C to +60°C'
            }
        }
    
    def _calculate_daily_breakdown(self, data: List[Dict]) -> List[Dict]:
        """Calculate daily energy breakdown"""
        daily_data = defaultdict(lambda: {'solar': [], 'load': [], 'efficiency': []})
        
        for record in data:
            date = record['date']
            if 'solar_power' in record['data']:
                daily_data[date]['solar'].append(record['data']['solar_power'])
            if 'load_power' in record['data']:
                daily_data[date]['load'].append(record['data']['load_power'])
            if 'energy_efficiency' in record['data']:
                daily_data[date]['efficiency'].append(record['data']['energy_efficiency'])
        
        breakdown = []
        for date, values in daily_data.items():
            solar_kwh = sum(values['solar']) * (5/60) / 1000 if values['solar'] else 0
            load_kwh = sum(values['load']) * (5/60) / 1000 if values['load'] else 0
            avg_efficiency = sum(values['efficiency']) / len(values['efficiency']) if values['efficiency'] else 0
            
            breakdown.append({
                'date': date,
                'solar_kwh': round(solar_kwh, 3),
                'load_kwh': round(load_kwh, 3),
                'net_kwh': round(solar_kwh - load_kwh, 3),
                'avg_efficiency': round(avg_efficiency, 1),
                'self_sufficiency': round((solar_kwh / load_kwh * 100) if load_kwh > 0 else 100, 1)
            })
        
        return sorted(breakdown, key=lambda x: x['date'])
    
    def _generate_recommendations(self, data: List[Dict]) -> List[str]:
        """Generate energy optimization recommendations"""
        recommendations = []
        
        # Analyze data for recommendations
        solar_powers = [r['data'].get('solar_power', 0) for r in data if 'solar_power' in r['data']]
        load_powers = [r['data'].get('load_power', 0) for r in data if 'load_power' in r['data']]
        efficiencies = [r['data'].get('energy_efficiency', 0) for r in data if 'energy_efficiency' in r['data']]
        
        if not solar_powers or not load_powers:
            return ["⚠️ Insufficient data for recommendations"]
        
        avg_solar = sum(solar_powers) / len(solar_powers)
        avg_load = sum(load_powers) / len(load_powers)
        avg_efficiency = sum(efficiencies) / len(efficiencies) if efficiencies else 0
        
        # Generate specific recommendations
        if avg_efficiency < 50:
            recommendations.append("🔋 Consider optimizing battery charging schedule for better efficiency")
        
        if avg_solar < avg_load * 0.8:
            recommendations.append("☀️ Solar generation is low - check panel positioning or add more panels")
        
        if max(load_powers) > avg_load * 2:
            recommendations.append("⚡ High power spikes detected - consider load balancing")
        
        if len(recommendations) == 0:
            recommendations.append("✅ System operating efficiently - maintain current settings")
        
        return recommendations
    
    def _calculate_distribution(self, values: List[float]) -> Dict[str, int]:
        """Calculate value distribution for histogram data"""
        if not values:
            return {}
        
        # Create 10 bins
        min_val, max_val = min(values), max(values)
        if min_val == max_val:
            return {str(min_val): len(values)}
        
        bin_size = (max_val - min_val) / 10
        distribution = defaultdict(int)
        
        for value in values:
            bin_index = min(9, int((value - min_val) / bin_size))
            bin_start = min_val + bin_index * bin_size
            bin_key = f"{bin_start:.1f}-{bin_start + bin_size:.1f}"
            distribution[bin_key] += 1
        
        return dict(distribution)
    
    def _get_default_analytics(self) -> Dict[str, Any]:
        """Return default analytics when no data available"""
        return {
            'period': {'start_date': '', 'end_date': '', 'days': 0, 'total_readings': 0},
            'energy_summary': {'total_solar_kwh': 0, 'total_load_kwh': 0, 'net_energy': 0, 'self_sufficiency': 0},
            'efficiency_analysis': {'avg_efficiency': 0, 'efficiency_trend': 'stable', 'peak_hours': []},
            'power_trends': {'solar_by_hour': [], 'load_by_hour': []},
            'battery_health': {'status': 'unknown', 'avg_voltage': 0, 'health_score': 0},
            'daily_breakdown': [],
            'recommendations': ["⚠️ No data available for analysis"]
        }
    
    def _start_background_writer(self):
        """Start background thread for periodic data writing"""
        def writer_loop():
            while True:
                try:
                    time.sleep(self.write_interval)
                    if self.write_buffer:
                        self._flush_write_buffer()
                except Exception as e:
                    self.logger.error(f"❌ Background writer error: {e}")
        
        writer_thread = threading.Thread(target=writer_loop, daemon=True)
        writer_thread.start()
        self.logger.info("🔄 Background writer started")
    
    def _start_analytics_updater(self):
        """Start background thread for analytics updates"""
        def analytics_loop():
            while True:
                try:
                    time.sleep(300)  # Update every 5 minutes
                    # Clear old cache entries
                    current_time = time.time()
                    expired_keys = [k for k, (cache_time, _) in self.analytics_cache.items() 
                                  if current_time - cache_time > self.cache_expiry]
                    for key in expired_keys:
                        del self.analytics_cache[key]
                except Exception as e:
                    self.logger.error(f"❌ Analytics updater error: {e}")
        
        analytics_thread = threading.Thread(target=analytics_loop, daemon=True)
        analytics_thread.start()
        self.logger.info("📊 Analytics updater started")
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Get storage usage information"""
        try:
            total_size = 0
            file_count = 0
            
            for root, dirs, files in os.walk(self.storage_path):
                for file in files:
                    file_path = Path(root) / file
                    if file_path.exists():
                        total_size += file_path.stat().st_size
                        file_count += 1
            
            total_size_gb = total_size / (1024**3)
            usage_percentage = (total_size_gb / self.max_storage_gb) * 100
            
            return {
                'total_size_gb': round(total_size_gb, 3),
                'max_storage_gb': self.max_storage_gb,
                'usage_percentage': round(usage_percentage, 1),
                'file_count': file_count,
                'available_gb': round(self.max_storage_gb - total_size_gb, 3),
                'memory_buffer_size': len(self.memory_buffer),
                'write_buffer_size': len(self.write_buffer)
            }
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get storage info: {e}")
            return {'error': str(e)}
    
    def cleanup_old_data(self):
        """Clean up old data based on retention policies"""
        try:
            current_date = datetime.now()
            
            # Clean raw data older than retention period
            cutoff_date = current_date - timedelta(days=self.retention_days['raw'])
            
            raw_path = self.storage_path / "raw"
            if raw_path.exists():
                for year_dir in raw_path.iterdir():
                    if not year_dir.is_dir():
                        continue
                    
                    for month_dir in year_dir.iterdir():
                        if not month_dir.is_dir():
                            continue
                        
                        for day_file in month_dir.iterdir():
                            if day_file.suffix == '.gz':
                                try:
                                    file_date = datetime.strptime(day_file.stem, '%Y-%m-%d')
                                    if file_date < cutoff_date:
                                        day_file.unlink()
                                        self.logger.info(f"🗑️ Cleaned old data: {day_file}")
                                except:
                                    continue
            
            self.logger.info("🧹 Data cleanup completed")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to cleanup old data: {e}")
    
    def export_data(self, start_date: str, end_date: str, format: str = "json") -> Optional[str]:
        """Export historical data to file"""
        try:
            data = self.get_historical_data(start_date, end_date)
            
            export_dir = self.storage_path / "exports"
            export_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"sensor_data_{start_date}_to_{end_date}_{timestamp}.{format}"
            export_file = export_dir / filename
            
            if format == "json":
                with open(export_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            elif format == "csv":
                # Convert to CSV format
                import csv
                with open(export_file, 'w', newline='', encoding='utf-8') as f:
                    if data:
                        fieldnames = ['timestamp'] + list(data[0]['data'].keys())
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        
                        for record in data:
                            row = {'timestamp': record['timestamp']}
                            row.update(record['data'])
                            writer.writerow(row)
            
            self.logger.info(f"📤 Data exported: {export_file}")
            return str(export_file)
            
        except Exception as e:
            self.logger.error(f"❌ Failed to export data: {e}")
            return None
    
    def get_live_data(self, limit: int = 100) -> List[Dict]:
        """Get recent live data from memory buffer"""
        with self.buffer_lock:
            return list(self.memory_buffer)[-limit:]
    
    def get_sensor_summary(self) -> Dict[str, Any]:
        """Get summary of all sensor types and their latest values"""
        try:
            if not self.memory_buffer:
                return {}
            
            latest_record = self.memory_buffer[-1]
            
            summary = {
                'timestamp': latest_record['timestamp'],
                'sensors': {},
                'status': 'online',
                'total_sensors': len(latest_record['data'])
            }
            
            for sensor, value in latest_record['data'].items():
                summary['sensors'][sensor] = {
                    'value': value,
                    'unit': self._get_sensor_unit(sensor),
                    'category': self._get_sensor_category(sensor)
                }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get sensor summary: {e}")
            return {}
    
    def _get_sensor_unit(self, sensor: str) -> str:
        """Get unit for sensor type"""
        units = {
            'soil_moisture': '%',
            'battery_voltage': 'V',
            'solar_voltage': 'V',
            'solar_current': 'A',
            'load_current': 'A',
            'dht22_feed_temp': '°C',
            'dht22_feed_humidity': '%',
            'dht22_control_temp': '°C',
            'dht22_control_humidity': '%',
            'water_temp': '°C',
            'load_cell_weight': 'kg',
            'battery_percentage': '%',
            'solar_power': 'W',
            'load_power': 'W',
            'energy_efficiency': '%'
        }
        return units.get(sensor, '')
    
    def _get_sensor_category(self, sensor: str) -> str:
        """Get category for sensor type"""
        categories = {
            'soil_moisture': 'environment',
            'battery_voltage': 'power',
            'solar_voltage': 'power',
            'solar_current': 'power',
            'load_current': 'power',
            'dht22_feed_temp': 'environment',
            'dht22_feed_humidity': 'environment',
            'dht22_control_temp': 'environment',
            'dht22_control_humidity': 'environment',
            'water_temp': 'environment',
            'load_cell_weight': 'system',
            'battery_percentage': 'power',
            'solar_power': 'power',
            'load_power': 'power',
            'energy_efficiency': 'analytics'
        }
        return categories.get(sensor, 'other') 