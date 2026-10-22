# syntax=docker/dockerfile:1
# LombokSimHash CLI — static musl binary on a zero-base (scratch) image.
#
# Build:  docker build -t ghcr.io/codinglombok/lomboksimhash .
# Run:    docker run ghcr.io/codinglombok/lomboksimhash simhash "the fox"

FROM rust:1-alpine AS build
WORKDIR /build
RUN apk add --no-cache musl-dev
COPY Cargo.toml Cargo.lock* ./
COPY src ./src
RUN cargo build --release --bin lomboksimhash-cli

FROM scratch
COPY --from=build /build/target/release/lomboksimhash-cli /usr/local/bin/lomboksimhash
ENTRYPOINT ["/usr/local/bin/lomboksimhash"]
