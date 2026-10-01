FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.29-alpine
COPY nginx/app.conf nginx/security-headers.conf nginx/log-format.conf /etc/nginx/snippets/
# Local run: plain HTTP.
COPY nginx/local.conf /etc/nginx/conf.d/default.conf
# Production: HTTPS. Used only when NGINX_ENVSUBST_TEMPLATE_DIR points here
# (docker-compose.prod.yml); the result replaces conf.d/default.conf.
COPY nginx/prod.conf.template /etc/nginx/templates-prod/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
