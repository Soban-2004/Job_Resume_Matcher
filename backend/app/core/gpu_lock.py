import concurrent.futures
from typing import Callable, TypeVar

T = TypeVar("T")

# A plain mutex isn't enough here: with recruiter_concurrency > 1, distinct OS
# threads from asyncio.to_thread's default pool each touch the same CUDA
# context over time, and this torch/cuBLASLt/driver combo corrupts under
# that cross-thread reuse (CUBLAS_STATUS_EXECUTION_FAILED), even when calls
# are individually serialized by a lock. Routing every GPU call through one
# permanent single-worker thread means the CUDA context is only ever touched
# from that one thread for the life of the process.
_GPU_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="gpu-worker")


def run_on_gpu_thread(fn: Callable[..., T], *args, **kwargs) -> T:
    return _GPU_EXECUTOR.submit(fn, *args, **kwargs).result()
