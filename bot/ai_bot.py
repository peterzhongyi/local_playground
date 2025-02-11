import asyncio
import websockets
import json
import random
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GameBot:
    def __init__(self):
        self.server_url = "ws://34.46.118.8:7117?type=ai"
        self.player_id = None
        self.connected = False

    async def connect(self):
        while not self.connected:
            try:
                self.websocket = await websockets.connect(self.server_url)
                self.connected = True
                logger.info("Connected to game server")
            except Exception as e:
                logger.error(f"Connection failed: {e}")
                await asyncio.sleep(5)

    async def handle_messages(self):
        while True:
            try:
                message = await self.websocket.recv()
                data = json.loads(message)
                
                if data['type'] == 'init':
                    self.player_id = data['playerId']
                    logger.info(f"Initialized with player ID: {self.player_id}")
                
                # Log game state updates
                if data['type'] == 'gameState':
                    if self.player_id in data['gameState']['players']:
                        pos = data['gameState']['players'][self.player_id]
                        logger.info(f"Current position: x={pos['x']}, y={pos['y']}")

            except Exception as e:
                logger.error(f"Error handling message: {e}")
                self.connected = False
                break

    async def move_randomly(self):
        while True:
            if self.connected:
                direction = random.choice(['up', 'down', 'left', 'right'])
                try:
                    await self.websocket.send(json.dumps({
                        'type': 'move',
                        'direction': direction
                    }))
                    logger.info(f"Moving {direction}")
                except Exception as e:
                    logger.error(f"Error sending move: {e}")
                    self.connected = False
                    break
            await asyncio.sleep(5)

    async def reconnect_if_needed(self):
        while True:
            if not self.connected:
                logger.info("Attempting to reconnect...")
                await self.connect()
            await asyncio.sleep(1)

async def main():
    bot = GameBot()
    
    # First ensure we're connected
    await bot.connect()
    
    # Create remaining tasks only after connection is established
    tasks = [
        asyncio.create_task(bot.handle_messages()),
        asyncio.create_task(bot.move_randomly()),
        asyncio.create_task(bot.reconnect_if_needed())
    ]
    
    # Run remaining tasks concurrently
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main()) 