# Contrato con el proyecto Vue (Dev C): en esta carpeta debe haber package.json + package-lock.json
# con un script "build" que genere la app estática en dist/ (default de Vite).
# El cliente debe llamar al backend con rutas relativas /api/...; Nginx las redirige al servicio backend.
FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
