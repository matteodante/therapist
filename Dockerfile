FROM node:22.19.0-bookworm-slim AS build

RUN corepack enable && corepack prepare pnpm@11.1.1 --activate
WORKDIR /app

COPY package.json ./
RUN pnpm install --no-frozen-lockfile

COPY . .
RUN pnpm build

FROM node:22.19.0-bookworm-slim AS runtime

RUN corepack enable && corepack prepare pnpm@11.1.1 --activate
WORKDIR /app
ENV NODE_ENV=production

COPY package.json ./
RUN pnpm install --prod --no-frozen-lockfile
COPY --from=build /app/dist ./dist

RUN mkdir -p /app/data && chown -R node:node /app
USER node

EXPOSE 3583
CMD ["node", "dist/server.mjs"]
