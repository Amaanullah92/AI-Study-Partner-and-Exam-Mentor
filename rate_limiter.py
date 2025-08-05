import time
import asyncio
last_request_time = 0
RATE_LIMIT_SECONDS = 6  

async def rate_limited_runner_call(func, *args, **kwargs):
    global last_request_time
    now = time.time()
    elapsed = now - last_request_time

    if elapsed < RATE_LIMIT_SECONDS:
        wait_time = RATE_LIMIT_SECONDS - elapsed
        await asyncio.sleep(wait_time)

    last_request_time = time.time()
    return await func(*args, **kwargs)

def rate_limited_runner_call_sync(func, *args, **kwargs):
    global last_request_time
    now = time.time()
    elapsed = now - last_request_time

    if elapsed < RATE_LIMIT_SECONDS:
        wait_time = RATE_LIMIT_SECONDS - elapsed
        time.sleep(wait_time)

    last_request_time = time.time()
    return func(*args, **kwargs)

