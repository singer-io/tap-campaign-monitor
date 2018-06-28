from tap_campaign_monitor.streams.campaigns import CampaignsStream
from tap_campaign_monitor.streams.campaign_bounces \
    import CampaignBouncesStream
from tap_campaign_monitor.streams.campaign_clicks \
    import CampaignClicksStream
from tap_campaign_monitor.streams.campaign_email_client_usage \
    import CampaignEmailClientUsageStream
from tap_campaign_monitor.streams.campaign_opens \
    import CampaignOpensStream
from tap_campaign_monitor.streams.campaign_recipients \
    import CampaignRecipientsStream
from tap_campaign_monitor.streams.campaign_spam_complaints \
    import CampaignSpamComplaintsStream
from tap_campaign_monitor.streams.campaign_summary \
    import CampaignSummaryStream
from tap_campaign_monitor.streams.campaign_unsubscribes \
    import CampaignUnsubscribesStream

from tap_campaign_monitor.streams.lists import ListsStream
from tap_campaign_monitor.streams.list_active_subscribers \
    import ListActiveSubscribersStream
from tap_campaign_monitor.streams.list_bounced_subscribers \
    import ListBouncedSubscribersStream
from tap_campaign_monitor.streams.list_deleted_subscribers \
    import ListDeletedSubscribersStream
from tap_campaign_monitor.streams.list_details \
    import ListDetailsStream
from tap_campaign_monitor.streams.list_unconfirmed_subscribers \
    import ListUnconfirmedSubscribersStream
from tap_campaign_monitor.streams.list_unsubscribed_subscribers \
    import ListUnsubscribedSubscribersStream


AVAILABLE_STREAMS = [
    CampaignsStream,
    CampaignBouncesStream,
    CampaignClicksStream,
    CampaignEmailClientUsageStream,
    CampaignOpensStream,
    CampaignRecipientsStream,
    CampaignSpamComplaintsStream,
    CampaignSummaryStream,
    CampaignUnsubscribesStream,

    ListsStream,
    ListActiveSubscribersStream,
    ListBouncedSubscribersStream,
    ListDeletedSubscribersStream,
    ListDetailsStream,
    ListUnconfirmedSubscribersStream,
    ListUnsubscribedSubscribersStream,
]
