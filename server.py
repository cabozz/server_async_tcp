import asyncio
import threading
from datetime import datetime

clients = {}  # {addr: writer}
console_queue = asyncio.Queue()

async def handle_client(reader, writer):
    addr = writer.get_extra_info('peername')
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [NEW CONNECTION] {addr}")
    clients[addr] = writer
    try:
        while True:
            data = await reader.read(1024)
            if not data:
                break
            message = data.decode().strip()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [FROM {addr}] {message}")
    except ConnectionResetError:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [DISCONNECTED] {addr} forcibly closed the connection.")
    finally:
        writer.close()
        await writer.wait_closed()
        del clients[addr]
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [DISCONNECTED] {addr} connection closed.")

async def send_to_client(addr, message):
    if addr in clients:
        writer = clients[addr]
        writer.write(message.encode())
        await writer.drain()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [SENT to {addr}] {message}")
    else:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [ERROR] Client {addr} not connected.")

async def broadcast(message):
    for addr in clients.keys():
        await send_to_client(addr, message)

async def periodic_broadcast(interval=10):
    """Send a message to all clients periodically"""
    while True:
        await asyncio.sleep(interval)
        if clients:
            await broadcast(f"Server periodic message at {datetime.now().strftime('%H:%M:%S')}")

async def console_sender():
    while True:
        line = await console_queue.get()
        if line.startswith("/all "):
            await broadcast(line[5:])
        elif line.startswith("/send "):
            try:
                rest = line[6:]
                target, msg = rest.split(" ", 1)
                ip, port = target.split(":")
                addr = (ip, int(port))
                await send_to_client(addr, msg)
            except Exception as e:
                print("Invalid format. Use: /send ip:port message")
        elif line.startswith("/list"):
            print("Connected clients:")
            for addr in clients.keys():
                print(addr)
        else:
            print("Unknown command. Use /all, /send, or /list.")

def input_thread():
    while True:
        line = input()
        asyncio.run_coroutine_threadsafe(console_queue.put(line), loop)

async def main():
    server = await asyncio.start_server(handle_client, "0.0.0.0", 12345)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [LISTENING] Server started on 0.0.0.0:12345")

    threading.Thread(target=input_thread, daemon=True).start()

    async with server:
        await asyncio.gather(
            server.serve_forever(),
            console_sender(),
            periodic_broadcast(10)  # broadcast every 10 seconds
        )

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
