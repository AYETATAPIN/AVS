FROM golang:1.25-alpine AS builder
WORKDIR /app
COPY . .
RUN go mod download && go build -o ingest-go .

FROM alpine
COPY --from=builder /app/ingest-go /ingest-go
CMD ["/ingest-go"]