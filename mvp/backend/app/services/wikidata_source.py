from app.services.http_utils import get_with_retry

_API = "https://www.wikidata.org/w/api.php"

# Property ids worth pulling for the MVP's environment/relationship context.
RELEVANT_PROPERTIES = {
    "P569": "birth_date",
    "P570": "death_date",
    "P19": "birth_place",
    "P20": "death_place",
    "P106": "occupation",
    "P26": "spouse",
    "P69": "educated_at",
    "P108": "employer",
    "P737": "influenced_by",
    "P800": "notable_work",
    "P463": "member_of",
}


async def search_entity(name: str) -> str | None:
    params = {
        "action": "wbsearchentities",
        "search": name,
        "language": "en",
        "format": "json",
        "type": "item",
        "limit": "1",
    }
    resp = await get_with_retry(_API, params=params)
    results = resp.json().get("search", [])
    return results[0]["id"] if results else None


async def fetch_entity_facts(qid: str) -> dict:
    """Returns {friendly_property_name: [{time|value|qid, label?}]}."""
    params = {
        "action": "wbgetentities",
        "ids": qid,
        "languages": "en",
        "format": "json",
        "props": "claims",
    }
    resp = await get_with_retry(_API, params=params)
    entity = resp.json()["entities"][qid]
    claims = entity.get("claims", {})

    facts: dict[str, list[dict]] = {}
    referenced_qids: set[str] = set()

    for pid, label in RELEVANT_PROPERTIES.items():
        parsed = []
        for value in claims.get(pid, []):
            datavalue = value.get("mainsnak", {}).get("datavalue", {})
            dtype = datavalue.get("type")
            if dtype == "wikibase-entityid":
                ref_qid = datavalue["value"]["id"]
                referenced_qids.add(ref_qid)
                parsed.append({"qid": ref_qid})
            elif dtype == "time":
                parsed.append({"time": datavalue["value"]["time"]})
            elif dtype == "string":
                parsed.append({"value": datavalue["value"]})
        if parsed:
            facts[label] = parsed

    if referenced_qids:
        labels = await _resolve_labels(referenced_qids)
        for values in facts.values():
            for item in values:
                if "qid" in item:
                    item["label"] = labels.get(item["qid"], item["qid"])

    return facts


async def _resolve_labels(qids: set[str]) -> dict[str, str]:
    # wbgetentities accepts up to 50 ids per call — plenty for MVP scope.
    params = {
        "action": "wbgetentities",
        "ids": "|".join(list(qids)[:50]),
        "languages": "en",
        "format": "json",
        "props": "labels",
    }
    resp = await get_with_retry(_API, params=params)
    entities = resp.json().get("entities", {})
    return {
        qid: entities.get(qid, {}).get("labels", {}).get("en", {}).get("value", qid)
        for qid in qids
    }
