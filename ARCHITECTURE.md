# Architecture notes

## Is it a script, or is it logic?

A file belongs in `scripts/` ONLY if BOTH are true:
1. It is run manually/occasionally by a human (data population, one-off
   migration, verification/diagnostic check) — not imported or called by
   the running application itself.
2. Removing it would not change any request-handling behavior in
   `server.py` — the app works identically whether or not this script has
   ever been run again after its data is already in the database.

If a file defines behavior the running app depends on — grading, question
generation, section dispatch, anything imported and called at request
time — it is LOGIC, not a script, and belongs in the relevant domain
folder (`departments/.../<company>/`, `banks/`, `games/`, `services/`,
`core/`), never in `scripts/`, regardless of how it was originally
written or what it's named.

When in doubt: grep for whether anything imports it. If `server.py` or
another app module imports and calls it, it's logic. If only a human runs
it directly (`python scripts/whatever.py`), it's a script.

### Worked example: a one-off Mongo-seeding script that already ran

`scripts/capgemini_round2_ai_literacy_insert.py` loaded 400 hand-authored
"AI Literacy" scenario questions from scratchpad JSON batches and upserted
them into Mongo's `capgemini_round2_bank` collection. It "contained
Capgemini OA logic" in a loose sense (its content is genuinely part of
Capgemini's Round 2 assessment), which made it tempting to merge wholesale
into `capgemini_recruitment_process.py` (the company's logic module,
imported live by `server.py`).

That would have been wrong, for two reasons:
- **It fails the test above.** Nothing imports or calls this script at
  request time; the data it inserted already lives in Mongo independent of
  whether the script file still exists. It's a script, not logic.
- **Pasting its executable body into a module `server.py` imports would
  have been a real behavior change.** The script's module-level lines
  (`sys.path.insert`, `load_dotenv`, the `motor` client import) would then
  fire on every `server.py` startup, not just when a human runs the
  script directly.

So it was handled the way Round 1's own insert scripts were handled before
it (none of which still exist in `scripts/` today): the data-population
fact was **documented** — where the content lives in Mongo, how it was
authored and staged, that it isn't wired into live dispatch yet — as a
comment block in `capgemini_recruitment_process.py`, in the same style
already used for Sections 1-6's own bank provenance notes. The script file
itself was then **deleted**, since its one job was already done. Nothing
was merged as executable code; only the fact of the data's existence and
lineage was.
