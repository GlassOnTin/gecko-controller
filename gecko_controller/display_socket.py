import asyncio
import os
import json
import base64
import logging
from io import BytesIO
from PIL import Image
from typing import Optional, Tuple, Dict
from dataclasses import dataclass
from threading import Lock

@dataclass
class SocketConfig:
    socket_path: str = "/var/run/gecko-controller/display.sock"
    chunk_size: int = 4096
    timeout: int = 2
    max_retries: int = 3
    permissions: int = 0o660
    max_size: int = 10 * 1024 * 1024
    compression_quality: int = 85

class ImageSocketBase:
    def __init__(self, config: Optional[SocketConfig] = None):
        self.config = config or SocketConfig()
        self.logger = logging.getLogger(__name__)
        self._lock = Lock()

        # Ensure socket directory exists with proper permissions
        socket_dir = os.path.dirname(self.config.socket_path)
        try:
            if not os.path.exists(socket_dir):
                os.makedirs(socket_dir, mode=0o755, exist_ok=True)
        except Exception as e:
            self.logger.error(f"Failed to create socket directory: {e}")
            raise

    def _compress_image(self, image: Image.Image) -> bytes:
        with BytesIO() as buffer:
            image.save(buffer, format='JPEG',
                      quality=self.config.compression_quality,
                      optimize=True)
            return buffer.getvalue()

    def _validate_image(self, image_data: bytes) -> bool:
        if len(image_data) > self.config.max_size:
            raise ValueError(f"Image size exceeds {self.config.max_size} bytes")
        try:
            with Image.open(BytesIO(image_data)) as img:
                img.verify()
            return True
        except Exception as e:
            raise ValueError(f"Invalid image data: {e}")

class DisplaySocketServer(ImageSocketBase):
    _instance: Optional['DisplaySocketServer'] = None
    _lock = Lock()

    def __new__(cls, config: Optional[SocketConfig] = None):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, config: Optional[SocketConfig] = None):
        if hasattr(self, '_initialized') and self._initialized:
            return

        with self._lock:
            super().__init__(config)
            self._cleanup_socket()
            self.server = None
            self.current_image = None
            self._initialized = True
            self._active_connections = set()
            self.logger.info("Display socket server initialized")

    def _cleanup_socket(self) -> None:
        """Safely clean up the socket file"""
        try:
            if os.path.exists(self.config.socket_path):
                os.unlink(self.config.socket_path)
                self.logger.debug(f"Cleaned up existing socket at {self.config.socket_path}")
        except (PermissionError, OSError) as e:
            self.logger.warning(f"Could not remove existing socket: {e}")

    async def start(self):
        """Start the socket server if not already running"""
        with self._lock:
            if self.server is None:
                try:
                    self.server = await asyncio.start_unix_server(
                        self._handle_client,
                        path=self.config.socket_path
                    )
                    # Make socket accessible to web service user
                    os.chmod(self.config.socket_path, 0o666)
                    self.logger.info(f"Server listening on {self.config.socket_path}")
                except Exception as e:
                    self.logger.error(f"Failed to start server: {e}")
                    raise

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle individual client connections"""
        client_id = id(writer)
        self._active_connections.add(client_id)

        try:
            with self._lock:
                compressed = await self._compress_image(self.current_image) if self.current_image else None

                if compressed:
                    response = {
                        'status': 'success',
                        'image': base64.b64encode(compressed).decode(),
                        'metadata': {
                            'size': len(compressed),
                            'format': 'JPEG',
                            'mode': self.current_image.mode
                        }
                    }
                else:
                    response = {
                        'status': 'error',
                        'message': 'No image available'
                    }

            msg = json.dumps(response).encode()
            writer.write(len(msg).to_bytes(4, byteorder='big'))
            writer.write(msg)
            await writer.drain()

        except Exception as e:
            self.logger.error(f"Error sending image: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            self._active_connections.remove(client_id)

    async def send_image(self, image: Image.Image) -> bool:
        """Update the current image with thread safety"""
        try:
            with self._lock:
                self.current_image = image
            return True
        except Exception as e:
            self.logger.error(f"Error updating image: {e}")
            return False

    async def stop(self):
        """Stop the server and clean up resources"""
        with self._lock:
            if self.server:
                self.server.close()
                await self.server.wait_closed()
                self._cleanup_socket()
                self.server = None
                self.current_image = None
                self.logger.info("Display socket server stopped")

    def __del__(self):
        """Ensure cleanup on deletion"""
        if hasattr(self, 'server') and self.server:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.stop())
                else:
                    loop.run_until_complete(self.stop())
            except Exception as e:
                self.logger.error(f"Error during cleanup: {e}")

class DisplaySocketClient(ImageSocketBase):
    _instance: Optional['DisplaySocketClient'] = None
    _lock = Lock()

    def __new__(cls, config: Optional[SocketConfig] = None):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, config: Optional[SocketConfig] = None):
        if hasattr(self, '_initialized') and self._initialized:
            return

        with self._lock:
            super().__init__(config)
            self._initialized = True
            self._connection = None
            self.logger.info("Display socket client initialized")

    async def get_image(self) -> Tuple[bool, Optional[Image.Image], Optional[str]]:
        """Get current display image with retry logic"""
        for attempt in range(self.config.max_retries):
            try:
                # First check if socket exists
                if not os.path.exists(self.config.socket_path):
                    self.logger.error(f"Socket not found at {self.config.socket_path}")
                    return False, None, f"Socket not found at {self.config.socket_path}"

                # Check socket permissions
                try:
                    socket_stat = os.stat(self.config.socket_path)
                    self.logger.debug(f"Socket permissions: {oct(socket_stat.st_mode)}")
                except OSError as e:
                    self.logger.error(f"Cannot stat socket: {e}")

                with self._lock:
                    try:
                        reader, writer = await asyncio.open_unix_connection(
                            path=self.config.socket_path
                        )
                    except ConnectionRefusedError:
                        self.logger.error("Connection refused - is the display server running?")
                        await asyncio.sleep(1)  # Wait before retry
                        continue
                    except PermissionError:
                        self.logger.error("Permission denied accessing socket")
                        return False, None, "Permission denied accessing display socket"

                    try:
                        length_bytes = await reader.read(4)
                        if not length_bytes:
                            self.logger.warning("No data received from socket")
                            continue

                        msg_length = int.from_bytes(length_bytes, byteorder='big')
                        data = await reader.read(msg_length)

                        response = json.loads(data.decode())

                        if response['status'] != 'success':
                            raise ValueError(response.get('error', 'Unknown error'))

                        if 'image' not in response:
                            self.logger.warning("No image in response")
                            return False, None, "No image available"

                        image_data = base64.b64decode(response['image'])
                        self._validate_image(image_data)

                        return True, Image.open(BytesIO(image_data)), None

                    except Exception as e:
                        self.logger.error(f"Error reading from socket: {e}")
                        raise

                    finally:
                        writer.close()
                        await writer.wait_closed()

            except Exception as e:
                self.logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
                await asyncio.sleep(1)  # Wait before retry
                continue

        return False, None, "Max retries exceeded"

    def __del__(self):
        """Cleanup any remaining connections"""
        if hasattr(self, '_connection') and self._connection:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._connection.close())
                else:
                    loop.run_until_complete(self._connection.close())
            except Exception as e:
                self.logger.error(f"Error during cleanup: {e}")
