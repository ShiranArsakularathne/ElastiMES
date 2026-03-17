"""
Barcode Scanner Driver for reading barcodes from various scanners.
Supports serial (USB) and keyboard wedge scanners.
"""
import serial
import threading
import time
import sys
import select
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class BarcodeScanner:
    """Base class for barcode scanners."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.running = False
        self.callbacks = []
        self.thread = None
        self.scanner_type = config.get("type", "serial")
    
    def add_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Add callback for barcode scans."""
        self.callbacks.append(callback)
    
    def remove_callback(self, callback: Callable):
        """Remove callback."""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def _notify_callbacks(self, barcode: str, metadata: Dict[str, Any] = None):
        """Notify all callbacks of a barcode scan."""
        data = {
            "barcode": barcode,
            "timestamp": datetime.utcnow().isoformat(),
            "scanner_type": self.scanner_type,
        }
        
        if metadata:
            data.update(metadata)
        
        for callback in self.callbacks:
            try:
                callback(barcode, data)
            except Exception as e:
                logger.error(f"Error in barcode callback: {e}")
    
    def connect(self) -> bool:
        """Connect to scanner."""
        raise NotImplementedError
    
    def disconnect(self):
        """Disconnect from scanner."""
        raise NotImplementedError
    
    def start_polling(self):
        """Start polling for barcodes."""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._poll, daemon=True)
        self.thread.start()
        logger.info(f"Started barcode scanner polling for {self.scanner_type}")
    
    def stop_polling(self):
        """Stop polling."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        self.disconnect()
        logger.info(f"Stopped barcode scanner polling for {self.scanner_type}")
    
    def _poll(self):
        """Poll for barcodes (implemented by subclasses)."""
        raise NotImplementedError


class SerialBarcodeScanner(BarcodeScanner):
    """Serial-based barcode scanner (USB)."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.serial = None
        self.port = config.get("port", "/dev/ttyUSB0")
        self.baudrate = config.get("baudrate", 9600)
        self.timeout = config.get("timeout", 1.0)
        
        # Scanner-specific configuration
        self.delimiter = config.get("delimiter", "\r\n")
        self.encoding = config.get("encoding", "utf-8")
        self.parity = config.get("parity", serial.PARITY_NONE)
        self.stopbits = config.get("stopbits", serial.STOPBITS_ONE)
        self.bytesize = config.get("bytesize", serial.EIGHTBITS)
        
        # Barcode type detection
        self.prefix_mapping = config.get("prefix_mapping", {})
        self.default_type = config.get("default_type", "unknown")
    
    def connect(self) -> bool:
        """Connect to serial barcode scanner."""
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
            
            logger.info(f"Connected to serial barcode scanner at {self.port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to serial barcode scanner: {e}")
            self.serial = None
            return False
    
    def disconnect(self):
        """Disconnect from scanner."""
        if self.serial:
            try:
                self.serial.close()
            except:
                pass
            finally:
                self.serial = None
    
    def _detect_barcode_type(self, barcode: str) -> str:
        """Detect barcode type based on prefix."""
        for prefix, barcode_type in self.prefix_mapping.items():
            if barcode.startswith(prefix):
                return barcode_type
        return self.default_type
    
    def _poll(self):
        """Poll for barcodes over serial."""
        buffer = ""
        
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
                        decoded = data.decode(self.encoding)
                        buffer += decoded
                        
                        # Check for delimiter
                        if self.delimiter and self.delimiter in buffer:
                            parts = buffer.split(self.delimiter)
                            
                            # Process all complete barcodes
                            for part in parts[:-1]:  # Last part may be incomplete
                                barcode = part.strip()
                                if barcode and len(barcode) > 0:
                                    barcode_type = self._detect_barcode_type(barcode)
                                    metadata = {
                                        "barcode_type": barcode_type,
                                        "raw_data": barcode,
                                        "scanner_port": self.port,
                                    }
                                    self._notify_callbacks(barcode, metadata)
                            
                            # Keep incomplete part in buffer
                            buffer = parts[-1]
                        
                        # If no delimiter, treat entire buffer as barcode
                        elif not self.delimiter and len(buffer) > 0:
                            # Some scanners send barcode without delimiter
                            # Wait a bit to ensure we have the complete barcode
                            time.sleep(0.05)
                            
                            if self.serial.in_waiting == 0:  # No more data coming
                                barcode = buffer.strip()
                                if barcode:
                                    barcode_type = self._detect_barcode_type(barcode)
                                    metadata = {
                                        "barcode_type": barcode_type,
                                        "raw_data": barcode,
                                        "scanner_port": self.port,
                                    }
                                    self._notify_callbacks(barcode, metadata)
                                buffer = ""
                    
                    except UnicodeDecodeError as e:
                        logger.error(f"Failed to decode barcode data: {e}")
                        buffer = ""  # Clear buffer on error
                
                # Small sleep to avoid CPU spinning
                time.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Error in serial barcode polling: {e}")
                buffer = ""
                time.sleep(1)


class KeyboardWedgeScanner(BarcodeScanner):
    """Keyboard wedge barcode scanner (emulates keyboard input)."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.input_source = config.get("input_source", "stdin")
        self.delimiter = config.get("delimiter", "\n")  # Usually Enter key
        self.encoding = config.get("encoding", "utf-8")
        self.buffer = ""
        
        # Barcode type detection
        self.prefix_mapping = config.get("prefix_mapping", {})
        self.default_type = config.get("default_type", "unknown")
    
    def connect(self) -> bool:
        """Connect to keyboard wedge scanner."""
        # Keyboard wedge scanners don't need explicit connection
        logger.info("Keyboard wedge scanner ready (using stdin)")
        return True
    
    def disconnect(self):
        """Disconnect from scanner."""
        # Nothing to disconnect
        pass
    
    def _detect_barcode_type(self, barcode: str) -> str:
        """Detect barcode type based on prefix."""
        for prefix, barcode_type in self.prefix_mapping.items():
            if barcode.startswith(prefix):
                return barcode_type
        return self.default_type
    
    def _poll(self):
        """Poll for barcodes from keyboard input."""
        if self.input_source == "stdin":
            self._poll_stdin()
        else:
            logger.error(f"Unsupported input source: {self.input_source}")
    
    def _poll_stdin(self):
        """Poll stdin for barcode input."""
        import sys
        
        logger.info("Listening for barcode input on stdin...")
        
        while self.running:
            try:
                # Use select to check if stdin has data (non-blocking)
                if sys.platform == "win32":
                    # Windows doesn't support select on stdin properly
                    # Use a different approach for Windows
                    line = sys.stdin.readline()
                    if line:
                        barcode = line.rstrip(self.delimiter)
                        if barcode:
                            self._process_barcode(barcode)
                else:
                    # Unix-like systems
                    ready, _, _ = select.select([sys.stdin], [], [], 0.1)
                    if ready:
                        line = sys.stdin.readline()
                        if line:
                            barcode = line.rstrip(self.delimiter)
                            if barcode:
                                self._process_barcode(barcode)
                
                # Small sleep to avoid CPU spinning
                time.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Error in keyboard wedge polling: {e}")
                time.sleep(1)
    
    def _process_barcode(self, barcode: str):
        """Process a scanned barcode."""
        barcode_type = self._detect_barcode_type(barcode)
        metadata = {
            "barcode_type": barcode_type,
            "raw_data": barcode,
            "input_source": self.input_source,
        }
        self._notify_callbacks(barcode, metadata)


class BarcodeManager:
    """Manager for multiple barcode scanners."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.scanners = {}  # scanner_id -> BarcodeScanner
        self.running = False
        self.callbacks = []  # Global callbacks
        
        # Initialize scanners from config
        self._initialize_scanners()
    
    def _initialize_scanners(self):
        """Initialize barcode scanners from configuration."""
        scanners_config = self.config.get("scanners", {})
        
        for scanner_id, scanner_config in scanners_config.items():
            scanner_type = scanner_config.get("type", "serial")
            
            try:
                if scanner_type == "serial":
                    scanner = SerialBarcodeScanner(scanner_config)
                elif scanner_type == "keyboard_wedge":
                    scanner = KeyboardWedgeScanner(scanner_config)
                else:
                    logger.error(f"Unknown barcode scanner type: {scanner_type}")
                    continue
                
                # Add manager's callbacks to each scanner
                for callback in self.callbacks:
                    scanner.add_callback(callback)
                
                self.scanners[scanner_id] = scanner
                logger.info(f"Initialized barcode scanner: {scanner_id}")
                
            except Exception as e:
                logger.error(f"Failed to initialize barcode scanner {scanner_id}: {e}")
    
    def add_global_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Add global callback for all scanners."""
        self.callbacks.append(callback)
        
        # Add to existing scanners
        for scanner in self.scanners.values():
            scanner.add_callback(callback)
    
    def remove_global_callback(self, callback: Callable):
        """Remove global callback."""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
            
            # Remove from existing scanners
            for scanner in self.scanners.values():
                scanner.remove_callback(callback)
    
    def start(self):
        """Start all barcode scanners."""
        if self.running:
            return
        
        self.running = True
        
        for scanner_id, scanner in self.scanners.items():
            try:
                if scanner.connect():
                    scanner.start_polling()
                    logger.info(f"Started barcode scanner: {scanner_id}")
                else:
                    logger.error(f"Failed to start barcode scanner: {scanner_id}")
            except Exception as e:
                logger.error(f"Error starting barcode scanner {scanner_id}: {e}")
    
    def stop(self):
        """Stop all barcode scanners."""
        self.running = False
        
        for scanner_id, scanner in self.scanners.items():
            try:
                scanner.stop_polling()
                logger.info(f"Stopped barcode scanner: {scanner_id}")
            except Exception as e:
                logger.error(f"Error stopping barcode scanner {scanner_id}: {e}")
        
        self.scanners.clear()
    
    def get_scanner(self, scanner_id: str) -> Optional[BarcodeScanner]:
        """Get specific barcode scanner."""
        return self.scanners.get(scanner_id)
    
    def get_all_scanners(self) -> Dict[str, BarcodeScanner]:
        """Get all barcode scanners."""
        return self.scanners.copy()
    
    def simulate_scan(self, scanner_id: str, barcode: str, barcode_type: str = None):
        """Simulate a barcode scan (for testing)."""
        scanner = self.scanners.get(scanner_id)
        if scanner:
            metadata = {
                "barcode_type": barcode_type or "simulated",
                "raw_data": barcode,
                "simulated": True,
            }
            scanner._notify_callbacks(barcode, metadata)
            return True
        return False


# Factory function to create barcode manager
def create_barcode_manager(config: Dict[str, Any]) -> BarcodeManager:
    """Create and configure a barcode manager."""
    return BarcodeManager(config)


# Example configuration format
EXAMPLE_CONFIG = {
    "scanners": {
        "beam_scanner": {
            "type": "serial",
            "port": "/dev/ttyUSB0",
            "baudrate": 9600,
            "timeout": 1.0,
            "delimiter": "\r\n",
            "encoding": "utf-8",
            "prefix_mapping": {
                "BEAM": "beam_code",
                "MACH": "machine_code",
                "OPER": "operator_code",
            },
            "default_type": "unknown",
            "init_command": "\x02",  # Some scanners need initialization
        },
        "operator_scanner": {
            "type": "keyboard_wedge",
            "input_source": "stdin",
            "delimiter": "\n",
            "encoding": "utf-8",
            "prefix_mapping": {
                "OP": "operator_id",
                "MG": "material_code",
            },
            "default_type": "general",
        },
    },
}