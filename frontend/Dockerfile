# --- build stage -------------------------------------------------------------
FROM node:20-alpine AS build

WORKDIR /app

# Copy manifests first so installs are cached and only re-run when deps change,
# not on every source edit.
COPY package.json package-lock.json ./

# `npm install`, not `npm ci`, deliberately.
#
# Vite 8 builds on rolldown, whose native bindings are platform-specific
# optional dependencies. A lock file generated on Windows cannot satisfy
# `npm ci`'s strict cross-platform check inside a Linux image:
#
#   npm error `npm ci` can only install packages when your package.json and
#   package-lock.json are in sync.
#   npm error Missing: @emnapi/core@1.11.2 from lock file
#
# This is long-standing npm behaviour with optional platform deps
# (npm/cli#4828), not a corrupt lock. `npm install` resolves per-platform and
# still honours the lock for everything else.
#
# Trade-off: builds are slightly less reproducible than `npm ci` would give.
# Acceptable here — the alternative is committing a Linux-generated lock that
# then breaks local development on Windows.
RUN npm install --no-audit --no-fund

# Vite inlines env vars at BUILD time, not runtime — VITE_API_URL is baked into
# the bundle here and cannot be changed by setting an env var on the container.
# Defaults to localhost:8000 because the browser resolves this, not the
# container: the request leaves the user's machine, so it must target the
# published host port rather than the compose service name.
ARG VITE_API_URL=http://localhost:8000/api/v1
ENV VITE_API_URL=$VITE_API_URL

COPY . .
RUN npm run build

# --- serve stage -------------------------------------------------------------
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 5173 rather than 80 so the origin matches the backend's CORS allowlist and the
# URL is identical to `npm run dev`.
EXPOSE 5173

# 127.0.0.1, not localhost: nginx binds 0.0.0.0:5173 (IPv4 only), while
# `localhost` resolves to [::1] first inside the container, so an otherwise
# healthy container reports Connection refused forever.
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1:5173/ >/dev/null 2>&1 || exit 1

CMD ["nginx", "-g", "daemon off;"]
