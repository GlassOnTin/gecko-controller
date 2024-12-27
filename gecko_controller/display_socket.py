 # gecko_controller/display_socket.py

import socket
import os
import json
import base64
import logging
from io import BytesIO
from PIL import Image
from typing import Optional, Tuple

SOCKET_PATH = "/tmp/gecko-display.sock"
CHUNK_SIZE = 4096
TIMEOUT = 2  # seconds

class DisplaySocketServer:
    """Server-side socket handler for sharing display image data"""

    def __init__(self):
        self.logger = logging.getLogger('gecko_controller.display_socket')
        self._cleanup_socket()
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        # Remove the timeout on the listening socket
        self.sock.bind(SOCKET_PATH)
        os.chmod(SOCKET_PATH, 0o666)
        self.sock.listen(1)
        self.logger.info(f"Display socket server listening on {SOCKET_PATH}")

    def _cleanup_socket(self):
        """Remove existing socket file if it exists"""
        try:
            if os.path.exists(SOCKET_PATH):
                os.unlink(SOCKET_PATH)
        except Exception as e:
            self.logger.error(f"Error cleaning up socket: {e}")

    def send_image(self, image: Image.Image) -> bool:
        """
        Accept a connection and send the current display image

        Args:
            image: PIL Image to send

        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            # Accept will now block until a client connects - this is what we want
            client, _ = self.sock.accept()

            # Only set timeout for the client communication
            client.settimeout(TIMEOUT)

            try:
                # Convert image to PNG bytes
                buffer = BytesIO()
                image.save(buffer, format='PNG')
                img_bytes = buffer.getvalue()

                # Encode as base64
                img_b64 = base64.b64encode(img_bytes).decode()

                # Create JSON response
                response = {
                    'status': 'success',
                    'image': img_b64
                }

                # Send JSON response
                msg = json.dumps(response).encode()
                client.sendall(len(msg).to_bytes(4, byteorder='big'))
                client.sendall(msg)

                return True

            finally:
                client.close()

        except socket.timeout:
            self.logger.warning("Socket timeout waiting for connection")
            return False
        except Exception as e:
            self.logger.error(f"Error sending image: {e}")
            return False

    def __del__(self):
        """Clean up socket on deletion"""
        try:
            self.sock.close()
            self._cleanup_socket()
        except:
            pass

class DisplaySocketClient:
    """Client-side socket handler for receiving display image data"""

    def __init__(self):
        self.logger = logging.getLogger('gecko_controller.display_socket')
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(TIMEOUT)

    def get_image(self) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Request current display image from the controller

        Returns:
            Tuple containing:
            - bool: Success status
            - Optional[str]: Base64 encoded image data if successful, None if failed
            - Optional[str]: Error message if failed, None if successful
        """
        try:
            # Connect to socket
            self.sock.connect(SOCKET_PATH)

            try:
                # Read message length (4 bytes)
                length_bytes = self.sock.recv(4)
                if not length_bytes:
                    return False, None, "No data received"

                msg_length = int.from_bytes(length_bytes, byteorder='big')

                # Read message in chunks
                chunks = []
                bytes_received = 0

                while bytes_received < msg_length:
                    chunk_size = min(CHUNK_SIZE, msg_length - bytes_received)
                    chunk = self.sock.recv(chunk_size)
                    if not chunk:
                        return False, None, "Connection closed prematurely"
                    chunks.append(chunk)
                    bytes_received += len(chunk)

                # Parse JSON response
                msg = b''.join(chunks).decode()
                data = json.loads(msg)

                if data['status'] == 'success':
                    return True, data['image'], None
                else:
                    return False, None, data.get('error', 'Unknown error')

            finally:
                self.sock.close()

        except socket.timeout:
            return False, None, "Connection timed out"
        except ConnectionRefusedError:
            return False, None, "Connection refused (is the controller running?)"
        except Exception as e:
            self.logger.error(f"Error getting image: {e}")
            return False, None, str(e)
