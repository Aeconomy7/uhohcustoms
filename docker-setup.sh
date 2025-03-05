#!/bin/bash

# Name of the container to monitor
CONTAINER_NAME="uhohcustoms"

# Function to check if the container is running
is_container_running() {
    docker ps --filter "name=$CONTAINER_NAME" --filter "status=running" -q
}

is_container_exists() {
    docker ps -a --filter "name=$CONTAINER_NAME" -q
}

# Function to stop the container
stop_container() {
    echo "[+] Stopping container $CONTAINER_NAME..."
    docker stop $CONTAINER_NAME
}

remove_container() {
    echo "[+] Removing container $CONTAINER_NAME..."
    docker rm $CONTAINER_NAME
}


# Check if the container is running and stop it if necessary
if [ -n "$(is_container_running)" ]; then
    echo "[?] Container $CONTAINER_NAME is running."
    stop_container
fi

# Check if the container exists and remove it if necessary
if [ -n "$(is_container_exists)" ]; then
    echo "[?] Container $CONTAINER_NAME exists."
    remove_container
fi
sleep 3


# Build the docker container
docker build --pull --rm -f 'Dockerfile' -t "$CONTAINER_NAME:latest" '.'

# Run the docker container
docker run -d -p 80:80 -p 443:443 --name $CONTAINER_NAME $CONTAINER_NAME:latest

# list dockers
docker ps

# start interactive session
docker exec -it $CONTAINER_NAME /bin/bash
