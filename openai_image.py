from typing import Callable
from mcp.server.fastmcp import FastMCP
import mimetypes
import io
import uuid
import asyncio
from openai import OpenAI
import base64
import logging
from fastapi import UploadFile
import os

log = logging.getLogger(__name__)
log.setLevel(logging._nameToLevel['INFO'])

# import storage server functions
os.curdir = os.path.dirname(__file__)
os.environ['PATH'] += f':{os.curdir}'
from storage_server import *

# Initialize FastMCP server
mcp = FastMCP("openai-image")

async def _run_blocking(fn: Callable, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))

@mcp.tool()
async def generate_image(
    prompt: str,
    n: int,
    size: str,
):
    """Generate images based on a prompt using OpenAI's API.

    Args:
        prompt: The text prompt to generate images from.
        n: The Number of images (1-10) to generate.
        size: Image resolution size, can only be these value: 1024x1024, 1536x1024, 1024x1536, auto
    """
    print("🖼️ Generating image(s)...")
    client = OpenAI()

    def _call_gen():
        return client.images.generate(
            model='gpt-image-1',
            prompt=prompt,
            n=n,
            size=size,
            quality='low'
        )

    try:
        resp = _call_gen()
        image_urls = []
        for i, img in enumerate(resp.data, 1):
            image_data, content_type = load_b64_image_data(img.b64_json)
            url = await upload_image(image_data,content_type)
            log.info(f"🎉 Image {i} generation successful")
            image_urls.append(f"![image_{i}](http://127.0.0.1:9000/{url})")
        return "\n".join(image_urls)
    except Exception as e:
        log.error("❌ Image generation failed")
        print(f"Error during image generation: {e}")
        return f"Error during image generation: {e}"
    
def load_b64_image_data(b64_str:str):
    try:
        if "," in b64_str:
            header, encoded = b64_str.split(",", 1)
            mime_type = header.split(";")[0]
            img_data = base64.b64decode(encoded)
        else:
            mime_type = "image/png"
            img_data = base64.b64decode(b64_str)
        return img_data, mime_type
    except Exception as e:
        log.exception(f"Error loading image data: {e}")
    
async def upload_image(image_data:bytes, content_type:str):
    image_format = mimetypes.guess_extension(content_type)
    file = UploadFile(
        file=io.BytesIO(image_data),
        filename=f"generated-image{image_format}",  # will be converted to a unique ID on upload_file
    )

    # create bucket
    exsist_buckets = await list_buckets()
    images_bucket = 'images'
    if images_bucket not in exsist_buckets:
        status = await create_bucket(images_bucket)
        log.info(status)

    # file upload
    object_key = str(uuid.uuid4())
    status = await upload_object(images_bucket,object_key,file)
    log.info(status)

    # get object url
    object_url = object_path(images_bucket,object_key)
    return object_url


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')