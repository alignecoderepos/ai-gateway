FROM golang:1.20 AS builder
WORKDIR /src
COPY . .
RUN go build -o /bin/ai-gateway ./cmd/gateway

FROM gcr.io/distroless/base-debian11
COPY --from=builder /bin/ai-gateway /bin/ai-gateway
ENTRYPOINT ["/bin/ai-gateway"]
