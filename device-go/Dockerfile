FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY . .
RUN go build -mod=readonly -o main ./cmd/device-go

FROM alpine
COPY --from=builder /app/main /main
CMD ["/main"]