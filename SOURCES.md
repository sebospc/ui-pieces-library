# Web sources

Read one at a time on 2026-10-31. These are web component libraries (React). The library takes techniques and patterns
only: no code is copied, no component is ported 1:1, no brand colour or name. The licence of each is below.

| source | licence found | where | what it allows |
|---|---|---|---|
| easyui.site | MIT | github.com/Surajmaurya1/easyui LICENSE | anything, code included, with the MIT notice; we copy no code anyway |
| rareui.com | MIT + Commons Clause + attribution | rareui.com/terms, LICENSE in github.com/swamimalode07/rare-ui (GitHub reads it as "Other") | use in our own app; NOT redistributing a component, "a version ported to another framework", or "a competing component library"; a credit link if any part of a component ships. So: techniques only, never a 1:1 port of one component into a piece |
| kobra.systems | free tier "Personal use only"; commercial needs Pro ($199) | kobra.systems/pricing | ideas only from the public docs page (e.g. the OTP input: a focus ring that slides across the filled range, digits that rise and un-blur, a success wave); no code read, no 1:1 port |
| ui.aceternity.com | free components: no licence text found; Pro licence forbids redistributing source and making templates or derivative products for a marketplace | ui.aceternity.com/licence | ideas only; no code, no 1:1 port |
| pinui.xyz | unknown | the site answered 429, then 403 to a fetch; a search found nothing | nothing taken until someone reads its terms in a browser |

Ideas and techniques (a sliding focus ring, a staggered wave) are not covered by these licences; copied code and a
recognisable 1:1 component are. That is my reading, not legal advice.

## Looked at, not taken

- easyui lock-input (2026-10-31): one text field whose focus ring scales in. The focus ring is drawn by each host,
  so there is no piece to keep.

## Taken (technique only)

- ui.aceternity.com Card Stack (2026-10-31): cards stacked with the ones behind peeking, the front one
  cycling back. Became entries/mobile/hero_list/card-stack, tap driven instead of on a timer. The demo was read at a
  phone viewport; the Code tab was not opened.
