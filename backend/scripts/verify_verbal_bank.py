# -*- coding: utf-8 -*-
"""Independent structural/rule-based verifier for the verbal topic in
mcq_static_bank. Run manually after adding a new verbal batch:

    python scripts/verify_verbal_bank.py

Vocabulary questions (synonyms/antonyms/idioms/one-word-substitution) have no
computable ground truth, so this does NOT attempt to verify word meanings.
It checks the two verbal subtypes that ARE mechanically checkable, independent
of whatever generated them:

  1. Grammar ("Identify the grammatically correct sentence:") -- flags known-
     invalid English constructions (e.g. "has working" instead of "has been
     working", doubled words, two auxiliary verbs in a row). This is the
     exact bug class that produced real errors in an early batch (caught via
     a Groq blind-solve disagreement, then traced to this root cause).

  2. Reading comprehension -- checks that the correct answer's key terms
     (including numbers/dates) actually appear in the passage, and that no
     wrong option is MORE supported by the passage than the correct answer.
     Handles "which is NOT mentioned / except" question framing, where the
     expected overlap direction inverts.

Any flagged item needs manual review -- this catches likely defects, it
doesn't replace judgment (see the false positives from the first version:
numeric-only answers not counted as keywords, and negation questions read
the same way as normal ones -- both fixed here, but keep an eye for new edge
cases as more question shapes get added).
"""
import re, os
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
import pymongo

client = pymongo.MongoClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]

# ---- Check 1: known-invalid English construction patterns ------------------
INVALID_PATTERNS = [
    (re.compile(r"\b(has|have|had)\s+(\w+ing)\b", re.IGNORECASE),
     "'{0} {1}' -- has/have/had directly followed by an -ing form is invalid without 'been' (e.g. 'has been working', not 'has working')"),
    (re.compile(r"\b(is|are|was|were)\s+(\w+ing)\s+\w+ing\b", re.IGNORECASE),
     "double -ing construction, likely malformed"),
    (re.compile(r"\b(\w+)\s+\1\b", re.IGNORECASE),
     "doubled word: '{0} {0}'"),
    (re.compile(r"\b(is|are|was|were|has|have|had)\s+(is|are|was|were|has|have|had)\b", re.IGNORECASE),
     "two auxiliary/copula verbs in a row -- malformed"),
]

def check_invalid_patterns(sentence):
    issues = []
    for rx, msg_template in INVALID_PATTERNS:
        for m in rx.finditer(sentence):
            groups = m.groups()
            try:
                msg = msg_template.format(*groups)
            except Exception:
                msg = msg_template
            issues.append(msg)
    return issues

# ---- Check 1b: subject-verb agreement, independent of surface malformation -
# The regex checks above only catch surface malformation (e.g. "has working").
# They cannot catch SVA items' actual error type -- the wrong options are
# syntactically well-formed sentences with the WRONG verb NUMBER (e.g. "A pair
# of shoes were left..." is fluent English, just wrong because "pair" is the
# true grammatical head, not "shoes"). Catching that requires classifying the
# subject phrase and knowing the expected verb number independently of the
# generator -- so this hardcodes the small, closed set of subject categories
# these questions are actually authored from (they always test one of these
# "looks plural, functions as singular" exceptions) and checks the stored
# correct/wrong verbs against that independent classification.

# Single words that look plural (end in -s) but are always grammatically
# singular -- academic-discipline names (Economics, Physics), and other fixed
# exceptions like disease names (Mumps, Measles) and mass nouns (News).
SINGULAR_DISCIPLINE_WORDS = {
    "economics", "civics", "physics", "mathematics", "ethics", "statistics",
    "athletics", "politics", "aesthetics", "genetics", "linguistics",
    "aerobics", "acoustics", "mumps", "measles", "rabies", "news", "mechanics",
    "robotics", "logistics",
}
# Nouns that make a "<noun> of <plural>" or bare "the <noun>" subject phrase
# grammatically singular (the verb agrees with this noun, not what follows).
QUANTIFIER_OR_COLLECTIVE_SINGULAR_NOUNS = {
    "pair", "bunch", "herd", "pack", "flock", "series", "number", "group",
    "crew", "jury", "committee", "council", "army", "staff", "audience",
    "team", "panel", "board", "cabinet", "class", "swarm", "regiment",
    "faculty", "orchestra", "battalion", "senate", "litter", "choir",
    "squadron", "colony", "gaggle", "troupe", "parliament", "bevy",
    "infantry", "troop", "delegation", "flotilla", "union",
    "clientele", "platoon", "cluster", "management", "convoy",
    "brigade", "shoal",
}
# NOTE: "clergy" (like "police", "people", "cattle") is a plural-only
# collective -- it refers to an aggregate of individuals with no "acting as
# one unit" sense, and always takes a plural verb ("The clergy were...", not
# "was"). Deliberately NOT included above alongside jury/committee/team/etc.,
# which genuinely can be singular when acting as one decision-making unit.
VERB_PAIRS = [{"is", "are"}, {"was", "were"}, {"has", "have"}]
NUMBER_WORDS = {
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "twenty",
    "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety",
    "dozen", "hundred", "thousand",
}

def classify_subject_expects_singular(subject_words):
    words = [w.lower() for w in subject_words]
    if len(words) == 1 and words[0] in SINGULAR_DISCIPLINE_WORDS:
        return True
    if words and (words[0] in NUMBER_WORDS or re.match(r"^\d+$", words[0])):
        return True
    if len(words) >= 2 and words[0] in ("neither", "each", "either") and words[1] == "of":
        return True
    if "of" in words:
        of_idx = words.index("of")
        quant_word = words[of_idx - 1] if of_idx > 0 else None
        if quant_word in QUANTIFIER_OR_COLLECTIVE_SINGULAR_NOUNS:
            return True
    elif words and words[-1] in QUANTIFIER_OR_COLLECTIVE_SINGULAR_NOUNS:
        return True
    return None  # subject phrase doesn't match a known category -- skip, don't guess

def find_shared_subject_and_verbs(options):
    """If all 4 options share a leading subject phrase followed by a
    copula/auxiliary verb (the SVA question shape), return
    (subject_words, {option_index: verb}, matched_verb_pair). Else None."""
    tokenized = [o.split() for o in options]
    min_len = min(len(t) for t in tokenized)
    common_len = 0
    for i in range(min_len):
        if len({t[i].lower() for t in tokenized}) == 1:
            common_len = i + 1
        else:
            break
    if common_len == 0 or common_len >= min_len:
        return None
    verbs = {}
    for i, t in enumerate(tokenized):
        verbs[i] = t[common_len].lower().strip(".,")
    verb_set = set(verbs.values())
    matched_pair = next((vp for vp in VERB_PAIRS if verb_set <= vp), None)
    if not matched_pair or len(verb_set) < 2:
        return None
    return tokenized[0][:common_len], verbs, matched_pair

def check_sva_agreement(options, correct_index):
    found = find_shared_subject_and_verbs(options)
    if found is None:
        return []
    subject_words, verbs, verb_pair = found
    expects_singular = classify_subject_expects_singular(subject_words)
    if expects_singular is None:
        return []
    singular_verb = "is" if "is" in verb_pair else ("was" if "was" in verb_pair else "has")
    plural_verb = (verb_pair - {singular_verb}).pop()
    expected_verb = singular_verb if expects_singular else plural_verb
    issues = []
    subject_str = " ".join(subject_words)
    for i, v in verbs.items():
        should_be_expected = (i == correct_index)
        is_expected = (v == expected_verb)
        if should_be_expected and not is_expected:
            issues.append(f"CORRECT option uses '{v}' but subject '{subject_str}' should take '{expected_verb}'")
        if not should_be_expected and is_expected:
            issues.append(f"WRONG option (index {i}) uses '{v}', which matches the correctly-agreeing verb for subject '{subject_str}' -- likely an ambiguous/duplicate answer")
    return issues

# ---- Check 2: reading comprehension answer/passage entailment --------------
STOPWORDS = {"the","a","an","is","are","was","were","in","on","at","to","of","and","or",
             "that","this","these","those","it","its","for","with","by","from","as","be",
             "has","have","had","not","no","did","does","do","which","what","who","how"}

# Question framings where the CORRECT answer is the one NOT supported by the
# passage (an exception/negation question) -- the overlap direction inverts.
# Deliberately narrower than a bare `\bnot\b`: a normal question can legitimately
# contain "not" while restating passage content (e.g. "...illustrate that X is
# not universal?"), which isn't an exception-question and shouldn't invert the
# expected direction. Only phrases where "not"/"except"/"least" are themselves
# the question's framing (not mentioned/stated/true/etc., or "except"/"least")
# count as negation questions.
NEGATION_MARKERS = re.compile(
    r"\bexcept\b|\bleast\b|\bnot\s+(?:mentioned|stated|true|correct|discussed|supported|included|one\s+of|a\b)",
    re.IGNORECASE,
)

def keywords(text):
    # Alphanumeric, not letters-only -- dates/numbers like "1960s" must count
    # as real keywords (an earlier version's letters-only regex produced a
    # false positive on a fully-supported numeric answer).
    words = re.findall(r"[a-z0-9]+", text.lower())
    return set(w for w in words if w not in STOPWORDS and len(w) > 2)

def check_comprehension(passage, correct_opt, wrong_opts, question_text):
    issues = []
    passage_kw = keywords(passage)
    correct_kw = keywords(correct_opt)
    overlap = correct_kw & passage_kw
    coverage = len(overlap) / max(1, len(correct_kw))
    is_negation_question = bool(NEGATION_MARKERS.search(question_text))

    if is_negation_question:
        if coverage > 0.5:
            issues.append(f"NEGATION question but correct answer has HIGH overlap ({coverage:.0%}) -- expected it to be the unsupported one")
    else:
        if coverage < 0.3:
            issues.append(f"LOW support: only {coverage:.0%} of the correct answer's key terms appear in the passage (overlap: {overlap})")
        for wo in wrong_opts:
            wo_kw = keywords(wo)
            wo_coverage = len(wo_kw & passage_kw) / max(1, len(wo_kw))
            if wo_coverage > coverage + 0.15:
                issues.append(f"SUSPICIOUS: a wrong option has MORE passage-keyword overlap ({wo_coverage:.0%}) than the correct answer ({coverage:.0%}) -- '{wo}'")
    return issues

def main():
    docs = list(db.mcq_static_bank.find({"topic": "verbal"}, {"_id": 0}))
    print(f"Checking {len(docs)} verbal documents...")

    grammar_issues = []
    comprehension_issues = []
    grammar_checked = 0
    comprehension_checked = 0

    for d in docs:
        prompt = d["prompt"]
        options = d["options"]
        correct = options[d["correct_index"]]

        if prompt.strip() == "Identify the grammatically correct sentence:":
            grammar_checked += 1
            issues = check_invalid_patterns(correct)
            if issues:
                grammar_issues.append((d["question_id"], correct, issues))
            sva_issues = check_sva_agreement(options, d["correct_index"])
            if sva_issues:
                grammar_issues.append((d["question_id"], correct, sva_issues))

        if prompt.startswith("Read the passage and answer the question."):
            comprehension_checked += 1
            m = re.search(r"Passage:\s*(.*?)\s*Question:\s*(.*)$", prompt, re.DOTALL)
            if not m:
                continue
            passage, question_text = m.group(1), m.group(2)
            wrongs = [o for i, o in enumerate(options) if i != d["correct_index"]]
            issues = check_comprehension(passage, correct, wrongs, question_text)
            if issues:
                comprehension_issues.append((d["question_id"], correct, issues))

    print()
    print(f"Grammar items checked: {grammar_checked}")
    print(f"Grammar items with detected invalid patterns: {len(grammar_issues)}")
    for qid, correct, issues in grammar_issues:
        print(f"  {qid}: {correct}")
        for issue in issues:
            print(f"      -> {issue}")

    print()
    print(f"Comprehension items checked: {comprehension_checked}")
    print(f"Comprehension items with flagged entailment issues: {len(comprehension_issues)}")
    for qid, correct, issues in comprehension_issues:
        print(f"  {qid}: {correct}")
        for issue in issues:
            print(f"      -> {issue}")

if __name__ == "__main__":
    main()
