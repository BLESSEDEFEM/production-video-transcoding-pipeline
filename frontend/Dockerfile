# ─────────────────────────────────────────────────────────────────
# STAGE 1: BUILD
# Build the Next.js app into static files
# ─────────────────────────────────────────────────────────────────
# node:18-alpine = Node.js 18 on Alpine Linux (very small image)
# "alpine" = tiny Linux (5MB vs 150MB for regular Debian)
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files first (same reason as Python — cache optimization)
COPY package.json package-lock.json* ./

# Install all Node dependencies
RUN npm ci
# npm ci = "clean install" — faster and more reliable than npm install
# Uses package-lock.json exactly (no version drift)

# Copy all frontend code
COPY . .

# Build the Next.js app
# This creates an optimized production build in the .next/ folder
RUN npm run build

# ─────────────────────────────────────────────────────────────────
# STAGE 2: PRODUCTION IMAGE
# Only keep what's needed to RUN the app (not build it)
# ─────────────────────────────────────────────────────────────────
# This is called "multi-stage build"
# The builder stage has all build tools (compilers, etc.)
# The production stage only has the runtime
# Final image is MUCH smaller
FROM node:20-alpine AS runner

WORKDIR /app

# Copy ONLY the built output from builder stage
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/public ./public

EXPOSE 3000

# next start = run the production Next.js server
CMD ["npm", "run", "start"]