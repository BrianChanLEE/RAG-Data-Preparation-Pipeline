import concurrent.futures
import logging
import time
from typing import List, Callable, Any
from pathlib import Path
from tqdm import tqdm
from ragprep.core.models import RunContext, ProcessingResult

logger = logging.getLogger("ragprep.executor")

class RetryWrapper:
    def __init__(self, func: Callable, ctx: RunContext):
        self.func = func
        self.ctx = ctx
        
    def __call__(self, item: Any) -> ProcessingResult:
        max_retries = getattr(self.ctx, 'max_retries', 0)
        backoff_ms = getattr(self.ctx, 'retry_backoff_ms', 1000)
        
        for attempt in range(max_retries + 1):
            try:
                if isinstance(item, tuple):
                    res = self.func(*item, self.ctx)
                else:
                    res = self.func(item, self.ctx)
                    
                if res.status != "FAILED" or attempt == max_retries:
                    if res.status == "FAILED":
                        self._route_to_dlq(item, res)
                    return res
                    
            except Exception as e:
                logger.error(f"Execution failed on attempt {attempt}: {e}")
                if attempt == max_retries:
                    name = str(item[0]) if isinstance(item, tuple) else (item.name if isinstance(item, Path) else str(item))
                    res = ProcessingResult(doc_id="unknown", filename=name, type="unknown", sha256="unknown", status="FAILED", failed_reason=str(e))
                    self._route_to_dlq(item, res)
                    return res
                    
            wait_time = backoff_ms / 1000.0
            logger.warning(f"Retry {attempt+1}/{max_retries} for {item} in {wait_time}s...")
            time.sleep(wait_time)
            backoff_ms *= 2 # exponential backoff
            
    def _route_to_dlq(self, item: Any, res: ProcessingResult):
        import shutil
        
        dlq_dir = self.ctx.dirs['dlq'] / res.doc_id
        dlq_dir.mkdir(parents=True, exist_ok=True)
        
        def copy_if_exists(p):
            if isinstance(p, Path) and p.exists():
                try:
                    shutil.copy2(str(p), dlq_dir / p.name)
                except:
                    pass
                    
        if isinstance(item, Path):
            copy_if_exists(item)
        elif isinstance(item, tuple) and isinstance(item[1], list):
            for f in item[1]:
                copy_if_exists(f)
                
        with open(dlq_dir / "error.log", "w", encoding="utf-8") as f:
            f.write(f"Failed Reason: {res.failed_reason}\nStatus: {res.status}\n")

class BaseExecutor:
    def execute(self, items: List[Any], func: Callable, ctx: RunContext) -> List[ProcessingResult]:
        raise NotImplementedError

class LocalProcessExecutor(BaseExecutor):
    def execute(self, items: List[Any], func: Callable, ctx: RunContext) -> List[ProcessingResult]:
        results = []
        wrapped_func = RetryWrapper(func, ctx)
        with concurrent.futures.ProcessPoolExecutor(max_workers=ctx.concurrency) as executor:
            future_to_item = {executor.submit(wrapped_func, item): item for item in items}
            for future in tqdm(concurrent.futures.as_completed(future_to_item), total=len(items), desc="Processing (ProcessPool)"):
                try:
                    res = future.result()
                    results.append(res)
                except Exception as exc:
                    logger.exception(f"Item generated an exception: {exc}")
        return results

class LocalThreadExecutor(BaseExecutor):
    def execute(self, items: List[Any], func: Callable, ctx: RunContext) -> List[ProcessingResult]:
        results = []
        wrapped_func = RetryWrapper(func, ctx)
        with concurrent.futures.ThreadPoolExecutor(max_workers=ctx.concurrency) as executor:
            future_to_item = {executor.submit(wrapped_func, item): item for item in items}
            for future in tqdm(concurrent.futures.as_completed(future_to_item), total=len(items), desc="Processing (ThreadPool)"):
                try:
                    res = future.result()
                    results.append(res)
                except Exception as exc:
                    logger.exception(f"Item generated an exception: {exc}")
        return results

def get_executor(executor_type: str) -> BaseExecutor:
    if executor_type == "thread":
        return LocalThreadExecutor()
    return LocalProcessExecutor()
