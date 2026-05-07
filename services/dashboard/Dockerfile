# Multi-stage build for FLOW Dashboard
FROM node:18-alpine as builder

WORKDIR /app

# Copy package files
COPY services/dashboard/package.json services/dashboard/package-lock.json* ./

# Install dependencies
RUN npm ci

# Copy source code
COPY services/dashboard/ .

# Build the application
RUN npm run build

# Production stage
FROM nginx:alpine

# Install htpasswd utility
RUN apk add --no-cache apache2-utils

# Copy built application
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY services/dashboard/nginx.conf /etc/nginx/nginx.conf

# Generate the credentials file at container startup from environment variables.
COPY services/dashboard/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 80

ENTRYPOINT ["/docker-entrypoint.sh"]