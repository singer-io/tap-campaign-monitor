#!/usr/bin/env python3

import argparse
import json
import sys

import singer


from tap_campaign_monitor.client import CampaignMonitorClient
from tap_campaign_monitor.state import save_state
from tap_campaign_monitor.streams import AVAILABLE_STREAMS
from tap_campaign_monitor.streams.base import is_stream_selected

LOGGER = singer.get_logger()  # noqa


def _apply_access_checks(config, client, streams):
    """
    Check each parent stream for API access. Returns the set of parent
    stream TABLE names that are inaccessible (HTTP 403).
    """
    inaccessible = set()
    for stream_cls in streams:
        if stream_cls.PARENT:
            continue  # child streams are checked via their parent
        stream = stream_cls(config, None, None, client)
        if not stream.check_access():
            LOGGER.warning(
                "Stream '%s' is not accessible (HTTP 403). "
                "Excluding it and its children from the catalog.",
                stream_cls.TABLE,
            )
            inaccessible.add(stream_cls.TABLE)
    return inaccessible


def _prune_inaccessible_children(streams, inaccessible_parents):
    """
    Return a filtered list of stream classes, removing any parent that is
    inaccessible and any child whose parent is inaccessible.
    """
    accessible = []
    for stream_cls in streams:
        if stream_cls.TABLE in inaccessible_parents:
            continue
        if stream_cls.PARENT and stream_cls.PARENT in inaccessible_parents:
            LOGGER.warning(
                "Excluding child stream '%s' because parent '%s' is inaccessible.",
                stream_cls.TABLE,
                stream_cls.PARENT,
            )
            continue
        accessible.append(stream_cls)
    return accessible


def do_discover(client, config):
    LOGGER.info("Starting discovery.")

    inaccessible_parents = _apply_access_checks(config, client, AVAILABLE_STREAMS)
    accessible_streams = _prune_inaccessible_children(AVAILABLE_STREAMS, inaccessible_parents)

    parent_streams = [s for s in AVAILABLE_STREAMS if not s.PARENT]
    accessible_parents = [s for s in accessible_streams if not s.PARENT]
    if parent_streams and not accessible_parents:
        raise RuntimeError(
            "No streams are accessible with the provided credentials. "
            "Please verify your API credentials and permissions."
        )

    catalog = []
    for stream_cls in accessible_streams:
        stream = stream_cls(config, None, None, None)
        catalog += stream.generate_catalog()

    json.dump({'streams': catalog}, sys.stdout, indent=4)
    LOGGER.info("Finished discover")


def get_streams_to_replicate(config, state, catalog, client):
    streams = []
    campaign_substreams = []
    list_substreams = []

    if not catalog:
        return streams, campaign_substreams, list_substreams

    for stream_catalog in catalog.streams:
        if not is_stream_selected(stream_catalog):
            LOGGER.info("'{}' is not marked selected, skipping."
                        .format(stream_catalog.stream))
            continue

        for available_stream in AVAILABLE_STREAMS:
            if available_stream.matches_catalog(stream_catalog):
                if not available_stream.requirements_met(catalog):
                    raise RuntimeError(
                        "{} requires that that the following are selected: {}"
                        .format(stream_catalog.stream,
                                ','.join(available_stream.REQUIRES)))

                to_add = available_stream(
                    config, state, stream_catalog, client)

                if stream_catalog.stream in ['campaigns', 'lists']:
                    # the others will be triggered by these streams
                    streams.append(to_add)

                elif stream_catalog.stream.startswith('campaign_'):
                    campaign_substreams.append(to_add)
                    to_add.write_schema()

                elif stream_catalog.stream.startswith('list_'):
                    list_substreams.append(to_add)
                    to_add.write_schema()

    return streams, campaign_substreams, list_substreams


def do_sync(args):
    LOGGER.info("Starting sync.")

    client = CampaignMonitorClient(args.config)

    state = args.state

    streams, campaign_substreams, list_substreams = \
        get_streams_to_replicate(
            args.config, state, args.catalog, client)

    for stream in streams:
        try:
            substreams = []

            if stream.TABLE == 'campaigns':
                substreams = campaign_substreams
            elif stream.TABLE == 'lists':
                substreams = list_substreams

            stream.state = args.state
            stream.sync(substreams=substreams)
            state = stream.state
        except OSError as e:
            LOGGER.error(str(e))
            exit(e.errno)

        except Exception as e:
            LOGGER.error(str(e))
            LOGGER.error('Failed to sync endpoint {}, moving on!'
                         .format(stream.TABLE))
            raise e

    save_state(state)


@singer.utils.handle_top_exception(LOGGER)
def main():
    args = singer.utils.parse_args(
        required_config_keys=['client_id', 'refresh_token'])

    if args.discover:
        client = CampaignMonitorClient(args.config)
        do_discover(client, args.config)
    elif args.catalog:
        do_sync(args)


if __name__ == '__main__':
    main()
