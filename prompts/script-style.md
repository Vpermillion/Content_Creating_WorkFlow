# Ifverse script-style addon — owner preference

Applies by default to English scripts for **ifverse_anime** and **ifverse_hollywood**. Confirmed and clarified by the owner on 2026-10-30. Current preference revision: **ifverse-playful-roast-v2**. Preserve this preference across sessions; this file supersedes the older neutral/explainer tone. The owner may override it for an individual video.

## Copy-ready writing prompt

Make the **whole narrator persona** funny, cheeky, creatively annoyed and casually streetwise, using modern Gen Z and millennial internet banter. The owner clarified after the first roast demo: use **many varied, creative roasts throughout**, not one “motherflicker” or a generic insult added to otherwise plain explanation. Treat this as the current default for both channels.

Use confident trash talk, playful disrespect toward fictional decisions, incredulous reactions, exaggerated complaints, quick analogies, mock praise, fake job reviews, gaming/group-chat language and callbacks. Aim for a comic turn in most short narration beats (roughly every one or two sentences), while preserving a clear alternate story. Vary the setup and target: a bad plan, a villain's logic, an outfit, a consequence, or a character's delusional confidence. Make the roast explain something about that particular scene.

Slang is a toolbox: “bro,” “my guy,” “be so for real,” “cooked,” “yapping,” “side quest,” “NPC,” “aura,” “rent was due,” and “group chat” may fit. Choose phrases that sound natural together and still make sense to the audience. Mix Gen Z phrasing with millennial sarcasm; avoid a random meme pile. Rotate reactions instead of beginning every line with “bro.” “Hood talk” here means colloquial swagger, rhythm and banter; no particular racial identity, real person's voice or stereotyped accent is requested.

Open with the what-if and an immediate funny reaction. Build a coherent alternate timeline with cause, escalation, a consequence and a choice. Make jokes specific to the character or scene. Carry the comic persona through setup, escalation and payoff, with brief sincere stakes when needed. Do not revert to a dry summary between two isolated insults. End with a punchline or concrete audience question. Avoid a dry encyclopedia voice, generic motivational filler and repeated engagement requests.

**Roasts should be frequent; swearing should remain occasional.** Increase wit, variety and comic density rather than increasing explicit profanity. Mild swearing is welcome when it earns the joke. Prefer playful clean substitutions such as **“motherflicker,” “mother father,” “what the heck,”** or **“holy crap.”** A sensible default is zero to two clean-swear punchlines per minute, not a quota; do not put one in every sentence. Do not silently restore the stronger phrase in TTS, captions, titles or descriptions. Keep profanity light; avoid explicit sexual language and slurs. Clean substitutions do not guarantee platform acceptance, monetization or freedom from moderation.

Aim the roast at fictional behavior, bad plans, villains and plot absurdity. Keep speculation clearly distinct from canon: introduce an alternate timeline, do not invent official quotes or assert that an imagined event appeared in the actual show/film. No particular actor, real person's voice, accent or racial identity is requested by this style preference.

Write **filmable narration beats**. Name concrete characters, objects, actions or places that the available moving footage can illustrate. Give each planned beat its source and match reason; preserve correct named characters when a joke lands. Metaphors like “job interview” do not justify unrelated office stock footage in an anime story. Illustrate the character/villain context and label hypothetical actions honestly.

For an approximately one-minute video, draft around 170–200 spoken English words, then measure actual narration. Allow breathing room and comic timing. The current 60-second example uses pitch-preserving bounded speech retiming; captions must be generated/aligned to the final waveform. Never reuse another script's narration or timestamps. Do not promise an expressive performance the chosen TTS has not demonstrated.

## Range of comic moves — adapt, do not repeat as catchphrases

- Mock career advice: “Bro saw a villain cloak and called it career growth.”
- Specific insult: “This tactical genius signed up to work for the people hunting him.”
- Incredulous correction: “My guy, you are not the new hire. You are the delivery order.”
- Villain roast: “Pain wants world peace. His opening argument is flattening the neighborhood.”
- Modern comparison: “Akatsuki is a group project where everybody brought a criminal record.”
- Mock praise: “Outstanding decision. Somehow both teams want your location now.”
- Gaming metaphor: “He accepted the side quest and accidentally became the loot.”
- Complaining narrator: “Can this man read one red flag before collecting the whole set?”
- Slang punchline: “All that aura and absolutely no exit strategy.”
- Clean-swear reaction: “Mother father, that is your village on the demolition list.”
- Callback: Set up the cloak as a career upgrade, then close with “Keep the cloak. Cancel the career advice.”

A continuous example of the intended density:

> What if Naruto joined the Akatsuki? Bro saw a red-cloud cloak and called it career growth. My guy, they are hunting the fox in your stomach. You are not the new hire. You are the delivery order. Pain is talking world peace while flattening the neighborhood. Sir, that is a demolition company with a dress code. Now Naruto wants to fix these people with a friendship speech. Be so for real. This group chat needs an exorcist.

These are hypothetical commentary examples, not official dialogue or claims about an actual alternate-timeline episode. Invent fresh, scene-specific jokes for each production; do not copy the bank verbatim into every video.

## Originality for a channel intended to earn revenue

Read `docs/MONETIZATION_REVIEW.md` and prepare the short `prompts/editorial-brief.md` before a commercial-publication candidate. Keep the selected Michael voice and funny v2 style. Make each episode's actual premise, causal development, commentary and jokes substantially its own; do not churn out name-swapped scripts. A comic story is allowed to entertain rather than teach, but captions, clean swears, sound effects and zooms are not substitutes for original substance or source-use clearance. Use original visual explanations and documented cleared material where suitable. Do not use mirroring/pitch changes to evade scanners, invent licenses or human-review evidence, or claim a video passes YPP. Treat the existing versions as demonstrations until editorial/source and channel requirements are actually reviewed.

## Sound design for comic timing

Plan short modern meme-style effects along with the joke: question → skeptical reaction/roast → short impact → comeback. Use the catalog descriptions/tags in `assets/sfx/catalog.json` and the cue rules in `docs/SOUND_EFFECTS.md`. Choose effects that support a particular scripted beat: a bass impact after a roast/revelation, an error buzz after a bad plan, a sarcastic reward ping, or a cartoon boing at an absurd payoff. Vary the choices and keep dialogue intelligible. Several deliberate cues per minute are preferable to a sound after every sentence.

Put sound directions in a separate cue plan with exact spoken phrase anchors and a reason; do not put “boom sound effect” into the spoken TTS text or invent recognized timestamps. On a new script, plan any short pause needed before the comeback; on an existing approved waveform preserve its timing and duck the effect during speech. Keep source/license/checksum metadata, original clean media and the final mix receipt. The current test uses public-domain game effects treated for meme-style editing; it does not claim they are the original viral recordings. Dialogue examples describe the desired rhythm; the tested review narrator still uses one voice for the whole script.

## Current example

The already rendered one-minute **v1** example is `pilots/ifverse-anime-roast-60-v1.json`, paired with `edits/ifverse-anime-roast-60-v1.json`. It riffs on Naruto joining the Akatsuki and includes “Motherflicker, they are hunting the fox inside you” and “That is not a job interview. You are the lunch.” It predates the owner's request for denser, more varied Gen Z/millennial banter. This v2 clarification updates future script instructions; it does not mean that earlier video was rewritten or rendered again. See `docs/CURRENT.md` for execution and review status.

This is a script-writing preference, not permission to publish or create accounts. Keep the existing one-plan, one-hosted-job, one-result workflow and preserve prior versions.
