const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const path = require('path');
const AgonesSDK = require('@google-cloud/agones-sdk');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });
const agonesSDK = new AgonesSDK();

// Serve static files from 'public' directory
app.use(express.static(path.join(__dirname, 'public')));

// Store connected players
const players = new Map();

// Game state
const GRID_SIZE = 10;
const gameState = {
    players: {}
};

// Initialize Agones
async function initAgones() {
    try {
        await agonesSDK.connect();
        console.log("Connected to Agones");
        
        // Mark server as ready
        await agonesSDK.ready();
        console.log("Server marked as ready");

        // Start health checking
        setInterval(async () => {
            try {
                await agonesSDK.health();
            } catch (err) {
                console.error("Failed to send health ping", err);
            }
        }, 1000);

    } catch (err) {
        console.error("Failed to initialize Agones:", err);
    }
}

wss.on('connection', async (ws, req) => {
    // Check if client is AI from URL parameters
    const isAI = new URL('ws://dummy' + req.url).searchParams.get('type') === 'ai';
    
    // Assign random starting position and ID
    const playerId = Math.random().toString(36).substr(2, 9);
    const playerState = {
        x: Math.floor(Math.random() * GRID_SIZE),
        y: Math.floor(Math.random() * GRID_SIZE),
        type: isAI ? 'ai' : 'human'  // Set type based on URL parameter
    };

    // Store player connection
    players.set(ws, playerId);
    gameState.players[playerId] = playerState;

    // Send initial game state to new player
    ws.send(JSON.stringify({
        type: 'init',
        playerId: playerId,
        gameState: gameState
    }));

    // Broadcast updated game state to all players
    broadcastGameState();

    // Update Agones player count
    try {
        await agonesSDK.alpha.setPlayerCapacity(10);
        await agonesSDK.alpha.playerConnect(playerId);
        const count = await agonesSDK.alpha.getPlayerCount();
        console.log(`Player connected. Total players: ${count}`);
    } catch (err) {
        console.error("Failed to update player count:", err);
    }

    // Handle messages from clients
    ws.on('message', (message) => {
        const data = JSON.parse(message);
        
        if (data.type === 'move') {
            const player = gameState.players[playerId];
            
            // Update player position
            switch(data.direction) {
                case 'up':
                    if (player.y > 0) player.y--;
                    break;
                case 'down':
                    if (player.y < GRID_SIZE - 1) player.y++;
                    break;
                case 'left':
                    if (player.x > 0) player.x--;
                    break;
                case 'right':
                    if (player.x < GRID_SIZE - 1) player.x++;
                    break;
            }

            // Broadcast updated state
            broadcastGameState();
        }
    });

    // Handle client disconnect
    ws.on('close', async () => {
        const playerId = players.get(ws);
        delete gameState.players[playerId];
        players.delete(ws);
        broadcastGameState();

        // Update Agones player count
        try {
            await agonesSDK.alpha.playerDisconnect(playerId);
            const count = await agonesSDK.alpha.getPlayerCount();
            console.log(`Player disconnected. Total players: ${count}`);

            // If no players are connected, shutdown after delay
            if (count === 0) {
                setTimeout(async () => {
                    const currentCount = await agonesSDK.alpha.getPlayerCount();
                    if (currentCount === 0) {
                        console.log("No players connected, shutting down server");
                        await agonesSDK.shutdown();
                    }
                }, 60000); // 1 minute delay
            }
        } catch (err) {
            console.error("Failed to update player disconnect:", err);
        }
    });
});

function broadcastGameState() {
    const message = JSON.stringify({
        type: 'gameState',
        gameState: gameState
    });
    
    wss.clients.forEach((client) => {
        if (client.readyState === WebSocket.OPEN) {
            client.send(message);
        }
    });
}

// Initialize Agones before starting the server
initAgones().then(() => {
    const PORT = process.env.PORT || 3000;
    server.listen(PORT, () => {
        console.log(`Server is running on port ${PORT}`);
    });
}).catch(err => {
    console.error("Failed to start server:", err);
    process.exit(1);
}); 