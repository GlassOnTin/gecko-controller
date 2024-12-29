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
    timeout: int = 10        # Increased to 10 seconds per operation
    max_retries: int = 10    # Increased to 10 retries
    retry_delay: float = 1.0 # Added explicit retry delay
    permissions: int = 0o660
    max_size: int = 10 * 1024 * 1024
    compression_quality: int = 85

class ImageSocketBase:
    def __init__(self, config: Optional[SocketConfig] = None):
        self.config = config or SocketConfig()
        # Create logger without adding handlers - let the root logger handle it
        self.logger = logging.getLogger(__name__)
        # Don't propagate to avoid duplicate logs
        self.logger.propagate = False
        # Only add handler if none exist
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

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
            self._active_connections = set()
            self._initialized = True
            self.logger.info(f"Display socket server initialized (id={id(self)})")

    async def start(self):
        """Start the socket server if not already running"""
        with self._lock:
            if self.server is None:
                try:
                    self.server = await asyncio.start_unix_server(
                        self._handle_client,
                        path=self.config.socket_path
                    )
                    os.chmod(self.config.socket_path, 0o666)
                    self.logger.info(f"Server listening on {self.config.socket_path} (id={id(self)})")
                except Exception as e:
                    self.logger.error(f"Failed to start server: {e}")
                    raise

    async def serve_forever(self):
        """Run the socket server forever"""
        if self.server is None:
            await self.start()

        self.logger.info("Socket server starting to serve")
        try:
            async with self.server:
                await self.server.serve_forever()
        except Exception as e:
            self.logger.error(f"Socket server error: {e}")
            raise

    async def send_image(self, image: Image.Image) -> bool:
        """Update the current image with debug logging"""
        self.logger.debug(f"Updating image on socket server (id={id(self)})")
        with self._lock:
            self.current_image = image
        return True

    def _cleanup_socket(self) -> None:
        """Safely clean up the socket file"""
        try:
            if os.path.exists(self.config.socket_path):
                os.unlink(self.config.socket_path)
                self.logger.debug(f"Cleaned up existing socket at {self.config.socket_path}")
        except (PermissionError, OSError) as e:
            self.logger.warning(f"Could not remove existing socket: {e}")

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle individual client connections"""
        client_id = id(writer)
        self.logger.debug(f"New client connection: {client_id}")
        self._active_connections.add(client_id)

        try:
            with self._lock:
                self.logger.debug(f"Preparing response for client {client_id}")
                compressed = await self._compress_image(self.current_image) if self.current_image else None

                if compressed:
                    self.logger.debug(f"Sending image ({len(compressed)} bytes) to client {client_id}")
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
                    self.logger.debug(f"No image available for client {client_id}")
                    response = {
                        'status': 'error',
                        'message': 'No image available'
                    }

            msg = json.dumps(response).encode()
            writer.write(len(msg).to_bytes(4, byteorder='big'))
            writer.write(msg)
            await writer.drain()
            self.logger.debug(f"Response sent to client {client_id}")

        except Exception as e:
            self.logger.error(f"Error handling client {client_id}: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            self._active_connections.remove(client_id)
            self.logger.debug(f"Client {client_id} connection closed")

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
        last_error = None

        while True:  # Keep trying indefinitely
            writer = None
            try:
                # Only log actual errors, not routine retries
                if last_error:
                    self.logger.debug(f"Retrying after error: {last_error}")
                    last_error = None

                with self._lock:
                    try:
                        # More generous timeouts
                        connect_task = asyncio.open_unix_connection(path=self.config.socket_path)
                        reader, writer = await asyncio.wait_for(connect_task, timeout=self.config.timeout)

                        length_bytes = await reader.read(4)
                        if not length_bytes:
                            await asyncio.sleep(self.config.retry_delay)
                            continue

                        msg_length = int.from_bytes(length_bytes, byteorder='big')
                        data = await reader.read(msg_length)

                        response = json.loads(data.decode())
                        if response['status'] != 'success':
                            last_error = response.get('error', 'Unknown error')
                            await asyncio.sleep(self.config.retry_delay)
                            continue

                        image_data = base64.b64decode(response['image'])
                        self._validate_image(image_data)

                        return True, Image.open(BytesIO(image_data)), None

                    except (asyncio.TimeoutError, ConnectionRefusedError) as e:
                        last_error = str(e)
                        await asyncio.sleep(self.config.retry_delay)
                        continue

            except Exception as e:
                last_error = str(e)
                await asyncio.sleep(self.config.retry_delay)
                continue

            finally:
                if writer:
                    try:
                        writer.close()
                        await writer.wait_closed()
                    except Exception as e:
                        self.logger.debug(f"Error closing writer: {e}")

    async def get_status(self) -> dict:
        """Get status of display socket connection"""
        status = {
            'socket_exists': False,
            'socket_path': self.config.socket_path,
            'socket_permissions': None,
            'socket_owner': None,
            'errors': []
        }

        try:
            # Check if socket exists
            status['socket_exists'] = os.path.exists(self.config.socket_path)

            # If it exists, get permissions and ownership
            if status['socket_exists']:
                try:
                    stat = os.stat(self.config.socket_path)
                    status['socket_permissions'] = oct(stat.st_mode)[-3:]  # Last 3 digits of octal permissions
                    status['socket_owner'] = f"{stat.st_uid}:{stat.st_gid}"

                    # Check if we can read the socket
                    if not os.access(self.config.socket_path, os.R_OK):
                        status['errors'].append("No read permission on socket")
                    if not os.access(self.config.socket_path, os.W_OK):
                        status['errors'].append("No write permission on socket")

                except Exception as e:
                    status['errors'].append(f"Error checking socket stats: {str(e)}")
            else:
                status['errors'].append("Socket file does not exist")

            # Add runtime user info
            status['current_user'] = os.getuid()
            status['current_group'] = os.getgid()

        except Exception as e:
            status['errors'].append(f"Error getting socket status: {str(e)}")

        return status

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
