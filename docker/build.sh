#!/bin/bash

DIRECTORY=${1:-zones}  # Default to 'zones' if no argument provided

# Check if the provided directory exists in the current directory
if [[ ! -d $DIRECTORY ]]; then
    echo "Error: $DIRECTORY directory not found in current directory."
    exit 1
fi

# If named.conf does not exist, run namedgen.py to generate it
if [[ ! -f named.conf ]]; then
    echo "named.conf not found. Generating using namedgen.py..."
    python3 namedgen.py "$DIRECTORY"
    # Check if namedgen.py successfully created named.conf
    if [[ $? -ne 0 || ! -f named.conf ]]; then
        echo "Error: Unable to generate named.conf."
        exit 1
    fi
fi

# Build the Docker image with the directory name as a build argument
docker build --build-arg DIRECTORY_NAME=$DIRECTORY -t bind-server .

# Run the container
docker run -d --name bind-server -p 53:53/udp -p 53:53/tcp bind-server
