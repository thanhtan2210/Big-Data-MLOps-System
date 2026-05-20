#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "postgres" <<-EOSQL
    CREATE DATABASE mlflow_registry;
    GRANT ALL PRIVILEGES ON DATABASE mlflow_registry TO $POSTGRES_USER;
EOSQL
