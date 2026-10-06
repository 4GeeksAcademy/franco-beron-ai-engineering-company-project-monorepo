FROM node:22-alpine

WORKDIR /app

COPY website/package.json website/package-lock.json ./website/
RUN cd website && npm ci

COPY backoffice/package.json backoffice/package-lock.json ./backoffice/
RUN cd backoffice && npm ci

COPY . .
RUN chmod +x /app/start.sh

EXPOSE 3000 3001

CMD ["/app/start.sh"]