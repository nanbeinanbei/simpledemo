import logging
import sys
import os
from pathlib import Path

# 创建logs目录
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)

# 配置根日志器
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# 移除所有现有的处理器
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

# 创建控制台处理器
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# 创建文件处理器
file_handler = logging.FileHandler(
    filename=log_dir / "temate.log",
    encoding='utf-8',
    mode='a'
)
file_handler.setLevel(logging.INFO)

# 设置日志格式
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# 添加处理器到根日志器
root_logger.addHandler(console_handler)
root_logger.addHandler(file_handler)

# 禁用uvicorn的访问日志
logging.getLogger("uvicorn.access").disabled = True

# 测试日志
logging.info("="*50)
logging.info("程序启动")
logging.info("="*50)

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from typing import Dict, Any, List
import json
from pydantic import BaseModel
from adapters.base import BaseAdapter, Message
from routes import router  # 修改为包导入

app = FastAPI(title="Temate Gateway", description="轻量级AI网关服务")

# 注册路由
app.include_router(router)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置限流
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# 配置文件路径
CONFIG_DIR = Path(__file__).parent / "config"
CONFIG_DIR.mkdir(exist_ok=True)
TENANT_CONFIG_FILE = CONFIG_DIR / "tenants.json"
MODEL_CONFIG_FILE = CONFIG_DIR / "models.json"

# 确保配置文件存在
if not TENANT_CONFIG_FILE.exists():
    TENANT_CONFIG_FILE.write_text(json.dumps({"tenants": {}}))
if not MODEL_CONFIG_FILE.exists():
    MODEL_CONFIG_FILE.write_text(json.dumps({"models": {}}))

def load_config(file_path: Path) -> Dict[str, Any]:
    """加载配置文件"""
    return json.loads(file_path.read_text())

def save_config(file_path: Path, config: Dict[str, Any]):
    """保存配置文件"""
    file_path.write_text(json.dumps(config, indent=2))

# def get_model_adapter(model_id: str) -> BaseAdapter:
#     """获取模型适配器"""
#     model_config = load_config(MODEL_CONFIG_FILE)
#     model_info = model_config["models"].get(model_id)
    
#     if not model_info:
#         raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    
#     if model_info["type"] == "openai_compatible":
#         return OpenAIAdapter(model_info["config"])
#     else:
#         raise HTTPException(status_code=400, detail=f"Unsupported model type: {model_info['type']}")

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    temperature: float = 0.7
    max_tokens: int = 1000

@app.get("/")
@limiter.limit("5/minute")
async def root(request: Request):
    return {"message": "Temate Gateway API"}

@app.get("/health")
@limiter.limit("10/minute")
async def health_check(request: Request):
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=18800) 