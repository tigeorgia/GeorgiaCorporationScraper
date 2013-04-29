import difflib
import terms
# Every checker returns a value 0 - 1, or None if a judgment couldn't
# be made.

def check_id(string):
    """ Runs a basic check for things that look like ID numbers.
    Currently, simply checks to see that numerals outnumber
    other types of characters."""
    if len(string) == 0:
        return 0
    count = 0.0
    for c in string:
        if c.isdigit():
            count += 1
    if count / len(string) > 0.5:
        return count/len(string)
    else:
        return None

def check_position(string):
    """ Checks to see if the string looks like a position in a company."""
    positions = terms.positions
    
    best_match = 0
    for p in positions:
        ratio = _find_similarity(string,p)
        if ratio > best_match:
            best_match = ratio
    if best_match > 0.8: 
        return best_match
    else:
        return None

def check_nationality(string):
    """ Checks to see if the string looks like an indicator of nationality."""

    nationalities = terms.nationalities
    demonyms = terms.demonyms

    if len(string) == 0:
        return 0

    best_match = 0
    for n in nationalities:
        ratio = _find_similarity(string,n)
        if ratio > best_match:
            best_match = ratio
    
    for d in demonyms:
        ratio = _find_similarity(string,d)
        if ratio > best_match:
            best_match = ratio

    if best_match >= 0.85:
        return best_match

    else: # Do a word-by-word search, but with more stringent matching
        strings = string.split()
        count = 0.0
        if _find_similarity(string, u"რესპუბლიკა") > 0.75:
            count += 1
        for s in strings:
            if s in nationalities or s in demonyms:
                count += 1
        best_match = count / len(strings)

    if best_match == 0:
        return None
    else:
        return best_match

def check_name(string):
    """ Check whether a string appears to be a name."""
    # Skipping this, for now.
    if u"http://" or u"რესპუბლიკა" in string:
        return 0.0
    return 0.25

def _find_similarity(string1,string2):
    return difflib.SequenceMatcher(None,string1,string2,autojunk=False).ratio()
