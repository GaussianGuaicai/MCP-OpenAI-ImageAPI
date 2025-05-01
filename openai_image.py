from typing import Callable,List
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
import requests

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
    images: List[str],
    prompt: str,
    n: int = 1,
    size: str = 'auto',
    quality: str = 'medium',
    max_retries: int = 0
):
    """Generate images based on a prompt and images using OpenAI's API.
    Default to medium quality image output, high and auto quality output only for final image.

    Args:
        images: List of image URLs to generate new image from.
        prompt: The text prompt to generate images from.
        n: The Number of images (1-10) to generate.
        size: Image resolution size, can only be these value: `auto`, `1024x1024`, `1536x1024`, `1024x1536`
        quality: The quality of the image that will be generated: `low`,`medium`,`auto`,`high`
        max_retries: The number of times to retry the request in case of failure.

    Return:
        List of Image URL.
        The image url link need to displayed in Markdown Image format as follow(NOTE: Do not remove character '!'):
            ![<image_name>](<image_url_link>)
    """
    client = OpenAI(max_retries=max_retries)

    images_array = []
    for i,img_url in enumerate(images):
        try:
            response = requests.get(img_url, timeout=60)
            response.raise_for_status()

            if len(response.content) > 25 * 1024 * 1024:
                log.error(f'Image {img_url} exceeds 25MB limit')
                raise ValueError("Image exceeds 25MB limit")
            
            content_type = response.headers.get('Content-Type', '').lower()
            if content_type not in ('image/png', 'image/jpeg','image/webp'):
                log.error(f'Image type {content_type} is not support!')
                raise ValueError(f'Image type {content_type} is not support!')

            data = io.BytesIO(response.content)
            images_array.append((f'image{i}',data,content_type))
        except Exception as e:
            log.error(f"Error process input images: {e}")
            raise ValueError(f"Error process input images: {e}")

    def _call_gen(images:List):
        if len(images) == 0:
            log.info("🖼️ Generating image(s)...")
            return client.images.generate(
                model='gpt-image-1',
                prompt=prompt,
                n=n,
                size=size,
                quality=quality
            )
        else:
            log.info("🖼️ Editing image(s)...")
            return client.images.edit(
                model='gpt-image-1',
                image=images,
                prompt=prompt,
                n=n,
                size=size,
                quality=quality
            )

    try:
        resp = _call_gen(images_array)
        image_urls = []
        for i, img in enumerate(resp.data, 1):
            image_data, content_type = load_b64_image_data(img.b64_json)
            url = await upload_image(image_data,content_type)
            log.info(f"🎉 Image {i} generation successful, with url: {url}")
            image_urls.append(f"![image_{i}](http://127.0.0.1:9000/{url})")
        return image_urls
    except Exception as e:
        log.error("❌ Image generation failed")
        log.error(f"Error during image generation: {e}")
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
    object_key = str(uuid.uuid4())
    image_ext = mimetypes.guess_extension(content_type)
    file = UploadFile(
        file=io.BytesIO(image_data),
        filename=f'{object_key}{image_ext}'
    )

    # create bucket
    exsist_buckets = await list_buckets()
    images_bucket = 'images'
    if images_bucket not in exsist_buckets:
        status = await create_bucket(images_bucket)
        log.info(f'Bucket create: {status}')

    # file upload
    if file.filename is None:
        log.error('filename is None')
        raise AssertionError('filename is None')
    status = await upload_object(images_bucket,file.filename,file)
    log.info(f'Image upload: {status}')

    # get object url
    object_url = status['url_path']
    return object_url


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')