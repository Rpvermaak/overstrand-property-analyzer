# Docker Deployment Guide for Overstrand Airbnb Analyzer

## Quick Start for Partners

### Option 1: Run with Docker (Recommended)

If you have Docker installed:

```bash
# Pull and run the image
docker run -p 8501:8501 overstrand-airbnb-analyzer
```

Then open your browser to: `http://localhost:8501`

### Option 2: Build from Source

If you want to build the image yourself:

```bash
# Clone the repository
git clone https://github.com/Rpvermaak/overstrand-airbnb-analyzer.git
cd overstrand-airbnb-analyzer

# Build the Docker image
docker build -t overstrand-airbnb-analyzer .

# Run the container
docker run -p 8501:8501 overstrand-airbnb-analyzer
```

### Stopping the Application

Press `Ctrl+C` in the terminal, or:

```bash
docker ps  # Find the container ID
docker stop <container_id>
```

## Sharing the Docker Image

### Method 1: Docker Hub (Public)

1. **Push to Docker Hub:**
```bash
# Tag the image
docker tag overstrand-airbnb-analyzer your-dockerhub-username/overstrand-airbnb-analyzer:latest

# Login to Docker Hub
docker login

# Push the image
docker push your-dockerhub-username/overstrand-airbnb-analyzer:latest
```

2. **Partners can pull and run:**
```bash
docker pull your-dockerhub-username/overstrand-airbnb-analyzer:latest
docker run -p 8501:8501 your-dockerhub-username/overstrand-airbnb-analyzer:latest
```

### Method 2: Save and Share Image File

1. **Save the image to a file:**
```bash
docker save overstrand-airbnb-analyzer > overstrand-airbnb-analyzer.tar
```

2. **Compress it (optional but recommended):**
```bash
gzip overstrand-airbnb-analyzer.tar
```

3. **Share the file via:**
   - Google Drive / Dropbox
   - USB drive
   - File sharing service

4. **Partners load and run:**
```bash
# Load the image
docker load < overstrand-airbnb-analyzer.tar

# Or if compressed
gunzip overstrand-airbnb-analyzer.tar.gz
docker load < overstrand-airbnb-analyzer.tar

# Run the container
docker run -p 8501:8501 overstrand-airbnb-analyzer
```

## Troubleshooting

**Port 8501 already in use:**
```bash
# Use a different port (e.g., 8502)
docker run -p 8502:8501 overstrand-airbnb-analyzer
# Then access at http://localhost:8502
```

**Permission issues:**
```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER
# Log out and back in
```

## System Requirements

- **Docker:** Version 20.10 or higher
- **RAM:** Minimum 2GB available
- **Disk Space:** ~1.5GB for the image

## Installing Docker

- **Windows/Mac:** [Docker Desktop](https://www.docker.com/products/docker-desktop)
- **Linux:** [Docker Engine](https://docs.docker.com/engine/install/)
