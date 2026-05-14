FROM node:20-alpine
WORKDIR /app
COPY package.json ./
RUN npm install && npm install -g tsx
COPY . .
CMD ["tsx", "main.ts"]
