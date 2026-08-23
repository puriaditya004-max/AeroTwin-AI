# AeroTwin AI - Operator HMI (M6)
# Multi-stage build: compile the Vite app, serve the static output via nginx.

FROM node:20-alpine AS build
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
# Baked in at build time — for the Docker Compose demo this points at the
# control-api service name, not localhost. Override with --build-arg if needed.
ARG VITE_CONTROL_API_URL=http://localhost:4000
ARG VITE_HMI_MODE=DEMO
ENV VITE_CONTROL_API_URL=$VITE_CONTROL_API_URL
ENV VITE_HMI_MODE=$VITE_HMI_MODE
RUN npm run build

# ---------------------------------------------------------------------------

FROM nginx:1.27-alpine AS production
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=5 \
  CMD wget -q -O /dev/null http://localhost:80 || exit 1

CMD ["nginx", "-g", "daemon off;"]