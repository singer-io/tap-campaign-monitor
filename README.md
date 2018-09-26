# tap-campaign-monitor

Author: Connor McArthur (connor@fishtownanalytics.com)

This is a [Singer](http://singer.io) tap that produces JSON-formatted data following the [Singer spec](https://github.com/singer-io/getting-started/blob/master/SPEC.md).

It:

- Generates a catalog of available data in Campaign Monitor
- Extracts the following resources:
  - [Campaigns](https://www.campaignmonitor.com/api/clients/#getting-sent-campaigns)
  - [Campaign Summaries](https://www.campaignmonitor.com/api/campaigns/#campaign-summary)
  - [Campaign Opens](https://www.campaignmonitor.com/api/campaigns/#campaign-opens)
  - [Campaign Clicks](https://www.campaignmonitor.com/api/campaigns/#campaign-clicks)
  - [Campaign Unsubscribes](https://www.campaignmonitor.com/api/campaigns/#campaign-unsubscribes)
  - [Campaign Bounces](https://www.campaignmonitor.com/api/campaigns/#campaign-bounces)
  - [Campaign Recipients](https://www.campaignmonitor.com/api/campaigns/#campaign-recipients)
  - [Campaign Email Client Usage](https://www.campaignmonitor.com/api/campaigns/#campaign-email-client-usage)
  - [Lists](https://www.campaignmonitor.com/api/clients/#getting-subscriber-lists)
  - [List Details](https://www.campaignmonitor.com/api/lists/#list-details)
  - [List Bounced Subscribers](https://www.campaignmonitor.com/api/lists/#bounced-subscribers)
  - [List Active Subscribers](https://www.campaignmonitor.com/api/lists/#active-subscribers)
  - [List Deleted Subscribers](https://www.campaignmonitor.com/api/lists/#deleted-subscribers)
  - [List Unconfirmed Subscribers](https://www.campaignmonitor.com/api/lists/#unconfirmed-subscribers)
  - [List Unsubscribed Subscribers](https://www.campaignmonitor.com/api/lists/#unsubscribed-subscribers)

### Quick Start

1. Install

```bash
git clone git@github.com:fishtown-analytics/tap-campaign-monitor.git
cd tap-campaign-monitor
pip install .
```

2. Get credentials from Campaign Monitor. You'll need your client ID and an API key.

3. Create the config file.

There is a template you can use at `config.example.json`, just copy it to `config.json` in the repo root and insert your client ID and secret.

4. Run the application to generate a catalog.

```bash
tap-campaign-monitor -c config.json --discover > catalog.json
```

5. Select the tables you'd like to replicate

Step 4 creates a file called `catalog.json` that specifies all the available endpoints and fields. You'll need to open the file and select the ones you'd like to replicate. See the [Singer guide on Catalog Format](https://github.com/singer-io/getting-started/blob/c3de2a10e10164689ddd6f24fee7289184682c1f/BEST_PRACTICES.md#catalog-format) for more information on how tables are selected.

6. Run it!

```bash
tap-campaign-monitor -c config.json --properties catalog.json
```

### Gotchas

- If you select any of the `campaign_*` streams, you MUST select `campaigns` as well. Likewise for `list_*` and `lists`.

---

Copyright &copy; 2018 Stitch
