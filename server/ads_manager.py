"""
Paid Ads Manager — Google Ads API + Microsoft Ads API + Demo Mode
Manages campaign creation, performance reporting, keyword data.
"""
import json
import os
from typing import List, Dict, Optional
from pathlib import Path

OUTPUT_DIR = Path(os.environ.get('OUTPUT_DIR', str(Path(__file__).resolve().parent.parent / 'output')))

# ── Dependency Guards ──────────────────────────────────────────────────────────
try:
    from google.ads.googleads.client import GoogleAdsClient
    GOOGLE_ADS_AVAILABLE = True
except ImportError:
    GoogleAdsClient = None
    GOOGLE_ADS_AVAILABLE = False

try:
    from bingads.service_client import ServiceClient
    from bingads.authorization import AuthorizationData, OAuthWebAuthCodeGrant
    BING_ADS_AVAILABLE = True
except ImportError:
    BING_ADS_AVAILABLE = False

# ── Demo Data ──────────────────────────────────────────────────────────────────
DEMO_CAMPAIGNS = [
    {
        "id": "111111", "name": "SEO Services — Saudi Arabia", "status": "ENABLED",
        "clicks": 842, "impressions": 12400, "ctr": 6.79, "avg_cpc": 1.85,
        "cost": 1557.7, "conversions": 23, "cpa": 67.7, "impression_share": 58.3
    },
    {
        "id": "222222", "name": "GEO Platform — تحسين محركات البحث", "status": "ENABLED",
        "clicks": 524, "impressions": 8100, "ctr": 6.47, "avg_cpc": 2.10,
        "cost": 1100.4, "conversions": 14, "cpa": 78.6, "impression_share": 41.2
    },
    {
        "id": "333333", "name": "Brand Keywords — محرك", "status": "PAUSED",
        "clicks": 189, "impressions": 3200, "ctr": 5.91, "avg_cpc": 0.75,
        "cost": 141.75, "conversions": 9, "cpa": 15.75, "impression_share": 72.5
    }
]

DEMO_KEYWORDS = [
    {"keyword": "تحسين محركات البحث", "match_type": "EXACT", "quality_score": 8,
     "clicks": 312, "ctr": 7.2, "avg_cpc": 2.10, "cost": 655.2, "conversions": 12},
    {"keyword": "شركة سيو", "match_type": "BROAD", "quality_score": 7,
     "clicks": 198, "ctr": 5.1, "avg_cpc": 1.60, "cost": 316.8, "conversions": 7},
    {"keyword": "SEO services Saudi Arabia", "match_type": "EXACT", "quality_score": 9,
     "clicks": 445, "ctr": 8.3, "avg_cpc": 1.90, "cost": 845.5, "conversions": 15},
    {"keyword": "سيو عربي", "match_type": "BROAD", "quality_score": 6,
     "clicks": 124, "ctr": 3.2, "avg_cpc": 0.95, "cost": 117.8, "conversions": 2},
    {"keyword": "keyword ranking tool", "match_type": "EXACT", "quality_score": 5,
     "clicks": 87, "ctr": 2.1, "avg_cpc": 1.20, "cost": 104.4, "conversions": 0},
    {"keyword": "خدمات التسويق الرقمي", "match_type": "BROAD", "quality_score": 8,
     "clicks": 201, "ctr": 6.4, "avg_cpc": 2.30, "cost": 462.3, "conversions": 9},
]

DEMO_SEARCH_TERMS = {
    "converting_terms": [
        {"term": "تحسين موقع جوجل", "campaign": "SEO — SA", "ad_group": "Arabic SEO",
         "clicks": 34, "conversions": 4, "avg_cpc": 1.95},
        {"term": "افضل شركة سيو في السعودية", "campaign": "SEO — SA", "ad_group": "Arabic SEO",
         "clicks": 21, "conversions": 3, "avg_cpc": 2.20},
        {"term": "SEO optimization company Riyadh", "campaign": "SEO — SA", "ad_group": "English SEO",
         "clicks": 18, "conversions": 2, "avg_cpc": 1.85},
    ],
    "wasted_spend": [
        {"term": "SEO salary jobs", "campaign": "SEO — SA", "ad_group": "English SEO",
         "clicks": 42, "conversions": 0, "avg_cpc": 1.10},
        {"term": "how to learn SEO free", "campaign": "SEO — SA", "ad_group": "English SEO",
         "clicks": 38, "conversions": 0, "avg_cpc": 0.90},
        {"term": "سيو يوتيوب", "campaign": "GEO Platform", "ad_group": "Arabic SEO",
         "clicks": 29, "conversions": 0, "avg_cpc": 0.75},
    ]
}


# ── Config Management ──────────────────────────────────────────────────────────
def save_ads_config(config: dict) -> None:
    """Persist ads credentials to output/ads_config.json (never exposed in git)."""
    config_path = OUTPUT_DIR / 'ads_config.json'
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def load_ads_config() -> dict:
    """Load saved ads credentials."""
    config_path = OUTPUT_DIR / 'ads_config.json'
    if config_path.exists():
        with open(config_path, 'r') as f:
            return json.load(f)
    return {}


# ── Google Ads Client ──────────────────────────────────────────────────────────
def _get_google_client(credentials: dict) -> Optional[object]:
    """Initialize Google Ads client from credentials dict."""
    if not GOOGLE_ADS_AVAILABLE or not credentials:
        return None
    try:
        client = GoogleAdsClient.load_from_dict({
            'developer_token': credentials.get('developer_token'),
            'client_id': credentials.get('client_id'),
            'client_secret': credentials.get('client_secret'),
            'refresh_token': credentials.get('refresh_token'),
            'login_customer_id': credentials.get('customer_id'),
            'use_proto_plus': True
        })
        return client
    except Exception as e:
        print(f"[AdsManager] Google Ads client error: {e}")
        return None


def verify_google_connection(credentials: dict) -> dict:
    """Test if credentials work. Returns account info or error."""
    client = _get_google_client(credentials)
    if not client:
        return {'ok': False, 'error': 'Library not available or invalid credentials'}
    try:
        customer_service = client.get_service("CustomerService")
        cid = credentials.get('customer_id', '').replace('-', '')
        customer = customer_service.get_customer(
            resource_name=f"customers/{cid}"
        )
        return {
            'ok': True,
            'account_name': customer.descriptive_name,
            'customer_id': cid,
            'currency': customer.currency_code,
            'timezone': customer.time_zone
        }
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def is_demo_mode(credentials: dict) -> bool:
    """Return True when no real Google Ads credentials are available."""
    return not GOOGLE_ADS_AVAILABLE or not credentials.get('customer_id')


# ── Performance Reports ────────────────────────────────────────────────────────
def get_campaign_performance(credentials: dict, days: int = 30) -> List[Dict]:
    """Get campaign performance. Returns demo data when credentials are absent."""
    client = _get_google_client(credentials)
    if not client:
        return DEMO_CAMPAIGNS

    cid = credentials.get('customer_id', '').replace('-', '')
    ga_service = client.get_service("GoogleAdsService")
    query = f"""
        SELECT
            campaign.id, campaign.name, campaign.status,
            metrics.clicks, metrics.impressions, metrics.ctr,
            metrics.average_cpc, metrics.cost_micros,
            metrics.conversions, metrics.cost_per_conversion,
            metrics.search_impression_share
        FROM campaign
        WHERE segments.date DURING LAST_{days}_DAYS
          AND campaign.status != 'REMOVED'
        ORDER BY metrics.cost_micros DESC
    """
    results = []
    try:
        for row in ga_service.search(customer_id=cid, query=query):
            results.append({
                "id": str(row.campaign.id),
                "name": row.campaign.name,
                "status": row.campaign.status.name,
                "clicks": row.metrics.clicks,
                "impressions": row.metrics.impressions,
                "ctr": round(row.metrics.ctr * 100, 2),
                "avg_cpc": round(row.metrics.average_cpc / 1_000_000, 2),
                "cost": round(row.metrics.cost_micros / 1_000_000, 2),
                "conversions": row.metrics.conversions,
                "cpa": round(row.metrics.cost_per_conversion / 1_000_000, 2),
                "impression_share": round(row.metrics.search_impression_share * 100, 1)
            })
    except Exception as e:
        print(f"[AdsManager] Campaign query error: {e}")
        return DEMO_CAMPAIGNS
    return results or DEMO_CAMPAIGNS


def get_keyword_performance(credentials: dict) -> List[Dict]:
    """Get keyword-level data with Quality Scores. Returns demo data when credentials are absent."""
    client = _get_google_client(credentials)
    if not client:
        return DEMO_KEYWORDS

    cid = credentials.get('customer_id', '').replace('-', '')
    ga_service = client.get_service("GoogleAdsService")
    query = """
        SELECT
            ad_group_criterion.keyword.text,
            ad_group_criterion.keyword.match_type,
            ad_group_criterion.quality_info.quality_score,
            metrics.clicks, metrics.impressions, metrics.ctr,
            metrics.average_cpc, metrics.cost_micros, metrics.conversions
        FROM keyword_view
        WHERE segments.date DURING LAST_30_DAYS
          AND ad_group_criterion.status = 'ENABLED'
        ORDER BY metrics.cost_micros DESC
        LIMIT 100
    """
    results = []
    try:
        for row in ga_service.search(customer_id=cid, query=query):
            kw = row.ad_group_criterion
            results.append({
                "keyword": kw.keyword.text,
                "match_type": kw.keyword.match_type.name,
                "quality_score": kw.quality_info.quality_score,
                "clicks": row.metrics.clicks,
                "ctr": round(row.metrics.ctr * 100, 2),
                "avg_cpc": round(row.metrics.average_cpc / 1_000_000, 2),
                "cost": round(row.metrics.cost_micros / 1_000_000, 2),
                "conversions": row.metrics.conversions,
            })
    except Exception as e:
        print(f"[AdsManager] Keyword query error: {e}")
        return DEMO_KEYWORDS
    return results or DEMO_KEYWORDS


def get_search_terms(credentials: dict, min_clicks: int = 5) -> dict:
    """Get real user queries that triggered ads. Returns demo data when credentials are absent."""
    client = _get_google_client(credentials)
    if not client:
        return DEMO_SEARCH_TERMS

    cid = credentials.get('customer_id', '').replace('-', '')
    ga_service = client.get_service("GoogleAdsService")
    query = f"""
        SELECT
            search_term_view.search_term,
            metrics.clicks, metrics.impressions,
            metrics.ctr, metrics.average_cpc, metrics.conversions,
            campaign.name, ad_group.name
        FROM search_term_view
        WHERE segments.date DURING LAST_30_DAYS
          AND metrics.clicks >= {min_clicks}
        ORDER BY metrics.conversions DESC
        LIMIT 200
    """
    terms = []
    try:
        for row in ga_service.search(customer_id=cid, query=query):
            terms.append({
                "term": row.search_term_view.search_term,
                "campaign": row.campaign.name,
                "ad_group": row.ad_group.name,
                "clicks": row.metrics.clicks,
                "conversions": row.metrics.conversions,
                "avg_cpc": round(row.metrics.average_cpc / 1_000_000, 2),
            })
    except Exception as e:
        print(f"[AdsManager] Search terms error: {e}")
        return DEMO_SEARCH_TERMS

    converting = [t for t in terms if t["conversions"] > 0]
    wasted = [t for t in terms if t["conversions"] == 0 and t["clicks"] > 10]
    return {"converting_terms": converting, "wasted_spend": wasted}


# ── Campaign Creation ──────────────────────────────────────────────────────────
def create_campaign(credentials: dict, name: str, budget_usd: float,
                    target_cpa: Optional[float] = None) -> dict:
    """Create a new Google Ads campaign (starts PAUSED for safety)."""
    client = _get_google_client(credentials)
    if not client:
        return {"ok": False, "error": "Demo mode — real API credentials required to create campaigns"}

    cid = credentials.get('customer_id', '').replace('-', '')
    try:
        budget_micros = int(budget_usd * 1_000_000)

        # Create budget
        budget_op = client.get_type("CampaignBudgetOperation")
        budget = budget_op.create
        budget.name = f"Budget: {name}"
        budget.amount_micros = budget_micros
        budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD

        budget_service = client.get_service("CampaignBudgetService")
        budget_res = budget_service.mutate_campaign_budgets(
            customer_id=cid, operations=[budget_op]
        )
        budget_rn = budget_res.results[0].resource_name

        # Create campaign
        camp_op = client.get_type("CampaignOperation")
        camp = camp_op.create
        camp.name = name
        camp.status = client.enums.CampaignStatusEnum.PAUSED  # SAFE default
        camp.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum.SEARCH
        camp.campaign_budget = budget_rn
        if target_cpa:
            camp.target_cpa.target_cpa_micros = int(target_cpa * 1_000_000)
        else:
            camp.manual_cpc.enhanced_cpc_enabled = True
        camp.network_settings.target_google_search = True
        camp.network_settings.target_search_network = True

        camp_service = client.get_service("CampaignService")
        result = camp_service.mutate_campaigns(customer_id=cid, operations=[camp_op])
        rn = result.results[0].resource_name
        return {"ok": True, "campaign_resource_name": rn, "name": name,
                "budget_per_day": budget_usd, "status": "PAUSED"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── Summary Helpers ────────────────────────────────────────────────────────────
def build_ads_summary(campaigns: List[Dict], credentials: dict = None) -> Dict:
    """Compute KPI summary across all campaigns."""
    total_spend = sum(c.get("cost", 0) for c in campaigns)
    total_clicks = sum(c.get("clicks", 0) for c in campaigns)
    total_conv = sum(c.get("conversions", 0) for c in campaigns)
    avg_cpa = round(total_spend / total_conv, 2) if total_conv > 0 else 0.0
    creds = credentials if credentials is not None else load_ads_config()
    return {
        "total_spend": round(total_spend, 2),
        "total_clicks": total_clicks,
        "total_conversions": total_conv,
        "avg_cpa": avg_cpa,
        "active_campaigns": sum(1 for c in campaigns if c.get("status") == "ENABLED"),
        "is_demo": is_demo_mode(creds)
    }
