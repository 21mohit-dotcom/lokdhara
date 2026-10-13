# The contributor app, built once and served by Caddy, which also forwards /api to the API.
FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM caddy:2.10-alpine
COPY --from=build /app/dist /srv
COPY Caddyfile.demo /etc/caddy/Caddyfile
