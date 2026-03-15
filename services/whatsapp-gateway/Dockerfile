FROM golang:1.25-alpine AS builder
WORKDIR /src

COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o /out/whatsapp-gateway .

FROM alpine:3.21
WORKDIR /app

RUN adduser -D -u 10001 appuser
RUN mkdir -p /data && chown -R appuser:appuser /data

COPY --from=builder /out/whatsapp-gateway /usr/local/bin/whatsapp-gateway

USER appuser
EXPOSE 8090

ENTRYPOINT ["whatsapp-gateway"]
