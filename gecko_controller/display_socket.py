import socket
import os
import json
import base64
import logging
import ssl
from io import BytesIO
from PIL import Image
from typing import Optional, Tuple, Dict
from contextlib import contextmanager
from dataclasses import dataclass
from threading import Lock

@dataclass
class SocketConfig:
    socket_path: str = "/tmp/gecko-display.sock"
    chunk_size: int = 4096
    timeout: int = 2
    max_retries: int = 3
    permissions: int = 0o600  # More restrictive permissions
    max_size: int = 10 * 1024 * 1024  # 10MB limit
    compression_quality: int = 85

class ImageSocketBase:
    def __init__(self, config: Optional[SocketConfig] = None):
        self.config = config or SocketConfig()
        self.logger = logging.getLogger(__name__)
        self._lock = Lock()

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
    def __init__(self, config: Optional[SocketConfig] = None):
        super().__init__(config)
        self._cleanup_socket()
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.bind(self.config.socket_path)
        os.chmod(self.config.socket_path, self.config.permissions)
        self.sock.listen(5)  # Allow queue of 5 connections
        self.logger.info(f"Server listening on {self.config.socket_path}")

    def _cleanup_socket(self) -> None:
        with self._lock:
            if os.path.exists(self.config.socket_path):
                os.unlink(self.config.socket_path)

    @contextmanager
    def _client_connection(self):
        client = None
        try:
            client, _ = self.sock.accept()
            client.settimeout(self.config.timeout)
            yield client
        finally:
            if client:
                client.close()

    def send_image(self, image: Image.Image) -> bool:
        try:
            with self._lock:
                compressed = self._compress_image(image)
                self._validate_image(compressed)

                with self._client_connection() as client:
                    response = {
                        'status': 'success',
                        'image': base64.b64encode(compressed).decode(),
                        'metadata': {
                            'size': len(compressed),
                            'format': 'JPEG',
                            'mode': image.mode
                        }
                    }

                    msg = json.dumps(response).encode()
                    client.sendall(len(msg).to_bytes(4, byteorder='big'))
                    client.sendall(msg)

                return True

        except Exception as e:
            self.logger.error(f"Error sending image: {e}")
            return False

    def __del__(self):
        try:
            self.sock.close()
            self._cleanup_socket()
        except Exception as e:
            self.logger.error(f"Error in cleanup: {e}")

class DisplaySocketClient(ImageSocketBase):
    def __init__(self, config: Optional[SocketConfig] = None):
        super().__init__(config)
        self.sock = None

    def _connect(self) -> None:
        if self.sock:
            self.sock.close()
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.config.timeout)
        self.sock.connect(self.config.socket_path)

    def get_image(self) -> Tuple[bool, Optional[Image.Image], Optional[str]]:
        for attempt in range(self.config.max_retries):
            try:
                with self._lock:
                    self._connect()

                    length_bytes = self.sock.recv(4)
                    if not length_bytes:
                        continue

                    msg_length = int.from_bytes(length_bytes, byteorder='big')
                    chunks = []
                    bytes_received = 0

                    while bytes_received < msg_length:
                        chunk = self.sock.recv(
                            min(self.config.chunk_size,
                                msg_length - bytes_received))
                        if not chunk:
                            raise ConnectionError("Connection closed prematurely")
                        chunks.append(chunk)
                        bytes_received += len(chunk)

                    data = json.loads(b''.join(chunks).decode())

                    if data['status'] != 'success':
                        raise ValueError(data.get('error', 'Unknown error'))

                    image_data = base64.b64decode(data['image'])
                    self._validate_image(image_data)

                    return True, Image.open(BytesIO(image_data)), None

            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt == self.config.max_retries - 1:
                    return False, None, str(e)

            finally:
                if self.sock:
                    self.sock.close()
                    self.sock = None

        return False, None, "Max retries exceeded"

    def __del__(self):
        if self.sock:
            self.sock.close()
