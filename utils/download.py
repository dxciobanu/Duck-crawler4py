import requests
import cbor
import time

from utils.response import Response

def download(url, config, logger=None):
    host, port = config.cache_server

    try:
        resp = requests.get(
            f"http://{host}:{port}/",
            params=[
                ("q", url),
                ("u", config.user_agent)
            ],
            timeout=30
        )

    except requests.exceptions.RequestException as e:
        if logger:
            logger.error(f"Connection error downloading {url}: {e}")

        return Response({
            "error": str(e),
            "status": -1,
            "url": url
        })

    try:
        if resp.content:
            return Response(cbor.loads(resp.content))

    except (EOFError, ValueError) as e:
        if logger:
            logger.error(f"Invalid server response for {url}: {e}")

    if logger:
        logger.error(f"Spacetime Response error {resp} with url {url}.")

    return Response({
    "error": f"Invalid cache response for {url}",
    "status": -1,
    "url": url
    })