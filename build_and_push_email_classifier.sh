#!/bin/bash

# Set your GitHub username and repository
USERNAME="veer034"  # Your GitHub username
REGISTRY="ghcr.io"
REPO_NAME="cn-lexi-gen-ai"  # Repository name
VERSION="1.0.0"     # Version tag for your image

# Prompt for the GitHub Personal Access Token (PAT)
read -sp "Enter your GitHub Personal Access Token: " PAT
echo ""

# Function to fetch a JWT token for API requests
get_jwt_token() {
    curl -s -u "$USERNAME:$PAT" \
        -H "Accept: application/vnd.github+json" \
        https://ghcr.io/token\?scope\="repository:$USERNAME/$1:pull" \
        | jq -r '.token'
}

# Log in to GitHub Container Registry securely for Docker CLI
echo "Logging into GitHub Container Registry..."
if ! echo "$PAT" | docker login $REGISTRY -u "$USERNAME" --password-stdin; then
    echo "Login failed. Please check your Personal Access Token and permissions."
    exit 1
fi

# Build the Docker image
echo "Building Docker image: $REPO_NAME:$VERSION..."
if ! docker build -t "$REPO_NAME:$VERSION" .; then
    echo "Error: Failed to build Docker image. Exiting."
    exit 1
fi

# Tag the image for the target repository
TARGET="$REGISTRY/$USERNAME/$REPO_NAME:$VERSION"
echo "Tagging $REPO_NAME:$VERSION as $TARGET..."
docker tag "$REPO_NAME:$VERSION" "$TARGET"

# Fetch JWT token for API requests
JWT_TOKEN=$(get_jwt_token "$REPO_NAME")
if [[ -z "$JWT_TOKEN" ]]; then
    echo "Error: Failed to fetch JWT token for $REPO_NAME."
    exit 1
fi

# Check if the image exists in the registry
echo "Checking if $REPO_NAME:$VERSION already exists in the registry..."
RESPONSE=$(curl -s -o response.json -w "%{http_code}" \
    -H "Authorization: Bearer $JWT_TOKEN" \
    "https://ghcr.io/v2/$USERNAME/$REPO_NAME/manifests/$VERSION")

if [[ "$RESPONSE" == "403" ]]; then
    echo "Error: Authentication failed for $REPO_NAME. Check token permissions."
    cat response.json
    rm -f response.json
    exit 1
elif [[ "$RESPONSE" == "200" ]]; then
    echo "Warning: $REPO_NAME:$VERSION already exists in the registry. Proceeding to override."
elif [[ "$RESPONSE" == "404" ]]; then
    echo "$REPO_NAME:$VERSION does not exist in the registry. Proceeding with push."
else
    echo "Unexpected response: $RESPONSE"
    cat response.json
    rm -f response.json
    exit 1
fi

rm -f response.json

# Push the image to the target repository
echo "Pushing $TARGET..."
if ! docker push "$TARGET"; then
    echo "Error: Failed to push $TARGET. Exiting."
    exit 1
fi

echo "Vector Search Service image successfully built and pushed to GitHub Container Registry!"
echo "Image URL: $TARGET"