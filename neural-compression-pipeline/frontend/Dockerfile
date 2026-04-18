FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY . .

ARG VITE_OCR_URL=http://localhost:8001
ARG VITE_COMPRESS_URL=http://localhost:8002
ENV VITE_OCR_URL=${VITE_OCR_URL}
ENV VITE_COMPRESS_URL=${VITE_COMPRESS_URL}

RUN npm run build

FROM nginx:alpine

RUN apk add --no-cache curl

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
