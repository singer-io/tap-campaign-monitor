#!/usr/bin/env python3

import argparse
import json
import sys

import singer

from tap_framework.streams import is_selected

from tap_campaign_monitor.client import CampaignMonitorClient
from tap_campaign_monitor.state import save_state
from tap_campaign_monitor.streams import AVAILABLE_STREAMS

LOGGER = singer.get_logger()  # noqa


def do_discover(args):
    LOGGER.info("Starting discovery.")

    catalog = []

    for available_stream in AVAILABLE_STREAMS:
        stream = available_stream(args.config, args.state, None, None)

        catalog += stream.generate_catalog()

    json.dump({'streams': catalog}, sys.stdout, indent=4)


def get_streams_to_replicate(config, state, catalog, client):
    streams = []
    campaign_substreams = []
    list_substreams = []

    for stream_catalog in catalog.streams:
        if not is_selected(stream_catalog):
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
        required_config_keys=['api_key', 'client_id'])

    if args.discover:
        do_discover(args)
    else:
        do_sync(args)


if __name__ == '__main__':
    main()
