FROM golang:1.25-alpine AS builder
WORKDIR /app
COPY . .
RUN go mod download && go build -o main ./cmd/ingest-go

FROM alpine
COPY --from=builder /app/main /main
CMD ["/main"]
