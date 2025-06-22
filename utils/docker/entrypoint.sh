#!/bin/sh

# Download the latest coins file, creating the directory if it doesn't exist
mkdir -p /root/.kdf
curl -o /root/.kdf/coins https://raw.githubusercontent.com/KomodoPlatform/coins/refs/heads/master/coins

# Execute the main container command
exec /kdf/target/release/kdf 