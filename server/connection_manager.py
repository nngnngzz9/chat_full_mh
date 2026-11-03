import asyncio

from server.authentication import (
    generate_receiver_id,
    hash_password,
    verify_password
)


class ConnectionManager:
    def __init__(self):
        self.receivers = {}
        self.lock = asyncio.Lock()

    async def register_receiver(self, websocket, password):
        salt, password_hash = hash_password(password)

        async with self.lock:
            receiver_id = generate_receiver_id()

            while receiver_id in self.receivers:
                receiver_id = generate_receiver_id()

            self.receivers[receiver_id] = {
                "websocket": websocket,
                "salt": salt,
                "password_hash": password_hash,
                "sender": None
            }

        return receiver_id

    async def connect_sender(self, receiver_id, password, websocket):
        async with self.lock:
            receiver = self.receivers.get(receiver_id)

            if receiver is None:
                return "receiver_not_found"

            if not verify_password(
                password,
                receiver["salt"],
                receiver["password_hash"]
            ):
                return "wrong_password"

            if receiver["sender"] is not None:
                return "already_connected"

            receiver["sender"] = websocket

            return "connected"

    async def disconnect_receiver(self, receiver_id, websocket):
        async with self.lock:
            receiver = self.receivers.get(receiver_id)

            if receiver is None:
                return None

            if receiver["websocket"] is not websocket:
                return None

            sender = receiver["sender"]
            del self.receivers[receiver_id]

            return sender

    async def disconnect_sender(self, receiver_id, websocket):
        async with self.lock:
            receiver = self.receivers.get(receiver_id)

            if receiver is None:
                return False

            if receiver["sender"] is not websocket:
                return False

            receiver["sender"] = None

            return True


manager = ConnectionManager()
