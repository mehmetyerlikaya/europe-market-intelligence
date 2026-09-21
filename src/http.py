"""Small credential-free JSON client using the operating system's TLS trust store."""

import json
import logging
import ssl
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import truststore

from src.config import PipelineError

LOGGER = logging.getLogger(__name__)


def get_json(url: str) -> dict | list:
    context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    request = Request(url, headers={"User-Agent": "europe-market-intelligence/0.1"})
    for attempt in range(3):
        try:
            with urlopen(request, timeout=45, context=context) as response:
                return json.load(response)
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise PipelineError(f"HTTP {exc.code} retrieving {url}") from exc
        except (URLError, TimeoutError) as exc:
            if attempt == 2:
                raise PipelineError(f"Unable to retrieve {url}: {exc}") from exc
        except (ValueError, UnicodeError) as exc:
            raise PipelineError(f"Invalid JSON from {url}") from exc
        LOGGER.warning("Retrying request (%s/3): %s", attempt + 2, url)
        time.sleep(2**attempt)
    raise AssertionError("unreachable")
