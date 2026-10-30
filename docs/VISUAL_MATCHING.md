# Match the pictures to the spoken script

The current revision preserves the 44.672-second Kokoro narration and its corrected caption record. It replaces equal splits of a multi-clause scene with explicit spoken-beat shot boundaries. This addresses observed mismatches: a smiling-friend shot continuing over a dangerous price, friends appearing while the organization was being named, and a fox close-up during the question about changing Akatsuki.

Prioritize the actually named character/entity, then action/location, then tone or context. A label is only a search hint. Inspect the clip before claiming its content. Keep source URL, usage status, checksum, in-point and the reason for its narrative match. If an exact invented action has no canon shot, use a relevant illustrative excerpt and mark the limitation rather than inserting an unrelated clip or asserting a literal scene exists.

`start` and `end` on every shot are global seconds on the narration timeline. Within each scene the shots must be contiguous, ordered, finite and cover the scene exactly; partial/gapped/overlapping plans fail. Legacy untimed plans retain equal splitting. Each source excerpt must cover its actual reviewed interval after `trim_start`. Changing speech timings invalidates this exact plan and requires a new alignment. The renderer checks these contracts; semantic relevance is still an editorial decision, not a proven model score.

## Current reviewed beat plan

| Seconds | Spoken beat | Source | Visual reason | Match type |
| --- | --- | --- | --- | --- |
| 0.00–1.44 | Naruto joined | `18786249` | Naruto is visible while the protagonist is named. | direct_entity |
| 1.44–3.84 | the Akatsuki; the first surprise | `pain-naruto-10` | Show the cloaked organization when Akatsuki is named. | direct_entity |
| 3.84–5.35 | joining would not make him safe | `18786244` | Masked Obito supplies a concrete antagonist for the danger; the alliance remains hypothetical. | contextual_threat |
| 5.35–6.70 | He carries the Nine Tails | `18787233` | The moving Nine-Tails avatar appears during the actual Nine Tails phrase. | direct_entity |
| 6.70–9.56 | the Akatsuki wants the tailed beasts | `pain-naruto-10` | Cut to the organization during the stated motive, instead of continuing the fox shot. | direct_entity |
| 9.56–11.39 | Their new recruit is also their target | `18786193` | Naruto close-up identifies the recruit/target being discussed. | direct_entity |
| 11.39–14.84 | Naruto offers a deal | `18786193` | Naruto speaks and gestures during the invented offer; this is illustrative canon footage. | hypothetical_illustration |
| 14.84–16.48 | his help in exchange for | `18786238` | Kakashi moves into action to establish the help/protection context. | contextual_action |
| 16.48–17.51 | protecting his friends | `naruto-team-7-0` | Team Seven is visible precisely during protecting his friends. | direct_entity |
| 17.51–19.10 | At first the missions give him | `18786256` | Naruto advances with chakra power to illustrate mission activity. | contextual_action |
| 19.10–21.04 | the respect he always wanted | `sakura-8` | A friendly Naruto/Sakura moment illustrates belonging, not a literal Akatsuki approval scene. | hypothetical_illustration |
| 21.04–22.78 | But every favor comes with a price | `18787221` | Replace the smiling-friend shot with the masked antagonist as the narration turns threatening. | contextual_threat |
| 22.78–25.82 | his new allies demand | `18786244` | Show the Akatsuki representative during the demand. | direct_entity |
| 25.82–27.61 | turn against the Hidden Leaf | `pain-naruto-1` | Pain overlooks the village, making the Hidden Leaf reference visually concrete. | direct_location |
| 27.61–28.45 | He refuses | `18787217` | Naruto speaking forcefully is placed on the short refusal beat, not half of the entire scene. | hypothetical_illustration |
| 28.45–31.20 | both sides question his loyalty | `18787221` | The opposing masked face accompanies distrust and divided loyalty. | contextual_threat |
| 31.20–33.73 | the deal that protected his friends falls apart | `sakura-0` | Sakura in village rubble shows the friends and consequences as their protection collapses. | contextual_consequence |
| 33.73–35.64 | Naruto has to choose | `18787224` | Naruto alone in the inner space frames his personal decision. | hypothetical_illustration |
| 35.64–37.80 | prove himself to the organization | `pain-naruto-10` | Show Akatsuki during organization; the old equal split showed friends too early here. | direct_entity |
| 37.80–39.96 | or protect the people who still believe in him | `naruto-team-7-0` | Switch to Team Seven on the actual alternative about protecting his people. | direct_entity |
| 39.96–42.40 | Could he change the Akatsuki from inside | `pain-naruto-10` | Show Akatsuki during the organization question, replacing the unrelated Kurama close-up. | direct_entity |
| 42.40–44.67 | Or would joining them change Naruto first | `18787224` | Return to Naruto in his inner space when the closing question shifts back to him. | hypothetical_illustration |

All 22 entries use moving online excerpts from the retained traced source plan, with full-frame containment to avoid the heavy portrait crop that enlarged low-resolution footage. No original speech or caption bytes need regeneration for this visual-only revision. Existing captions and source ownership/editorial limitations remain. Inspect representative frames and cuts in the completed output; the rationale table alone is not proof that the whole video was reviewed.
