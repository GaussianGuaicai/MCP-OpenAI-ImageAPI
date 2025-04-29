import os
import shutil
from typing import List
import aiofiles
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
import uvicorn

app = FastAPI(title="Mini Object Storage Server")

# 根存储目录（生产请配置到磁盘路径或挂载盘）
STORAGE_ROOT = "storage_data"
os.makedirs(STORAGE_ROOT, exist_ok=True)

# 辅助：获取桶目录绝对路径
def bucket_path(bucket: str) -> str:
    return os.path.join(STORAGE_ROOT, bucket)

# 辅助：获取对象在文件系统的真实路径
def object_path(bucket: str, object_key: str) -> str:
    # 防止 .. 越权
    safe_key = object_key.strip("/").replace("..", "")
    return os.path.join(bucket_path(bucket), safe_key)

# 1) 列举所有 buckets
@app.get("/buckets", response_model=List[str])
async def list_buckets():
    return [d for d in os.listdir(STORAGE_ROOT)
            if os.path.isdir(os.path.join(STORAGE_ROOT, d))]

# 2) 创建 bucket
@app.put("/buckets/{bucket}")
async def create_bucket(bucket: str):
    bp = bucket_path(bucket)
    if os.path.exists(bp):
        raise HTTPException(400, f"Bucket '{bucket}' already exists.")
    os.makedirs(bp)
    return {"bucket": bucket, "created": True}

# 5) 上传/覆盖一个对象
@app.put("/buckets/{bucket}/objects/{object_key:path}")
async def upload_object(bucket: str, object_key: str, file: UploadFile):
    bp = bucket_path(bucket)
    if not os.path.isdir(bp):
        raise HTTPException(404, "Bucket not found.")
    dest_path = object_path(bucket, object_key)
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    # 以异步方式写入文件
    async with aiofiles.open(dest_path, "wb") as out_f:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            await out_f.write(chunk)
    return {"bucket": bucket, "key": object_key, "size": os.path.getsize(dest_path)}

# 6) 下载一个对象
@app.get("/buckets/{bucket}/objects/{object_key:path}")
async def download_object(bucket: str, object_key: str):
    path = object_path(bucket, object_key)
    print(os.path.abspath(path))
    if not os.path.isfile(path):
        raise HTTPException(404, "Object not found.")
    # StreamingResponse 支持大文件分块读取
    async def streamer():
        async with aiofiles.open(path, "rb") as f:
            while True:
                chunk = await f.read(1024 * 1024)
                if not chunk:
                    break
                yield chunk
    return StreamingResponse(streamer(), media_type="application/octet-stream")

if __name__ == "__main__":
    uvicorn.run(
        "storage_server:app",
        host="",
        port=9000,
        reload=True,       # 开发时热重载，可删
        workers=1,         # 生产可调整
    )