"""Job definitions for all scheduled tasks.

This file defines all jobs that were previously cron jobs.
Each job has a trigger (cron/interval) and execution details.
"""

from app.models.job import JobDefinition, JobTriggerType


# ==============================================================================
# Job Definitions
# ==============================================================================

JOB_DEFINITIONS = [
    # -------------------------------------------------------------------------
    # Very High Frequency (every 1 minute)
    # -------------------------------------------------------------------------
    # NOTE: battle_event_detector moved to war-intel-service's own scheduler

    # -------------------------------------------------------------------------
    # High Frequency (every 5-15 minutes)
    # -------------------------------------------------------------------------
    JobDefinition(
        id="token_refresh",
        name="OAuth Token Refresh",
        description="Refresh expiring ESI tokens for all characters (EVE tokens expire after 20 min)",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"minute": "*/15"},
        func="app.jobs.executors.run_token_refresh",
        tags=["auth", "character", "high-frequency", "critical"]
    ),

    JobDefinition(
        id="aggregate_hourly_stats",
        name="Alliance Hourly Stats Aggregator",
        description="Aggregate killmails into intelligence_hourly_stats (Alliance level, Phase 2)",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"minute": "*/30"},  # Every 30 minutes
        func="app.jobs.executors.run_aggregate_hourly_stats",
        tags=["war", "intelligence", "high-frequency", "critical"]
    ),

    JobDefinition(
        id="aggregate_corp_hourly_stats",
        name="Corporation Hourly Stats Aggregator",
        description="Aggregate killmails into corporation_hourly_stats (Corporation level, Phase 1 Bottom-Up)",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"minute": "1,31"},  # Every 30 minutes (offset by 1 min to avoid DB contention)
        func="app.jobs.executors.run_aggregate_corp_hourly_stats",
        tags=["war", "intelligence", "corporation", "high-frequency", "critical"]
    ),

    JobDefinition(
        id="batch_calculator",
        name="Manufacturing Opportunities Calculator",
        description="Calculate profitable manufacturing opportunities",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"minute": "*/5"},
        func="app.jobs.executors.run_batch_calculator",
        tags=["market", "production", "high-frequency"]
    ),
    
    JobDefinition(
        id="economy_manipulation_scanner",
        name="Market Manipulation Scanner",
        description="Detect market manipulation via Z-score analysis",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"minute": "*/15"},
        func="app.jobs.executors.run_economy_manipulation_scanner",
        tags=["market", "security", "high-frequency"]
    ),

    # -------------------------------------------------------------------------
    # Medium Frequency (every 30 minutes)
    # -------------------------------------------------------------------------
    JobDefinition(
        id="regional_prices",
        name="Regional Price Fetcher",
        description="Fetch market prices from ESI for all regions",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"minute": "0,30"},
        func="app.jobs.executors.run_regional_prices",
        tags=["market", "medium-frequency"]
    ),
    
    JobDefinition(
        id="sov_tracker",
        name="Sovereignty Campaign Tracker",
        description="Update sovereignty campaign data from ESI",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"minute": "2,32"},
        func="app.jobs.executors.run_sov_tracker",
        tags=["war", "sovereignty", "medium-frequency"]
    ),
    
    JobDefinition(
        id="fw_tracker",
        name="Faction Warfare Tracker",
        description="Update faction warfare system status",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"minute": "4,34"},
        func="app.jobs.executors.run_fw_tracker",
        tags=["war", "faction-warfare", "medium-frequency"]
    ),
    
    JobDefinition(
        id="character_sync",
        name="Character Data Sync",
        description="Sync character data (wallet, skills, assets)",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"minute": "*/15"},
        func="app.jobs.executors.run_character_sync",
        tags=["character", "medium-frequency"]
    ),
    
    JobDefinition(
        id="economy_fuel_poller",
        name="Fuel Market Poller",
        description="Monitor isotope markets for capital movement intel",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"minute": "8,38"},
        func="app.jobs.executors.run_economy_fuel_poller",
        tags=["market", "war-economy", "medium-frequency"]
    ),
    
    JobDefinition(
        id="economy_price_snapshotter",
        name="Price History Snapshotter",
        description="Snapshot critical item prices for trend analysis",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"minute": "10,40"},
        func="app.jobs.executors.run_economy_price_snapshotter",
        tags=["market", "history", "medium-frequency"]
    ),
    
    JobDefinition(
        id="coalition_refresh",
        name="Coalition Fight Tables Update",
        description="Update alliance fight relationships (together/against) with 90-day data for Power Bloc detection",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"minute": "12,42"},
        func="app.jobs.executors.run_coalition_refresh",
        tags=["war", "coalition", "medium-frequency"]
    ),

    JobDefinition(
        id="battle_cleanup",
        name="Battle Cleanup",
        description="End stale battles and cleanup old data",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"minute": "12,42"},
        func="app.jobs.executors.run_battle_cleanup",
        tags=["war", "cleanup", "medium-frequency"]
    ),

    # NOTE: pi_monitor will move to production-service's own scheduler in Week 3
    JobDefinition(
        id="pi_monitor",
        name="PI Colony Monitor",
        description="Check PI colonies for expiring extractors and storage alerts",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"minute": "14,44"},
        func="app.jobs.executors.run_pi_monitor",
        tags=["pi", "alerts", "medium-frequency"],
        enabled=False  # Disabled until production-service migration
    ),

    JobDefinition(
        id="portfolio_snapshotter",
        name="Portfolio Snapshotter",
        description="Snapshot portfolio values for tracking",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"minute": "20,50"},
        func="app.jobs.executors.run_portfolio_snapshotter",
        tags=["portfolio", "tracking", "medium-frequency"]
    ),

    JobDefinition(
        id="arbitrage_calculator",
        name="Arbitrage Route Calculator",
        description="Pre-calculate profitable arbitrage routes between trade hubs",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"minute": "15,45"},
        func="app.jobs.executors.run_arbitrage_calculator",
        tags=["market", "arbitrage", "medium-frequency"]
    ),

    JobDefinition(
        id="market_undercut_checker",
        name="Market Undercut Checker",
        description="Check for undercut orders and send alerts",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"minute": "*/15"},
        func="app.jobs.executors.run_market_undercut_checker",
        tags=["market", "trading", "alerts", "medium-frequency"]
    ),

    JobDefinition(
        id="wallet_poll",
        name="Wallet Journal Poll",
        description="Check for ISK payments to service wallet",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"minute": "*/5"},
        func="app.jobs.executors.run_wallet_poll",
        tags=["subscription", "payments", "high-frequency"]
    ),

    # -------------------------------------------------------------------------
    # Hourly Jobs
    # -------------------------------------------------------------------------
    JobDefinition(
        id="telegram_report",
        name="Telegram Battle Report",
        description="Send hourly battle summary to Telegram",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"minute": "0"},
        func="app.jobs.executors.run_telegram_report",
        tags=["reporting", "telegram", "hourly"]
    ),
    
    JobDefinition(
        id="alliance_wars",
        name="Alliance Wars Analyzer",
        description="Analyze alliance conflicts and wars",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"minute": "30"},
        func="app.jobs.executors.run_alliance_wars",
        tags=["war", "analysis", "hourly"]
    ),

    # -------------------------------------------------------------------------
    # Every 6 Hours
    # -------------------------------------------------------------------------
    JobDefinition(
        id="war_profiteering",
        name="War Profiteering Analyzer",
        description="Identify war-driven market opportunities",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"hour": "*/6", "minute": "0"},
        func="app.jobs.executors.run_war_profiteering",
        tags=["market", "war", "low-frequency"]
    ),
    
    JobDefinition(
        id="report_generator",
        name="Intelligence Report Generator",
        description="Generate comprehensive intelligence reports",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"hour": "*/6", "minute": "15"},
        func="app.jobs.executors.run_report_generator",
        tags=["reporting", "intelligence", "low-frequency"]
    ),

    # -------------------------------------------------------------------------
    # Daily Jobs
    # -------------------------------------------------------------------------
    JobDefinition(
        id="capability_sync",
        name="Corporation Capability Sync",
        description="Sync corporation capabilities and blueprints",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"hour": "4", "minute": "0"},
        func="app.jobs.executors.run_capability_sync",
        tags=["corporation", "daily"]
    ),

    JobDefinition(
        id="market_history_sync",
        name="Market History Sync",
        description="Sync ESI market history and calculate trading metrics",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"hour": "4", "minute": "0"},
        func="app.jobs.executors.run_market_history_sync",
        tags=["market", "trading", "daily"]
    ),
    
    JobDefinition(
        id="skill_snapshot",
        name="Character Skill Snapshot",
        description="Snapshot character skills for progress tracking",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"hour": "5", "minute": "15"},
        func="app.jobs.executors.run_skill_snapshot",
        tags=["character", "daily"]
    ),

    JobDefinition(
        id="alliance_fingerprints",
        name="Alliance Doctrine Fingerprints",
        description="Build ship usage fingerprints per alliance from killmail data",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"hour": "5", "minute": "30"},
        func="app.jobs.executors.run_alliance_fingerprints",
        tags=["war", "doctrines", "daily"]
    ),

    JobDefinition(
        id="wh_sov_threats",
        name="WH SOV Threats Analysis",
        description="Analyze wormhole threats to alliance sovereignty space (threat levels, attackers, regions, doctrines)",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"hour": "5", "minute": "45"},
        func="app.jobs.executors.run_wh_sov_threats",
        tags=["wormhole", "war", "daily"]
    ),

    JobDefinition(
        id="pilot_skill_estimates",
        name="Pilot Skill Estimates",
        description="Calculate minimum skillpoints for pilots based on ships and modules used in combat",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"hour": "6", "minute": "15"},
        func="app.jobs.executors.run_pilot_skill_estimates",
        tags=["intelligence", "capsuleer", "daily"]
    ),

    JobDefinition(
        id="corporation_sync",
        name="Corporation Sync",
        description="Sync corporation membership for active alliances from ESI (Truth #1: structural membership)",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"hour": "6", "minute": "0"},
        func="app.jobs.executors.run_corporation_sync",
        tags=["war", "coalition", "daily"]
    ),

    JobDefinition(
        id="killmail_fetcher",
        name="Daily Killmail Fetcher",
        description="Fetch daily killmails (legacy backup)",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"hour": "6", "minute": "0"},
        func="app.jobs.executors.run_killmail_fetcher",
        tags=["war", "killmails", "daily"]
    ),
    
    JobDefinition(
        id="doctrine_clustering",
        name="Doctrine Clustering",
        description="Cluster ship losses to detect doctrines",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"hour": "6", "minute": "30"},
        func="app.jobs.executors.run_doctrine_clustering",
        tags=["war", "doctrines", "daily"]
    ),
    
    JobDefinition(
        id="everef_importer",
        name="Everef Killmail Importer",
        description="Import killmails from Everef daily dumps",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"hour": "7", "minute": "0"},
        func="app.jobs.executors.run_everef_importer",
        tags=["war", "killmails", "daily"]
    ),

    # -------------------------------------------------------------------------
    # Wormhole Service Jobs
    # -------------------------------------------------------------------------
    JobDefinition(
        id="wormhole_data_sync",
        name="Wormhole Data Sync",
        description="Sync static wormhole data from Pathfinder",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"hour": "3", "minute": "0"},
        func="app.jobs.executors.run_wormhole_data_sync",
        tags=["wormhole", "data-sync", "daily"]
    ),

    JobDefinition(
        id="wormhole_stats_refresh",
        name="Wormhole Stats Refresh",
        description="Refresh resident detection and activity stats",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"hour": "*/6", "minute": "15"},
        func="app.jobs.executors.run_wormhole_stats_refresh",
        tags=["wormhole", "stats", "low-frequency"]
    ),

    # -------------------------------------------------------------------------
    # DOTLAN Scraping Service Jobs
    # -------------------------------------------------------------------------
    JobDefinition(
        id="dotlan_activity_region",
        name="DOTLAN Activity Region Scan",
        description="Scrape current activity values for all K-Space regions from DOTLAN",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"hour": "*/2", "minute": "5"},
        func="app.jobs.executors.run_dotlan_activity_region",
        tags=["dotlan", "activity", "medium-frequency"]
    ),

    JobDefinition(
        id="dotlan_activity_detail",
        name="DOTLAN Activity Detail Scan",
        description="Scrape 7-day hourly history for top active systems from DOTLAN",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"hour": "*/6", "minute": "20"},
        func="app.jobs.executors.run_dotlan_activity_detail",
        tags=["dotlan", "activity", "low-frequency"]
    ),

    JobDefinition(
        id="dotlan_sov_campaigns",
        name="DOTLAN Sovereignty Campaigns",
        description="Scrape active sovereignty campaigns from DOTLAN (time-critical)",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"minute": "*/10"},
        func="app.jobs.executors.run_dotlan_sov_campaigns",
        tags=["dotlan", "sovereignty", "high-frequency"]
    ),

    JobDefinition(
        id="dotlan_sov_changes",
        name="DOTLAN Sovereignty Changes",
        description="Scrape historical sovereignty changes from DOTLAN",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"hour": "4", "minute": "10"},
        func="app.jobs.executors.run_dotlan_sov_changes",
        tags=["dotlan", "sovereignty", "daily"]
    ),

    JobDefinition(
        id="dotlan_alliance_rankings",
        name="DOTLAN Alliance Rankings",
        description="Scrape alliance rankings (systems, members, corps) from DOTLAN",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"hour": "0,12", "minute": "30"},
        func="app.jobs.executors.run_dotlan_alliance_rankings",
        tags=["dotlan", "alliances", "low-frequency"]
    ),

    JobDefinition(
        id="dotlan_cleanup",
        name="DOTLAN Data Cleanup",
        description="Clean up old DOTLAN data based on retention policies",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"hour": "3", "minute": "15"},
        func="app.jobs.executors.run_dotlan_cleanup",
        tags=["dotlan", "cleanup", "daily"]
    ),

    # -------------------------------------------------------------------------
    # Management Suite Jobs
    # -------------------------------------------------------------------------
    JobDefinition(
        id="notification_sync",
        name="ESI Notification Sync",
        description="Sync ESI notifications for all authenticated characters",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"minute": "*/10"},
        func="app.jobs.executors.run_notification_sync",
        tags=["esi", "notifications", "10min"]
    ),

    JobDefinition(
        id="contract_sync",
        name="Corporation Contract Sync",
        description="Sync corporation contracts from ESI for all corps",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"minute": "15,45"},
        func="app.jobs.executors.run_contract_sync",
        tags=["esi", "contracts", "30min"]
    ),

    JobDefinition(
        id="timer_expiry_check",
        name="Timer Expiry Check",
        description="Expire old timers and alert on soon-expiring timers",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"minute": "*/5"},
        func="app.jobs.executors.run_timer_expiry_check",
        tags=["timers", "5min"]
    ),

    JobDefinition(
        id="sov_asset_snapshot",
        name="Sovereignty Asset Snapshot",
        description="Create snapshots of sovereignty assets for delta analysis",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"hour": "*/6", "minute": "45"},
        func="app.jobs.executors.run_sov_asset_snapshot",
        tags=["sovereignty", "snapshots", "6h"]
    ),

    JobDefinition(
        id="token_rekey",
        name="Token Re-encryption Check",
        description="Re-encrypt tokens with current key if encrypted with old key",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"hour": "3", "minute": "0"},
        func="app.jobs.executors.run_token_rekey",
        tags=["security", "daily"]
    ),

    JobDefinition(
        id="corp_wallet_sync",
        name="Corporation Wallet Sync",
        description="Sync corporation wallet journals from ESI via finance-service",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"minute": "5,35"},
        func="app.jobs.executors.run_corp_wallet_sync",
        tags=["finance", "wallet", "30min"]
    ),

    JobDefinition(
        id="mining_observer_sync",
        name="Mining Observer & Extraction Sync",
        description="Sync mining observers, ledgers, extractions, and ore prices via finance-service",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"minute": "10,40"},
        func="app.jobs.executors.run_mining_observer_sync",
        tags=["finance", "mining", "30min"]
    ),

    # === SaaS Payment & Subscription ===
    JobDefinition(
        id="payment_poll",
        name="ISK Payment Poll",
        description="Poll holding character wallet journal for subscription payments",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"minute": "*/1"},
        func="app.jobs.executors.run_payment_poll",
        enabled=True,  # Holding character "Mind Overmatter" configured
        tags=["saas", "payments"]
    ),
    JobDefinition(
        id="subscription_expiry",
        name="Subscription Expiry Check",
        description="Expire stale subscriptions (active->grace->expired)",
        trigger_type=JobTriggerType.CRON,
        trigger_args={"minute": "0"},
        func="app.jobs.executors.run_subscription_expiry",
        enabled=True,  # SaaS live — grace period: active → grace → expired
        tags=["saas", "subscriptions"]
    ),
]


def get_job_definitions() -> list[JobDefinition]:
    """Get all job definitions."""
    return JOB_DEFINITIONS


def get_job_by_id(job_id: str) -> JobDefinition | None:
    """Get a job definition by ID."""
    for job in JOB_DEFINITIONS:
        if job.id == job_id:
            return job
    return None
