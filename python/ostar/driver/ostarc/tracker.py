import logging
from urllib.parse import urlparse

# pylint: disable=invalid-name
logger = logging.getLogger("OSTARC")


def tracker_host_port_from_cli(rpc_tracker_str):

    rpc_hostname = rpc_port = None

    if rpc_tracker_str:
        parsed_url = urlparse("//%s" % rpc_tracker_str)
        rpc_hostname = parsed_url.hostname
        rpc_port = parsed_url.port or 9090
        logger.info("RPC tracker hostname: %s", rpc_hostname)
        logger.info("RPC tracker port: %s", rpc_port)

    return rpc_hostname, rpc_port
