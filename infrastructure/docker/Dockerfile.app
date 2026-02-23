# Dockerfile for Next.js App
FROM node:22-alpine AS base

# Install dependencies only when needed
FROM base AS deps
RUN apk add --no-cache libc6-compat

WORKDIR /app

# Install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

# Copy package files
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY frontend/package.json ./frontend/
COPY turbo.json ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Development image
FROM deps AS dev
WORKDIR /app

ENV NODE_ENV=development
ENV WATCHPACK_POLLING=true

# Copy source code
COPY frontend ./frontend
COPY turbo.json ./
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./

CMD ["pnpm", "dev:app"]

# Build the application
FROM base AS builder
WORKDIR /app

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/frontend/node_modules ./frontend/node_modules

# Copy source code
COPY frontend ./frontend
COPY turbo.json ./
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./

# Enable pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

# Build the Next.js app
RUN pnpm --filter @repo/app build

# Production image
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy built application
COPY --from=builder /app/frontend/public ./frontend/public
COPY --from=builder --chown=nextjs:nodejs /app/frontend/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/frontend/.next/static ./frontend/.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "frontend/server.js"]
