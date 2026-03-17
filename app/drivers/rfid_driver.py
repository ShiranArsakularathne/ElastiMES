"""
RFID Driver for reading RFID tags from various readers.
Supports TCP-based RFID readers and serial communication.
"""
import socket
import serial
import threading
import time
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class RFIDReader:
    """Base class for RFID readers."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.running = False
        self.callbacks = []
        self.thread = None
    
    def add_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Add callback for tag reads."""
        self.callbacks.append(callback)
    
    def remove_callback(self, callback: Callable):
        """Remove callback."""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def _notify_callbacks(self, tag_id: str, metadata: Dict[str, Any] = None):
        """Notify all callbacks of a tag read."""
        data = {
            "tag_id": tag_id,
            "timestamp": datetime.utcnow().isoformat(),
            "reader_type": self.__class__.__name__,
        }
        
        if metadata:
            data.update(metadata)
        
        for callback in self.callbacks:
            try:
                callback(tag_id, data)
            except Exception as e:
                logger.error(f"Error in RFID callback: {e}")
    
    def connect(self) -> bool:
        """Connect to reader."""
        raise NotImplementedError
    
    def disconnect(self):
        """Disconnect from reader."""
        raise NotImplementedError
    
    def start_polling(self):
        """Start polling for tags."""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._poll, daemon=True)
        self.thread.start()
        logger.info(f"Started RFID polling for {self.__class__.__name__}")
    
    def stop_polling(self):
        """Stop polling."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        self.disconnect()
        logger.info(f"Stopped RFID polling for {self.__class__.__name__}")
    
    def _poll(self):
        """Poll for tags (implemented by subclasses)."""
        raise NotImplementedError


class TCPRFIDReader(RFIDReader):
    """TCP-based RFID reader."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.socket = None
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 10001)
        self.timeout = config.get("timeout", 5.0)
        self.buffer_size = config.get("buffer_size", 1024)
        
        # Reader-specific configuration
        self.delimiter = config.get("delimiter", "\r\n")
        self.encoding = config.get("encoding", "utf-8")
        self.keepalive_interval = config.get("keepalive_interval", 30)
        self.last_keepalive = time.time()
    
    def connect(self) -> bool:
        """Connect to TCP RFID reader."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            logger.info(f"Connected to RFID reader at {self.host}:{self.port}")
            
            # Send initialization command if configured
            init_command = self.config.get("init_command")
            if init_command:
                self.socket.sendall(init_command.encode(self.encoding))
                time.sleep(0.1)
            
            return True
        except Exception as e:
            logger.error(f"Failed to connect to RFID reader: {e}")
            self.socket = None
            return False
    
    def disconnect(self):
        """Disconnect from reader."""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            finally:
                self.socket = None
    
    def _poll(self):
        """Poll for tags over TCP."""
        while self.running:
            try:
                # Check connection
                if not self.socket:
                    time.sleep(1)
                    self.connect()
                    continue
                
                # Send keepalive if needed
                current_time = time.time()
                if current_time - self.last_keepalive > self.keepalive_interval:
                    try:
                        keepalive = self.config.get("keepalive_command", "")
                        if keepalive:
                            self.socket.sendall(keepalive.encode(self.encoding))
                        self.last_keepalive = current_time
                    except:
                        logger.warning("Keepalive failed, reconnecting...")
                        self.disconnect()
                        continue
                
                # Read data
                try:
                    data = self.socket.recv(self.buffer_size)
                except socket.timeout:
                    # Timeout is OK, just continue
                    continue
                except ConnectionError:
                    logger.warning("Connection lost, reconnecting...")
                    self.disconnect()
                    time.sleep(1)
                    continue
                
                if data:
                    try:
                        decoded = data.decode(self.encoding).strip()
                        
                        # Process based on delimiter
                        if self.delimiter:
                            parts = decoded.split(self.delimiter)
                            for part in parts:
                                tag_id = part.strip()
                                if tag_id and len(tag_id) > 0:
                                    self._notify_callbacks(tag_id, {"raw_data": decoded})
                        else:
                            # Whole message is tag ID
                            if decoded and len(decoded) > 0:
                                self._notify_callbacks(decoded, {"raw_data": decoded})
                    
                    except UnicodeDecodeError as e:
                        logger.error(f"Failed to decode RFID data: {e}")
                        # Try to interpret as hex string
                        try:
                            hex_str = data.hex()
                            self._notify_callbacks(hex_str, {"raw_data": hex_str, "format": "hex"})
                        except:
                            pass
                
            except Exception as e:
                logger.error(f"Error in RFID polling: {e}")
                time.sleep(1)
    
    def send_command(self, command: str) -> Optional[str]:
        """Send command to RFID reader."""
        if not self.socket:
            if not self.connect():
                return None
        
        try:
            self.socket.sendall(command.encode(self.encoding))
            time.sleep(0.1)
            
            # Read response if expected
            response = self.socket.recv(self.buffer_size)
            if response:
                return response.decode(self.encoding).strip()
        except Exception as e:
            logger.error(f"Error sending command to RFID reader: {e}")
        
        return None


class SerialRFIDReader(RFIDReader):
    """Serial-based RFID reader."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.serial = None
        self.port = config.get("port", "/dev/ttyUSB0")
        self.baudrate = config.get("baudrate", 9600)
        self.timeout = config.get("timeout", 1.0)
        
        # Reader-specific configuration
        self.delimiter = config.get("delimiter", "\r\n")
        self.encoding = config.get("encoding", "utf-8")
        self.parity = config.get("parity", serial.PARITY_NONE)
        self.stopbits = config.get("stopbits", serial.STOPBITS_ONE)
        self.bytesize = config.get("bytesize", serial.EIGHTBITS)
    
    def connect(self) -> bool:
        """Connect to serial RFID reader."""
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                parity=self.parity,
                stopbits=self.stopbits,
                bytesize=self.bytesize,
                timeout=self.timeout
            )
            
            # Wait for serial port to be ready
            time.sleep(0.5)
            
            # Send initialization command if configured
            init_command = self.config.get("init_command")
            if init_command:
                self.serial.write(init_command.encode(self.encoding))
                time.sleep(0.1)
            
            logger.info(f"Connected to serial RFID reader at {self.port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to serial RFID reader: {e}")
            self.serial = None
            return False
    
    def disconnect(self):
        """Disconnect from reader."""
        if self.serial:
            try:
                self.serial.close()
            except:
                pass
            finally:
                self.serial = None
    
    def _poll(self):
        """Poll for tags over serial."""
        while self.running:
            try:
                # Check connection
                if not self.serial:
                    time.sleep(1)
                    self.connect()
                    continue
                
                # Read data
                if self.serial.in_waiting > 0:
                    data = self.serial.read(self.serial.in_waiting)
                    
                    try:
                        decoded = data.decode(self.encoding).strip()
                        
                        # Process based on delimiter
                        if self.delimiter:
                            parts = decoded.split(self.delimiter)
                            for part in parts:
                                tag_id = part.strip()
                                if tag_id and len(tag_id) > 0:
                                    self._notify_callbacks(tag_id, {"raw_data": decoded})
                        else:
                            # Whole message is tag ID
                            if decoded and len(decoded) > 0:
                                self._notify_callbacks(decoded, {"raw_data": decoded})
                    
                    except UnicodeDecodeError as e:
                        logger.error(f"Failed to decode serial RFID data: {e}")
                        # Try to interpret as hex string
                        try:
                            hex_str = data.hex()
                            self._notify_callbacks(hex_str, {"raw_data": hex_str, "format": "hex"})
                        except:
                            pass
                
                # Small sleep to avoid CPU spinning
                time.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Error in serial RFID polling: {e}")
                time.sleep(1)


class RFIDManager:
    """Manager for multiple RFID readers."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.readers = {}  # reader_id -> RFIDReader
        self.running = False
        self.callbacks = []  # Global callbacks
        
        # Initialize readers from config
        self._initialize_readers()
    
    def _initialize_readers(self):
        """Initialize RFID readers from configuration."""
        readers_config = self.config.get("readers", {})
        
        for reader_id, reader_config in readers_config.items():
            reader_type = reader_config.get("type", "tcp")
            
            try:
                if reader_type == "tcp":
                    reader = TCPRFIDReader(reader_config)
                elif reader_type == "serial":
                    reader = SerialRFIDReader(reader_config)
                else:
                    logger.error(f"Unknown RFID reader type: {reader_type}")
                    continue
                
                # Add manager's callbacks to each reader
                for callback in self.callbacks:
                    reader.add_callback(callback)
                
                self.readers[reader_id] = reader
                logger.info(f"Initialized RFID reader: {reader_id}")
                
            except Exception as e:
                logger.error(f"Failed to initialize RFID reader {reader_id}: {e}")
    
    def add_global_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Add global callback for all readers."""
        self.callbacks.append(callback)
        
        # Add to existing readers
        for reader in self.readers.values():
            reader.add_callback(callback)
    
    def remove_global_callback(self, callback: Callable):
        """Remove global callback."""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
            
            # Remove from existing readers
            for reader in self.readers.values():
                reader.remove_callback(callback)
    
    def start(self):
        """Start all RFID readers."""
        if self.running:
            return
        
        self.running = True
        
        for reader_id, reader in self.readers.items():
            try:
                if reader.connect():
                    reader.start_polling()
                    logger.info(f"Started RFID reader: {reader_id}")
                else:
                    logger.error(f"Failed to start RFID reader: {reader_id}")
            except Exception as e:
                logger.error(f"Error starting RFID reader {reader_id}: {e}")
    
    def stop(self):
        """Stop all RFID readers."""
        self.running = False
        
        for reader_id, reader in self.readers.items():
            try:
                reader.stop_polling()
                logger.info(f"Stopped RFID reader: {reader_id}")
            except Exception as e:
                logger.error(f"Error stopping RFID reader {reader_id}: {e}")
        
        self.readers.clear()
    
    def get_reader(self, reader_id: str) -> Optional[RFIDReader]:
        """Get specific RFID reader."""
        return self.readers.get(reader_id)
    
    def get_all_readers(self) -> Dict[str, RFIDReader]:
        """Get all RFID readers."""
        return self.readers.copy()


# Factory function to create RFID manager
def create_rfid_manager(config: Dict[str, Any]) -> RFIDManager:
    """Create and configure an RFID manager."""
    return RFIDManager(config)


# Example configuration format
EXAMPLE_CONFIG = {
    "readers": {
        "gate_reader": {
            "type": "tcp",
            "host": "192.168.1.100",
            "port": 10001,
            "timeout": 5.0,
            "delimiter": "\r\n",
            "encoding": "utf-8",
            "init_command": "INIT\r\n",
            "keepalive_command": "PING\r\n",
            "keepalive_interval": 30,
        },
        "entry_reader": {
            "type": "serial",
            "port": "/dev/ttyUSB0",
            "baudrate": 9600,
            "timeout": 1.0,
            "delimiter": "\r\n",
            "encoding": "utf-8",
            "init_command": "START\r\n",
        },
    },
}