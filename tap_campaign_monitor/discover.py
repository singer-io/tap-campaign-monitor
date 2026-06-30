import json
import sys

import singer

from tap_campaign_monitor.client import CampaignMonitorForbiddenError
from tap_campaign_monitor.streams import AVAILABLE_STREAMS

LOGGER = singer.get_logger()


def _get_inaccessible_streams(config, state, client):
    """Return set of TABLE names for parent streams that return 403."""
    inaccessible_streams = set()
    for stream_cls in AVAILABLE_STREAMS:
        if not stream_cls.PARENT:
            stream = stream_cls(config, state, None, client)
            if not stream.check_access():
                inaccessible_streams.add(stream_cls.TABLE)
    return inaccessible_streams


def discover(config, state, client):
    """
    Build and return the catalog list, excluding streams the credentials
    cannot access (HTTP 403). Raises CampaignMonitorForbiddenError if no
    parent stream is accessible.
    """
    inaccessible_streams = _get_inaccessible_streams(config, state, client)

    parent_streams = {s.TABLE for s in AVAILABLE_STREAMS if not s.PARENT}
    if not (parent_streams - inaccessible_streams):
        raise CampaignMonitorForbiddenError(
            "HTTP-error-code: 403, Error: The credentials do not have "
            "'read' access to any supported streams."
        )

    if inaccessible_streams:
        LOGGER.warning(
            "No 'read' access to stream(s): %s. Excluded from catalog.",
            ", ".join(inaccessible_streams),
        )

    catalog = []
    for stream_cls in AVAILABLE_STREAMS:
        if stream_cls.TABLE in inaccessible_streams:
            continue
        if stream_cls.PARENT and stream_cls.PARENT in inaccessible_streams:
            LOGGER.warning(
                "Stream '%s' excluded from catalog because its parent "
                "stream '%s' is not accessible.",
                stream_cls.TABLE, stream_cls.PARENT,
            )
            continue
        catalog += stream_cls(config, state, None, None).generate_catalog()

    return catalog
