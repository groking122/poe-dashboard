"""
PoE Mirage Economy Dashboard v5
================================
All prices in chaos. Fetches live div/chaos ratio.
Features: Economy, Craft Finder, Suggest, Flip Finder, Budget Planner, Alerts,
          Currency Exchange, Zero to Mirror, Tools & Resources, Whale Mode.
Simple/Pro mode toggle. Centered layout with improved UI/UX.
History snapshots saved to poe_dashboard_history/ (last 20 kept).
Alerts include: spike, crash, drying, flood, new, underpriced, meta_spike, corner_risk.

Run:  python poe_dashboard.py           (generate static HTML)
      python poe_dashboard.py --serve   (live server with refresh button)
Open: http://localhost:5000 (serve mode) or poe_dashboard.html (static mode)
"""

import urllib.request
import json
import os
import sys
import glob as globmod
import statistics
import threading
from datetime import datetime

LEAGUE = "Mirage"
PREV_DATA_FILE = "poe_dashboard_prev.json"
HISTORY_DIR = "poe_dashboard_history"
HISTORY_MAX = 20

ITEM_TYPES = [
    ("UniqueArmour",    "Unique Armours"),
    ("UniqueWeapon",    "Unique Weapons"),
    ("UniqueJewel",     "Unique Jewels"),
    ("UniqueAccessory", "Unique Accessories"),
    ("UniqueFlask",     "Unique Flasks"),
    ("SkillGem",        "Skill Gems"),
    ("BaseType",        "Base Types"),
]

META_BUILDS = {
    "Poisonous Concoction Pathfinder": {
        "abbr": "PC PF",
        "armours": ["dendrobate", "cherrubim", "carcass jack", "atziri's step",
                     "the embalmer", "darkray vectors", "rat's nest"],
        "weapons": [],
        "accessories": ["mark of the elder", "circle of nostalgia", "aul's uprising",
                        "impresence", "atziri's foible"],
        "flasks": ["dying sun", "atziri's promise", "taste of hate",
                   "bottled faith", "the writhing jar"],
        "jewels": ["watcher's eye", "large cluster jewel", "medium cluster jewel",
                   "forbidden flame", "forbidden flesh", "unnatural instinct"],
        "gems": ["poisonous concoction", "plague bearer", "herald of agony",
                 "malevolence", "determination", "grace", "vaal grace"],
    },
    "Lightning Arrow Deadeye": {
        "abbr": "LA DE",
        "armours": ["hyrri's ire", "queen of the forest", "hyrri's demise",
                     "atziri's step", "darkray vectors", "rat's nest",
                     "starkonja's head", "farrul's fur"],
        "weapons": ["windripper", "deaths opus", "death's opus", "doomfletch's prism",
                     "voltaxic rift", "the tempest"],
        "accessories": ["rigwald's quills", "hyrri's truth", "hyrri's bite",
                        "mark of the elder", "aul's uprising", "badge of the brotherhood"],
        "flasks": ["dying sun", "taste of hate", "bottled faith",
                   "atziri's promise", "the wise oak"],
        "jewels": ["watcher's eye", "inspired learning", "unnatural instinct",
                   "forbidden flame", "forbidden flesh", "large cluster jewel"],
        "gems": ["lightning arrow", "barrage", "wrath", "grace",
                 "determination", "herald of ice", "mark of the elder"],
    },
    "Glacial Cascade Miner": {
        "abbr": "GC Mine",
        "armours": ["tremor rod", "cloak of defiance", "indigon",
                     "atziri's step", "kaom's heart", "carcass jack"],
        "weapons": ["tremor rod", "void battery", "pledge of hands"],
        "accessories": ["atziri's foible", "mark of the shaper",
                        "badge of the brotherhood", "aul's uprising",
                        "presence of chayula"],
        "flasks": ["bottled faith", "atziri's promise", "dying sun",
                   "cinderswallow urn", "taste of hate"],
        "jewels": ["watcher's eye", "large cluster jewel", "medium cluster jewel",
                   "forbidden flame", "forbidden flesh", "unnatural instinct"],
        "gems": ["glacial cascade", "high-impact mine support", "trap and mine damage support",
                 "zealotry", "determination", "clarity"],
    },
    "Righteous Fire Chieftain": {
        "abbr": "RF Chief",
        "armours": ["rise of the phoenix", "saffell's frame",
                     "kaom's heart", "legacy of fury", "aegis aurora",
                     "the brass dome", "dawnbreaker"],
        "weapons": ["searing touch"],
        "accessories": ["pyre", "leadership's price", "atziri's foible",
                        "aul's uprising", "presence of chayula"],
        "flasks": ["bottled faith", "dying sun", "ruby flask",
                   "taste of hate", "atziri's promise"],
        "jewels": ["watcher's eye", "large cluster jewel", "medium cluster jewel",
                   "forbidden flame", "forbidden flesh", "unnatural instinct",
                   "sublime vision"],
        "gems": ["righteous fire", "fire trap", "determination",
                 "purity of fire", "purity of elements", "malevolence",
                 "vaal righteous fire"],
    },
    "CWS Chieftain": {
        "abbr": "CWS Chief",
        "armours": ["kaom's heart", "carcass jack", "the brass dome",
                     "aegis aurora", "legacy of fury", "dawnbreaker"],
        "weapons": ["mjolner", "cospri's malice"],
        "accessories": ["aul's uprising", "atziri's foible",
                        "presence of chayula", "leadership's price",
                        "mageblood"],
        "flasks": ["bottled faith", "dying sun", "atziri's promise",
                   "taste of hate"],
        "jewels": ["watcher's eye", "forbidden flame", "forbidden flesh",
                   "large cluster jewel", "unnatural instinct", "sublime vision"],
        "gems": ["cast when stunned support", "determination", "molten shell",
                 "purity of elements", "defiance banner"],
    },
    "Bleed Bow Gladiator": {
        "abbr": "Bleed Glad",
        "armours": ["lioneye's vision", "assailum", "haemophilia",
                     "atziri's step", "belly of the beast", "farrul's fur",
                     "hyrri's ire", "drillneck"],
        "weapons": ["lioneye's glare", "chin sol", "reach of the council",
                     "the crimson storm"],
        "accessories": ["ryslatha's coil", "rigwald's quills",
                        "mark of the elder", "aul's uprising",
                        "vulnerability on hit ring"],
        "flasks": ["lion's roar", "taste of hate", "atziri's promise",
                   "dying sun", "bottled faith"],
        "jewels": ["watcher's eye", "large cluster jewel", "medium cluster jewel",
                   "forbidden flame", "forbidden flesh", "unnatural instinct"],
        "gems": ["puncture", "split arrow", "ensnaring arrow",
                 "pride", "determination", "malevolence", "blood and sand"],
    },
}

TRADE_CATEGORIES = {
    "UniqueArmour": "unique-armours", "UniqueWeapon": "unique-weapons",
    "UniqueJewel": "unique-jewels", "UniqueAccessory": "unique-accessories",
    "UniqueFlask": "unique-flasks", "SkillGem": "skill-gems", "BaseType": "base-types",
}


# ═══════════════════════════════════════════════════════════════════════════════
# FETCHING
# ═══════════════════════════════════════════════════════════════════════════════

def fetch(item_type):
    url = f"https://poe.ninja/api/data/itemoverview?league={LEAGUE}&type={item_type}"
    print(f"  Fetching {item_type}...")
    req = urllib.request.Request(url, headers={"User-Agent": "poe-dashboard/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read()).get("lines", [])


def fetch_divine_ratio():
    url = f"https://poe.ninja/api/data/currencyoverview?league={LEAGUE}&type=Currency"
    print("  Fetching currency rates...")
    req = urllib.request.Request(url, headers={"User-Agent": "poe-dashboard/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        for line in data.get("lines", []):
            if line.get("currencyTypeName") == "Divine Orb":
                return round(line.get("chaosEquivalent", 0), 1)
    except Exception as e:
        print(f"  !! Failed to fetch currency: {e}")
    return 0


def fetch_all_currencies():
    """Fetch currency data with REAL in-game exchange ratios.

    poe.ninja API values:
      pay.value = how many of THIS CURRENCY people offer per 1 chaos
                  (e.g. GCP pay=0.55 means "I give 0.55 GCP for your 1c" → buy ratio ~1.82:1)
      receive.value = how many chaos people offer per 1 of this currency
                  (e.g. GCP receive=3.0 means "I give 3c for your 1 GCP")

    IMPORTANT: These are poe.ninja averages, NOT exact in-game listings.
    Real spreads are much tighter than what the raw numbers suggest.
    We show the ratios honestly and warn when spread looks unreliable.
    """
    url = f"https://poe.ninja/api/data/currencyoverview?league={LEAGUE}&type=Currency"
    print("  Fetching all currencies...")
    req = urllib.request.Request(url, headers={"User-Agent": "poe-dashboard/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        currencies = []
        lines = data.get("lines", [])
        for line in lines:
            name = line.get("currencyTypeName", "")
            chaos_eq = round(line.get("chaosEquivalent", 0), 2)
            pay_obj = line.get("pay")
            receive_obj = line.get("receive")

            if not pay_obj or not pay_obj.get("value") or not pay_obj.get("listing_count"):
                continue
            if not receive_obj or not receive_obj.get("value") or not receive_obj.get("listing_count"):
                continue

            pay_val = pay_obj["value"]       # units of currency per 1 chaos (buy side)
            recv_val = receive_obj["value"]  # chaos per 1 unit of currency (sell side)
            pay_listings = pay_obj.get("listing_count", 0)
            recv_listings = receive_obj.get("listing_count", 0)

            if pay_listings < 3 or recv_listings < 3:
                continue

            # Show as ratios people actually see in-game
            # Buy ratio: how many of this currency per 1 chaos you get
            buy_ratio = round(pay_val, 4)  # e.g. 2.89 GCP per chaos
            # Sell ratio: how many of this currency per 1 chaos you give
            sell_ratio = round(1.0 / recv_val, 4) if recv_val > 0 else 0  # e.g. 2.7 GCP per chaos

            # For expensive currencies (>1c each), show as chaos per unit
            is_expensive = chaos_eq >= 1
            if is_expensive:
                # Buy: you pay X chaos to get 1 unit
                buy_chaos = round(1.0 / pay_val, 2) if pay_val > 0 else 0
                # Sell: you get X chaos per 1 unit
                sell_chaos = round(recv_val, 2) if recv_val > 0 else 0
                if buy_chaos <= 0 or sell_chaos <= 0:
                    continue
                spread = round((sell_chaos - buy_chaos) / buy_chaos * 100, 2)
                profit_per = round(sell_chaos - buy_chaos, 2)
                display_buy = f"{buy_chaos}c each"
                display_sell = f"{sell_chaos}c each"
            else:
                # Cheap currencies: show as X:1c ratio
                if buy_ratio <= 0 or sell_ratio <= 0:
                    continue
                # Profit = you buy X per chaos, sell them back and get more chaos
                # Buy X at buy_ratio per chaos → sell X at sell_ratio per chaos
                # Profit per chaos = (buy_ratio / sell_ratio) - 1
                if sell_ratio > 0:
                    profit_ratio = (buy_ratio / sell_ratio) - 1
                    spread = round(profit_ratio * 100, 2)
                    profit_per = round(profit_ratio, 4)
                else:
                    spread = 0
                    profit_per = 0
                display_buy = f"{buy_ratio}:1c"
                display_sell = f"{sell_ratio}:1c"

            # Flag unreliable spreads (poe.ninja averages can be stale)
            reliable = "yes" if abs(spread) < 30 else "check"
            volume = min(pay_listings, recv_listings)

            currencies.append({
                "name": name, "chaos_eq": chaos_eq,
                "buy_ratio": buy_ratio, "sell_ratio": sell_ratio,
                "display_buy": display_buy, "display_sell": display_sell,
                "spread": spread, "profit": profit_per,
                "buy_listings": pay_listings, "sell_listings": recv_listings,
                "volume": volume, "reliable": reliable,
                "is_expensive": is_expensive,
            })

        currencies.sort(key=lambda c: c["spread"], reverse=True)

        # Only flag as arbitrage if spread is realistic (2-20%) and reliable
        arb_opps = []
        for c in currencies:
            if c["spread"] > 2 and c["spread"] < 20 and c["reliable"] == "yes" and c["volume"] >= 5:
                if c["is_expensive"]:
                    desc = f"Buy at {c['display_buy']}, sell at {c['display_sell']}"
                    net = c["profit"]
                else:
                    desc = f"Buy at {c['display_buy']}, sell at {c['display_sell']} — profit {c['spread']:.1f}% per cycle"
                    net = round(c["spread"], 2)
                arb_opps.append({
                    "name": c["name"], "spread": c["spread"],
                    "desc": desc, "net_profit": net,
                    "volume": c["volume"], "reliable": c["reliable"],
                })
        arb_opps.sort(key=lambda x: x["spread"], reverse=True)

        return currencies, arb_opps
    except Exception as e:
        print(f"  !! Failed to fetch all currencies: {e}")
        return [], []


def fetch_mirror_price():
    """Fetch the mirror of kalandra price from poe.ninja currency data."""
    url = f"https://poe.ninja/api/data/currencyoverview?league={LEAGUE}&type=Currency"
    print("  Fetching mirror price...")
    req = urllib.request.Request(url, headers={"User-Agent": "poe-dashboard/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        for line in data.get("lines", []):
            if "mirror" in line.get("currencyTypeName", "").lower():
                return round(line.get("chaosEquivalent", 0), 1)
    except Exception as e:
        print(f"  !! Failed to fetch mirror price: {e}")
    return 0


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYSIS — all in chaos
# ═══════════════════════════════════════════════════════════════════════════════

def opportunity_score(item):
    chaos = item.get("chaosValue", 0) or 0
    listings = item.get("listingCount", 999) or 999
    if chaos < 50:
        return 0
    value_score = min(chaos / 10000, 1.0)
    scarcity_score = max(0, 1 - listings / 100)
    return round((value_score * 0.6 + scarcity_score * 0.4) * 100)


def get_tier(chaos, div_ratio):
    """Tier based on chaos price, using live div ratio."""
    d = div_ratio if div_ratio > 0 else 200
    if chaos < d:       return {"label": f"Under 1 div (<{round(d)}c)", "color": "#888888", "idx": 0}
    if chaos <= d * 3:  return {"label": f"1-3 div",   "color": "#5b9bd5", "idx": 1}
    if chaos <= d * 6:  return {"label": f"3-6 div",   "color": "#4CAF82", "idx": 2}
    if chaos <= d * 10: return {"label": f"6-10 div",  "color": "#d4a017", "idx": 3}
    if chaos <= d * 15: return {"label": f"11-15 div", "color": "#e08833", "idx": 4}
    return {"label": f"15+ div", "color": "#e05555", "idx": 5}


def calc_demand(item, builds):
    listings = item.get("listingCount", 0) or 0
    sparkline = item.get("sparkline", {}) or {}
    spark_data = sparkline.get("data", []) or []
    if listings == 0:     scarcity = 40
    elif listings <= 5:   scarcity = 35
    elif listings <= 15:  scarcity = 28
    elif listings <= 30:  scarcity = 20
    elif listings <= 100: scarcity = 10
    else:                 scarcity = 0
    trend = 0
    if len(spark_data) >= 3:
        avg = sum(spark_data[-3:]) / 3
        if avg > 10:   trend = 35
        elif avg > 5:  trend = 28
        elif avg > 2:  trend = 20
        elif avg > 0:  trend = 10
        elif avg > -2: trend = 5
    build_score = min(len(builds) * 8, 25)
    return min(scarcity + trend + build_score, 100)


def match_builds(name, item_type):
    name_lower = name.lower()
    matched = []
    cat_map = {"UniqueArmour": "armours", "UniqueWeapon": "weapons",
               "UniqueJewel": "jewels", "UniqueAccessory": "accessories",
               "UniqueFlask": "flasks", "SkillGem": "gems"}
    cat = cat_map.get(item_type)
    if not cat:
        return matched
    for build_data in META_BUILDS.values():
        for keyword in build_data.get(cat, []):
            if keyword in name_lower:
                matched.append(build_data["abbr"])
                break
    return matched


# Craft costs in chaos (will be set from live div ratio)
CRAFT_COSTS_CHAOS = {}


def init_craft_costs(div_ratio):
    d = div_ratio if div_ratio > 0 else 200
    CRAFT_COSTS_CHAOS.update({
        "6-link":           round(d * 1.5),   # ~1500 fusings average
        "6-link-tainted":   round(d * 0.3),   # tainted fusings on corrupted items — MUCH cheaper
        "corrupt":          round(d * 0.1),
        "double_corrupt":   round(d * 2),
        "harvest":          round(d * 1),
        "fracture":         round(d * 3),
        "essence":          round(d * 0.5),
    })


# ── Price lookup table (populated from raw API data before craft suggestions) ──
# Maps "base_name" -> list of {chaos, links, gem_level, gem_quality, variant, ...}
PRICE_LOOKUP = {}


def build_price_lookup(raw_items_by_type):
    """Build a lookup table from ALL raw poe.ninja data so craft suggestions
    can compare actual market prices instead of guessing multipliers."""
    PRICE_LOOKUP.clear()
    for item_type, items in raw_items_by_type.items():
        for item in items:
            name = item.get("name") or item.get("baseType") or ""
            if not name:
                continue
            entry = {
                "chaos": round(item.get("chaosValue") or 0),
                "listings": item.get("listingCount") or 0,
                "links": item.get("links") or 0,
                "gem_level": item.get("gemLevel") or 0,
                "gem_quality": item.get("gemQuality") or 0,
                "variant": item.get("variant") or "",
                "type": item_type,
                "corrupted": item.get("corrupted", False),
            }
            PRICE_LOOKUP.setdefault(name, []).append(entry)


def lookup_price(name, **filters):
    """Find the market price of a specific variant from real data.
    Returns (chaos_price, listings) or (None, 0) if not found."""
    entries = PRICE_LOOKUP.get(name, [])
    for e in entries:
        match = True
        for k, v in filters.items():
            if e.get(k) != v:
                match = False
                break
        if match:
            return e["chaos"], e["listings"]
    return None, 0


def get_craft_suggestions(name, item_type, chaos, links, listings, demand,
                          gem_level=0, gem_quality=0):
    suggestions = []
    is_equip = item_type in ("UniqueArmour", "UniqueWeapon")
    is_jewel = item_type == "UniqueJewel"
    is_accessory = item_type == "UniqueAccessory"
    is_gem = item_type == "SkillGem"
    corrupt_cost = CRAFT_COSTS_CHAOS.get("corrupt", 25)

    # ── 6-linking: use REAL 6L price from poe.ninja ──
    if is_equip and links < 6 and chaos >= 100:
        sixl_price, sixl_listings = lookup_price(name, links=6)
        if sixl_price and sixl_price > chaos:
            link_cost = CRAFT_COSTS_CHAOS["6-link"]
            profit = round(sixl_price - chaos - link_cost)
            if profit > 0:
                suggestions.append({"method": "6-link", "action": "6-link then sell",
                    "reason": f"6L sells for {sixl_price}c (real price, {sixl_listings} listed). "
                              f"Buy {links}L at {chaos}c + ~{link_cost}c linking cost",
                    "profit": profit,
                    "risk": "low" if profit > link_cost * 0.3 else "medium"})

    # ── Gem corrupt to 21: use REAL 21/20 price ──
    if is_gem and gem_level and int(gem_level) == 20:
        lv21_price, lv21_listings = lookup_price(name, gem_level=21,
                                                  gem_quality=gem_quality or 20)
        if not lv21_price:
            # Try without quality filter
            lv21_price, lv21_listings = lookup_price(name, gem_level=21)
        if lv21_price:
            # Vaal orb outcomes: 1/8 chance level+1, 1/8 level-1,
            # 1/4 add/change quality, 1/4 nothing, 1/8 brick to random gem
            # EV = 0.125 * lv21_price + 0.125 * (chaos*0.3) + 0.25 * (chaos*0.8)
            #    + 0.25 * chaos + 0.25 * 0 (brick)
            ev = (0.125 * lv21_price +      # +1 level
                  0.125 * chaos * 0.3 +      # -1 level (nearly worthless)
                  0.25 * chaos * 0.8 +       # quality change (slight loss)
                  0.25 * chaos +             # nothing happens
                  0.25 * 0)                  # brick to random gem
            profit = round(ev - chaos - corrupt_cost)
            if profit > 0:
                suggestions.append({"method": "corrupt", "action": f"Vaal Orb for 21/{gem_quality or 20}",
                    "reason": f"21/{gem_quality or 20} sells for {lv21_price}c ({lv21_listings} listed). "
                              f"12.5% chance. EV per attempt: {round(ev)}c",
                    "profit": profit, "risk": "medium"})
            elif lv21_price > chaos:
                # Still show it but mark as negative EV
                suggestions.append({"method": "corrupt", "action": f"Vaal Orb for 21/{gem_quality or 20}",
                    "reason": f"21/{gem_quality or 20} = {lv21_price}c but EV is negative. "
                              f"Only {round((lv21_price/chaos - 1)*100)}% premium vs 12.5% hit rate. Skip unless gambling",
                    "profit": 0, "risk": "high"})
        elif chaos >= 200:
            # No 21 data at all — warn user
            suggestions.append({"method": "corrupt", "action": "Vaal Orb (no 21 data)",
                "reason": "No 21/20 price data on poe.ninja — cannot calculate profit. Check trade site manually",
                "profit": 0, "risk": "high"})

    # ── Double corrupt: conservative estimate ──
    if is_equip and chaos >= 300:
        dc_cost = CRAFT_COSTS_CHAOS["double_corrupt"]
        # 25% two good implicits, 25% one good, 25% bad, 25% brick
        # Very hard to price without actual data — use conservative 15% chance of 2x
        ev = chaos * (0.15 * 2.0 + 0.25 * 1.0 + 0.35 * 0.5 + 0.25 * 0)
        profit = round(ev - chaos - dc_cost)
        if profit > 0:
            suggestions.append({"method": "double_corrupt",
                "action": "Double corrupt unique",
                "reason": f"~15% chance of 2x+ value. Cost: {chaos}c item + {dc_cost}c temple. "
                          "High variance — only do if you can absorb total loss",
                "profit": profit, "risk": "high"})

    # ── Corrupt jewels/accessories: ~25% chance of good implicit ──
    if (is_accessory or is_jewel) and chaos >= 100:
        # Conservative: 25% chance of 30% value increase
        ev = chaos * 0.25 * 1.3
        profit = round(ev - corrupt_cost)
        if profit > 0:
            suggestions.append({"method": "corrupt", "action": "Corrupt for implicit",
                "reason": f"~25% chance of good implicit. Cost: {corrupt_cost}c. "
                          "Good implicits can add 30%+ value",
                "profit": profit, "risk": "low"})

    # ── Single corrupt on equip ──
    if is_equip and chaos >= 100 and chaos < 1000:
        ev = chaos * 0.25 * 1.3
        profit = round(ev - corrupt_cost)
        if profit > 0:
            suggestions.append({"method": "corrupt", "action": "Single corrupt",
                "reason": f"~25% chance of good implicit. {corrupt_cost}c cost",
                "profit": profit, "risk": "low"})

    # ── Harvest reforge ──
    if is_equip and chaos >= 500:
        harvest_cost = CRAFT_COSTS_CHAOS["harvest"]
        profit = round(chaos * 0.2 - harvest_cost)
        if profit > 0:
            suggestions.append({"method": "harvest", "action": "Harvest reforge",
                "reason": f"Targeted reforge. ~20% avg value add, {harvest_cost}c cost",
                "profit": profit, "risk": "medium"})

    # ── Fracture (base types) ──
    if item_type == "BaseType" and chaos >= 500:
        frac_cost = CRAFT_COSTS_CHAOS["fracture"]
        ev = chaos * 0.3 * 1.5
        profit = round(ev - frac_cost)
        if profit > 0:
            suggestions.append({"method": "fracture", "action": "Fracture + craft",
                "reason": f"~30% chance to lock good mod. Cost: {frac_cost}c",
                "profit": profit, "risk": "high"})

    # ── Essence craft (base types) ──
    if item_type == "BaseType" and chaos >= 100:
        ess_cost = CRAFT_COSTS_CHAOS["essence"]
        profit = round(chaos * 0.2 - ess_cost)
        if profit > 0:
            suggestions.append({"method": "essence", "action": "Essence spam",
                "reason": f"Guaranteed mod. ~5 attempts avg ({ess_cost}c each) for sellable result",
                "profit": profit, "risk": "low"})

    # ── Low listings context ──
    if listings <= 5 and chaos >= 100:
        for s in suggestions:
            if s["profit"] > 0:
                s["reason"] = "Low supply — price may spike. " + s["reason"]
    elif listings <= 20 and chaos >= 300:
        for s in suggestions:
            s["reason"] = "Scarce — price holds. " + s["reason"]

    suggestions.sort(key=lambda c: c["profit"], reverse=True)
    return suggestions


# ═══════════════════════════════════════════════════════════════════════════════
# ROW BUILDING
# ═══════════════════════════════════════════════════════════════════════════════

def price_confidence(listings, spark_data):
    """Rate price confidence 0-100 based on listing count and data quality."""
    if listings <= 1:
        return 10
    elif listings <= 3:
        return 25
    elif listings <= 5:
        return 40
    elif listings <= 10:
        return 55
    elif listings <= 20:
        return 70
    elif listings <= 50:
        return 85
    else:
        conf = 95
    # Penalize if sparkline has gaps (stale data)
    if spark_data:
        zeroes = sum(1 for v in spark_data if v == 0 or v is None)
        if zeroes > len(spark_data) * 0.5:
            conf = max(conf - 20, 10)
    return conf


def build_rows(raw_items, item_type, div_ratio):
    rows = []
    for item in raw_items:
        name = item.get("name") or item.get("baseType") or ""
        variant = item.get("variant") or ""
        details_id = item.get("detailsId") or ""
        chaos = round(item.get("chaosValue") or 0)
        listings = item.get("listingCount") or 0
        links = item.get("links") or 0
        gem_level = item.get("gemLevel") or ""
        gem_quality = item.get("gemQuality") or ""
        level_req = item.get("levelRequired") or ""
        score = opportunity_score(item)
        tier = get_tier(chaos, div_ratio)
        builds = match_builds(name, item_type)
        demand = calc_demand(item, builds)
        crafts = get_craft_suggestions(name, item_type, chaos, links, listings, demand,
                                       gem_level=gem_level, gem_quality=gem_quality)
        best = crafts[0] if crafts else None
        sparkline = item.get("sparkline", {}) or {}
        spark_data = sparkline.get("data", []) or []
        conf = price_confidence(listings, spark_data)

        rows.append({
            "name": name, "variant": variant, "details_id": details_id,
            "chaos": chaos, "listings": listings,
            "links": links, "gem_level": gem_level, "gem_quality": gem_quality,
            "level_req": level_req, "score": score, "type": item_type,
            "tier_label": tier["label"], "tier_color": tier["color"],
            "tier_idx": tier["idx"], "builds": builds, "demand": demand,
            "confidence": conf,
            "craft_method": best["method"] if best else "",
            "craft_action": best["action"] if best else "",
            "craft_reason": best["reason"] if best else "",
            "craft_profit": best["profit"] if best else 0,
            "top3": crafts[:3],
            "spark": spark_data[-7:] if spark_data else [],
            "trade_cat": TRADE_CATEGORIES.get(item_type, ""),
        })
    return rows


def compute_underpriced(all_rows):
    groups = {}
    for r in all_rows:
        groups.setdefault(f"{r['type']}_{r['tier_idx']}", []).append(r)
    for items in groups.values():
        prices = [r["chaos"] for r in items if r["chaos"] > 0]
        if len(prices) < 3:
            for r in items: r["underpriced"] = 0
            continue
        median = statistics.median(prices)
        q1 = statistics.median([p for p in prices if p <= median]) if len(prices) >= 4 else median * 0.5
        for r in items:
            if r["chaos"] > 0 and r["chaos"] <= q1 and median > 0:
                r["underpriced"] = max(round((1 - r["chaos"] / median) * 100), 0)
            else:
                r["underpriced"] = 0


# ═══════════════════════════════════════════════════════════════════════════════
# FLIP FINDER
# ═══════════════════════════════════════════════════════════════════════════════

def find_flips(all_rows):
    flips = []
    by_name = {}
    for r in all_rows:
        by_name.setdefault(r["name"], []).append(r)

    for name, variants in by_name.items():
        if len(variants) < 2:
            continue
        vs = sorted(variants, key=lambda v: v["chaos"])

        # Link Arbitrage
        unlinked = [v for v in vs if v["links"] < 6 and v["type"] in ("UniqueArmour", "UniqueWeapon") and v["chaos"] > 10]
        linked = [v for v in vs if v["links"] >= 6 and v["type"] in ("UniqueArmour", "UniqueWeapon") and v["chaos"] > 10]
        if unlinked and linked:
            buy, sell = unlinked[0], linked[-1]
            cost = CRAFT_COSTS_CHAOS.get("6-link", 300)
            spread = sell["chaos"] - buy["chaos"] - cost
            if spread > 50 and sell["chaos"] > buy["chaos"] * 1.3:
                flips.append({
                    "name": name, "flip_type": "6-Link Spread",
                    "buy_price": buy["chaos"], "sell_price": sell["chaos"],
                    "buy_variant": f"{buy['links'] or 0}L", "sell_variant": "6L",
                    "cost": cost, "profit": spread,
                    "buy_listings": buy["listings"], "sell_listings": sell["listings"],
                    "demand": max(buy.get("demand", 0), sell.get("demand", 0)),
                    "builds": buy.get("builds", []) or sell.get("builds", []),
                    "type": buy["type"], "trade_cat": buy.get("trade_cat", ""),
                    "reason": f"Buy {buy['links'] or 0}L at {buy['chaos']}c -> 6-link (~{cost}c) -> sell 6L at {sell['chaos']}c",
                    "risk": "low" if spread > 200 else "medium",
                })

        # Gem Level Gap
        gems = [v for v in vs if v["type"] == "SkillGem" and v["chaos"] > 10]
        if len(gems) >= 2:
            lo, hi = gems[0], gems[-1]
            spread = hi["chaos"] - lo["chaos"] - CRAFT_COSTS_CHAOS.get("corrupt", 25)
            if spread > 50 and hi["chaos"] > lo["chaos"] * 1.5:
                buy_d = f"Lv{lo['gem_level']}" if lo["gem_level"] else "low"
                sell_d = f"Lv{hi['gem_level']}" if hi["gem_level"] else "high"
                if lo.get("gem_quality") != hi.get("gem_quality"):
                    buy_d += f"/{lo['gem_quality'] or 0}%"; sell_d += f"/{hi['gem_quality'] or 0}%"
                flips.append({
                    "name": name, "flip_type": "Gem Level Gap",
                    "buy_price": lo["chaos"], "sell_price": hi["chaos"],
                    "buy_variant": buy_d, "sell_variant": sell_d,
                    "cost": CRAFT_COSTS_CHAOS.get("corrupt", 25), "profit": spread,
                    "buy_listings": lo["listings"], "sell_listings": hi["listings"],
                    "demand": max(lo.get("demand", 0), hi.get("demand", 0)),
                    "builds": lo.get("builds", []) or hi.get("builds", []),
                    "type": "SkillGem", "trade_cat": lo.get("trade_cat", ""),
                    "reason": f"Buy {buy_d} at {lo['chaos']}c -> level/corrupt -> sell {sell_d} at {hi['chaos']}c",
                    "risk": "medium",
                })

        # Price Gap (same base, big variance)
        non_gem = [v for v in vs if v["type"] != "SkillGem" and v["chaos"] > 50]
        if len(non_gem) >= 2:
            lo, hi = non_gem[0], non_gem[-1]
            spread = hi["chaos"] - lo["chaos"]
            if spread > 100 and hi["chaos"] > lo["chaos"] * 2:
                flips.append({
                    "name": name, "flip_type": "Price Gap",
                    "buy_price": lo["chaos"], "sell_price": hi["chaos"],
                    "buy_variant": f"{lo['links']}L" if lo.get("links") else "base",
                    "sell_variant": f"{hi['links']}L" if hi.get("links") else "premium",
                    "cost": 0, "profit": spread,
                    "buy_listings": lo["listings"], "sell_listings": hi["listings"],
                    "demand": max(lo.get("demand", 0), hi.get("demand", 0)),
                    "builds": lo.get("builds", []) or hi.get("builds", []),
                    "type": lo["type"], "trade_cat": lo.get("trade_cat", ""),
                    "reason": f"Buy low variant at {lo['chaos']}c -> sell premium at {hi['chaos']}c (check rolls)",
                    "risk": "medium",
                })

    # Dedupe, sort, cap insane profits
    seen = set()
    result = []
    for f in sorted(flips, key=lambda x: x["profit"], reverse=True):
        key = f"{f['name']}_{f['flip_type']}"
        if key in seen:
            continue
        # Cap profit at 5x buy price to remove buggy entries
        if f["buy_price"] > 0 and f["profit"] > f["buy_price"] * 5:
            f["profit"] = round(f["buy_price"] * 5)
        # Skip entries with insanely high or clearly broken profits
        if f["profit"] > 50000:
            continue
        seen.add(key)
        result.append(f)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# ALERTS
# ═══════════════════════════════════════════════════════════════════════════════

def load_previous_data():
    """Load the most recent snapshot from the history directory."""
    # Try history directory first
    if os.path.isdir(HISTORY_DIR):
        snaps = sorted(globmod.glob(os.path.join(HISTORY_DIR, "snap_*.json")))
        if snaps:
            try:
                with open(snaps[-1], "r", encoding="utf-8") as f:
                    return json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                pass
    # Fallback to legacy file
    try:
        with open(PREV_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_history_snapshot(all_rows):
    """Save a timestamped snapshot to poe_dashboard_history/ and keep last 20."""
    os.makedirs(HISTORY_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    lookup = {}
    for r in all_rows:
        key = f"{r['name']}|{r['type']}|{r['links']}"
        lookup[key] = {"chaos": r["chaos"], "listings": r["listings"]}
    snap = {"timestamp": datetime.now().isoformat(), "items": lookup}
    path = os.path.join(HISTORY_DIR, f"snap_{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snap, f)
    # Cleanup: keep only last HISTORY_MAX snapshots
    snaps = sorted(globmod.glob(os.path.join(HISTORY_DIR, "snap_*.json")))
    while len(snaps) > HISTORY_MAX:
        os.remove(snaps.pop(0))
    return path


def get_history_list():
    """Return list of {timestamp, item_count} for all snapshots."""
    history = []
    if not os.path.isdir(HISTORY_DIR):
        return history
    snaps = sorted(globmod.glob(os.path.join(HISTORY_DIR, "snap_*.json")))
    for s in snaps:
        try:
            with open(s, "r", encoding="utf-8") as f:
                data = json.load(f)
            history.append({
                "timestamp": data.get("timestamp", "unknown"),
                "item_count": len(data.get("items", {})),
            })
        except (json.JSONDecodeError, OSError):
            pass
    return history


def save_current_data(all_rows):
    """Save to both history directory (timestamped) and legacy file."""
    save_history_snapshot(all_rows)
    # Also save legacy file for backward compat
    lookup = {}
    for r in all_rows:
        key = f"{r['name']}|{r['type']}|{r['links']}"
        lookup[key] = {"chaos": r["chaos"], "listings": r["listings"]}
    with open(PREV_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"timestamp": datetime.now().isoformat(), "items": lookup}, f)


def compute_alerts(all_rows, prev_data):
    if not prev_data or "items" not in prev_data:
        for r in all_rows:
            r["alert"] = ""; r["price_change"] = 0; r["listings_change"] = 0
        return 0
    prev_items = prev_data["items"]
    alert_count = 0
    for r in all_rows:
        key = f"{r['name']}|{r['type']}|{r['links']}"
        if r["chaos"] < 50:
            r["alert"] = ""; r["price_change"] = 0; r["listings_change"] = 0
            continue
        prev = prev_items.get(key)
        if not prev:
            if r["chaos"] >= 200:
                r["alert"] = "new"; alert_count += 1
            else:
                r["alert"] = ""
            r["price_change"] = 0; r["listings_change"] = 0
            continue
        old_c = prev.get("chaos", 0)
        old_l = prev.get("listings", 0)
        pct = round(((r["chaos"] - old_c) / old_c) * 100, 1) if old_c > 0 else (100 if r["chaos"] > 0 else 0)
        lc = r["listings"] - old_l
        r["price_change"] = pct; r["listings_change"] = lc

        # Underpriced alert: only when price DROPPED into underpriced territory
        # (>30% below median AND high demand AND price actually fell)
        if r.get("underpriced", 0) > 30 and r.get("demand", 0) > 50 and pct < -5:
            r["alert"] = "underpriced"; alert_count += 1
        # Meta spike: used by a meta build AND price spiked >15%
        elif len(r.get("builds", [])) > 0 and pct > 15:
            r["alert"] = "meta_spike"; alert_count += 1
        # Corner risk: had >10 listings last run, now <=3
        elif old_l > 10 and r["listings"] <= 3:
            r["alert"] = "corner_risk"; alert_count += 1
        elif abs(pct) < 5:
            r["alert"] = ""
        elif pct >= 25:
            r["alert"] = "spike"; alert_count += 1
        elif pct <= -25:
            r["alert"] = "crash"; alert_count += 1
        elif lc < -15 and old_l > 20:
            r["alert"] = "drying"; alert_count += 1
        elif lc > 50:
            r["alert"] = "flood"; alert_count += 1
        else:
            r["alert"] = ""
    return alert_count


# ═══════════════════════════════════════════════════════════════════════════════
# WHALE MODE — supply cornering + advanced strategies
# ═══════════════════════════════════════════════════════════════════════════════

# All advanced money-making strategies with tags
WHALE_STRATEGIES = [
    {"id": "corner", "name": "Supply Cornering", "desc": "Buy all listings of low-supply valuable items to control price", "tag": "flipping"},
    {"id": "6link_flip", "name": "6-Link Flipping", "desc": "Buy cheap unlinked → 6-link → sell at premium", "tag": "flipping"},
    {"id": "gem_level", "name": "Awakened Gem Leveling", "desc": "Buy lv4 awakened gems → level to 5 → sell (huge markup)", "tag": "leveling"},
    {"id": "double_corrupt", "name": "Double Corrupt Uniques", "desc": "Glimpse of Chaos on valuable uniques for dual implicits", "tag": "corruption"},
    {"id": "vaal_corrupt", "name": "Vaal Corruption", "desc": "Corrupt for +1 gems, 50% dmg, etc on good bases", "tag": "corruption"},
    {"id": "tainted_mythic", "name": "Tainted Mythic Orbs on 6L", "desc": "Use on corrupted 6-links — can hit chase uniques", "tag": "corruption"},
    {"id": "tainted_chaos_jewels", "name": "Tainted Chaos on Jewels", "desc": "Buy strong implicit jewels, tainted chaos until GG. If goes normal → mythic orb", "tag": "corruption"},
    {"id": "fracture_cluster", "name": "Fracture Cluster Jewels", "desc": "Fracture 35% inc effect on mana reservation clusters (i84 3-passive)", "tag": "crafting"},
    {"id": "harvest_fracture", "name": "Harvest Fracture", "desc": "Fracture good mods then reroll — very high value", "tag": "crafting"},
    {"id": "harvest_exalt_jewels", "name": "Harvest Exalt Jewels", "desc": "Exalt fractured jewels (e.g. 7% max life) — target suffixes", "tag": "crafting"},
    {"id": "det_craft_amulet", "name": "Craft +2 Amulets", "desc": "Deterministic +2 all gems + t1 life amulets", "tag": "crafting"},
    {"id": "temple_gloves", "name": "Temple Glove Resistance Swap", "desc": "Change fire/lightning to cold on good base — 1-2 div profit per craft (500 lifeforce)", "tag": "crafting"},
    {"id": "essence_craft", "name": "Essence Crafting", "desc": "Spam essences on high-demand bases for guaranteed good mods", "tag": "crafting"},
    {"id": "influence_swap", "name": "Influence Type Swap", "desc": "Change influence on desired ring bases for profit", "tag": "crafting"},
    {"id": "div_card_sets", "name": "Divination Card Flipping", "desc": "Buy div card sets below completion value, turn in for profit", "tag": "flipping"},
    {"id": "low_level_turnin", "name": "Low-Level Div Card Turn-in", "desc": "Use lv1 character to turn in unique div cards → blocks bad corruptions, enables +1 gems etc", "tag": "advanced"},
    {"id": "mirror_craft", "name": "Mirror Crafting", "desc": "Mirror-service wand/shield — endgame wealth", "tag": "endgame"},
    {"id": "mirrored_ring_bulk", "name": "Mirrored Ring Bulk Buy", "desc": "Buy mirrored dusk rings ilvl 82+ and sell 5:1 ratio", "tag": "flipping"},
    {"id": "currency_arb", "name": "Currency Arbitrage", "desc": "Exploit exchange rate gaps between whetstones, baubles, flask crafts etc", "tag": "flipping"},
]


def find_whale_targets(all_rows, div_ratio):
    """Find items suitable for supply cornering and strategy application."""
    targets = []
    d = div_ratio if div_ratio > 0 else 200

    # Valuable corruption outcomes by item slot
    CORRUPT_OUTCOMES = {
        "UniqueArmour": {
            "body": ["+1 to Level of Socketed Gems", "+2 Socketed Duration/AoE Gems", "Additional Curse", "+50% increased Damage"],
            "helmet": ["+2 to Socketed AoE/Minion Gems", "+2 to Socketed Aura Gems", "Nearby enemies take 9% inc Ele Dmg"],
            "gloves": ["Vulnerability on Hit", "Elemental Weakness on Hit", "+1 Frenzy Charge", "+1 Power Charge"],
            "boots": ["+1 to Socketed Gems", "Cannot be Frozen", "+2% base Crit Chance"],
            "shield": ["+1 to Socketed Gems", "+5% Block/Spell Block", "Additional Curse"],
            "generic": ["+1 to Level of Socketed Gems", "+50% increased Damage", "% max Life/ES"],
        },
        "UniqueWeapon": {
            "generic": ["+2 to Level of Socketed Gems", "Hits can't be Evaded", "Culling Strike", "+% to Critical Strike Multiplier"],
        },
        "UniqueJewel": {
            "generic": ["Corrupted Blood immunity", "2% reduced Mana Reserved", "+1% max All Resistances", "Hinder/Maim on Hit"],
        },
        "UniqueAccessory": {
            "amulet": ["+1 to Level of All Skill Gems", "+1 All Str/Dex/Int Gems", "% additional Phys Dmg Reduction"],
            "ring": ["Vulnerability on Hit", "Assassin's Mark on Hit", "Poacher's Mark on Hit"],
            "belt": ["% increased max Energy Shield", "% increased max Life"],
            "generic": ["+1 to Level of All Skill Gems", "Curse on Hit"],
        },
    }

    def get_corrupt_info(item_type, name):
        """Get specific valuable corruption outcomes for this item type."""
        name_l = name.lower()
        slot_map = CORRUPT_OUTCOMES.get(item_type, {})
        # Try to guess slot from name keywords
        if item_type == "UniqueArmour":
            if any(w in name_l for w in ["plate", "vest", "robe", "coat", "jack", "regalia", "ire", "fur", "heart", "vision"]):
                return slot_map.get("body", slot_map.get("generic", []))
            elif any(w in name_l for w in ["crown", "helm", "mask", "hood", "head", "halo", "cage", "burgonet"]):
                return slot_map.get("helmet", slot_map.get("generic", []))
            elif any(w in name_l for w in ["gauntlet", "glove", "mitt", "hand"]):
                return slot_map.get("gloves", slot_map.get("generic", []))
            elif any(w in name_l for w in ["boot", "shoe", "step", "greave", "slink", "track"]):
                return slot_map.get("boots", slot_map.get("generic", []))
            elif any(w in name_l for w in ["shield", "buckler", "kite", "tower", "aegis", "frame", "phoenix"]):
                return slot_map.get("shield", slot_map.get("generic", []))
        elif item_type == "UniqueAccessory":
            if any(w in name_l for w in ["amulet", "talisman", "choker", "pendant", "foible", "presence", "impresence", "uprising"]):
                return slot_map.get("amulet", slot_map.get("generic", []))
            elif any(w in name_l for w in ["ring", "circle", "mark", "pyre", "coil"]):
                return slot_map.get("ring", slot_map.get("generic", []))
            elif any(w in name_l for w in ["belt", "sash", "stygian", "chain", "clasp"]):
                return slot_map.get("belt", slot_map.get("generic", []))
        return slot_map.get("generic", ["Good implicits possible"])

    def build_reason(r):
        """Build a 'why this item' explanation."""
        parts = []
        if r.get("builds"):
            parts.append(f"Used by {', '.join(r['builds'])}")
        if r["listings"] <= 3:
            parts.append(f"Only {r['listings']} listed — extremely scarce")
        elif r["listings"] <= 10:
            parts.append(f"Low supply ({r['listings']} listed)")
        if r["demand"] >= 60:
            parts.append("High demand (60+)")
        elif r["demand"] >= 30:
            parts.append("Moderate demand")
        if r.get("underpriced", 0) > 0:
            parts.append(f"{r['underpriced']}% below median price")
        return ". ".join(parts) if parts else ""

    for r in all_rows:
        if r["chaos"] < 50:
            continue

        strategies = []
        corner_score = 0
        item_reason = build_reason(r)
        has_meta = len(r.get("builds", [])) > 0

        # ── Supply Cornering ──
        if r["listings"] <= 10 and r["chaos"] >= d:
            cost_to_corner = r["chaos"] * r["listings"]
            demand_pct = 0.2 + (r["demand"] / 200)
            if has_meta:
                demand_pct += 0.15
            projected_price = round(r["chaos"] * (1 + demand_pct))
            projected_profit = round((projected_price - r["chaos"]) * r["listings"])
            if projected_profit > 0 and cost_to_corner < 50000:
                demand_pts = min(round(r["demand"] * 0.4), 40)
                meta_pts = min(len(r.get("builds", [])) * 10, 30)
                scarcity_pts = max(0, round((10 - r["listings"]) * 3))
                corner_score = min(demand_pts + meta_pts + scarcity_pts, 100)
                why = f"Buy all {r['listings']} at {r['chaos']}c = {cost_to_corner}c total"
                why += f". Relist at ~{projected_price}c (+{round(demand_pct*100)}%)"
                if has_meta:
                    why += f". Builds ({', '.join(r['builds'])}) guarantee buyers"
                if r["listings"] <= 3:
                    why += ". Almost no supply — easy to control"
                strategies.append({"id": "corner", "profit": projected_profit,
                    "detail": why, "cost": cost_to_corner})

        # ── 6-Link Flipping ──
        if r["type"] in ("UniqueArmour", "UniqueWeapon") and r["links"] < 6 and r["chaos"] >= 100:
            link_cost = CRAFT_COSTS_CHAOS.get("6-link", 370)
            tainted_cost = CRAFT_COSTS_CHAOS.get("6-link-tainted", 75)
            sell_est = round(r["chaos"] * 1.4)
            # Normal fusings path
            profit_normal = sell_est - r["chaos"] - link_cost
            # Tainted fusings path (corrupt first, then tainted fuse — much cheaper)
            profit_tainted = sell_est - r["chaos"] - tainted_cost
            if profit_normal > 50 or profit_tainted > 50:
                detail = f"Buy {r['links'] or 0}L at {r['chaos']}c"
                detail += f". Option A: Regular fusings (~{link_cost}c, profit {profit_normal}c)"
                detail += f". Option B: Corrupt first → tainted fusings (~{tainted_cost}c, profit {profit_tainted}c — much cheaper but item is corrupted)"
                detail += f". Sell 6L for ~{sell_est}c"
                if has_meta:
                    detail += f". Needed by {', '.join(r['builds'])}"
                best_profit = max(profit_normal, profit_tainted)
                best_cost = r["chaos"] + (link_cost if profit_normal >= profit_tainted else tainted_cost)
                strategies.append({"id": "6link_flip", "profit": best_profit,
                    "detail": detail, "cost": best_cost})

        # ── Awakened Gem Leveling ──
        if r["type"] == "SkillGem" and "awakened" in r["name"].lower():
            if r.get("gem_level") and str(r["gem_level"]) in ("4", "3"):
                lv = int(r["gem_level"])
                profit = round(r["chaos"] * 1.5)
                detail = f"Buy lv{lv} at {r['chaos']}c. Level to {lv+1} in your offhand while mapping"
                detail += f". Lv{lv+1} sells for ~{r['chaos']+profit}c. Takes ~2-5 days of casual play"
                if has_meta:
                    detail += f". Needed by {', '.join(r['builds'])}"
                strategies.append({"id": "gem_level", "profit": profit,
                    "detail": detail, "cost": r["chaos"]})

        # ── Double Corrupt (Glimpse of Chaos) ──
        if r["type"] in ("UniqueArmour", "UniqueWeapon") and r["chaos"] >= d * 2:
            dc_cost = CRAFT_COSTS_CHAOS.get("double_corrupt", 500)
            outcomes = get_corrupt_info(r["type"], r["name"])
            # Conservative EV: 15% GG (2x), 25% decent (1x), 35% bad (0.5x), 25% brick (0)
            ev = r["chaos"] * (0.15 * 2.0 + 0.25 * 1.0 + 0.35 * 0.5 + 0.25 * 0)
            profit = round(ev - dc_cost)
            if profit > 50:
                detail = f"Use Glimpse of Chaos on {r['name']} ({r['chaos']}c + {dc_cost}c altar cost)"
                detail += f". Target implicits: {', '.join(outcomes[:3])}"
                detail += f". ~25% chance of bricking (poof), ~15% chance of GG double implicit"
                strategies.append({"id": "double_corrupt", "profit": profit,
                    "detail": detail, "cost": r["chaos"] + dc_cost})

        # ── Vaal Corruption ──
        if r["type"] in ("UniqueArmour", "UniqueWeapon", "UniqueAccessory") and r["chaos"] >= 100 and r["chaos"] < d * 5:
            outcomes = get_corrupt_info(r["type"], r["name"])
            corrupt_cost = CRAFT_COSTS_CHAOS.get("corrupt", 25)
            # EV: 25% good implicit (1.5x), 25% nothing (1x), 25% white sockets (1x), 25% brick (0.3x)
            ev = r["chaos"] * (0.25 * 1.5 + 0.25 * 1.0 + 0.25 * 1.0 + 0.25 * 0.3)
            profit = round(ev - r["chaos"] - corrupt_cost)
            if profit > 30:
                detail = f"Vaal Orb on {r['name']} ({r['chaos']}c). Valuable outcomes: {', '.join(outcomes[:3])}"
                detail += f". ~25% chance of good implicit. Good hit = {round(r['chaos']*1.5)}-{round(r['chaos']*2)}c"
                detail += ". 25% nothing, 25% reroll (brick), 25% white sockets"
                strategies.append({"id": "vaal_corrupt", "profit": profit,
                    "detail": detail, "cost": r["chaos"] + corrupt_cost})

        # ── Tainted Chaos on Jewels ──
        if r["type"] == "UniqueJewel" and r["chaos"] >= 50:
            outcomes = get_corrupt_info(r["type"], r["name"])
            profit = round(r["chaos"] * 1.2)
            detail = f"Buy {r['name']} with good implicit ({', '.join(outcomes[:2])})"
            detail += f". Use Tainted Chaos Orbs to reroll mods while keeping implicit"
            detail += ". If it goes normal (uncorrupted), use Tainted Mythic Orb — jewels have tons of uniques so you'll hit something"
            strategies.append({"id": "tainted_chaos_jewels", "profit": profit,
                "detail": detail, "cost": r["chaos"] + 50})

        # ── Harvest Fracture ──
        if r["type"] == "BaseType" and r["chaos"] >= d * 2:
            frac_cost = CRAFT_COSTS_CHAOS.get("fracture", 750)
            profit = round(r["chaos"] * 0.8)
            if profit > 100:
                detail = f"Fracture a T1 mod on {r['name']} ({frac_cost}c for fracture)"
                detail += ". Fractured mod is locked forever — reroll rest with essences/harvest"
                detail += ". Sells at premium because crafters can deterministically finish the item"
                strategies.append({"id": "harvest_fracture", "profit": profit,
                    "detail": detail, "cost": r["chaos"] + frac_cost})

        # ── Essence Crafting ──
        if r["type"] == "BaseType" and r["chaos"] >= 100:
            ess_cost = CRAFT_COSTS_CHAOS.get("essence", 125)
            profit = round(r["chaos"] * 0.5)
            if profit > 30:
                detail = f"Use Deafening Essences on {r['name']} (~{ess_cost}c per attempt)"
                detail += ". Guarantees one good mod, need ~5 attempts avg for sellable result"
                detail += ". Best on bases meta builds need (check build badges)"
                strategies.append({"id": "essence_craft", "profit": profit,
                    "detail": detail, "cost": r["chaos"] + ess_cost})

        if not strategies:
            continue

        best = max(strategies, key=lambda s: s["profit"])
        targets.append({
            "name": r["name"], "variant": r.get("variant", ""),
            "type": r["type"], "chaos": r["chaos"],
            "listings": r["listings"], "demand": r["demand"],
            "confidence": r.get("confidence", 95),
            "builds": r["builds"], "trade_cat": r.get("trade_cat", ""),
            "tier_label": r["tier_label"], "tier_color": r["tier_color"],
            "corner_score": corner_score,
            "strategies": strategies,
            "best_strategy": best["id"],
            "best_profit": best["profit"],
            "best_detail": best["detail"],
            "best_cost": best["cost"],
            "item_reason": item_reason,
        })

    targets = [t for t in targets if t["best_profit"] < 100000]
    targets.sort(key=lambda t: (
        t["corner_score"] * 2 +
        len(t["builds"]) * 20 +
        t["demand"] +
        min(t["best_profit"] / 10, 50)
    ), reverse=True)
    return targets


# ═══════════════════════════════════════════════════════════════════════════════
# HTML
# ═══════════════════════════════════════════════════════════════════════════════

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PoE Mirage Economy v5</title>
<style>
:root{--bg:#0f0f10;--surface:#1a1a1e;--surface2:#222228;--border:#2e2e38;--text:#e8e8e8;--muted:#888;--accent:#c89b3c;--green:#4CAF82;--red:#e05555;--yellow:#d4a017;--blue:#5b9bd5;--orange:#e08833;--purple:#aa55e0}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;font-size:14px}
.page-wrapper{max-width:1400px;margin:0 auto;padding:0 2rem}
header{padding:1.25rem 0;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px}
header h1{font-size:18px;font-weight:600;color:var(--accent);display:inline}
header .meta{font-size:12px;color:var(--muted)}
.ratio-badge{display:inline-block;background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:4px 10px;font-size:12px;color:var(--accent);font-weight:600;margin-left:8px}
.header-left{display:flex;align-items:center;gap:12px;flex-wrap:wrap}

/* Simple/Pro toggle */
.pro-toggle{display:flex;background:var(--surface2);border:1px solid var(--border);border-radius:20px;overflow:hidden;height:32px}
.pro-toggle-btn{padding:0 16px;font-size:12px;font-weight:600;cursor:pointer;border:none;background:transparent;color:var(--muted);transition:all .2s;line-height:30px;white-space:nowrap}
.pro-toggle-btn.active{background:var(--accent);color:var(--bg);border-radius:20px}

.mode-tabs{display:flex;gap:0;padding:0;border-bottom:2px solid var(--border);flex-wrap:wrap}
.mode-tab{padding:10px 14px;cursor:pointer;font-size:13px;font-weight:600;color:var(--muted);border-bottom:2px solid transparent;margin-bottom:-2px;transition:all .15s;white-space:nowrap;position:relative}
.mode-tab:hover{color:var(--text)}.mode-tab.active{color:var(--accent);border-bottom-color:var(--accent)}
.mode-tab.active::after{content:'';position:absolute;bottom:-2px;left:20%;right:20%;height:2px;background:var(--accent);filter:blur(4px);opacity:0.6}
.mode-tab .alert-dot{display:inline-block;width:7px;height:7px;background:var(--red);border-radius:50%;margin-left:4px;vertical-align:middle}
.tabs{display:flex;gap:4px;padding:1rem 0 0;flex-wrap:wrap}
.tab{padding:6px 14px;border-radius:6px 6px 0 0;border:1px solid var(--border);border-bottom:none;background:var(--surface2);color:var(--muted);cursor:pointer;font-size:13px;transition:all .15s}
.tab:hover{color:var(--text)}.tab.active{background:var(--surface);color:var(--accent)}
.main{padding:0 0 1.5rem}
.controls{display:flex;flex-wrap:wrap;gap:12px;align-items:center;padding:1rem 0;border-bottom:1px solid var(--border);margin-bottom:1rem}
.control-group{display:flex;align-items:center;gap:6px}
.control-group label{font-size:12px;color:var(--muted);white-space:nowrap}
input[type=number],input[type=text],select{background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:5px 10px;border-radius:6px;font-size:13px;outline:none}
input[type=number]{width:90px}input[type=text]{width:150px}select{min-width:120px;cursor:pointer}
input:focus,select:focus{border-color:var(--accent)}
label.checkbox{display:flex;align-items:center;gap:6px;cursor:pointer;font-size:13px;color:var(--muted)}label.checkbox:hover{color:var(--text)}
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:1.25rem}
.stat-card{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:1rem 1.2rem;transition:box-shadow .2s}
.stat-card:hover{box-shadow:0 4px 16px rgba(0,0,0,0.3)}
.stat-label{font-size:11px;color:var(--muted);margin-bottom:6px;text-transform:uppercase;letter-spacing:.5px}
.stat-val{font-size:24px;font-weight:700}
.table-wrap{overflow-x:auto;border:1px solid var(--border);border-radius:8px}
table{width:100%;border-collapse:collapse}
thead th{background:var(--surface2);padding:11px 14px;text-align:left;font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;cursor:pointer;white-space:nowrap;user-select:none;border-bottom:1px solid var(--border)}
thead th:hover{color:var(--text)}thead th.sorted{color:var(--accent)}
tbody tr{border-bottom:1px solid var(--border);transition:background .1s}tbody tr:last-child{border-bottom:none}tbody tr:hover{background:var(--surface2)}
tbody td{padding:10px 14px;font-size:13px;vertical-align:middle}
.name-cell{display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.badge{display:inline-block;font-size:10px;font-weight:700;padding:2px 6px;border-radius:4px}
.badge-6l{background:#1a3d28;color:#4CAF82;border:1px solid #2d6b45}
.badge-hot{background:#3d2a08;color:#e09d2a;border:1px solid #6b4a12}
.badge-build{background:#1a2a3d;color:#5b9bd5;border:1px solid #2d4a6b;font-size:9px}
.badge-underpriced{background:#1a3d1a;color:#4CAF82;border:1px solid #2d6b2d;font-size:9px}
.badge-alert{font-size:9px;font-weight:700;padding:2px 6px;border-radius:4px}
.alert-spike{background:#3d1a1a;color:#e05555;border:1px solid #6b2d2d}
.alert-crash{background:#1a1a3d;color:#5b9bd5;border:1px solid #2d2d6b}
.alert-drying{background:#3d2a08;color:#e09d2a;border:1px solid #6b4a12}
.alert-flood{background:#1a3d28;color:#4CAF82;border:1px solid #2d6b45}
.alert-new{background:#2a1a3d;color:#aa55e0;border:1px solid #4a2d6b}
.alert-underpriced{background:#1a3d1a;color:#4CAF82;border:1px solid #2d6b2d}
.alert-meta_spike{background:#3d2a08;color:#e09d2a;border:1px solid #6b4a12}
.alert-corner_risk{background:#3d1a2a;color:#e055aa;border:1px solid #6b2d4a}
/* Refresh modal */
.refresh-modal-overlay{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.6);z-index:1000;align-items:center;justify-content:center}
.refresh-modal-overlay.show{display:flex}
.refresh-modal{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:1.5rem 2rem;max-width:440px;text-align:center;box-shadow:0 8px 32px rgba(0,0,0,0.5)}
.refresh-modal h3{color:var(--accent);margin-bottom:10px;font-size:16px}
.refresh-modal p{color:var(--muted);font-size:13px;line-height:1.6;margin-bottom:12px}
.refresh-modal code{background:var(--surface2);color:var(--accent);padding:2px 8px;border-radius:4px;font-size:12px}
.refresh-modal button{background:var(--accent);color:var(--bg);border:none;padding:8px 24px;border-radius:6px;font-size:13px;font-weight:600;cursor:pointer;margin-top:6px}
.refresh-modal button:hover{opacity:.85}
.refresh-btn{background:var(--surface2);border:1px solid var(--border);color:var(--muted);padding:5px 14px;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;transition:all .15s}
.refresh-btn:hover{border-color:var(--accent);color:var(--accent)}
/* Hint box */
.hint-bar{background:var(--surface);border:1px solid var(--border);border-radius:8px;margin-bottom:12px;overflow:hidden;transition:box-shadow .2s}
.hint-toggle{padding:8px 14px;cursor:pointer;display:flex;align-items:center;gap:8px;font-size:12px;color:var(--muted);transition:background .1s;user-select:none}
.hint-toggle:hover{background:var(--surface2);color:var(--text)}
.hint-body{padding:0 14px 10px;font-size:12px;color:var(--muted);line-height:1.6;display:none}
.hint-body.open{display:block}
.hint-body ul{padding-left:18px;margin:4px 0}
.hint-body li{margin-bottom:3px}
/* History section */
.history-section{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:12px 16px;margin-top:16px}
.history-section h3{font-size:13px;color:var(--accent);margin-bottom:8px}
.history-item{font-size:12px;color:var(--muted);padding:3px 0;border-bottom:1px solid var(--border)}
.history-item:last-child{border-bottom:none}
.chaos-val{color:var(--accent);font-weight:600}
.listings-low{color:var(--red);font-weight:600}.listings-mid{color:var(--yellow)}.listings-ok{color:var(--muted)}
.conf-low{color:var(--red);font-weight:600;font-size:10px}.conf-mid{color:var(--yellow);font-size:10px}.conf-ok{color:var(--green);font-size:10px}
.conf-bar{display:inline-block;width:40px;height:4px;background:var(--border);border-radius:2px;overflow:hidden;vertical-align:middle;margin-left:4px}
.conf-fill{height:100%;border-radius:2px}
.trade-links{display:flex;gap:4px;align-items:center}
.trade-link-ninja{font-size:10px;color:var(--muted);text-decoration:none;padding:2px 5px;border-radius:3px;border:1px solid var(--border);transition:all .15s;cursor:pointer;white-space:nowrap}
.trade-link-ninja:hover{color:var(--blue);border-color:var(--blue)}
.score-wrap,.demand-wrap{display:flex;align-items:center;gap:6px}
.score-bar,.demand-bar{width:50px;height:5px;background:var(--border);border-radius:3px;overflow:hidden}
.score-fill,.demand-fill{height:100%;border-radius:3px}
.score-num{font-size:11px;color:var(--muted);min-width:20px}
.demand-high{color:var(--red);font-weight:600}.demand-mid{color:var(--yellow)}.demand-low{color:var(--muted)}
.empty{text-align:center;padding:3rem;color:var(--muted)}
.footer{font-size:11px;color:var(--muted);margin-top:1rem}
.trade-link{display:inline-flex;align-items:center;gap:4px;font-size:11px;color:var(--blue);text-decoration:none;padding:2px 6px;border-radius:4px;border:1px solid var(--border);transition:all .15s;cursor:pointer;white-space:nowrap}
.trade-link:hover{border-color:var(--blue);background:#1a2a3d}
.spark-svg{vertical-align:middle}
.tier-badge{display:inline-block;font-size:11px;font-weight:700;padding:3px 8px;border-radius:4px;border:1px solid}
.craft-reason{font-size:12px;color:var(--muted);max-width:260px;line-height:1.4}
.craft-action{font-size:12px;font-weight:600;white-space:nowrap}
.craft-method-badge{display:inline-block;font-size:10px;font-weight:700;padding:2px 7px;border-radius:4px;text-transform:uppercase;letter-spacing:.3px}
.method-6-link{background:#1a3d28;color:#4CAF82;border:1px solid #2d6b45}
.method-corrupt{background:#3d1a1a;color:#e05555;border:1px solid #6b2d2d}
.method-double_corrupt{background:#3d1a2a;color:#e055aa;border:1px solid #6b2d4a}
.method-harvest{background:#2a3d1a;color:#82e055;border:1px solid #4a6b2d}
.method-fracture{background:#2a1a3d;color:#aa55e0;border:1px solid #4a2d6b}
.method-essence{background:#3d2a1a;color:#e09d2a;border:1px solid #6b4a12}
.profit-positive{color:var(--green);font-weight:600}
.profit-high{color:#4CAF82;font-weight:700;font-size:14px}
.risk-low{color:var(--green);font-size:10px;font-weight:600}
.risk-medium{color:var(--yellow);font-size:10px;font-weight:600}
.risk-high{color:var(--red);font-size:10px;font-weight:600}
.price-up{color:var(--green);font-size:11px;font-weight:600}
.price-down{color:var(--red);font-size:11px;font-weight:600}
.suggest-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:14px}
.suggest-card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:1rem 1.2rem;transition:border-color .15s,box-shadow .2s}
.suggest-card:hover{border-color:var(--accent);box-shadow:0 4px 16px rgba(0,0,0,0.3)}
.suggest-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;gap:8px;flex-wrap:wrap}
.suggest-name{font-size:15px;font-weight:600}
.suggest-meta{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px;align-items:center}
.suggest-options{display:flex;flex-direction:column;gap:8px}
.suggest-option{background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:10px 12px}
.suggest-option.best{border-color:var(--accent)}
.suggest-option-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;gap:8px}
.suggest-option-num{display:inline-flex;align-items:center;justify-content:center;width:20px;height:20px;border-radius:50%;font-size:11px;font-weight:700}
.opt-1{background:var(--accent);color:var(--bg)}.opt-2{background:var(--blue);color:var(--bg)}.opt-3{background:var(--muted);color:var(--bg)}
.suggest-option-action{font-weight:600;font-size:13px}
.suggest-option-reason{font-size:12px;color:var(--muted);line-height:1.4;margin-top:4px}
.suggest-option-footer{display:flex;gap:10px;align-items:center;margin-top:6px}
.best-label{font-size:9px;font-weight:700;text-transform:uppercase;color:var(--accent)}
.flip-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(380px,1fr));gap:14px}
.flip-card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:1rem 1.2rem;transition:border-color .15s,box-shadow .2s}
.flip-card:hover{border-color:var(--green);box-shadow:0 4px 16px rgba(0,0,0,0.3)}
.flip-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;flex-wrap:wrap;gap:8px}
.flip-name{font-size:15px;font-weight:600}
.flip-type-badge{font-size:11px;font-weight:700;padding:3px 8px;border-radius:4px}
.flip-6link{background:#1a3d28;color:#4CAF82;border:1px solid #2d6b45}
.flip-gem{background:#2a1a3d;color:#aa55e0;border:1px solid #4a2d6b}
.flip-price{background:#3d2a08;color:#e09d2a;border:1px solid #6b4a12}
.flip-flow{display:flex;align-items:center;gap:10px;margin:10px 0;flex-wrap:wrap}
.flip-box{background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:8px 12px;text-align:center;min-width:80px}
.flip-box-label{font-size:10px;color:var(--muted);text-transform:uppercase;margin-bottom:2px}
.flip-box-val{font-size:16px;font-weight:700}
.flip-arrow{font-size:18px;color:var(--muted)}
.flip-profit-box{border-color:var(--green)}.flip-profit-box .flip-box-val{color:var(--green)}
.flip-reason{font-size:12px;color:var(--muted);line-height:1.4;margin-top:8px}
.flip-footer{display:flex;gap:12px;align-items:center;margin-top:8px;font-size:11px;color:var(--muted);flex-wrap:wrap}
.budget-input-row{display:flex;gap:12px;align-items:center;margin-bottom:1rem;padding:1rem;background:var(--surface);border:1px solid var(--border);border-radius:8px;flex-wrap:wrap}
.budget-input-row label{font-size:13px;color:var(--muted)}
.budget-btn{background:var(--accent);color:var(--bg);border:none;padding:8px 18px;border-radius:6px;font-size:13px;font-weight:600;cursor:pointer}
.budget-btn:hover{opacity:.85}
.budget-plan{display:flex;flex-direction:column;gap:8px}
.budget-item{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:10px 14px;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;transition:box-shadow .2s}
.budget-item:hover{box-shadow:0 4px 16px rgba(0,0,0,0.3)}
.budget-item-left{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.budget-step{display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:50%;background:var(--accent);color:var(--bg);font-size:12px;font-weight:700;flex-shrink:0}
.budget-item-name{font-weight:600;font-size:14px}
.budget-item-right{display:flex;gap:16px;align-items:center;flex-wrap:wrap}
.budget-summary{background:var(--surface);border:2px solid var(--accent);border-radius:10px;padding:1.2rem;margin-top:12px;display:flex;gap:24px;flex-wrap:wrap}
.budget-summary-item{text-align:center}
.budget-summary-label{font-size:11px;color:var(--muted);text-transform:uppercase}
.budget-summary-val{font-size:24px;font-weight:700;color:var(--accent)}
.tier-legend{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:1rem;padding:.75rem 1rem;background:var(--surface);border:1px solid var(--border);border-radius:8px}
.tier-legend-item{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--muted)}
.tier-dot{width:10px;height:10px;border-radius:50%}

/* Currency tab */
.currency-highlight{background:#1a3d28 !important;border-color:#2d6b45 !important}
.arb-card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:1rem 1.2rem;margin-bottom:10px;transition:box-shadow .2s}
.arb-card:hover{box-shadow:0 4px 16px rgba(0,0,0,0.3)}
.arb-path{font-size:14px;font-weight:600;color:var(--accent)}
.arb-profit{font-size:16px;font-weight:700;color:var(--green)}
.arb-detail{font-size:12px;color:var(--muted);margin-top:4px}

/* Zero to Mirror */
.z2m-phase{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:1.2rem;margin-bottom:14px;transition:box-shadow .2s}
.z2m-phase:hover{box-shadow:0 4px 16px rgba(0,0,0,0.3)}
.z2m-phase.active-phase{border-color:var(--accent);box-shadow:0 0 12px rgba(200,155,60,0.15)}
.z2m-phase-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;flex-wrap:wrap;gap:8px}
.z2m-phase-name{font-size:16px;font-weight:700;color:var(--accent)}
.z2m-phase-target{font-size:13px;color:var(--muted)}
.z2m-progress{width:100%;height:8px;background:var(--border);border-radius:4px;overflow:hidden;margin:8px 0}
.z2m-progress-fill{height:100%;border-radius:4px;background:linear-gradient(90deg,var(--accent),var(--green));transition:width .3s}
.z2m-item{background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:8px 12px;margin:6px 0;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px}
.z2m-item-name{font-weight:600;font-size:13px}
.z2m-item-detail{font-size:12px;color:var(--muted)}
.z2m-item-profit{color:var(--green);font-weight:600;font-size:13px}
.z2m-summary{display:flex;gap:16px;margin-top:8px;flex-wrap:wrap;font-size:12px;color:var(--muted)}
.z2m-input-row{display:flex;gap:12px;align-items:center;margin-bottom:1rem;padding:1rem;background:var(--surface);border:1px solid var(--border);border-radius:8px;flex-wrap:wrap}
.z2m-overall-progress{margin-bottom:1.5rem;padding:1.2rem;background:var(--surface);border:2px solid var(--accent);border-radius:10px}
.z2m-overall-label{font-size:13px;color:var(--muted);margin-bottom:4px}
.z2m-overall-val{font-size:28px;font-weight:700;color:var(--accent)}

/* Guide */
.guide-wrap{max-width:900px}
.guide-section{background:var(--surface);border:1px solid var(--border);border-radius:10px;margin-bottom:10px;overflow:hidden;transition:box-shadow .2s}
.guide-section:hover{box-shadow:0 4px 16px rgba(0,0,0,0.3)}
.guide-header{padding:12px 16px;cursor:pointer;display:flex;justify-content:space-between;align-items:center;transition:background .1s}
.guide-header:hover{background:var(--surface2)}
.guide-header h2{font-size:14px;font-weight:600;color:var(--accent);margin:0}
.guide-arrow{color:var(--muted);font-size:14px;transition:transform .2s}
.guide-arrow.open{transform:rotate(180deg)}
.guide-body{padding:0 16px 14px;font-size:13px;color:var(--muted);line-height:1.6;display:none}
.guide-body.open{display:block}
.guide-body p{margin:6px 0}.guide-body ul{padding-left:18px;margin:6px 0}.guide-body li{margin-bottom:3px}
.guide-body code{background:var(--surface2);color:var(--accent);padding:1px 6px;border-radius:4px;font-size:12px}
.guide-summary{padding:14px 16px;font-size:13px;color:var(--text);line-height:1.5}
.guide-color{width:12px;height:12px;border-radius:3px;display:inline-block;vertical-align:middle;margin-right:4px}

@media(max-width:900px){.page-wrapper{padding:0 1rem}.suggest-grid,.flip-grid{grid-template-columns:1fr}.stats-grid{grid-template-columns:repeat(auto-fit,minmax(110px,1fr))}}
@media(max-width:600px){.page-wrapper{padding:0 .5rem}.mode-tab{padding:8px 8px;font-size:11px}.stats-grid{grid-template-columns:repeat(2,1fr)}.flip-flow{flex-direction:column;align-items:stretch}.flip-flow .flip-arrow{text-align:center}.controls{flex-direction:column;align-items:stretch}.control-group{width:100%}}
</style></head><body>

<div class="page-wrapper">
<header>
  <div class="header-left">
    <div><h1>&#9876; PoE Mirage Economy v5</h1><span class="ratio-badge">1 div = DIV_RATIO_VALUEc</span></div>
    <div class="pro-toggle" id="proToggle">
      <button class="pro-toggle-btn active" onclick="setProMode(false)">Simple</button>
      <button class="pro-toggle-btn" onclick="setProMode(true)">Pro</button>
    </div>
    <button class="refresh-btn" id="refreshBtn" onclick="doRefresh()">&#8635; Refresh Data</button>
  </div>
  <span class="meta">TIMESTAMP &middot; LEAGUE_NAME &middot; PREV_STATUS</span>
</header>
<div class="refresh-modal-overlay" id="refreshModal" onclick="if(event.target===this)this.classList.remove('show')">
  <div class="refresh-modal">
    <h3 id="refreshTitle">&#8635; Refresh Data</h3>
    <p id="refreshMsg">Run <code>python poe_dashboard.py</code> in your terminal to refresh.<br><br>Or use <code>python poe_dashboard.py --serve</code> for live refresh.</p>
    <button onclick="document.getElementById('refreshModal').classList.remove('show')">Got it</button>
  </div>
</div>

<div class="mode-tabs" id="modeTabs">
  <div class="mode-tab active" onclick="switchMode('economy')">Economy</div>
  <div class="mode-tab" onclick="switchMode('craft')">Craft Finder</div>
  <div class="mode-tab" onclick="switchMode('suggest')">Suggest</div>
  <div class="mode-tab" onclick="switchMode('flip')">Flip Finder</div>
  <div class="mode-tab" onclick="switchMode('budget')">Budget</div>
  <div class="mode-tab" onclick="switchMode('alerts')">Alerts<span class="alert-dot" id="alertDot" style="display:none"></span></div>
  <div class="mode-tab" onclick="switchMode('currency')">Currency</div>
  <div class="mode-tab" onclick="switchMode('z2m')">Zero to Mirror</div>
  <div class="mode-tab" onclick="switchMode('whale')" style="color:var(--purple)">Whale Mode</div>
  <div class="mode-tab" onclick="switchMode('guide')" style="margin-left:auto;color:var(--blue)">Tools &amp; Resources</div>
</div>
<div class="tabs" id="tabs"></div>

<div class="main">
  <div class="controls" id="economyControls">
    <div class="control-group"><label>Min chaos</label><input type="number" id="minChaos" value="50" min="0" step="10" oninput="render()"></div>
    <div class="control-group"><label>Max listings</label><input type="number" id="maxListings" value="500" min="1" step="10" oninput="render()"></div>
    <div class="control-group"><label class="checkbox"><input type="checkbox" id="sixLink" onchange="render()"> 6L only</label></div>
    <div class="control-group"><label class="checkbox"><input type="checkbox" id="hotOnly" onchange="render()"> Hot only</label></div>
    <div class="control-group"><label class="checkbox"><input type="checkbox" id="underpricedOnly" onchange="render()"> Underpriced</label></div>
    <div class="control-group"><input type="text" id="search" placeholder="Search..." oninput="render()"></div>
  </div>
  <div class="controls" id="craftControls" style="display:none">
    <div class="control-group"><label>Method</label><select id="craftMethod" onchange="render()"><option value="all">All</option><option value="6-link">6-Link</option><option value="corrupt">Corrupt</option><option value="double_corrupt">Dbl Corrupt</option><option value="harvest">Harvest</option><option value="fracture">Fracture</option><option value="essence">Essence</option></select></div>
    <div class="control-group"><label>Tier</label><select id="craftTier" onchange="render()"><option value="all">All</option><option value="0">&lt;1d</option><option value="1">1-3d</option><option value="2">3-6d</option><option value="3">6-10d</option><option value="4">11-15d</option><option value="5">15+d</option></select></div>
    <div class="control-group"><label>Min profit (c)</label><input type="number" id="minProfit" value="0" min="0" step="50" oninput="render()"></div>
    <div class="control-group"><label class="checkbox"><input type="checkbox" id="metaOnly" onchange="render()"> Meta only</label></div>
    <div class="control-group"><input type="text" id="craftSearch" placeholder="Search..." oninput="render()"></div>
  </div>
  <div class="controls" id="suggestControls" style="display:none">
    <div class="control-group"><label>Tier</label><select id="suggestTier" onchange="render()"><option value="all">All</option><option value="0">&lt;1d</option><option value="1">1-3d</option><option value="2">3-6d</option><option value="3">6-10d</option><option value="4">11-15d</option><option value="5">15+d</option></select></div>
    <div class="control-group"><label>Min demand</label><input type="number" id="suggestMinDemand" value="0" min="0" max="100" step="5" oninput="render()"></div>
    <div class="control-group"><label class="checkbox"><input type="checkbox" id="suggestMeta" onchange="render()"> Meta only</label></div>
    <div class="control-group"><label class="checkbox"><input type="checkbox" id="suggestUnderpriced" onchange="render()"> Underpriced</label></div>
    <div class="control-group"><input type="text" id="suggestSearch" placeholder="Search..." oninput="render()"></div>
  </div>
  <div class="controls" id="flipControls" style="display:none">
    <div class="control-group"><label>Type</label><select id="flipType" onchange="render()"><option value="all">All</option><option value="6-Link Spread">6-Link</option><option value="Gem Level Gap">Gem Level</option><option value="Price Gap">Price Gap</option></select></div>
    <div class="control-group"><label>Min profit (c)</label><input type="number" id="flipMinProfit" value="50" min="0" step="50" oninput="render()"></div>
    <div class="control-group"><label class="checkbox"><input type="checkbox" id="flipMetaOnly" onchange="render()"> Meta only</label></div>
    <div class="control-group"><input type="text" id="flipSearch" placeholder="Search..." oninput="render()"></div>
  </div>
  <div class="controls" id="alertControls" style="display:none">
    <div class="control-group"><label>Alert type</label><select id="alertType" onchange="render()"><option value="all">All</option><option value="spike">Spikes (+25%)</option><option value="crash">Crashes (-25%)</option><option value="drying">Drying Up</option><option value="flood">Flooding</option><option value="new">New</option><option value="underpriced">Underpriced</option><option value="meta_spike">Meta Spike</option><option value="corner_risk">Corner Risk</option></select></div>
    <div class="control-group"><input type="text" id="alertSearch" placeholder="Search..." oninput="render()"></div>
  </div>
  <div id="budgetControls" style="display:none"></div>
  <!-- Whale controls -->
  <div class="controls" id="whaleControls" style="display:none">
    <div class="control-group"><label>Strategy</label><select id="whaleStrategy" onchange="render()"><option value="all">All Strategies</option><option value="corner">Supply Cornering</option><option value="6link_flip">6-Link Flipping</option><option value="gem_level">Gem Leveling</option><option value="double_corrupt">Double Corrupt</option><option value="vaal_corrupt">Vaal Corrupt</option><option value="tainted_chaos_jewels">Tainted Chaos Jewels</option><option value="harvest_fracture">Harvest Fracture</option><option value="essence_craft">Essence Craft</option></select></div>
    <div class="control-group"><label>Category</label><select id="whaleTag" onchange="render()"><option value="all">All</option><option value="flipping">Flipping</option><option value="corruption">Corruption</option><option value="crafting">Crafting</option><option value="leveling">Leveling</option><option value="advanced">Advanced</option></select></div>
    <div class="control-group"><label>Max cost (c)</label><input type="number" id="whaleMaxCost" value="50000" min="0" step="1000" oninput="render()"></div>
    <div class="control-group"><label>Max listings</label><input type="number" id="whaleMaxList" value="20" min="1" step="5" oninput="render()"></div>
    <div class="control-group"><label class="checkbox"><input type="checkbox" id="whaleCornerable" onchange="render()"> Cornerable only</label></div>
    <div class="control-group"><input type="text" id="whaleSearch" placeholder="Search..." oninput="render()"></div>
  </div>
  <div id="currencyControls" style="display:none" class="controls">
    <div class="control-group"><label class="checkbox"><input type="checkbox" id="currProfitOnly" onchange="render()"> Profitable only (&gt;3%)</label></div>
    <div class="control-group"><input type="text" id="currSearch" placeholder="Search currency..." oninput="render()"></div>
  </div>
  <div id="z2mControls" style="display:none"></div>

  <div class="tier-legend" id="tierLegend" style="display:none">
    <div class="tier-legend-item"><div class="tier-dot" style="background:#888"></div>&lt;1d</div>
    <div class="tier-legend-item"><div class="tier-dot" style="background:#5b9bd5"></div>1-3d</div>
    <div class="tier-legend-item"><div class="tier-dot" style="background:#4CAF82"></div>3-6d</div>
    <div class="tier-legend-item"><div class="tier-dot" style="background:#d4a017"></div>6-10d</div>
    <div class="tier-legend-item"><div class="tier-dot" style="background:#e08833"></div>11-15d</div>
    <div class="tier-legend-item"><div class="tier-dot" style="background:#e05555"></div>15+d</div>
  </div>

  <div class="hint-bar" id="hintBox" style="display:none"><div class="hint-toggle" onclick="this.nextElementSibling.classList.toggle('open')">&#128161; How to use this tab</div><div class="hint-body" id="hintBody"></div></div>
  <div class="stats-grid" id="stats"></div>
  <div id="contentArea">
    <div class="table-wrap" id="tableWrap"><table id="tbl"><thead id="thead"></thead><tbody id="tbody"></tbody></table></div>
    <div class="suggest-grid" id="suggestGrid" style="display:none"></div>
    <div class="flip-grid" id="flipGrid" style="display:none"></div>
    <div id="budgetArea" style="display:none"></div>
    <div id="currencyArea" style="display:none"></div>
    <div id="z2mArea" style="display:none"></div>
    <div class="flip-grid" id="whaleGrid" style="display:none"></div>
    <div id="guideArea" style="display:none"></div>
  </div>
  <div class="footer" id="footerText"></div>
</div>
</div>

<script>
const SERVE_MODE=SERVE_MODE_FLAG;
function doRefresh(){
  if(SERVE_MODE){
    const btn=document.getElementById('refreshBtn');
    btn.textContent='Refreshing...';btn.style.color='var(--accent)';btn.disabled=true;
    fetch('/refresh').then(r=>{if(r.ok){btn.textContent='Done! Reloading...';setTimeout(()=>location.reload(),500);}else{btn.textContent='Error — retry';btn.disabled=false;}}).catch(()=>{btn.textContent='Error — retry';btn.disabled=false;btn.style.color='var(--red)';});
  } else {
    document.getElementById('refreshModal').classList.add('show');
  }
}
const DATA=ALL_DATA_JSON, FLIPS=ALL_FLIPS_JSON, DIV_RATIO=DIV_RATIO_NUM, LEAGUE='LEAGUE_NAME';
const CURRENCIES=ALL_CURRENCY_JSON;
const ARB_LOOPS=ALL_ARB_JSON;
const WHALES=ALL_WHALE_JSON;
const WHALE_STRATS=ALL_STRATS_JSON;
const MIRROR_PRICE=MIRROR_PRICE_NUM;
const HISTORY=ALL_HISTORY_JSON;
let mode='economy';
let proMode=false;
const MODES=['economy','craft','suggest','flip','budget','alerts','currency','z2m','whale','guide'];
const TL={UniqueArmour:'Armours',UniqueWeapon:'Weapons',UniqueJewel:'Jewels',UniqueAccessory:'Accessories',UniqueFlask:'Flasks',SkillGem:'Gems',BaseType:'Bases'};
const ML={'6-link':'6-Link','corrupt':'Corrupt','double_corrupt':'Dbl Corrupt','harvest':'Harvest','fracture':'Fracture','essence':'Essence'};
const TYPES=[...new Set(DATA.map(d=>d.type))];
let activeType=TYPES[0],sortKey='chaos',sortDir=-1;

function setProMode(v){
  proMode=v;
  const btns=document.querySelectorAll('.pro-toggle-btn');
  btns[0].classList.toggle('active',!v);
  btns[1].classList.toggle('active',v);
  render();
}

function tradeUrl(n,c){return c?`https://poe.ninja/economy/${LEAGUE.toLowerCase()}/${c}?name=${encodeURIComponent(n)}`:`https://poe.ninja/economy/${LEAGUE.toLowerCase()}?name=${encodeURIComponent(n)}`;}
function tradeUrlOfficial(n){return `https://www.pathofexile.com/trade/search/${LEAGUE}?q={"query":{"term":"${encodeURIComponent(n)}"}}`;}
function confColor(c){return c<=25?'var(--red)':c<=50?'var(--yellow)':'var(--green)';}
function confLabel(c){return c<=25?'Unreliable':c<=50?'Low confidence':c<=70?'Moderate':'Reliable';}
function sparkSvg(d){if(!d||d.length<2)return'';const w=70,h=18,p=2,mn=Math.min(...d),mx=Math.max(...d),r=mx-mn||1;const pts=d.map((v,i)=>`${(p+i/(d.length-1)*(w-p*2)).toFixed(1)},${(p+(1-(v-mn)/r)*(h-p*2)).toFixed(1)}`);const c=d[d.length-1]>=d[0]?'#4CAF82':'#e05555';return `<svg class="spark-svg" width="${w}" height="${h}"><polyline points="${pts.join(' ')}" fill="none" stroke="${c}" stroke-width="1.5" stroke-linecap="round"/></svg>`;}
function esc(s){return typeof s!=='string'?s:s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function dc(d){return d>=60?'#e05555':d>=30?'#d4a017':'#5b9bd5';}
function sc(s){return s>=70?'#4CAF82':s>=40?'#d4a017':'#5b9bd5';}
function fmt(c){return c>=1000?(c/1000).toFixed(1)+'k':c.toLocaleString();}

function alertBadge(a,p){if(!a)return'';const m={spike:['SPIKE','alert-spike'],crash:['CRASH','alert-crash'],drying:['DRYING','alert-drying'],flood:['FLOOD','alert-flood'],'new':['NEW','alert-new'],underpriced:['UNDERPRICED','alert-underpriced'],meta_spike:['META SPIKE','alert-meta_spike'],corner_risk:['CORNER RISK','alert-corner_risk']};const v=m[a];return v?`<span class="badge-alert ${v[1]}">${v[0]}</span>`:'';}

const HINTS={
  economy:'<ul><li>Sort by Demand to find hot items.</li><li>Use "Underpriced" filter to find buy-low opportunities.</li><li>Click Trade to open official trade site, or ninja for poe.ninja.</li><li>⚠ on price = unreliable (very few listings). ~ on listings = approximate poe.ninja count.</li></ul>',
  craft:'<ul><li>Set "Min profit" to filter noise.</li><li>Use "Meta only" for guaranteed demand.</li><li>Higher risk = higher variance, not guaranteed profit.</li></ul>',
  suggest:'<ul><li>Gold #1 = highest expected profit.</li><li>Compare risk levels before committing.</li><li>Underpriced + high demand = best targets.</li></ul>',
  flip:'<ul><li>6-Link spreads are safest.</li><li>Check listing counts — more listings = easier to execute.</li><li>Start with small flips.</li></ul>',
  budget:'<ul><li>Enter your total available chaos.</li><li>The plan optimizes for best ROI.</li><li>Meta-only mode ensures items actually sell.</li></ul>',
  whale:'<ul><li>Filter "Cornerable only" + sort by corner score.</li><li>Items with meta build badges have guaranteed demand.</li><li>Start small — corner 1-2 items first.</li><li>⚠ = unreliable price. Always verify on the official trade site before buying.</li></ul>',
  currency:'<ul><li>Only shows currencies with real exchange pairs (3+ listings both sides).</li><li>Spread &gt;3% = profitable to flip.</li><li>Volume matters — more listings = sustainable.</li></ul>',
  z2m:'<ul><li>Uncheck strategies you don\'t want to use.</li><li>Phase 1 items are your starting point.</li><li>Each phase builds on the previous.</li></ul>',
  alerts:'<ul><li>Run the script twice (morning + evening) for meaningful alerts.</li><li>UNDERPRICED alerts are your best buy signals.</li><li>CORNER RISK means someone may be manipulating supply.</li></ul>',
  guide:''
};
function toggleHint(m){
  const box=document.getElementById('hintBox');
  const body=document.getElementById('hintBody');
  if(!HINTS[m]){box.style.display='none';return;}
  box.style.display='block';
  body.innerHTML=HINTS[m];
  body.classList.remove('open');
}

function fmtCell(f,val,row){
  switch(f){
    case 'name':{const p=[`<span>${esc(val)}</span>`];if(row.variant)p.push(`<span style="font-size:10px;color:var(--muted);margin-left:4px">(${esc(row.variant)})</span>`);if(proMode){if(row.confidence<=25)p.push('<span class="conf-low" title="Price unreliable — very few listings">⚠ price</span>');if(row.score>=60)p.push('<span class="badge badge-hot">HOT</span>');if(row.underpriced>0)p.push(`<span class="badge badge-underpriced">${row.underpriced}%under</span>`);if(row.alert)p.push(alertBadge(row.alert,row.price_change));}return `<div class="name-cell">${p.join('')}</div>`;}
    case 'craft_name':{const p=[`<span>${esc(val)}</span>`];if(row.variant)p.push(`<span style="font-size:10px;color:var(--muted);margin-left:4px">(${esc(row.variant)})</span>`);if(proMode){if(row.confidence<=25)p.push('<span class="conf-low" title="Price unreliable">⚠</span>');if(row.builds&&row.builds.length)row.builds.forEach(b=>p.push(`<span class="badge badge-build">${esc(b)}</span>`));if(row.links>=6)p.push('<span class="badge badge-6l">6L</span>');if(row.underpriced>0)p.push(`<span class="badge badge-underpriced">${row.underpriced}%</span>`);}return `<div class="name-cell">${p.join('')}</div>`;}
    case 'type_label':return TL[val]||val||'-';
    case 'tier':return `<span class="tier-badge" style="color:${row.tier_color};border-color:${row.tier_color}30;background:${row.tier_color}18">${esc(val)}</span>`;
    case 'links':return val>=6?'<span class="badge badge-6l">6L</span>':val>0?val+'L':'-';
    case 'chaos':{const cf=row.confidence||95;const warn=cf<=25?` <span class="conf-low" title="${confLabel(cf)} price (${cf}/100) — only ${row.listings} on poe.ninja">⚠</span>`:cf<=50?` <span class="conf-mid" title="${confLabel(cf)} (${cf}/100)">~</span>`:'';return `<span class="chaos-val">${fmt(val)}c</span>${warn}`;}
    case 'listings':{const c=val<=5?'listings-low':val<=20?'listings-mid':'listings-ok';const tip=val<=3?' title="poe.ninja count — check trade site for actual listings"':'';return `<span class="${c}"${tip}>~${val}</span>`;}
    case 'demand':{const c=dc(val);const cl=val>=60?'demand-high':val>=30?'demand-mid':'demand-low';return `<div class="demand-wrap"><div class="demand-bar"><div class="demand-fill" style="width:${Math.min(val,100)}%;background:${c}"></div></div><span class="${cl}" style="font-size:11px">${val}</span></div>`;}
    case 'score':{const c=sc(val);return `<div class="score-wrap"><div class="score-bar"><div class="score-fill" style="width:${Math.min(val,100)}%;background:${c}"></div></div><span class="score-num">${val}</span></div>`;}
    case 'spark':return sparkSvg(val);
    case 'trade':return `<div class="trade-links"><a class="trade-link" href="${tradeUrlOfficial(row.name)}" target="_blank" rel="noopener">Trade &#10148;</a><a class="trade-link-ninja" href="${tradeUrl(row.name,row.trade_cat)}" target="_blank" rel="noopener">ninja</a></div>`;
    case 'method':return val?`<span class="craft-method-badge method-${val}">${ML[val]||val}</span>`:'-';
    case 'craft_action':return val?`<span class="craft-action">${esc(val)}</span>`:'-';
    case 'craft_reason':return val?`<span class="craft-reason">${esc(val)}</span>`:'-';
    case 'profit':{if(!val||val<=0)return'-';return `<span class="${val>=500?'profit-high':'profit-positive'}">${fmt(val)}c</span>`;}
    case 'price_change':return val?`<span class="${val>0?'price-up':'price-down'}">${val>0?'+':''}${val}%</span>`:'-';
    case 'pct':return val?val+'%':'-';
    default:return val||'-';
  }
}

/* Column definitions */
const COLS_PRO={
  default:[{key:'name',label:'Item',fmt:'name'},{key:'links',label:'Links',fmt:'links'},{key:'spark',label:'7d',fmt:'spark'},{key:'chaos',label:'Price',fmt:'chaos'},{key:'listings',label:'List',fmt:'listings'},{key:'demand',label:'Demand',fmt:'demand'},{key:'score',label:'Opp',fmt:'score'},{key:'_t',label:'',fmt:'trade'}],
  SkillGem:[{key:'name',label:'Gem',fmt:'name'},{key:'gem_level',label:'Lv',fmt:'plain'},{key:'gem_quality',label:'Q',fmt:'pct'},{key:'spark',label:'7d',fmt:'spark'},{key:'chaos',label:'Price',fmt:'chaos'},{key:'listings',label:'List',fmt:'listings'},{key:'demand',label:'Demand',fmt:'demand'},{key:'score',label:'Opp',fmt:'score'},{key:'_t',label:'',fmt:'trade'}],
  BaseType:[{key:'name',label:'Base',fmt:'name'},{key:'level_req',label:'Lvl',fmt:'plain'},{key:'spark',label:'7d',fmt:'spark'},{key:'chaos',label:'Price',fmt:'chaos'},{key:'listings',label:'List',fmt:'listings'},{key:'demand',label:'Demand',fmt:'demand'},{key:'score',label:'Opp',fmt:'score'},{key:'_t',label:'',fmt:'trade'}],
};
const COLS_SIMPLE={
  default:[{key:'name',label:'Item',fmt:'name'},{key:'chaos',label:'Price',fmt:'chaos'},{key:'listings',label:'List',fmt:'listings'},{key:'_t',label:'',fmt:'trade'}],
  SkillGem:[{key:'name',label:'Gem',fmt:'name'},{key:'chaos',label:'Price',fmt:'chaos'},{key:'listings',label:'List',fmt:'listings'},{key:'_t',label:'',fmt:'trade'}],
  BaseType:[{key:'name',label:'Base',fmt:'name'},{key:'chaos',label:'Price',fmt:'chaos'},{key:'listings',label:'List',fmt:'listings'},{key:'_t',label:'',fmt:'trade'}],
};
const CC_PRO=[{key:'name',fmt:'craft_name',label:'Item'},{key:'type',fmt:'type_label',label:'Type'},{key:'tier_label',fmt:'tier',label:'Tier'},{key:'chaos',fmt:'chaos',label:'Price'},{key:'listings',fmt:'listings',label:'List'},{key:'demand',fmt:'demand',label:'Dem'},{key:'craft_method',fmt:'method',label:'Method'},{key:'craft_action',fmt:'craft_action',label:'Action'},{key:'craft_reason',fmt:'craft_reason',label:'Why'},{key:'craft_profit',fmt:'profit',label:'Profit'},{key:'_t',fmt:'trade',label:''}];
const CC_SIMPLE=[{key:'name',fmt:'craft_name',label:'Item'},{key:'chaos',fmt:'chaos',label:'Price'},{key:'craft_method',fmt:'method',label:'Method'},{key:'craft_action',fmt:'craft_action',label:'Action'},{key:'craft_profit',fmt:'profit',label:'Profit'},{key:'_t',fmt:'trade',label:''}];
const AC=[{key:'name',fmt:'name',label:'Item'},{key:'type',fmt:'type_label',label:'Type'},{key:'spark',fmt:'spark',label:'7d'},{key:'chaos',fmt:'chaos',label:'Price'},{key:'price_change',fmt:'price_change',label:'Change'},{key:'listings',fmt:'listings',label:'List'},{key:'listings_change',fmt:'plain',label:'\u0394'},{key:'demand',fmt:'demand',label:'Dem'},{key:'_t',fmt:'trade',label:''}];

function getCols(){return proMode?COLS_PRO:COLS_SIMPLE;}
function getCC(){return proMode?CC_PRO:CC_SIMPLE;}

function switchMode(m){
  mode=m;sortKey=m==='flip'?'profit':m==='alerts'?'price_change':m==='craft'?'craft_profit':'chaos';sortDir=-1;
  document.querySelectorAll('.mode-tab').forEach((el,i)=>el.classList.toggle('active',MODES[i]===m));
  toggleHint(m);
  document.getElementById('footerText').innerHTML='';
  ['economyControls','craftControls','suggestControls','flipControls','alertControls','budgetControls','currencyControls','z2mControls','whaleControls'].forEach(id=>{const el=document.getElementById(id);if(el)el.style.display='none';});
  const cm={economy:'economyControls',craft:'craftControls',suggest:'suggestControls',flip:'flipControls',alerts:'alertControls',budget:'budgetControls',currency:'currencyControls',z2m:'z2mControls',whale:'whaleControls'};
  if(cm[m]){const el=document.getElementById(cm[m]);if(el)el.style.display=['budget','z2m'].includes(m)?'block':'flex';}
  document.getElementById('tierLegend').style.display=['craft','suggest','flip'].includes(m)?'flex':'none';
  document.getElementById('tabs').style.display=m==='economy'?'flex':'none';
  document.getElementById('tableWrap').style.display=['economy','craft','alerts','currency'].includes(m)?'':'none';
  document.getElementById('suggestGrid').style.display=m==='suggest'?'grid':'none';
  document.getElementById('flipGrid').style.display=m==='flip'?'grid':'none';
  document.getElementById('whaleGrid').style.display=m==='whale'?'grid':'none';
  document.getElementById('budgetArea').style.display=m==='budget'?'block':'none';
  document.getElementById('currencyArea').style.display=m==='currency'?'block':'none';
  document.getElementById('z2mArea').style.display=m==='z2m'?'block':'none';
  document.getElementById('guideArea').style.display=m==='guide'?'block':'none';
  render();
}
function buildTabs(){document.getElementById('tabs').innerHTML=TYPES.map(t=>`<div class="tab${t===activeType?' active':''}" onclick="switchType('${t}')">${TL[t]||t}</div>`).join('');}
function switchType(t){activeType=t;buildTabs();render();}
function render(){({economy:renderEconomy,craft:renderCraft,suggest:renderSuggest,flip:renderFlip,budget:renderBudget,alerts:renderAlerts,currency:renderCurrency,z2m:renderZ2M,whale:renderWhale,guide:renderGuide})[mode]();}

function renderEconomy(){
  buildTabs();
  const mc=parseFloat(document.getElementById('minChaos').value)||0,ml=parseInt(document.getElementById('maxListings').value)||99999,sl=document.getElementById('sixLink').checked,ho=document.getElementById('hotOnly').checked,up=document.getElementById('underpricedOnly').checked,q=document.getElementById('search').value.toLowerCase();
  let items=DATA.filter(d=>d.type===activeType).filter(d=>{if(d.chaos<mc)return false;if(d.listings>ml)return false;if(sl&&d.links<6)return false;if(ho&&d.score<60)return false;if(up&&!d.underpriced)return false;if(q&&!d.name.toLowerCase().includes(q))return false;return true;});
  items.sort((a,b)=>{let av=a[sortKey],bv=b[sortKey];if(typeof av==='string')return sortDir*av.localeCompare(bv);return sortDir*((bv||0)-(av||0));});
  const all=DATA.filter(d=>d.type===activeType);
  document.getElementById('stats').innerHTML=`<div class="stat-card"><div class="stat-label">Total</div><div class="stat-val">${all.length}</div></div><div class="stat-card"><div class="stat-label">Underpriced</div><div class="stat-val" style="color:var(--green)">${all.filter(d=>d.underpriced>0).length}</div></div><div class="stat-card"><div class="stat-label">Hot (60+)</div><div class="stat-val">${all.filter(d=>d.score>=60).length}</div></div><div class="stat-card"><div class="stat-label">Showing</div><div class="stat-val">${items.length}</div></div>`;
  const cols=getCols();
  renderTable(cols[activeType]||cols.default,items);
}
function renderCraft(){
  const mf=document.getElementById('craftMethod').value,tf=document.getElementById('craftTier').value,mp=parseFloat(document.getElementById('minProfit').value)||0,mo=document.getElementById('metaOnly').checked,q=document.getElementById('craftSearch').value.toLowerCase();
  let items=DATA.filter(d=>d.craft_method).filter(d=>{if(mf!=='all'&&d.craft_method!==mf)return false;if(tf!=='all'&&d.tier_idx!==parseInt(tf))return false;if(d.craft_profit<mp)return false;if(mo&&(!d.builds||!d.builds.length))return false;if(q&&!d.name.toLowerCase().includes(q))return false;return true;});
  items.sort((a,b)=>{let av=a[sortKey],bv=b[sortKey];if(typeof av==='string')return sortDir*(av||'').localeCompare(bv||'');return sortDir*((bv||0)-(av||0));});
  const cr=DATA.filter(d=>d.craft_method);
  document.getElementById('stats').innerHTML=`<div class="stat-card"><div class="stat-label">Craftable</div><div class="stat-val">${cr.length}</div></div><div class="stat-card"><div class="stat-label">Meta</div><div class="stat-val">${cr.filter(d=>d.builds&&d.builds.length).length}</div></div><div class="stat-card"><div class="stat-label">500c+ profit</div><div class="stat-val" style="color:var(--green)">${cr.filter(d=>d.craft_profit>=500).length}</div></div><div class="stat-card"><div class="stat-label">Showing</div><div class="stat-val">${items.length}</div></div>`;
  renderTable(getCC(),items);
}
function renderSuggest(){
  const tf=document.getElementById('suggestTier').value,md=parseInt(document.getElementById('suggestMinDemand').value)||0,mo=document.getElementById('suggestMeta').checked,up=document.getElementById('suggestUnderpriced').checked,q=document.getElementById('suggestSearch').value.toLowerCase();
  let items=DATA.filter(d=>d.top3&&d.top3.length>0&&d.top3[0].profit>0).filter(d=>{if(tf!=='all'&&d.tier_idx!==parseInt(tf))return false;if(d.demand<md)return false;if(mo&&(!d.builds||!d.builds.length))return false;if(up&&!d.underpriced)return false;if(q&&!d.name.toLowerCase().includes(q))return false;return true;});
  items.sort((a,b)=>(b.top3[0].profit||0)-(a.top3[0].profit||0));
  document.getElementById('stats').innerHTML=`<div class="stat-card"><div class="stat-label">2+ options</div><div class="stat-val">${items.filter(d=>d.top3.length>=2).length}</div></div><div class="stat-card"><div class="stat-label">High demand</div><div class="stat-val" style="color:var(--red)">${items.filter(d=>d.demand>=60).length}</div></div><div class="stat-card"><div class="stat-label">Underpriced</div><div class="stat-val" style="color:var(--green)">${items.filter(d=>d.underpriced>0).length}</div></div><div class="stat-card"><div class="stat-label">Showing</div><div class="stat-val">${items.length}</div></div>`;
  document.getElementById('thead').innerHTML='';document.getElementById('tbody').innerHTML='';
  const g=document.getElementById('suggestGrid');
  if(!items.length){g.innerHTML='<div class="empty" style="grid-column:1/-1">No items match</div>';return;}
  g.innerHTML=items.slice(0,80).map(r=>{
    const badges=[];
    if(proMode){
      if(r.builds&&r.builds.length)r.builds.forEach(b=>badges.push(`<span class="badge badge-build">${esc(b)}</span>`));
      if(r.links>=6)badges.push('<span class="badge badge-6l">6L</span>');
      if(r.underpriced>0)badges.push(`<span class="badge badge-underpriced">${r.underpriced}%</span>`);
    }
    const showOpts=proMode?r.top3:r.top3.slice(0,1);
    if(!proMode){
      /* Simple mode: compact card */
      const o=showOpts[0];
      return `<div class="suggest-card"><div class="suggest-header"><span class="suggest-name">${esc(r.name)}</span><span class="chaos-val">${fmt(r.chaos)}c</span></div><div class="suggest-meta">${badges.join('')}<div class="trade-links"><a class="trade-link" href="${tradeUrlOfficial(r.name)}" target="_blank">Trade &#10148;</a><a class="trade-link-ninja" href="${tradeUrl(r.name,r.trade_cat)}" target="_blank">ninja</a></div></div><div class="suggest-options"><div class="suggest-option best"><div class="suggest-option-header"><div style="display:flex;align-items:center;gap:8px"><span class="craft-method-badge method-${o.method}">${ML[o.method]||o.method}</span><span class="suggest-option-action">${esc(o.action)}</span></div><span class="${o.profit>=500?'profit-high':'profit-positive'}">${fmt(o.profit)}c</span></div></div></div></div>`;
    }
    const opts=showOpts.map((o,i)=>{const profitHtml=o.profit>0?`<span class="${o.profit>=500?'profit-high':'profit-positive'}">${fmt(o.profit)}c</span>`:`<span style="color:var(--red)">-EV</span>`;return `<div class="suggest-option${i===0?' best':''}"><div class="suggest-option-header"><div style="display:flex;align-items:center;gap:8px"><span class="suggest-option-num opt-${i+1}">${i+1}</span><span class="craft-method-badge method-${o.method}">${ML[o.method]||o.method}</span><span class="suggest-option-action">${esc(o.action)}</span>${i===0?'<span class="best-label">BEST</span>':''}</div>${profitHtml}</div><div class="suggest-option-reason">${esc(o.reason)}</div><div class="suggest-option-footer"><span class="risk-${o.risk||'low'}">Risk: ${(o.risk||'low').toUpperCase()}</span></div></div>`;}).join('');
    return `<div class="suggest-card"><div class="suggest-header"><span class="suggest-name">${esc(r.name)}</span><span class="chaos-val">${fmt(r.chaos)}c</span></div><div class="suggest-meta"><span class="tier-badge" style="color:${r.tier_color};border-color:${r.tier_color}30;background:${r.tier_color}18">${esc(r.tier_label)}</span><span style="font-size:12px;color:var(--muted)">${TL[r.type]||r.type}</span>${sparkSvg(r.spark)}${badges.join('')}<div class="trade-links"><a class="trade-link" href="${tradeUrlOfficial(r.name)}" target="_blank">Trade &#10148;</a><a class="trade-link-ninja" href="${tradeUrl(r.name,r.trade_cat)}" target="_blank">ninja</a></div></div><div class="suggest-options">${opts}</div></div>`;
  }).join('');
}
function renderFlip(){
  const ft=document.getElementById('flipType').value,mp=parseFloat(document.getElementById('flipMinProfit').value)||0,mo=document.getElementById('flipMetaOnly').checked,q=document.getElementById('flipSearch').value.toLowerCase();
  let items=FLIPS.filter(f=>{if(ft!=='all'&&f.flip_type!==ft)return false;if(f.profit<mp)return false;if(mo&&(!f.builds||!f.builds.length))return false;if(q&&!f.name.toLowerCase().includes(q))return false;return true;});
  document.getElementById('stats').innerHTML=`<div class="stat-card"><div class="stat-label">Total flips</div><div class="stat-val">${FLIPS.length}</div></div><div class="stat-card"><div class="stat-label">500c+ profit</div><div class="stat-val" style="color:var(--green)">${FLIPS.filter(f=>f.profit>=500).length}</div></div><div class="stat-card"><div class="stat-label">6-Link arb</div><div class="stat-val">${FLIPS.filter(f=>f.flip_type==='6-Link Spread').length}</div></div><div class="stat-card"><div class="stat-label">Showing</div><div class="stat-val">${items.length}</div></div>`;
  document.getElementById('thead').innerHTML='';document.getElementById('tbody').innerHTML='';
  const g=document.getElementById('flipGrid');
  if(!items.length){g.innerHTML='<div class="empty" style="grid-column:1/-1">No flips match</div>';return;}
  const fc={'6-Link Spread':'flip-6link','Gem Level Gap':'flip-gem','Price Gap':'flip-price'};
  g.innerHTML=items.slice(0,80).map(f=>{
    if(!proMode){
      /* Simple mode: name, buy, sell, profit, trade */
      return `<div class="flip-card"><div class="flip-header"><span class="flip-name">${esc(f.name)}</span></div><div class="flip-flow"><div class="flip-box"><div class="flip-box-label">Buy</div><div class="flip-box-val chaos-val">${fmt(f.buy_price)}c</div></div><span class="flip-arrow">&#8594;</span><div class="flip-box"><div class="flip-box-label">Sell</div><div class="flip-box-val chaos-val">${fmt(f.sell_price)}c</div></div><span class="flip-arrow">=</span><div class="flip-box flip-profit-box"><div class="flip-box-label">Profit</div><div class="flip-box-val">+${fmt(f.profit)}c</div></div></div><div class="flip-footer"><div class="trade-links"><a class="trade-link" href="${tradeUrlOfficial(f.name)}" target="_blank">Trade &#10148;</a><a class="trade-link-ninja" href="${tradeUrl(f.name,f.trade_cat)}" target="_blank">ninja</a></div></div></div>`;
    }
    const badges=[];if(f.builds&&f.builds.length)f.builds.forEach(b=>badges.push(`<span class="badge badge-build">${esc(b)}</span>`));
    return `<div class="flip-card"><div class="flip-header"><span class="flip-name">${esc(f.name)}</span><span class="flip-type-badge ${fc[f.flip_type]||'flip-price'}">${f.flip_type}</span></div><div class="flip-flow"><div class="flip-box"><div class="flip-box-label">Buy (${esc(f.buy_variant)})</div><div class="flip-box-val chaos-val">${fmt(f.buy_price)}c</div><div style="font-size:10px;color:var(--muted)">${f.buy_listings} listed</div></div><span class="flip-arrow">&#8594;</span>${f.cost>0?`<div class="flip-box"><div class="flip-box-label">Craft</div><div class="flip-box-val" style="color:var(--muted)">${fmt(f.cost)}c</div></div><span class="flip-arrow">&#8594;</span>`:''}<div class="flip-box"><div class="flip-box-label">Sell (${esc(f.sell_variant)})</div><div class="flip-box-val chaos-val">${fmt(f.sell_price)}c</div><div style="font-size:10px;color:var(--muted)">${f.sell_listings} listed</div></div><span class="flip-arrow">=</span><div class="flip-box flip-profit-box"><div class="flip-box-label">Profit</div><div class="flip-box-val">+${fmt(f.profit)}c</div></div></div><div class="flip-reason">${esc(f.reason)}</div><div class="flip-footer"><span class="risk-${f.risk||'low'}">Risk: ${(f.risk||'low').toUpperCase()}</span><span>Demand: ${f.demand||0}</span>${badges.join('')}<div class="trade-links"><a class="trade-link" href="${tradeUrlOfficial(f.name)}" target="_blank">Trade &#10148;</a><a class="trade-link-ninja" href="${tradeUrl(f.name,f.trade_cat)}" target="_blank">ninja</a></div></div></div>`;
  }).join('');
}
function renderBudget(){
  document.getElementById('thead').innerHTML='';document.getElementById('tbody').innerHTML='';document.getElementById('stats').innerHTML='';
  const a=document.getElementById('budgetArea');
  if(!a.innerHTML)a.innerHTML=`<div class="budget-input-row"><label>My budget:</label><input type="number" id="budgetAmt" value="2000" min="50" step="100" style="font-size:18px;width:120px"><span class="chaos-val" style="font-size:16px">chaos</span><button class="budget-btn" onclick="calcBudget()">Calculate Plan</button><div class="control-group" style="margin-left:12px"><label class="checkbox"><input type="checkbox" id="budgetMeta"> Meta only</label></div></div><div id="budgetResults"></div>`;
}
function calcBudget(){
  const budget=parseFloat(document.getElementById('budgetAmt').value)||2000,mo=document.getElementById('budgetMeta').checked;
  const cc={'6-link':${0},'corrupt':${0},'double_corrupt':${0},'harvest':${0},'fracture':${0},'essence':${0}};
  let cands=DATA.filter(d=>d.craft_profit>0&&d.chaos>0&&d.chaos<=budget);
  if(mo)cands=cands.filter(d=>d.builds&&d.builds.length);
  cands=cands.map(d=>{const c=cc[d.craft_method]||100;const tc=d.chaos+c;return{...d,total_cost:tc,roi:d.craft_profit/tc};}).filter(d=>d.total_cost<=budget);
  cands.sort((a,b)=>b.roi-a.roi);
  let rem=budget,plan=[],tp=0,ts=0;const used=new Set();
  for(const c of cands){if(rem<c.total_cost)continue;const k=c.name+'|'+c.type;if(used.has(k))continue;used.add(k);rem=Math.round(rem-c.total_cost);tp+=c.craft_profit;ts+=c.total_cost;plan.push(c);if(plan.length>=15)break;}
  const roi=ts>0?Math.round(tp/ts*100):0;
  const r=document.getElementById('budgetResults');
  if(!plan.length){r.innerHTML='<div class="empty">No profitable crafts found. Try increasing budget.</div>';return;}
  r.innerHTML=`<div class="budget-summary"><div class="budget-summary-item"><div class="budget-summary-label">Budget</div><div class="budget-summary-val">${fmt(budget)}c</div></div><div class="budget-summary-item"><div class="budget-summary-label">Spent</div><div class="budget-summary-val">${fmt(Math.round(ts))}c</div></div><div class="budget-summary-item"><div class="budget-summary-label">Profit</div><div class="budget-summary-val" style="color:var(--green)">+${fmt(Math.round(tp))}c</div></div><div class="budget-summary-item"><div class="budget-summary-label">ROI</div><div class="budget-summary-val">${roi}%</div></div><div class="budget-summary-item"><div class="budget-summary-label">Left</div><div class="budget-summary-val" style="color:var(--muted)">${fmt(rem)}c</div></div></div><div class="budget-plan" style="margin-top:14px">${plan.map((p,i)=>{const bg=[];if(p.builds&&p.builds.length)p.builds.forEach(b=>bg.push(`<span class="badge badge-build">${esc(b)}</span>`));return `<div class="budget-item"><div class="budget-item-left"><span class="budget-step">${i+1}</span><span class="budget-item-name">${esc(p.name)}</span><span class="craft-method-badge method-${p.craft_method}">${ML[p.craft_method]||p.craft_method}</span>${bg.join('')}</div><div class="budget-item-right"><span style="font-size:12px;color:var(--muted)">Buy: <span class="chaos-val">${fmt(p.chaos)}c</span></span><span style="font-size:12px;color:var(--muted)">${esc(p.craft_action)}</span><span class="profit-positive">+${fmt(p.craft_profit)}c</span><a class="trade-link" href="${tradeUrlOfficial(p.name)}" target="_blank">Buy &#10148;</a><a class="trade-link-ninja" href="${tradeUrl(p.name,p.trade_cat)}" target="_blank">ninja</a></div></div>`;}).join('')}</div>`;
}
function renderAlerts(){
  const af=document.getElementById('alertType').value,q=document.getElementById('alertSearch').value.toLowerCase();
  let items=DATA.filter(d=>d.alert).filter(d=>{if(af!=='all'&&d.alert!==af)return false;if(q&&!d.name.toLowerCase().includes(q))return false;return true;});
  items.sort((a,b)=>Math.abs(b.price_change||0)-Math.abs(a.price_change||0));
  const aa=DATA.filter(d=>d.alert);
  document.getElementById('alertDot').style.display=aa.length?'inline-block':'none';
  document.getElementById('stats').innerHTML=`<div class="stat-card"><div class="stat-label">Alerts</div><div class="stat-val" style="color:var(--red)">${aa.length}</div></div><div class="stat-card"><div class="stat-label">Spikes</div><div class="stat-val" style="color:var(--red)">${aa.filter(d=>d.alert==='spike').length}</div></div><div class="stat-card"><div class="stat-label">Crashes</div><div class="stat-val" style="color:var(--blue)">${aa.filter(d=>d.alert==='crash').length}</div></div><div class="stat-card"><div class="stat-label">Underpriced</div><div class="stat-val" style="color:var(--green)">${aa.filter(d=>d.alert==='underpriced').length}</div></div><div class="stat-card"><div class="stat-label">Meta Spike</div><div class="stat-val" style="color:var(--orange)">${aa.filter(d=>d.alert==='meta_spike').length}</div></div><div class="stat-card"><div class="stat-label">Corner Risk</div><div class="stat-val" style="color:var(--purple)">${aa.filter(d=>d.alert==='corner_risk').length}</div></div><div class="stat-card"><div class="stat-label">Showing</div><div class="stat-val">${items.length}</div></div>`;
  renderTable(AC,items);
  /* History section */
  let histHtml='';
  if(HISTORY&&HISTORY.length>0){
    histHtml='<div class="history-section"><h3>Snapshot History (last '+HISTORY.length+')</h3>';
    HISTORY.slice().reverse().forEach(h=>{
      const d=new Date(h.timestamp);
      const ts=d.toLocaleString();
      histHtml+=`<div class="history-item">${ts} &mdash; ${h.item_count} items tracked</div>`;
    });
    histHtml+='</div>';
  }
  document.getElementById('footerText').innerHTML=histHtml;
}

/* ══════════════════ CURRENCY EXCHANGE ══════════════════ */
function renderCurrency(){
  document.getElementById('suggestGrid').style.display='none';
  document.getElementById('flipGrid').style.display='none';
  const po=document.getElementById('currProfitOnly').checked;
  const q=(document.getElementById('currSearch').value||'').toLowerCase();
  let clist=CURRENCIES.filter(c=>{
    if(po&&c.spread<=3)return false;
    if(q&&!c.name.toLowerCase().includes(q))return false;
    return true;
  });
  clist.sort((a,b)=>b.spread-a.spread);
  const profitable=CURRENCIES.filter(c=>c.spread>3).length;
  document.getElementById('stats').innerHTML=`<div class="stat-card"><div class="stat-label">Currencies</div><div class="stat-val">${CURRENCIES.length}</div></div><div class="stat-card"><div class="stat-label">Profitable (&gt;3%)</div><div class="stat-val" style="color:var(--green)">${profitable}</div></div><div class="stat-card"><div class="stat-label">Arb Loops</div><div class="stat-val" style="color:var(--purple)">${ARB_LOOPS.length}</div></div><div class="stat-card"><div class="stat-label">Showing</div><div class="stat-val">${clist.length}</div></div>`;

  /* Currency table — show real exchange ratios */
  const cols=[{key:'name',label:'Currency'},{key:'chaos_eq',label:'Value'},{key:'display_buy',label:'Buy Rate'},{key:'display_sell',label:'Sell Rate'},{key:'spread',label:'Spread'},{key:'volume',label:'Volume'},{key:'reliable',label:''}];
  document.getElementById('thead').innerHTML='<tr>'+cols.map(c=>`<th>${c.label}</th>`).join('')+'</tr>';
  if(!clist.length){document.getElementById('tbody').innerHTML='<tr><td colspan="7" class="empty">No currencies match</td></tr>';}
  else{
    document.getElementById('tbody').innerHTML=clist.slice(0,100).map(c=>{
      const spreadColor=c.spread>5&&c.reliable==='yes'?'var(--green)':c.spread>2?'var(--yellow)':'var(--muted)';
      const reliableTag=c.reliable==='check'?'<span style="color:var(--red);font-size:10px" title="Spread looks too high — verify in-game before trading">⚠ verify</span>':'';
      return `<tr><td><strong>${esc(c.name)}</strong></td><td><span class="chaos-val">${c.chaos_eq}c</span></td><td style="font-size:12px">${esc(c.display_buy)}</td><td style="font-size:12px">${esc(c.display_sell)}</td><td><span style="color:${spreadColor};font-weight:600">${c.spread}%</span></td><td style="color:var(--muted)">${c.volume}</td><td>${reliableTag}</td></tr>`;
    }).join('');
  }

  /* Arbitrage — only reliable spreads */
  const ca=document.getElementById('currencyArea');
  ca.innerHTML='<div style="margin:1rem 0 .5rem;padding:10px 14px;background:var(--surface);border:1px solid var(--border);border-radius:8px;font-size:12px;color:var(--muted);line-height:1.6"><strong style="color:var(--yellow)">⚠ Important:</strong> poe.ninja ratios are averages, not exact listings. Always verify the actual buy/sell ratio in-game before flipping. Real spreads are tighter than shown. Look for currencies where you can buy at X:1c and sell at a lower ratio for profit.</div>';
  if(ARB_LOOPS.length>0){
    ca.innerHTML+='<h3 style="margin:1rem 0 .5rem;color:var(--accent);font-size:15px">Potential Currency Flips (verify in-game)</h3>'+ARB_LOOPS.map(l=>`<div class="arb-card"><div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px"><span class="arb-path"><strong>${esc(l.name)}</strong></span><span class="arb-profit">${l.spread.toFixed(1)}% spread</span></div><div class="arb-detail">${esc(l.desc)}</div><div style="display:flex;gap:12px;margin-top:4px;font-size:12px;color:var(--muted)"><span>Volume: ${l.volume} listings</span></div></div>`).join('');
  } else {
    ca.innerHTML+='<div class="empty" style="margin-top:1rem">No reliable currency flips found (need 2-20% spread with 5+ listings).</div>';
  }
}

/* ══════════════════ ZERO TO MIRROR ══════════════════ */
function renderZ2M(){
  document.getElementById('thead').innerHTML='';document.getElementById('tbody').innerHTML='';document.getElementById('stats').innerHTML='';
  const a=document.getElementById('z2mArea');
  const defaultBudget=DIV_RATIO>0?Math.round(DIV_RATIO):200;
  if(!a.getAttribute('data-init')){
    a.setAttribute('data-init','1');
    a.innerHTML=`<div class="z2m-input-row"><label style="font-size:13px;color:var(--muted)">Starting budget:</label><input type="number" id="z2mBudget" value="${defaultBudget}" min="1" step="100" style="font-size:18px;width:140px"><span class="chaos-val" style="font-size:16px">chaos</span><button class="budget-btn" onclick="calcZ2M()">Plan Path to Mirror</button></div>
    <div style="display:flex;flex-wrap:wrap;gap:10px;padding:10px 14px;background:var(--surface);border:1px solid var(--border);border-radius:8px;margin-bottom:1rem">
      <span style="font-size:12px;color:var(--muted);width:100%">Enable/disable strategies:</span>
      <label class="checkbox"><input type="checkbox" id="z2mFlip" checked> Flipping</label>
      <label class="checkbox"><input type="checkbox" id="z2mCraft" checked> Crafting</label>
      <label class="checkbox"><input type="checkbox" id="z2mCurrency" checked> Currency Exchange</label>
      <label class="checkbox"><input type="checkbox" id="z2mCorrupt" checked> Corruption</label>
      <label class="checkbox"><input type="checkbox" id="z2mGem" checked> Gem Leveling</label>
    </div>
    <div id="z2mResults"></div>`;
  }
}
function calcZ2M(){
  const startBudget=parseFloat(document.getElementById('z2mBudget').value)||DIV_RATIO||200;
  const mirrorPrice=MIRROR_PRICE>0?MIRROR_PRICE:50000;
  const res=document.getElementById('z2mResults');

  // Strategy toggles
  const useFlip=document.getElementById('z2mFlip').checked;
  const useCraft=document.getElementById('z2mCraft').checked;
  const useCurrency=document.getElementById('z2mCurrency').checked;
  const useCorrupt=document.getElementById('z2mCorrupt').checked;
  const useGem=document.getElementById('z2mGem').checked;

  /* Phase boundaries */
  const p1End=startBudget*2;
  const p2End=startBudget*10;
  const p3End=startBudget*50;
  const p4End=mirrorPrice;

  /* Find items for each phase */
  function findPhaseItems(minBuy,maxBuy,count){
    let candidates=[];
    /* From flips */
    if(useFlip){
      FLIPS.forEach(f=>{
        if(f.buy_price>=minBuy&&f.buy_price<=maxBuy&&f.profit>0){
          candidates.push({name:f.name,buy:f.buy_price,sell:f.sell_price,profit:f.profit,action:f.flip_type+': '+f.reason,type:'flip'});
        }
      });
    }
    /* From crafts */
    if(useCraft){
      DATA.filter(d=>d.craft_profit>0&&d.chaos>=minBuy&&d.chaos<=maxBuy&&d.craft_method!=='corrupt').forEach(d=>{
        candidates.push({name:d.name,buy:d.chaos,sell:d.chaos+d.craft_profit,profit:d.craft_profit,action:d.craft_action||d.craft_method,type:'craft'});
      });
    }
    /* From corruptions */
    if(useCorrupt){
      DATA.filter(d=>d.craft_profit>0&&d.chaos>=minBuy&&d.chaos<=maxBuy&&(d.craft_method==='corrupt'||d.craft_method==='double_corrupt')).forEach(d=>{
        candidates.push({name:d.name,buy:d.chaos,sell:d.chaos+d.craft_profit,profit:d.craft_profit,action:d.craft_action||d.craft_method,type:'corrupt'});
      });
    }
    /* From gem leveling */
    if(useGem){
      DATA.filter(d=>d.type==='SkillGem'&&d.craft_profit>0&&d.chaos>=minBuy&&d.chaos<=maxBuy).forEach(d=>{
        candidates.push({name:d.name,buy:d.chaos,sell:d.chaos+d.craft_profit,profit:d.craft_profit,action:'Level/quality gem',type:'gem'});
      });
    }
    /* From currency flips — only reliable ones with realistic spreads */
    if(useCurrency){
      CURRENCIES.filter(c=>c.spread>2&&c.spread<20&&c.reliable==='yes'&&c.chaos_eq>=0.1).forEach(c=>{
        const investAmt=Math.max(minBuy,50);
        const profitPerCycle=Math.round(investAmt*c.spread/100);
        if(profitPerCycle>0){
          candidates.push({name:c.name+' exchange',buy:investAmt,sell:investAmt+profitPerCycle,profit:profitPerCycle,action:'Buy/sell '+c.name+' ('+c.spread+'% spread, verify in-game)',type:'currency'});
        }
      });
    }
    candidates.sort((a,b)=>{
      const roiA=a.profit/a.buy;
      const roiB=b.profit/b.buy;
      return roiB-roiA;
    });
    const seen=new Set();
    const result=[];
    for(const c of candidates){
      if(seen.has(c.name))continue;
      seen.add(c.name);
      result.push(c);
      if(result.length>=count)break;
    }
    return result;
  }

  const phases=[
    {name:'Phase 1: Starter',target:`${fmt(Math.round(startBudget))}c to ${fmt(Math.round(p1End))}c`,startC:startBudget,endC:p1End,items:findPhaseItems(1,startBudget,5),desc:'Double your money with low-risk flips and crafts'},
    {name:'Phase 2: Builder',target:`${fmt(Math.round(p1End))}c to ${fmt(Math.round(p2End))}c`,startC:p1End,endC:p2End,items:findPhaseItems(Math.round(startBudget*0.5),Math.round(p1End*2),5),desc:'Scale up with 6-link flipping, bulk gem leveling, mid-tier uniques'},
    {name:'Phase 3: Investor',target:`${fmt(Math.round(p2End))}c to ${fmt(Math.round(p3End))}c`,startC:p2End,endC:p3End,items:findPhaseItems(Math.round(p1End),Math.round(p2End*2),5),desc:'High-value crafts, double corruptions, meta build item flipping'},
    {name:'Phase 4: Endgame',target:`${fmt(Math.round(p3End))}c to ${fmt(Math.round(p4End))}c (Mirror)`,startC:p3End,endC:p4End,items:findPhaseItems(Math.round(p2End),Math.round(p3End*2),5),desc:'Bulk flipping strategies, high-end crafts, final push'},
  ];

  /* Determine current phase */
  let currentPhase=0;
  if(startBudget>=p3End)currentPhase=3;
  else if(startBudget>=p2End)currentPhase=2;
  else if(startBudget>=p1End)currentPhase=1;

  const overallPct=Math.min(100,Math.round(startBudget/mirrorPrice*100*100)/100);

  let html=`<div class="z2m-overall-progress"><div class="z2m-overall-label">Progress to Mirror (${fmt(Math.round(mirrorPrice))}c)</div><div class="z2m-overall-val">${overallPct}% &mdash; ${fmt(Math.round(startBudget))}c / ${fmt(Math.round(mirrorPrice))}c</div><div class="z2m-progress" style="margin-top:8px"><div class="z2m-progress-fill" style="width:${overallPct}%"></div></div></div>`;

  phases.forEach((ph,i)=>{
    const isActive=i===currentPhase;
    const totalProfit=ph.items.reduce((s,it)=>s+it.profit,0);
    const phasePct=ph.endC>ph.startC?Math.min(100,Math.max(0,Math.round((startBudget-ph.startC)/(ph.endC-ph.startC)*100))):0;
    const phaseProgress=i<currentPhase?100:(i===currentPhase?Math.max(0,phasePct):0);

    /* Calculate cycles needed */
    const gap=ph.endC-Math.max(startBudget,ph.startC);
    const avgProfit=totalProfit>0?Math.round(totalProfit/ph.items.length):1;
    const cyclesNeeded=avgProfit>0?Math.ceil(Math.max(0,gap)/avgProfit):999;

    html+=`<div class="z2m-phase${isActive?' active-phase':''}"><div class="z2m-phase-header"><div><span class="z2m-phase-name">${ph.name}</span><span style="font-size:12px;color:var(--muted);margin-left:8px">${ph.desc}</span></div><span class="z2m-phase-target">${ph.target}</span></div><div class="z2m-progress"><div class="z2m-progress-fill" style="width:${phaseProgress}%"></div></div>`;

    if(ph.items.length>0){
      html+=ph.items.map(it=>`<div class="z2m-item"><div><span class="z2m-item-name">${esc(it.name)}</span><span class="z2m-item-detail" style="margin-left:8px">Buy at <span class="chaos-val">${fmt(it.buy)}c</span>, ${esc(it.action)}, sell for <span class="chaos-val">${fmt(it.sell)}c</span></span></div><span class="z2m-item-profit">+${fmt(it.profit)}c</span></div>`).join('');
    } else {
      html+='<div class="z2m-item"><span class="z2m-item-detail">No specific items found in this price range. Try manual trading or bulk strategies.</span></div>';
    }

    html+=`<div class="z2m-summary"><span>Start: <strong class="chaos-val">${fmt(Math.round(ph.startC))}c</strong></span><span>End: <strong class="chaos-val">${fmt(Math.round(ph.endC))}c</strong></span><span>Expected profit/cycle: <strong class="profit-positive">+${fmt(totalProfit)}c</strong></span><span>Est. cycles: <strong>${cyclesNeeded}</strong></span></div></div>`;
  });

  /* Final note */
  const remainingGap=Math.max(0,mirrorPrice-startBudget);
  const avgAllProfit=phases.reduce((s,p)=>s+p.items.reduce((s2,it)=>s2+it.profit,0),0);
  const totalCycles=avgAllProfit>0?Math.ceil(remainingGap/(avgAllProfit/4)):999;
  html+=`<div style="margin-top:1rem;padding:1rem;background:var(--surface);border:1px solid var(--border);border-radius:8px;font-size:13px;color:var(--muted)"><strong style="color:var(--accent)">Summary:</strong> You need <strong class="chaos-val">${fmt(Math.round(remainingGap))}c</strong> more to reach a Mirror. At an average of ~${fmt(Math.round(avgAllProfit/4))}c profit per cycle across all phases, you need roughly <strong>${totalCycles}</strong> more trade cycles. Good luck, Exile!</div>`;

  res.innerHTML=html;
}

function renderWhale(){
  const sf=document.getElementById('whaleStrategy').value;
  const tf=document.getElementById('whaleTag').value;
  const mc=parseFloat(document.getElementById('whaleMaxCost').value)||99999;
  const ml=parseInt(document.getElementById('whaleMaxList').value)||999;
  const co=document.getElementById('whaleCornerable').checked;
  const q=document.getElementById('whaleSearch').value.toLowerCase();

  // Map strategy to tag
  const stratTags={corner:'flipping','6link_flip':'flipping',gem_level:'leveling',double_corrupt:'corruption',vaal_corrupt:'corruption',tainted_chaos_jewels:'corruption',harvest_fracture:'crafting',essence_craft:'crafting'};

  let items=WHALES.filter(w=>{
    if(sf!=='all'){
      if(!w.strategies.some(s=>s.id===sf))return false;
    }
    if(tf!=='all'){
      const matching=WHALE_STRATS.filter(s=>s.tag===tf).map(s=>s.id);
      if(!w.strategies.some(s=>matching.includes(s.id)))return false;
    }
    if(w.best_cost>mc)return false;
    if(w.listings>ml)return false;
    if(co&&w.corner_score<=0)return false;
    if(q&&!w.name.toLowerCase().includes(q))return false;
    return true;
  });

  const total=WHALES.length;
  const cornerable=WHALES.filter(w=>w.corner_score>0).length;
  const highP=items.filter(w=>w.best_profit>=500).length;

  document.getElementById('stats').innerHTML=`
    <div class="stat-card"><div class="stat-label">Whale Targets</div><div class="stat-val">${total}</div></div>
    <div class="stat-card"><div class="stat-label">Cornerable</div><div class="stat-val" style="color:var(--purple)">${cornerable}</div></div>
    <div class="stat-card"><div class="stat-label">500c+ Profit</div><div class="stat-val" style="color:var(--green)">${highP}</div></div>
    <div class="stat-card"><div class="stat-label">Showing</div><div class="stat-val">${items.length}</div></div>`;

  document.getElementById('thead').innerHTML='';document.getElementById('tbody').innerHTML='';
  const g=document.getElementById('whaleGrid');
  if(!items.length){g.innerHTML='<div class="empty" style="grid-column:1/-1">No whale targets match filters</div>';return;}

  const stratColors={corner:'var(--purple)','6link_flip':'var(--green)',gem_level:'var(--blue)',double_corrupt:'var(--red)',vaal_corrupt:'var(--red)',tainted_chaos_jewels:'var(--orange)',harvest_fracture:'var(--green)',essence_craft:'var(--yellow)'};
  const stratNames={corner:'Corner Supply','6link_flip':'6-Link Flip',gem_level:'Gem Level',double_corrupt:'Double Corrupt',vaal_corrupt:'Vaal Corrupt',tainted_chaos_jewels:'Tainted Chaos',harvest_fracture:'Harvest Fracture',essence_craft:'Essence Craft'};

  g.innerHTML=items.slice(0,60).map(w=>{
    const badges=[];
    if(w.builds&&w.builds.length)w.builds.forEach(b=>badges.push(`<span class="badge badge-build">${esc(b)}</span>`));

    // Corner score bar
    const cornerHtml=w.corner_score>0?`<div style="display:flex;align-items:center;gap:6px;margin:6px 0"><span style="font-size:11px;color:var(--purple);font-weight:600">Corner Score: ${w.corner_score}/100</span><div style="width:80px;height:5px;background:var(--border);border-radius:3px;overflow:hidden"><div style="height:100%;width:${w.corner_score}%;background:var(--purple);border-radius:3px"></div></div></div>`:'';

    // Strategy pills
    const stratPills=w.strategies.map(s=>`<span style="display:inline-block;font-size:10px;font-weight:600;padding:2px 8px;border-radius:4px;margin:2px;background:${stratColors[s.id]||'var(--muted)'}20;color:${stratColors[s.id]||'var(--muted)'};border:1px solid ${stratColors[s.id]||'var(--muted)'}40">${stratNames[s.id]||s.id} +${fmt(s.profit)}c</span>`).join('');

    // Listings warning + confidence
    const listColor=w.listings<=3?'var(--red)':w.listings<=10?'var(--yellow)':'var(--muted)';
    const listWarn=w.listings<=5?'<span style="font-size:10px;color:var(--red);font-weight:600"> LOW SUPPLY</span>':'';
    const cf=w.confidence||95;
    const confHtml=cf<=50?`<div style="display:flex;align-items:center;gap:4px;margin:2px 0"><span style="font-size:10px;color:${confColor(cf)};font-weight:600">${confLabel(cf)} price</span><div class="conf-bar"><div class="conf-fill" style="width:${cf}%;background:${confColor(cf)}"></div></div></div>`:'';

    // Why this item
    const reasonHtml=w.item_reason?`<div style="font-size:11px;color:var(--blue);margin-bottom:6px;padding:4px 8px;background:var(--blue)10;border-radius:4px;border-left:3px solid var(--blue)">${esc(w.item_reason)}</div>`:'';

    return `<div class="flip-card" style="border-color:${w.corner_score>50?'var(--purple)':'var(--border)'}">
      <div class="flip-header">
        <span class="flip-name">${esc(w.name)}${w.variant?` <span style="font-size:11px;color:var(--muted);font-weight:400">(${esc(w.variant)})</span>`:''}</span>
        <span class="tier-badge" style="color:${w.tier_color};border-color:${w.tier_color}30;background:${w.tier_color}18">${esc(w.tier_label)}</span>
      </div>
      <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:6px">
        <span class="chaos-val" style="font-size:16px">${fmt(w.chaos)}c</span>${cf<=25?'<span style="font-size:10px;color:var(--red);font-weight:600" title="Very few listings on poe.ninja — price may not reflect actual market"> ⚠</span>':''}
        <span style="font-size:12px;color:${listColor};font-weight:600" title="Approximate count from poe.ninja — check trade site for real listings">~${w.listings} listed${listWarn}</span>
        <span style="font-size:12px;color:var(--muted)">${TL[w.type]||w.type}</span>
        ${badges.join('')}
      </div>
      ${confHtml}
      ${reasonHtml}
      ${cornerHtml}
      <div style="margin:8px 0;padding:8px 10px;background:var(--surface2);border-radius:6px;border:1px solid var(--border)">
        <div style="font-size:11px;color:var(--accent);font-weight:600;margin-bottom:4px;text-transform:uppercase;letter-spacing:.5px">Best Strategy: ${stratNames[w.best_strategy]||w.best_strategy}</div>
        <div style="font-size:12px;color:var(--text);line-height:1.5">${esc(w.best_detail)}</div>
        <div style="display:flex;align-items:center;gap:12px;margin-top:6px">
          <span style="font-size:11px;color:var(--muted)">Cost: <span class="chaos-val">${fmt(w.best_cost)}c</span></span>
          <span style="font-size:11px;color:var(--muted)">Expected: <span class="profit-${w.best_profit>=500?'high':'positive'}">+${fmt(w.best_profit)}c</span></span>
        </div>
      </div>
      ${w.strategies.length>1?`<div style="margin-top:6px"><span style="font-size:10px;color:var(--muted)">Also viable:</span> ${stratPills}</div>`:''}
      <div style="margin-top:8px;display:flex;gap:6px;align-items:center"><a class="trade-link" href="${tradeUrlOfficial(w.name)}" target="_blank">Trade ➜</a><a class="trade-link-ninja" href="${tradeUrl(w.name,w.trade_cat)}" target="_blank">ninja</a></div>
    </div>`;
  }).join('');
}

function renderGuide(){
  document.getElementById('stats').innerHTML='';document.getElementById('thead').innerHTML='';document.getElementById('tbody').innerHTML='';
  document.getElementById('guideArea').innerHTML=`<div class="guide-wrap">
  <div class="guide-section"><div class="guide-summary"><strong>Tools &amp; Resources</strong> &mdash; Everything you need to make currency in PoE, all in one place.</div></div>
  ${[
    ['Essential Tools','<ul><li><strong>Awakened PoE Trade</strong> &mdash; in-game price checking overlay (Ctrl+D on items). Get it at: <a href="https://snosme.github.io/awakened-poe-trade" target="_blank" style="color:var(--blue)">snosme.github.io/awakened-poe-trade</a></li><li><strong>poe.ninja</strong> &mdash; real-time market data (you\'re looking at it). API-powered. <a href="https://poe.ninja" target="_blank" style="color:var(--blue)">poe.ninja</a></li><li><strong>Craft of Exile</strong> &mdash; simulate crafts before spending currency. <a href="https://craftofexile.com" target="_blank" style="color:var(--blue)">craftofexile.com</a></li><li><strong>Wealthy Exile</strong> &mdash; wealth tracking, chaos/hour, stash breakdowns. <a href="https://wealthyexile.com" target="_blank" style="color:var(--blue)">wealthyexile.com</a></li><li><strong>Exilence Next</strong> &mdash; net worth tracker, profit tracking per session.</li></ul>'],
    ['Currency Making Methods','<ul><li><strong>Bulk Trading:</strong> Buy essences/scarabs/fossils cheap in small quantities, sell in bulk for 20-40% premium.</li><li><strong>Currency Flipping:</strong> Buy/sell same currency to different players. Use this dashboard\'s Currency tab to find spreads.</li><li><strong>Boss Farming:</strong> Farm specific bosses for guaranteed drops. Maven, Sirus, Uber Elder.</li><li><strong>Crafting Services:</strong> Use Craft of Exile to plan, offer services in trade chat.</li><li><strong>Vendor Recipes:</strong> Full rare set (ilvl 60-74) = 1 chaos. Unidentified = 2 chaos.</li><li><strong>Lab Running:</strong> Enchant popular helmets, sell for premium.</li><li><strong>Heist:</strong> Run grand heists for raw currency and unique drops.</li><li><strong>Div Card Investing:</strong> Buy incomplete sets below completion value.</li></ul>'],
    ['Pro Tips','<ul><li>Always check poe.ninja 7-day trend before buying.</li><li>Use Awakened PoE Trade for instant in-game price checks.</li><li>Track your chaos/hour with Wealthy Exile or Exilence.</li><li>This dashboard works best when run morning + evening for alert coverage.</li><li>Start with the Budget Planner to get a focused plan before trading.</li></ul>'],
    ['Price Tiers','<span class="guide-color" style="background:#888"></span>Under 1 div = base material. <span class="guide-color" style="background:#5b9bd5"></span>1-3 div = cheap targets. <span class="guide-color" style="background:#4CAF82"></span>3-6 div = mid profit zone. <span class="guide-color" style="background:#d4a017"></span>6-10 div = solid. <span class="guide-color" style="background:#e08833"></span>11-15 div = high value. <span class="guide-color" style="background:#e05555"></span>15+ div = chase items.'],
    ['Meta Builds','<span class="badge badge-build">PC PF</span> Poisonous Concoction PF, <span class="badge badge-build">LA DE</span> Lightning Arrow DE, <span class="badge badge-build">GC Mine</span> Glacial Cascade Miner, <span class="badge badge-build">RF Chief</span> Righteous Fire Chief, <span class="badge badge-build">CWS Chief</span> CWS Chieftain, <span class="badge badge-build">Bleed Glad</span> Bleed Bow Glad. Items for these builds get blue badges and higher demand.'],
    ['Alert Types','<ul><li><span class="badge-alert alert-spike">SPIKE</span> = +25% price increase.</li><li><span class="badge-alert alert-crash">CRASH</span> = -25% price drop.</li><li><span class="badge-alert alert-drying">DRYING</span> = listings dropping fast.</li><li><span class="badge-alert alert-flood">FLOOD</span> = listings surging.</li><li><span class="badge-alert alert-new">NEW</span> = new item appeared.</li><li><span class="badge-alert alert-underpriced">UNDERPRICED</span> = &gt;30% below median + high demand. Best buy signal.</li><li><span class="badge-alert alert-meta_spike">META SPIKE</span> = meta build item with rising price.</li><li><span class="badge-alert alert-corner_risk">CORNER RISK</span> = supply collapsed, possible market manipulation.</li></ul>'],
    ['Workflow','1. Run script before session. 2. Check Alerts for changes. 3. Check Flip Finder for quick wins. 4. Check Currency tab for exchange profits. 5. Budget Planner for craft plan. 6. Use Zero to Mirror for long-term goals. 7. Click Trade links to buy. 8. Run again after session.'],
  ].map(([t,b])=>`<div class="guide-section"><div class="guide-header" onclick="this.nextElementSibling.classList.toggle('open');this.querySelector('.guide-arrow').classList.toggle('open')"><h2>${t}</h2><span class="guide-arrow">&#9660;</span></div><div class="guide-body"><p>${b}</p></div></div>`).join('')}
  </div>`;
}

function renderTable(cols,items){
  document.getElementById('thead').innerHTML='<tr>'+cols.map(c=>{const a=sortKey===c.key?(sortDir===-1?' \u2193':' \u2191'):'';return `<th class="${sortKey===c.key?'sorted':''}" onclick="setSort('${c.key}')">${c.label}${a}</th>`;}).join('')+'</tr>';
  if(!items.length){document.getElementById('tbody').innerHTML=`<tr><td colspan="${cols.length}" class="empty">No items match</td></tr>`;return;}
  document.getElementById('tbody').innerHTML=items.slice(0,200).map(r=>'<tr>'+cols.map(c=>`<td>${fmtCell(c.fmt,r[c.key],r)}</td>`).join('')+'</tr>').join('');
}
function setSort(k){if(k==='_t')return;if(sortKey===k)sortDir*=-1;else{sortKey=k;sortDir=-1;}render();}
if(DATA.some(d=>d.alert))document.getElementById('alertDot').style.display='inline-block';
toggleHint('economy');
buildTabs();render();
</script></body></html>
"""


def main():
    print(f"\n{'='*60}")
    print(f"  PoE Mirage Economy Dashboard v5 (all chaos)")
    print(f"{'='*60}")
    print(f"Fetching data from poe.ninja...\n")

    div_ratio = fetch_divine_ratio()
    if div_ratio:
        print(f"  -> Divine Orb = {div_ratio}c")
    else:
        div_ratio = 200
        print(f"  -> Fallback: {div_ratio}c")

    init_craft_costs(div_ratio)

    # First pass: fetch all raw data for price lookup
    raw_by_type = {}
    for type_key, type_label in ITEM_TYPES:
        try:
            raw_by_type[type_key] = fetch(type_key)
            print(f"  -> {len(raw_by_type[type_key])} raw items for {type_label}")
        except Exception as e:
            print(f"  !! Failed {type_label}: {e}")
            raw_by_type[type_key] = []

    # Build price lookup from ALL data before craft suggestions
    build_price_lookup(raw_by_type)
    print(f"  -> Price lookup: {sum(len(v) for v in PRICE_LOOKUP.values())} entries "
          f"for {len(PRICE_LOOKUP)} unique items")

    # Second pass: build rows (craft suggestions now use real prices)
    all_rows = []
    for type_key, type_label in ITEM_TYPES:
        try:
            rows = build_rows(raw_by_type[type_key], type_key, div_ratio)
            all_rows.extend(rows)
        except Exception as e:
            print(f"  !! Failed building rows for {type_label}: {e}")

    compute_underpriced(all_rows)
    prev_data = load_previous_data()
    prev_ts = prev_data.get("timestamp", "never")
    alert_count = compute_alerts(all_rows, prev_data)
    save_current_data(all_rows)
    flips = find_flips(all_rows)

    # Fetch currency data
    currencies, arb_loops = fetch_all_currencies()
    print(f"  -> {len(currencies)} currencies, {len(arb_loops)} arbitrage loops")

    # Fetch mirror price
    mirror_price = fetch_mirror_price()
    if mirror_price:
        print(f"  -> Mirror = {mirror_price}c")
    else:
        mirror_price = 50000
        print(f"  -> Mirror fallback: {mirror_price}c")

    # Whale mode
    whale_targets = find_whale_targets(all_rows, div_ratio)
    whale_cornerable = sum(1 for w in whale_targets if w["corner_score"] > 0)

    craft_count = sum(1 for r in all_rows if r["craft_method"])
    meta_count = sum(1 for r in all_rows if r["builds"])
    under_count = sum(1 for r in all_rows if r.get("underpriced", 0) > 0)

    print(f"\n  Total: {len(all_rows)} | Craftable: {craft_count} | Meta: {meta_count}")
    print(f"  Underpriced: {under_count} | Flips: {len(flips)} | Alerts: {alert_count}")
    print(f"  Whale targets: {len(whale_targets)} | Cornerable: {whale_cornerable}")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    prev_status = f"vs {prev_ts[:16]}" if prev_ts != "never" else "First run"

    # Inject craft costs into budget planner JS
    html = HTML_TEMPLATE
    for k, v in CRAFT_COSTS_CHAOS.items():
        html = html.replace(f"'{k}':" + "${0}", f"'{k}':{v}")
    html = html.replace("ALL_DATA_JSON", json.dumps(all_rows))
    html = html.replace("ALL_FLIPS_JSON", json.dumps(flips))
    html = html.replace("ALL_WHALE_JSON", json.dumps(whale_targets))
    html = html.replace("ALL_STRATS_JSON", json.dumps(WHALE_STRATEGIES))
    html = html.replace("ALL_CURRENCY_JSON", json.dumps(currencies))
    html = html.replace("ALL_ARB_JSON", json.dumps(arb_loops))
    history_list = get_history_list()
    html = html.replace("ALL_HISTORY_JSON", json.dumps(history_list))
    html = html.replace("MIRROR_PRICE_NUM", str(mirror_price))
    html = html.replace("DIV_RATIO_VALUE", str(div_ratio))
    html = html.replace("DIV_RATIO_NUM", str(div_ratio))
    html = html.replace("SERVE_MODE_FLAG", "false")
    html = html.replace("PREV_STATUS", prev_status)
    html = html.replace("TIMESTAMP", timestamp)
    html = html.replace("LEAGUE_NAME", LEAGUE)

    with open("poe_dashboard.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n  -> poe_dashboard.html")
    print(f"  -> {os.path.abspath('poe_dashboard.html')}\n")


def generate_html(serve_mode=False):
    """Run main() and return the generated HTML string."""
    main()
    with open("poe_dashboard.html", "r", encoding="utf-8") as f:
        html = f.read()
    if serve_mode:
        # main() set it to false, flip it to true for serve mode
        html = html.replace("const SERVE_MODE=false", "const SERVE_MODE=true")
    return html


def serve():
    """Start a local HTTP server with live refresh."""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import webbrowser

    PORT = 5000
    html_cache = {"html": ""}

    def rebuild():
        print("\n  Rebuilding dashboard...\n")
        html_cache["html"] = generate_html(serve_mode=True)
        print(f"  Server running at http://localhost:{PORT}\n")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/refresh":
                try:
                    rebuild()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain")
                    self.end_headers()
                    self.wfile.write(b"OK")
                except Exception as e:
                    self.send_response(500)
                    self.send_header("Content-Type", "text/plain")
                    self.end_headers()
                    self.wfile.write(str(e).encode())
            else:
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html_cache["html"].encode("utf-8"))

        def log_message(self, format, *args):
            pass  # Suppress request logs

    # Initial build
    rebuild()

    server = HTTPServer(("localhost", PORT), Handler)
    print(f"  ================================================")
    print(f"  PoE Dashboard LIVE at http://localhost:{PORT}")
    print(f"  Click 'Refresh Data' in the page to re-fetch")
    print(f"  Press Ctrl+C to stop")
    print(f"  ================================================\n")

    webbrowser.open(f"http://localhost:{PORT}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")
        server.server_close()


if __name__ == "__main__":
    if "--serve" in sys.argv:
        serve()
    else:
        main()
