FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY . .
RUN go mod download && go build -o main ./cmd/device-go

FROM alpine
COPY --from=builder /app/main /main
CMD ["/main"]