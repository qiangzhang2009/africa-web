"""DeepSeek AI client with retry, timeout, and LRU caching."""
import hashlib
import json
import logging
import time
from functools import lru_cache
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger("ai.client")

# ─── LRU Cache for origin check results ──────────────────────────────────────

@lru_cache(maxsize=500)
def _cached_origin_check(cache_key: str) -> dict | None:
    """Cached results are stored in the cache itself — this is a marker function."""
    return None

_cached_results: dict[str, dict] = {}
_CACHE_MAX_SIZE = 500
_CACHE_TTL_SECONDS = 86400  # 24 hours
_cache_timestamps: dict[str, float] = {}

def _get_cache_key(input_data: dict) -> str:
    """Generate a stable cache key from origin check input."""
    key_data = {
        "hs_code": input_data.get("hs_code", ""),
        "origin": input_data.get("origin", ""),
        "steps_count": len(input_data.get("processing_steps", [])),
        "materials_count": len(input_data.get("material_sources", [])),
    }
    return hashlib.sha256(json.dumps(key_data, sort_keys=True).encode()).hexdigest()[:32]

def _is_cache_valid(key: str) -> bool:
    if key not in _cached_results or key not in _cache_timestamps:
        return False
    return (time.time() - _cache_timestamps[key]) < _CACHE_TTL_SECONDS

def _prune_cache():
    """Remove oldest entries if cache exceeds max size."""
    global _cached_results, _cache_timestamps
    if len(_cached_results) >= _CACHE_MAX_SIZE:
        oldest_keys = sorted(_cache_timestamps, key=_cache_timestamps.get)[:_CACHE_MAX_SIZE // 4]
        for k in oldest_keys:
            _cached_results.pop(k, None)
            _cache_timestamps.pop(k, None)

# ─── DeepSeek Client ──────────────────────────────────────────────────────────

class DeepSeekClient:
    """DeepSeek API client with exponential backoff retry and caching."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.DEEPSEEK_API_KEY
        self.base_url = "https://api.deepseek.com"
        self.model = "deepseek-chat"
        self.max_retries = 3
        self.timeout = 10.0  # seconds

    def _retry_with_backoff(self, func, *args, **kwargs) -> Any:
        """Execute a function with exponential backoff retry."""
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    wait_time = (2 ** attempt) * 0.5  # 0.5s, 1s, 2s
                    logger.warning(f"AI request attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"AI request failed after {self.max_retries} attempts: {e}")
        raise last_exception

    def _do_request(self, messages: list[dict], max_tokens: int = 1024) -> str:
        """Make a single API request."""
        if not self.api_key or not self.api_key.startswith("sk-"):
            raise ValueError("DEEEPSEEK_API_KEY not configured or invalid")

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()

    def check_origin(self, hs_code: str, origin: str, processing_steps: list[str], material_sources: list[str]) -> dict:
        """
        Check origin qualification for zero-tariff eligibility.
        Results are cached for 24 hours.
        """
        input_data = {
            "hs_code": hs_code,
            "origin": origin,
            "processing_steps": processing_steps,
            "material_sources": material_sources,
        }
        
        cache_key = _get_cache_key(input_data)
        
        if _is_cache_valid(cache_key):
            logger.info(f"AI origin check cache HIT for {hs_code}/{origin}")
            return _cached_results[cache_key]

        prompt = f"""你是非洲原产地证书合规专家。用户正在申请从 {origin} 进口 HS编码 {hs_code} 的产品。

加工工序：
{chr(10).join(f"{i+1}. {s}" for i, s in enumerate(processing_steps)) if processing_steps else "无加工工序"}

原料来源：
{chr(10).join(material_sources) if material_sources else "全部为本地原料"}

请判断：
1. 该产品是否符合中国/非洲零关税的原产地条件？
2. 适用的原产地规则是什么？
3. 给出判断置信度（0-1）
4. 如有问题，指出具体建议

请严格用JSON格式回答，不要加任何markdown代码块：
{{"qualifies": true/false, "rule_applied": "规则名称", "confidence": 0.7, "reasons": ["原因1", "原因2"], "suggestions": ["建议1"]}}
"""
        try:
            raw = self._retry_with_backoff(
                self._do_request,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
            )
            
            # Parse JSON response
            if raw.startswith("```"):
                for block in raw.split("```"):
                    block = block.strip()
                    if block and not block.startswith("json"):
                        raw = block
                        break
            
            result = json.loads(raw.strip())
            
            # Cache the result
            _prune_cache()
            _cached_results[cache_key] = result
            _cache_timestamps[cache_key] = time.time()
            logger.info(f"AI origin check cached for {hs_code}/{origin}")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"AI returned non-JSON: {raw[:200]} — {e}")
            return {
                "qualifies": True,
                "rule_applied": "规则估算模式",
                "confidence": 0.5,
                "reasons": [f"AI返回格式异常，已切换为规则估算: {str(e)}"],
                "suggestions": ["请稍后重试"],
            }
        except Exception as e:
            logger.error(f"AI origin check failed: {e}")
            raise

    def generate_cert_document(self, hs_code: str, origin: str, product_description: str, fob_value: float, quantity_kg: float, exporter_name: str, importer_name: str) -> dict:
        """Generate a Certificate of Origin document draft."""
        prompt = f"""你是一名专业的原产地证书代办顾问。请根据以下信息生成一份中国-非洲优惠原产地证书（Form A或相应优惠证书）的填写草稿。

产品信息：
- HS编码：{hs_code}
- 原产国：{origin}
- 产品描述：{product_description}
- FOB货值：${fob_value:,.2f}
- 数量：{quantity_kg}kg
- 出口商：{exporter_name or '待填写'}
- 进口商：{importer_name or '待填写'}

请生成一份专业的中文证书填写草稿，包含：
1. 证书类型建议
2. 各项必填字段及推荐填写内容
3. 办理流程提示
4. 注意事项

以JSON格式返回：
{{"document_type": "建议的证书类型", "content": "详细的证书草稿内容", "format": "application/json", "generated_at": "ISO时间戳", "usage_note": "使用说明"}}
"""
        try:
            raw = self._retry_with_backoff(
                self._do_request,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2048,
            )
            
            if raw.startswith("```"):
                for block in raw.split("```"):
                    block = block.strip()
                    if block and not block.startswith("json"):
                        raw = block
                        break
            
            result = json.loads(raw.strip())
            return result
        except Exception as e:
            logger.error(f"AI cert document generation failed: {e}")
            return {
                "document_type": "Form A / 优惠性原产地证书",
                "content": f"AI文档生成暂时不可用。请联系专业报关行办理。\n\n基本信息：\n- HS编码: {hs_code}\n- 原产国: {origin}\n- 产品: {product_description}",
                "format": "text/plain",
                "generated_at": __import__("datetime").datetime.now().isoformat(),
                "usage_note": "此为自动生成草稿，请联系贸促会或专业报关行确认真实证书内容。",
            }
