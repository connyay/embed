FROM rust:1-bookworm as builder

WORKDIR /usr/src/app
COPY . .

# Cache dependencies and build in release mode
RUN --mount=type=cache,target=/usr/local/cargo,from=rust:latest,source=/usr/local/cargo \
    --mount=type=cache,target=target \
    cargo build --release && mv ./target/release/embed-proxy ./embed-proxy

# Runtime image
FROM debian:bookworm-slim

# Install CA certificates for HTTPS requests to backends
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

# Run as non-root user
RUN useradd -ms /bin/bash app

USER app
WORKDIR /app

COPY --from=builder /usr/src/app/embed-proxy /app/embed-proxy

EXPOSE 8080

CMD ["./embed-proxy"]
