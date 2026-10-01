import json

import singer

from tap_campaign_monitor.client import CampaignMonitorForbiddenError
from tap_campaign_monitor.streams import AVAILABLE_STREAMS

LOGGER = singer.get_logger()

STREAMS = {stream.TABLE: stream for stream in AVAILABLE_STREAMS}


def _prune_inaccessible_children(streams):
    """
    Remove child streams from the catalog whose parent stream was excluded.
    Mutates the streams list in place.
    """
    accessible_streams = {stream['tap_stream_id'] for stream in streams}
    to_remove = [
        stream['tap_stream_id']
        for stream in streams
        if STREAMS[stream['tap_stream_id']].PARENT
        and STREAMS[stream['tap_stream_id']].PARENT not in accessible_streams
    ]

    for stream in to_remove:
        LOGGER.warning(
            "Stream '%s' excluded from catalog because its parent "
            "stream '%s' is not accessible.",
            stream,
            STREAMS[stream].PARENT,
        )

    streams[:] = [
        stream for stream in streams
        if stream['tap_stream_id'] not in to_remove
    ]
    return to_remove


def _apply_access_checks(config, state, client, streams):
    """
    Probe streams for read access, remove inaccessible streams and children,
    and raise CampaignMonitorForbiddenError if none remain accessible.
    Mutates the streams list in place.
    """
    inaccessible_streams = [
        stream['tap_stream_id']
        for stream in streams
        if not STREAMS[stream['tap_stream_id']](
            config, state, None, client
        ).check_access()
    ]

    streams[:] = [
        stream for stream in streams
        if stream['tap_stream_id'] not in inaccessible_streams
    ]

    inaccessible_streams.extend(_prune_inaccessible_children(streams))

    if inaccessible_streams:
        LOGGER.warning(
            "No 'read' access to stream(s): %s. Excluded from catalog.",
            ", ".join(inaccessible_streams),
        )

    if not streams:
        raise CampaignMonitorForbiddenError(
            "HTTP-error-code: 403, Error: The credentials do not have "
            "'read' access to any supported streams."
        )

    return inaccessible_streams


def discover(config, state, client):
    """
    Build and return the catalog list, excluding streams the credentials
    lack 'read' access to (HTTP 403). Raises CampaignMonitorForbiddenError if
    no parent stream is accessible, or CampaignMonitorUnauthorizedError
    immediately if credentials are invalid/expired (HTTP 401).
    """
    catalog = []
    for stream_cls in AVAILABLE_STREAMS:
        catalog += stream_cls(config, state, None, None).generate_catalog()

    _apply_access_checks(config, state, client, catalog)

    return catalog
