import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from server.connection_manager import manager


app = FastAPI(title="MyDesktopApp Relay Server")


@app.get("/")
async def home():
    return {
        "status": "online",
        "server": "MyDesktopApp Relay Server"
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    role = None
    receiver_id = None

    try:
        data = await websocket.receive_json()
        role = data.get("role")

        # Receiver registration
        if role == "receiver":
            password = data.get("password", "")
            desired_id = str(data.get("receiver_id") or "")

            receiver_id = await manager.register_receiver(
                websocket,
                password,
                desired_id
            )

            await websocket.send_json({
                "type": "registered",
                "receiver_id": receiver_id
            })

            if manager.receivers[receiver_id]["sender"] is not None:
                await websocket.send_json({
                    "type": "sender_connected"
                })

            while True:
                data = await websocket.receive_json()

                if data.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong"
                    })

        # Sender authentication
        elif role == "sender":
            receiver_id = str(data.get("receiver_id", ""))
            password = data.get("password", "")

            result = await manager.connect_sender(
                receiver_id,
                password,
                websocket
            )

            if result != "connected":
                await websocket.send_json({
                    "type": "error",
                    "message": result
                })
                await websocket.close()
                return

            receiver = manager.receivers[receiver_id]

            await websocket.send_json({
                "type": "connected"
            })

            await receiver["websocket"].send_json({
                "type": "sender_connected"
            })

            while True:
                data = await websocket.receive_json()

                if data.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong"
                    })
                    continue

                if data.get("type") == "message":
                    message = data.get("text", "")

                    if not isinstance(message, str) or not message.strip():
                        continue

                    if len(message) > 5000:
                        await websocket.send_json({
                            "type": "error",
                            "message": "message_too_long"
                        })
                        continue

                    await receiver["websocket"].send_json({
                        "type": "message",
                        "text": message
                    })

        else:
            await websocket.send_json({
                "type": "error",
                "message": "invalid_role"
            })
            await websocket.close()

    except WebSocketDisconnect:
        pass

    except Exception as e:
        print("WebSocket error:", e)

    finally:
        if role == "receiver" and receiver_id:
            sender = await manager.disconnect_receiver(
                receiver_id,
                websocket
            )

            if sender:
                try:
                    await sender.send_json({
                        "type": "disconnected",
                        "message": "Receiver disconnected"
                    })
                    await sender.close()
                except Exception:
                    pass

        elif role == "sender" and receiver_id:
            disconnected = await manager.disconnect_sender(
                receiver_id,
                websocket
            )

            if disconnected:
                receiver = manager.receivers.get(receiver_id)

                if receiver:
                    try:
                        await receiver["websocket"].send_json({
                            "type": "sender_disconnected"
                        })
                    except Exception:
                        pass

        print("Client disconnected")
