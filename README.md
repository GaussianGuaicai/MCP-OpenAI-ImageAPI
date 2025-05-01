# MCP-OpenAI-ImageAPI

A Model Context Protocol (MCP) server for generating and editing images using OpenAI's GPT-Image-1 API. This project provides an API interface to generate or edit images based on text prompts and input images, with results stored and served via an S3-compatible object storage server.

## Features
- Generate images from text prompts using OpenAI's GPT-Image-1
- Edit images based on prompts and input images
- Asynchronous FastAPI-based MCP server
- Automatic upload and retrieval of images from object storage

## Requirements
- Python 3.8+
- OpenAI API key
- Access to an S3-compatible object storage server (e.g., MinIO, AWS S3, or self-hosted)

**Note:** You must provide your own S3-compatible object storage server. This project does not include an object storage backend.

## Installation
1. Clone this repository:
   ```bash
   git clone <this-repo-url>
   cd MCP-OpenAI-ImageAPI
   ```
2. Install dependencies (recommended: use a virtual environment):
   ```bash
   pip install -r requirements.txt
   ```
   Or, if using PDM:
   ```bash
   pdm install
   ```
3. Configure your OpenAI API key and object storage credentials as environment variables or in the appropriate config files.

## Usage
Run the MCP server:
```bash
python openai_image.py
```

The server exposes a tool `gpt-image-generator` for generating or editing images. See the code for API details.

## Configuration
- Set your OpenAI API key as an environment variable: `OPENAI_API_KEY`
- Configure your S3-compatible object storage credentials as required by your storage server implementation.

## License
MIT

## Disclaimer
This project requires an external or self-hosted S3-compatible object storage server. Please ensure you have access to such a service before using this project.
