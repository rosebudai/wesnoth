#!/usr/bin/env python3
"""WebSocket-to-TCP proxy for Wesnoth campaignd (add-on server).

Each WebSocket connection to ws://host:port/{target_host}/{target_port}
opens a TCP connection to target_host:target_port and transparently
forwards binary data in both directions.

Requirements: pip install websockets

Usage:
    python3 ws_proxy.py [--port 8041] [-v]
"""

import argparse
import asyncio
import logging
import sys

try:
    import websockets
except ImportError:
    print(
        "ERROR: 'websockets' package required.\n"
        "Install with: pip install websockets",
        file=sys.stderr,
    )
    sys.exit(1)

log = logging.getLogger("ws_proxy")


async def proxy_handler(websocket):
    """Handle a single WebSocket connection by proxying to TCP."""
    # Support both old (websocket.path) and new (websocket.request.path) API.
    try:
        path = websocket.request.path
    except AttributeError:
        path = websocket.path

    parts = path.strip("/").split("/")
    if len(parts) != 2:
        log.warning("Bad path: %s (expected /host/port)", path)
        await websocket.close(1008, "Path must be /host/port")
        return

    target_host, target_port_str = parts
    try:
        target_port = int(target_port_str)
    except ValueError:
        await websocket.close(1008, f"Invalid port: {target_port_str}")
        return

    log.info("New connection → TCP %s:%d", target_host, target_port)

    try:
        reader, writer = await asyncio.open_connection(target_host, target_port)
    except Exception as e:
        log.error("TCP connect to %s:%d failed: %s", target_host, target_port, e)
        await websocket.close(1011, f"TCP connect failed: {e}")
        return

    async def ws_to_tcp():
        """Forward WebSocket binary frames → TCP."""
        try:
            async for message in websocket:
                if isinstance(message, bytes):
                    writer.write(message)
                    await writer.drain()
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def tcp_to_ws():
        """Forward TCP bytes → WebSocket binary frames."""
        try:
            while True:
                data = await reader.read(65536)
                if not data:
                    break
                await websocket.send(data)
        except (websockets.exceptions.ConnectionClosed, ConnectionError):
            pass
        finally:
            try:
                await websocket.close(1000)
            except Exception:
                pass

    try:
        await asyncio.gather(ws_to_tcp(), tcp_to_ws())
    except Exception as e:
        log.error("Proxy error for %s:%d: %s", target_host, target_port, e)
    finally:
        log.info("Connection closed for %s:%d", target_host, target_port)


async def main(port: int) -> None:
    async with websockets.serve(proxy_handler, "0.0.0.0", port):
        log.info("WebSocket-to-TCP proxy listening on ws://0.0.0.0:%d", port)
        log.info("Connect to: ws://localhost:%d/{host}/{port}", port)
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="WebSocket-to-TCP proxy for Wesnoth add-on server"
    )
    parser.add_argument(
        "--port", type=int, default=8041, help="Listen port (default: 8041)"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    try:
        asyncio.run(main(args.port))
    except KeyboardInterrupt:
        pass
