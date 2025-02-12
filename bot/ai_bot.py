import asyncio
import websockets
import json
import random
import logging
import requests
import os
from difflib import get_close_matches

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get LLM service URL from environment variable or use default
LLM_SERVICE_URL = os.getenv('LLM_SERVICE_URL', '')

class GameBot:
    def __init__(self):
        self.server_url = f"ws://{os.getenv('GAME_SERVER_HOST', 'localhost')}:{os.getenv('GAME_SERVER_PORT', '7117')}?type=ai"
        self.player_id = None
        self.connected = False
        self.conversation_history = []  # List of (speaker, message) tuples
        self.max_history = 5  # Keep last 5 messages for context

    async def connect(self):
        while not self.connected:
            try:
                print(f"Connecting to server at {self.server_url}")
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
            print(f"Processing prompt --- {prompt}")
            payload = {
                "inputs": f"<start_of_turn>user\n{prompt}<end_of_turn>\n",
                "parameters": {
                    "temperature": 0.1,
                    "top_p": 0.95,
                    "max_new_tokens": 128
                }
            }

            headers = {
                "Content-Type": "application/json"
            }
            
            response = requests.post(LLM_SERVICE_URL, json=payload, headers=headers)
            response.raise_for_status()
            
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error querying LLM service: {e}")
            return None

    async def send_chat_response(self, received_message):
        try:
            # Add received message to history
            self.conversation_history.append(("human", received_message))
            self.conversation_history = self.conversation_history[-self.max_history:]  # Keep last N messages

            # Build conversation context
            conversation_context = "\n".join([
                f"{'Human' if speaker == 'human' else 'You'}: {message}"
                for speaker, message in self.conversation_history
            ])

            # Get response from LLM
            prompt = f"""You are a bot. You are in a 10x10 grid. You can move up, down, left, or right in the grid. Here's your previous conversation: [{conversation_context}] What do you say in a simple sentence?"""
            
            llm_response = await self.query_llm(prompt)
            
            if llm_response:
                # Send the response
                response_text = llm_response.get('generated_text', 'I cannot respond right now.').strip()
                # Add bot's response to history
                self.conversation_history.append(("bot", response_text))
                self.conversation_history = self.conversation_history[-self.max_history:]  # Keep last N messages
                
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
            # Query LLM to determine movement, including conversation context
            conversation_context = "\n".join([
                f"{'Human' if speaker == 'human' else 'You'}: {message}"
                for speaker, message in self.conversation_history  # Use full conversation history for movement context
            ])

            movement_prompt = f"""You are a bot. You are in a 10x10 grid. You can move up, down, left, or right in the grid. What do you do now? IMPORTANT: SAY EXACTLY ONE WORD from ["up", "down", "left", "right"]. Previous conversation: [{conversation_context}]"""
            
            movement_response = await self.query_llm(movement_prompt)
                        
            if movement_response:
                print(f"movement_response --- {movement_response}")
                movement_text = movement_response.get('generated_text', '').strip().lower()
                print(f"movement_text turns out to be --- {movement_text}")
                directions = ['up', 'down', 'left', 'right']
                
                if movement_text in directions:
                    movement_json = {
                        'type': 'move',
                        'direction': movement_text
                    }
                    await self.websocket.send(json.dumps(movement_json))
                    logger.info(f"Moving {movement_text} based on response: {response_text}")
                else:
                    logger.info(f"Staying in place based on response: {response_text}")
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