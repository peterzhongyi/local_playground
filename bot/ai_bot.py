import asyncio
import websockets
import json
import random
import logging
import requests
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get LLM service URL from environment variable or use default
LLM_SERVICE_URL = os.getenv('LLM_SERVICE_URL', '')

class GameBot:
    def __init__(self):
        self.server_url = "ws://34.46.118.8:7117?type=ai"
        self.player_id = None
        self.connected = False
        self.conversation_history = []  # Keep track of conversation for context

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
                
                # Handle chat messages and respond
                if data['type'] == 'chat' and data['from'] != self.player_id:
                    logger.info(f"Received message: {data['message']}")
                    # Generate and send response
                    await self.send_chat_response(data['message'])

            except Exception as e:
                logger.error(f"Error handling message: {e}")
                self.connected = False
                break

    async def query_llm(self, prompt):
        try:
            payload = {
                "inputs": prompt,
                "parameters": {
                    "temperature": 0.70,
                    "top_p": 0.9,
                    "max_new_tokens": 128
                }
            }
            
            response = requests.post(LLM_SERVICE_URL, json=payload)
            response.raise_for_status()
            
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error querying LLM service: {e}")
            return None

    async def send_chat_response(self, received_message):
        try:
            # Get response from LLM
            context = f"You are a bot. You are in a 10x10 grid. You can move up, down, left, or right in the grid. A human has sent you this message: {received_message}. How do you respond?"
            llm_response = await self.query_llm(context + received_message)
            
            if llm_response:
                # Send the response
                response_text = llm_response.get('generated_text', 'I cannot respond right now.')
                await self.websocket.send(json.dumps({
                    'type': 'chat',
                    'message': response_text
                }))
                logger.info(f"Sent LLM response: {response_text}")

                # Check if response implies movement and move accordingly
                await self.handle_movement_from_response(response_text.lower())
        except Exception as e:
            logger.error(f"Error sending chat response: {e}")
            self.connected = False

    async def handle_movement_from_response(self, response_text):
        try:
            # Query LLM to determine movement
            movement_prompt = f"""Given your response: "{response_text}"
            Should you move? If yes, choose exactly one word from these options: "up", "down", "left" or "right". If no, output "no_movement".
            Don't output anything else."""
            
            movement_response = await self.query_llm(movement_prompt)
            print("movement_response is:")
            print(movement_response)
            
            if movement_response:
                movement_text = movement_response.get('generated_text', '').strip().lower()
                logger.info(f"Movement text from LLM: {movement_text}")
                if movement_text != 'no_movement' and movement_text in ['up', 'down', 'left', 'right']:
                    movement_json = {
                        'type': 'move',
                        'direction': movement_text
                    }
                    await self.websocket.send(json.dumps(movement_json))
                    logger.info(f"Moving {movement_text} based on response: {response_text}")
                        
        except Exception as e:
            logger.error(f"Error handling movement from response: {e}")
            self.connected = False

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
    
    # Create remaining tasks
    tasks = [
        asyncio.create_task(bot.handle_messages()),
        asyncio.create_task(bot.reconnect_if_needed())
    ]
    
    # Run tasks concurrently
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main()) 