#!/bin/sh

# builds the image of FlowerEvolver-backend (Alpine). Run it from the repo root:
#   sh .devops/build_docker.sh
# `flowerevolver` has no musl wheels on PyPI, so the build stage compiles it (needs access to GitHub, a few minutes).
echo "building docker Alpine..."
docker build -t docker.io/cristianglezm/fe:backend-alpine-dev -f dockerfile.alpine .
