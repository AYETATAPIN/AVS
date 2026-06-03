FROM golang:1.25-alpine AS builder
WORKDIR /app
COPY . .
RUN go build -mod=readonly -o main ./cmd/ingest-go

FROM alpine
COPY --from=builder /app/main /main
CMD ["/main"]
