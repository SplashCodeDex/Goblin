# Simple dev-oriented Dockerfile for Next.js app
FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json* pnpm-lock.yaml* yarn.lock* ./
RUN npm install --legacy-peer-deps || true
COPY . .
RUN chmod +x ./wait-for-api.sh || true
EXPOSE 3000
CMD ["sh", "-lc", "./wait-for-api.sh npm run dev"]
