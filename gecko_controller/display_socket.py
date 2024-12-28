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
        self.server = None

    def _cleanup_socket(self) -> None:
        with self._lock:
            if os.path.exists(self.config.socket_path):
                os.unlink(self.config.socket_path)

    async def start(self):
        self.server = await asyncio.start_unix_server(
            self._handle_client,
            path=self.config.socket_path
        )
        os.chmod(self.config.socket_path, self.config.permissions)
        self.logger.info(f"Server listening on {self.config.socket_path}")

    async def _handle_client(self, reader, writer):
        try:
            compressed = await self._compress_image(self.current_image)
            self._validate_image(compressed)

            response = {
                'status': 'success',
                'image': base64.b64encode(compressed).decode(),
                'metadata': {
                    'size': len(compressed),
                    'format': 'JPEG',
                    'mode': self.current_image.mode
                }
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

    async def send_image(self, image: Image.Image) -> bool:
        with self._lock:
            self.current_image = image
            return True

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self._cleanup_socket()

class DisplaySocketClient(ImageSocketBase):
    def __init__(self, config: Optional[SocketConfig] = None):
        super().__init__(config)

    async def get_image(self) -> Tuple[bool, Optional[Image.Image], Optional[str]]:
        for attempt in range(self.config.max_retries):
            try:
                with self._lock:
                    reader, writer = await asyncio.open_unix_connection(
                        path=self.config.socket_path
                    )

                    length_bytes = await reader.read(4)
                    if not length_bytes:
                        continue

                    msg_length = int.from_bytes(length_bytes, byteorder='big')
                    data = await reader.read(msg_length)

                    response = json.loads(data.decode())

                    if response['status'] != 'success':
                        raise ValueError(response.get('error', 'Unknown error'))

                    image_data = base64.b64decode(response['image'])
                    self._validate_image(image_data)

                    return True, Image.open(BytesIO(image_data)), None

            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt == self.config.max_retries - 1:
                    return False, None, str(e)

            finally:
                if writer:
                    writer.close()
                    await writer.wait_closed()

        return False, None, "Max retries exceeded"

async def main():
    server = DisplaySocketServer()
    await server.start()

    # Example usage
    image = Image.new('RGB', (100, 100), color='red')
    await server.send_image(image)

    client = DisplaySocketClient()
    success, received_image, error = await client.get_image()
    if success:
        print("Image received successfully")
    else:
        print(f"Failed to receive image: {error}")

    await server.stop()

if __name__ == "__main__":
    asyncio.run(main())
