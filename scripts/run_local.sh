#!/bin/bash

source ../.env

python get_local_issues.py ../filtered_issues.json

docker compose \
  -f ../docker-compose.yml \
  up --build