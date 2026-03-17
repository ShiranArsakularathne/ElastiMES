"""
PLC Driver for Modbus TCP communication.
Supports reading load cell data, machine status, and other PLC data.
"""
import socket
import struct
import time
import threading
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ModbusTCPClient:
    """Modbus TCP client for reading/writing PLC data."""
    
    def __init__(self, host: str, port: int = 502, unit_id: int = 1, timeout: float = 5.0):
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.timeout = timeout
        self.transaction_id = 0
        self.socket = None
        self.lock = threading.RLock()
        
    def connect(self) -> bool:
        """Connect to PLC."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            logger.info(f"Connected to PLC at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to PLC: {e}")
            self.socket = None
            return False
    
    def disconnect(self):
        """Disconnect from PLC."""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            finally:
                self.socket = None
    
    def _get_transaction_id(self) -> int:
        """Get next transaction ID."""
        with self.lock:
            self.transaction_id = (self.transaction_id + 1) % 65536
            return self.transaction_id
    
    def _build_read_holding_registers_request(self, address: int, count: int) -> bytes:
        """Build Modbus read holding registers request."""
        transaction_id = self._get_transaction_id()
        protocol_id = 0  # Modbus protocol
        length = 6  # Unit ID + Function Code + Address + Quantity
        
        # MBAP header
        header = struct.pack('>HHHBB', transaction_id, protocol_id, length, self.unit_id, 0x03)
        
        # PDU
        pdu = struct.pack('>HH', address, count)
        
        return header + pdu
    
    def _parse_read_holding_registers_response(self, data: bytes, expected_count: int) -> List[int]:
        """Parse Modbus read holding registers response."""
        if len(data) < 9:
            raise ValueError("Response too short")
        
        # Parse MBAP header
        transaction_id, protocol_id, length, unit_id, function_code = struct.unpack('>HHHBB', data[:9])
        
        if function_code == 0x83:  # Exception code
            error_code = data[9]
            error_map = {
                0x01: "Illegal Function",
                0x02: "Illegal Data Address",
                0x03: "Illegal Data Value",
                0x04: "Slave Device Failure",
            }
            error_msg = error_map.get(error_code, f"Unknown error {error_code}")
            raise ValueError(f"Modbus exception: {error_msg}")
        
        if function_code != 0x03:
            raise ValueError(f"Unexpected function code: {function_code}")
        
        byte_count = data[9]
        if byte_count != expected_count * 2:
            raise ValueError(f"Unexpected byte count: {byte_count}")
        
        # Parse register values
        registers = []
        for i in range(expected_count):
            start = 10 + i * 2
            value = struct.unpack('>H', data[start:start+2])[0]
            registers.append(value)
        
        return registers
    
    def read_holding_registers(self, address: int, count: int) -> List[int]:
        """Read holding registers from PLC."""
        if not self.socket:
            if not self.connect():
                raise ConnectionError("Not connected to PLC")
        
        request = self._build_read_holding_registers_request(address, count)
        
        try:
            with self.lock:
                self.socket.sendall(request)
                response = self.socket.recv(1024)
            
            return self._parse_read_holding_registers_response(response, count)
        except socket.timeout:
            logger.error("PLC read timeout")
            raise
        except Exception as e:
            logger.error(f"PLC read error: {e}")
            # Try to reconnect
            self.disconnect()
            raise
    
    def read_float(self, address: int) -> Optional[float]:
        """Read a float value (two registers) from PLC."""
        try:
            registers = self.read_holding_registers(address, 2)
            # Convert two 16-bit registers to 32-bit float
            combined = (registers[0] << 16) | registers[1]
            # Use struct to interpret as IEEE 754 float
            float_bytes = struct.pack('>I', combined)
            value = struct.unpack('>f', float_bytes)[0]
            return value
        except Exception as e:
            logger.error(f"Error reading float from address {address}: {e}")
            return None
    
    def read_weight(self, load_cell_address: int) -> Optional[float]:
        """Read weight from load cell."""
        return self.read_float(load_cell_address)


class PLCManager:
    """Manager for PLC connections and data polling."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.clients = {}  # machine_id -> ModbusTCPClient
        self.data_cache = {}  # machine_id -> latest data
        self.polling_threads = {}
        self.running = False
        self.callbacks = []
        
    def add_callback(self, callback):
        """Add callback for new data."""
        self.callbacks.append(callback)
    
    def remove_callback(self, callback):
        """Remove callback."""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def _notify_callbacks(self, machine_id: int, data: Dict[str, Any]):
        """Notify all callbacks of new data."""
        for callback in self.callbacks:
            try:
                callback(machine_id, data)
            except Exception as e:
                logger.error(f"Error in PLC callback: {e}")
    
    def _poll_machine(self, machine_id: int, client: ModbusTCPClient, addresses: Dict[str, int]):
        """Poll data from a single machine."""
        while self.running:
            try:
                data = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "machine_id": machine_id,
                }
                
                # Read load cell weight if configured
                if "load_cell_address" in addresses:
                    weight = client.read_weight(addresses["load_cell_address"])
                    if weight is not None:
                        data["weight_kg"] = weight
                
                # Read machine status if configured
                if "status_address" in addresses:
                    registers = client.read_holding_registers(addresses["status_address"], 1)
                    if registers:
                        data["status_code"] = registers[0]
                        # Map status code to human-readable status
                        status_map = {
                            0: "idle",
                            1: "running",
                            2: "paused",
                            3: "maintenance",
                            4: "error",
                        }
                        data["status"] = status_map.get(registers[0], "unknown")
                
                # Read other configured registers
                for name, address in addresses.items():
                    if name not in ["load_cell_address", "status_address"]:
                        try:
                            value = client.read_float(address)
                            if value is not None:
                                data[name] = value
                        except:
                            pass
                
                # Update cache and notify
                self.data_cache[machine_id] = data
                self._notify_callbacks(machine_id, data)
                
            except Exception as e:
                logger.error(f"Error polling machine {machine_id}: {e}")
                # Try to reconnect
                time.sleep(1)
                try:
                    client.connect()
                except:
                    pass
            
            # Sleep between polls
            time.sleep(self.config.get("poll_interval", 5))
    
    def start_polling(self):
        """Start polling all configured machines."""
        if self.running:
            return
        
        self.running = True
        
        # Load machine configurations from config
        machines = self.config.get("machines", {})
        
        for machine_id, machine_config in machines.items():
            try:
                client = ModbusTCPClient(
                    host=machine_config["host"],
                    port=machine_config.get("port", 502),
                    unit_id=machine_config.get("unit_id", 1),
                    timeout=machine_config.get("timeout", 5.0)
                )
                
                if client.connect():
                    self.clients[machine_id] = client
                    
                    # Start polling thread
                    thread = threading.Thread(
                        target=self._poll_machine,
                        args=(machine_id, client, machine_config.get("addresses", {})),
                        daemon=True
                    )
                    thread.start()
                    self.polling_threads[machine_id] = thread
                    
                    logger.info(f"Started polling machine {machine_id}")
                else:
                    logger.error(f"Failed to connect to machine {machine_id}")
                    
            except Exception as e:
                logger.error(f"Error setting up machine {machine_id}: {e}")
    
    def stop_polling(self):
        """Stop all polling threads."""
        self.running = False
        
        # Wait for threads to finish
        for thread in self.polling_threads.values():
            thread.join(timeout=2.0)
        
        # Disconnect all clients
        for client in self.clients.values():
            client.disconnect()
        
        self.clients.clear()
        self.polling_threads.clear()
        logger.info("PLC polling stopped")
    
    def get_machine_data(self, machine_id: int) -> Optional[Dict[str, Any]]:
        """Get latest data for a machine."""
        return self.data_cache.get(machine_id)
    
    def get_all_data(self) -> Dict[int, Dict[str, Any]]:
        """Get latest data for all machines."""
        return self.data_cache.copy()


# Factory function to create PLC manager
def create_plc_manager(config: Dict[str, Any]) -> PLCManager:
    """Create and configure a PLC manager."""
    return PLCManager(config)