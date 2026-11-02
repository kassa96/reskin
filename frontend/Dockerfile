# Build Angular (prod -> environment.prod.ts, cf. angular.json fileReplacements)
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

# Image finale : nginx sert le statique + proxy API vers le backend.
# Le frontend appelle l'API en relatif (/api/...), donc pas de CORS à gérer
# et ça fonctionne avec une simple IP, sans nom de domaine.
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/frontend/browser /usr/share/nginx/html
EXPOSE 80
