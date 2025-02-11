FROM node:18-slim

WORKDIR /app

# Install required dependencies for Agones SDK
RUN apt-get update && apt-get install -y wget

COPY package.json .
RUN npm install

COPY server.js .
COPY public/ public/

# Default game server port
EXPOSE 3000
# Default Agones SDK port
EXPOSE 9357

HEALTHCHECK --interval=5s --timeout=5s \
  CMD wget -q -O - http://localhost:3000/ || exit 1

CMD ["node", "server.js"] 