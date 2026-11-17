"""The answers of ``text_search()``: request checks, word matching and match order (api3 043 to 045).

Pure functions. The caller filters the rows per type and passes them as match dicts.
"""

import re

from shotgun_api3 import Fault

from .fields import ruby_pp

DEFAULT_LIMIT = 25  # api3 043: max_results None answers 25 rows
_METHOD = "API query_display_name_cache() "


def check_request(params, entity_types):
    """Raise the Fault the site answers for a bad ``query_display_name_cache`` request (api3 045)."""
    text = params["text"]
    if text is None:
        raise Fault(_METHOD + "'text' missing:\n" + ruby_pp(params))
    if not isinstance(text, str) or len(text) < 3:
        # The length is checked on the text as sent, spaces included.
        raise Fault(_METHOD + "query text too short! must be 3 or more characters :\n" + ruby_pp(params))
    for entity_type in params["entity_types"]:
        if entity_type not in entity_types:
            raise Fault(_METHOD + "invalid entity type. Found: %s" % entity_type)
    if not isinstance(params["project_ids"], list):
        raise Fault("Uncaught exception! undefined method 'collect' for an instance of %s"
                    % type(params["project_ids"]).__name__.replace("int", "Integer"))


def row_limit(max_results):
    """The number of matches ``max_results`` allows, read the way the site reads it (api3 043, 045)."""
    if max_results is None:
        return DEFAULT_LIMIT
    if isinstance(max_results, str):
        digits = re.match(r"\s*-?\d+", max_results)  # Ruby's to_i: leading digits, else 0
        max_results = int(digits.group()) if digits else 0
    if max_results < 0:
        raise Fault("Uncaught exception! PG::InvalidRowCountInLimitClause: ERROR:  LIMIT must not be negative")
    return max_results


def terms(text):
    """The words of ``text``, split on whitespace and lowercased."""
    return text.lower().split()


def match_kind(words, name, linked_name):
    """``"own"`` when the row's name holds every word, ``"link"`` when each word is in it or the linked name.

    A word matches as a case-insensitive substring (finding 053, api3 044).
    """
    if not words:
        return None
    name, linked_name = (name or "").lower(), (linked_name or "").lower()
    if all(w in name for w in words):
        return "own"
    if all(w in name or w in linked_name for w in words):
        return "link"
    return None


def search(text, rows, max_results):
    """The ``{"matches", "terms"}`` answer over ``rows``, each a match dict as the site returns one.

    Rows whose own name matches come first, then rows matched through their link, each part shortest name
    first (api3 043). Ties of equal length go by type and id; the site's tie order was not recorded.
    """
    words = terms(text)
    found = []
    for row in rows:
        kind = match_kind(words, row["name"], row["links"][1])
        if kind:
            found.append((0 if kind == "own" else 1, len(row["name"] or ""), row["type"], row["id"], row))
    found.sort(key=lambda f: f[:4])
    return {"matches": [f[4] for f in found[:row_limit(max_results)]], "terms": words}
