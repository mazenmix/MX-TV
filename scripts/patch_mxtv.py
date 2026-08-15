#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "StreamVault-src")


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"Patch anchor missing [{label}] in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"patched: {label}")


# 1) FAST XTREAM SYNC
# Manual Settings sync used to deliberately choose CATEGORY_BY_CATEGORY.
# On large providers (e.g. ~900 categories) that means hundreds of HTTP requests.
# Prefer the provider's single streamed get_live_streams catalog for manual/background
# syncs, while preserving existing low-memory, hidden-category, cooldown and user-mode guards.
policy = root / "data/src/main/java/com/streamvault/data/sync/XtreamLiveSyncPolicy.kt"
replace_once(
    policy,
    """        return when (syncReason) {\n            XtreamLiveSyncReason.BACKGROUND_STALE,\n            XtreamLiveSyncReason.MANUAL_SETTINGS -> EffectiveXtreamLiveSyncMethod.CATEGORY_BY_CATEGORY\n            XtreamLiveSyncReason.INITIAL_ONBOARDING,\n            XtreamLiveSyncReason.FOREGROUND -> EffectiveXtreamLiveSyncMethod.STREAM_ALL\n        }\n""",
    """        return when (syncReason) {\n            XtreamLiveSyncReason.BACKGROUND_STALE,\n            XtreamLiveSyncReason.MANUAL_SETTINGS,\n            XtreamLiveSyncReason.INITIAL_ONBOARDING,\n            XtreamLiveSyncReason.FOREGROUND -> EffectiveXtreamLiveSyncMethod.STREAM_ALL\n        }\n""",
    "manual/background sync uses streamed full catalog",
)

# Large Android-TV providers should not fall back to 1–2 category requests at a time.
# Keep concurrency bounded so the provider is not hammered, but make fallback practical.
profile = root / "data/src/main/java/com/streamvault/data/sync/CatalogSyncRuntimeProfile.kt"
replace_once(
    profile,
    "maxCategoryConcurrency = 1,",
    "maxCategoryConcurrency = if (snapshot.isTelevision) 4 else 1,",
    "low-tier TV category fallback concurrency",
)
replace_once(
    profile,
    "maxCategoryConcurrency = 2,",
    "maxCategoryConcurrency = if (snapshot.isTelevision) 8 else 2,",
    "mid-tier TV category fallback concurrency",
)
replace_once(
    profile,
    "maxCategoryConcurrency = Int.MAX_VALUE,",
    "maxCategoryConcurrency = if (snapshot.isTelevision) 12 else 16,",
    "high-tier bounded category fallback concurrency",
)

# Avoid hour-long EPG retry loops in the visible sync experience. Give transient EPG
# problems one WorkManager retry; after that keep the already-synced Live TV usable.
epg_worker = root / "data/src/main/java/com/streamvault/data/sync/BackgroundEpgSyncWorker.kt"
replace_once(
    epg_worker,
    """                        Log.i(TAG, \"Scheduling retry for provider $providerId: EPG completed with retryable failure\")\n                        Result.retry()\n""",
    """                        Log.i(TAG, \"EPG had a retryable partial failure for provider $providerId\")\n                        if (runAttemptCount >= 1) Result.success() else Result.retry()\n""",
    "cap partial EPG retry loop",
)
replace_once(
    epg_worker,
    """                    } else if (shouldRetry(result.exception)) {\n                        Result.retry()\n""",
    """                    } else if (shouldRetry(result.exception)) {\n                        if (runAttemptCount >= 1) Result.success() else Result.retry()\n""",
    "cap network/database EPG retry loop",
)
replace_once(
    epg_worker,
    "com.streamvault.domain.model.Result.Loading -> Result.retry()",
    "com.streamvault.domain.model.Result.Loading -> if (runAttemptCount >= 1) Result.success() else Result.retry()",
    "cap loading EPG retry loop",
)
replace_once(
    epg_worker,
    "if (shouldRetry(e)) Result.retry() else Result.failure()",
    "if (shouldRetry(e)) { if (runAttemptCount >= 1) Result.success() else Result.retry() } else Result.failure()",
    "cap exceptional EPG retry loop",
)

# 2) ROOMIER LIVE-TV BROWSER
home = root / "app/src/main/java/com/streamvault/app/ui/screens/home/HomeScreen.kt"
replace_once(home, "        272.dp\n    }\n    val channelSearchWidth", "        320.dp\n    }\n    val channelSearchWidth", "wider TV category sidebar")
replace_once(home, "        320.dp\n    } else if (isDenseMode) {\n        300.dp\n    } else {\n        340.dp", "        380.dp\n    } else if (isDenseMode) {\n        370.dp\n    } else {\n        400.dp", "wider channel search/list column")
replace_once(
    home,
    """    val channelRowHeight = when (uiState.liveTvChannelMode) {\n        LiveTvChannelMode.COMFORTABLE -> 92.dp\n        LiveTvChannelMode.COMPACT -> 54.dp\n        LiveTvChannelMode.PRO -> 52.dp\n    }\n    val channelListSpacing = when (uiState.liveTvChannelMode) {\n        LiveTvChannelMode.COMFORTABLE -> 8.dp\n        LiveTvChannelMode.COMPACT -> 2.dp\n        LiveTvChannelMode.PRO -> 2.dp\n    }\n""",
    """    val channelRowHeight = when (uiState.liveTvChannelMode) {\n        LiveTvChannelMode.COMFORTABLE -> 104.dp\n        LiveTvChannelMode.COMPACT -> 76.dp\n        LiveTvChannelMode.PRO -> 72.dp\n    }\n    val channelListSpacing = when (uiState.liveTvChannelMode) {\n        LiveTvChannelMode.COMFORTABLE -> 12.dp\n        LiveTvChannelMode.COMPACT -> 7.dp\n        LiveTvChannelMode.PRO -> 6.dp\n    }\n""",
    "larger channel rows and breathing room",
)

sidebar = root / "app/src/main/java/com/streamvault/app/ui/screens/home/HomeSidebarComponents.kt"
replace_once(sidebar, ".padding(vertical = 2.dp)", ".padding(vertical = 4.dp)", "more category row separation")
replace_once(sidebar, "Modifier.padding(horizontal = 12.dp, vertical = 10.dp)", "Modifier.padding(horizontal = 16.dp, vertical = 14.dp)", "larger category touch/focus rows")
replace_once(sidebar, "style = MaterialTheme.typography.bodyMedium,\n                maxLines = 1,", "style = MaterialTheme.typography.titleSmall,\n                maxLines = 1,", "larger category names")
# Also widen reorder/category-side panels on TV where the same 272dp desktop width is used.
text = sidebar.read_text(encoding="utf-8")
text = text.replace("        272.dp\n    }", "        320.dp\n    }")
sidebar.write_text(text, encoding="utf-8")

cards = root / "app/src/main/java/com/streamvault/app/ui/components/shell/AppMediaCards.kt"
replace_once(cards, "val contentPadding = if (isUltraCompact) 5.dp else 6.dp", "val contentPadding = if (isUltraCompact) 7.dp else 9.dp", "roomier live row vertical padding")
replace_once(cards, "val horizontalPadding = if (isUltraCompact) 8.dp else 10.dp", "val horizontalPadding = if (isUltraCompact) 10.dp else 14.dp", "roomier live row horizontal padding")
replace_once(cards, "val logoWidth = if (isDense) 42.dp else if (isUltraCompact) 46.dp else 52.dp", "val logoWidth = if (isDense) 48.dp else if (isUltraCompact) 54.dp else 64.dp", "larger channel logos")
replace_once(cards, "val contentSpacing = if (isUltraCompact) 8.dp else 10.dp", "val contentSpacing = if (isUltraCompact) 10.dp else 14.dp", "more live row content spacing")
replace_once(cards, "style = if (isDense) MaterialTheme.typography.bodyLarge else MaterialTheme.typography.titleSmall,", "style = if (isDense) MaterialTheme.typography.titleSmall else MaterialTheme.typography.titleMedium,", "larger channel titles")
replace_once(cards, "style = if (isDense) MaterialTheme.typography.labelMedium else MaterialTheme.typography.bodySmall,", "style = if (isDense) MaterialTheme.typography.bodySmall else MaterialTheme.typography.bodyMedium,", "larger EPG program text")

# 3) MX TV BRANDING for this side-by-side test build.
for strings in (root / "app/src/main/res").glob("values*/strings.xml"):
    data = strings.read_text(encoding="utf-8")
    data = data.replace("StreamVault", "MX TV").replace("Stream Vault", "MX TV")
    strings.write_text(data, encoding="utf-8")

debug_strings = root / "app/src/debug/res/values/strings.xml"
if debug_strings.exists():
    data = debug_strings.read_text(encoding="utf-8")
    data = re.sub(r'<string name="app_name">.*?</string>', '<string name="app_name">MX TV</string>', data)
    debug_strings.write_text(data, encoding="utf-8")

print("MX TV patch complete")
