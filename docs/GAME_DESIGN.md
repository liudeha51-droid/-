# 東方虚信録 ~ Touhou: Hollow Faith — Game Design Document (v0.2)

> Working title. A Touhou Project fan work (東方Project二次創作) intended for release on
> Steam, subject to permission from the rights holder (see §11).
> Touhou Project and all its characters belong to ZUN / Team Shanghai Alice (上海アリス幻樂団).

## 0. Direction decisions (2026-09-27)

| Topic | Decision |
|---|---|
| Protagonist | **Reimu Hakurei** is the primary protagonist. Original characters are welcome when they grow naturally out of Gensokyo's setting, lore and atmosphere (§6). |
| Tone | A **darker, distinctive, stylised Gensokyo** with a strong Soulslike atmosphere (§7). |
| 3D models | Made **in-house**. No commissioned or pre-made VRoid/MMD assets (§8). |
| Music | **Undecided.** Placeholder music is used during development (§9). |
| Release | **Steam** (§11). |

## 1. Pitch

A third-person Soulslike set in Gensokyo. Faith is draining out of Gensokyo and the
Great Hakurei Barrier is fraying; youkai and fairies who lose faith turn *hollow*: still
strong, but dreamless and violent. Reimu sets out from a broken shrine to settle each
incident the hard way.

The hook is the fusion: **Souls melee (stamina, dodge i-frames, punish windows) layered
with Touhou danmaku (bullet patterns, grazing, spell cards)**. Bosses fight you up close
*and* fill the arena with readable bullet curtains.

## 2. Pillars

1. **Every death is readable.** Telegraphs are long enough to learn; bullet patterns are
   deterministic in structure with small randomness. Fair, not cheap.
2. **Graze is the heartbeat.** Near-misses restore stamina and fill Spirit. Brave play
   (rolling *through* bullets) is rewarded rather than just survived.
3. **Gensokyo is beautiful and dying.** The paradise is still there under the mist:
   shrines, lanterns, cherry trees. But faith is draining out of it, and every area shows
   what is lost when people stop believing. Melancholy first, horror second.
4. **Respect the source.** Characters act like themselves; spell cards use their canonical
   names; nothing that would embarrass the Touhou community.

## 3. Core loop

Explore an area → find a **shrine** (checkpoint) → push through hollowed youkai →
boss arena (ice wall / barrier "fog gate") → learn the boss over several deaths →
settle the incident → new area and a new ability.

On death: respawn at the last shrine, area resets. (Planned: drop your **Faith**
currency where you died, recoverable once, the classic Souls tension.)

## 4. Combat (what the prototype already does)

| Verb | Cost | Notes |
|---|---|---|
| Light attack (gohei) | 16 stamina | 3-hit combo, last hit heavier; dodge-cancel after 0.25 s |
| Dodge roll | 20 stamina | ~0.33 s of i-frames; can roll through bullets |
| Sprint | 14 stamina/s | |
| Ofuda | 10 Spirit | 3 homing amulets from the yin-yang orb |
| Spell card: Fantasy Seal | 100 Spirit | clears enemy bullets, 6 homing orbs, 2 s invulnerable |
| Heal (gourd sip) | 1 of 3 charges | 1 s commitment, slow walk |
| Lock-on | | camera and facing track the target |

**Resources:** HP (red), Stamina (green), Spirit (gold). Spirit comes from melee hits
(+6) and grazing (+3, plus +5 stamina). Stamina can go negative to punish spamming.

**Bosses** have poise: enough damage in a short window staggers them and cancels their
bullets. Each has a recovery window after every action, which is the punish opening.

## 5. Vertical slice: Misty Lake at dusk (built)

- Wayside shrine (checkpoint, pray to restore HP/gourds) → stone causeway with lanterns →
  great torii → Misty Lake, frozen solid by Cirno: the arena.
- **Boss: Cirno, the Ice Fairy** (tutorial boss, 700 HP)
  - Phase 1: ice-sword swing (long wind-up), charging dash, ring waves, spiral, aimed
    icicle fans.
  - Phase 2 at 50%: shockwave, faster and double swings, frost-trail dash, and two spell
    cards: 氷符「アイシクルフォール」 *Icicle Fall* (icicles drop from the mist, shadows
    telegraph them) and 凍符「パーフェクトフリーズ」 *Perfect Freeze* (bullets burst,
    freeze white, then drift loose).

## 6. Full game outline (proposal)

| Area | Theme | Bosses (proposal) |
|---|---|---|
| Misty Lake | tutorial, dusk | Cirno |
| Scarlet Devil Mansion | gothic interior, clocks | Hong Meiling (gatekeeper duel), Sakuya Izayoi (time-stop), Remilia Scarlet |
| Forest of Magic | fungal swamp | Alice Margatroid (doll army) |
| Bamboo Forest of the Lost | maze, fire | Fujiwara no Mokou (revives mid-fight), Eirin Yagokoro |
| Youkai Mountain | vertical climb, wind | Aya Shameimaru (speed), Kanako Yasaka |
| Netherworld / Hakugyokurou | cherry blossoms, ghosts | Youmu Konpaku (pure swordplay), Yuyuko Saigyouji |
| Former Hell | underground heat | Utsuho Reiuji |
| The Great Barrier | final | Yukari Yakumo |

Optional bosses and NPC allies (Marisa as a summonable ally, Suika's gourd as the
Estus equivalent, Rinnosuke as the shopkeeper).

### Original characters

**Rule:** an original character (OC) must be something Gensokyo's own lore implies but
never shows. Examples are a role the setting has, a kind of being it describes, or a
consequence of this story's premise. OCs never replace or overshadow a canon character's
defining role, and canon characters keep their personalities, even hollowed.

Proposals that follow the rule:

| OC | Where it comes from | Role |
|---|---|---|
| **The Former Shrine Maiden** (先代の巫女) | Canon implies earlier Hakurei shrine maidens but never shows them. | A hollowed predecessor who kept guarding the Barrier after faith left her. Recurring rival, late boss, and the dark mirror of what Reimu could become. |
| **The Wayside God** (道祖神) | Small roadside gods are part of Gensokyo's folk religion. | Tends the shrine checkpoints and grows fainter as faith fails. The "firekeeper" NPC who levels you up with Faith. |
| **The Faithless** | This story's premise. | Youkai and fairies who lost faith: the common enemy roster (hollowed fairies, masked tengu scouts, rotting kappa machines). |
| **The Collector of Names** | Gensokyo is where forgotten things go. | Merchant who trades in names and memories, and speaks for what the world forgot. |

All four are kept (decision 2026-09-27). Their full briefs, the hidden premise behind
the Hakurei system, Reimu's arc and the draft endings are in
[STORY_AND_CHARACTERS.md](STORY_AND_CHARACTERS.md). The Former Shrine Maiden is central
to the main story: she is a tragic predecessor whose fate foreshadows Reimu's, not an
evil rival.

Progression: Faith (currency) levels HP / Stamina / Spirit / Power; new **gohei, sword
and amulet** weapon types; spell cards collected from defeated bosses become equippable
player spell cards.

## 7. Art direction: dark, stylised Gensokyo

- **Ink and ember.** Desaturated, cold world colours (slate, ash, bruised violet, bone),
  heavy mist and deep shadow. Warm light is scarce and means safety: shrine flames and
  lanterns. **Red is reserved** for Reimu, torii and blood-red spell cards, so the
  protagonist always reads against the world.
- **Stylised, not realistic.** Characters use cel-leaning shading with ink outlines.
  Environments use painterly PBR with sumi-e (ink wash) accents: brush-stroke silhouettes
  on distant trees and hills, and paper-grain in the fog.
- **Hollowing is visible.** Faithless characters are drained of colour, crack like
  porcelain, and have hollow eyes. Their spell cards glow a sickly, corrupted version of
  their canon colours. A boss's colour returns when you defeat them.
- **Danmaku stays readable.** Bullets are always the brightest, most saturated thing on
  screen (unshaded + glow). The dark world makes them pop.
- **Colour script.** Misty Lake is a violet-grey dusk with a dying red sun, black water,
  cold ice, and warm lantern islands.
- **Placeholder policy:** Reimu and the Misty Lake kit are now in-house Blender assets
  (§8). Cirno is still built from primitives in code. Gameplay code doesn't reference
  meshes, so swapping an asset never touches combat.

## 8. In-house 3D model pipeline

All models are made by the team. There are no commissioned or pre-made VRoid/MMD bases,
so every asset's copyright is clear and Steam-safe.

- **Tools:** Blender (modelling, rigging, animation), Krita or Substance Painter
  (textures). Export glTF 2.0 (`.glb`) to `assets/models/<category>/<name>/`.
- **Characters:** ~40–60k triangles, 1–2 texture sets (2K), hand-painted base colour plus
  a light ramp for toon shading. Use a humanoid skeleton that Godot's retargeting maps.
  Extra bones for hair, sleeves, ribbons and skirt drive physics-based secondary motion.
- **Enemies:** 15–30k tris, and share a rig with the player where possible so animations
  can be reused.
- **Environment kit:** modular pieces on a 1 m grid (shrine, torii, lanterns, stone
  paths, trees, rocks, fences), 1–10k tris each, with trim sheets and vertex-colour
  weathering. Use LODs for anything placed more than 20 times.
- **Shaders:** one character toon shader with an inverted-hull outline, and one
  environment shader with an ink-edge and fog-paper overlay. Both are shared across all
  assets.
- **Order of production:** (1) Reimu, (2) Cirno, (3) hollowed fairy, (4) Misty Lake kit.
  Each one gets a turnaround sheet → blockout in-engine → sculpt/retopo → rig → animation
  set (idle, run, roll, 3 attacks, hit, death).
- **Roles to fill:** character artist, environment artist, animator. One person can
  start with blockouts that replace the greybox directly.

### Status (2026-09-27): first in-house pass

The first assets are built by Python scripts that run inside Blender, so they are
reproducible and reviewable as code. Artists replace or refine them by hand from here.

| Asset | Script | What exists |
|---|---|---|
| **Reimu** `assets/models/characters/reimu/reimu.glb` | `tools/blender/build_reimu.py` | ~15.6k tris. Stylised body, head and hair; the bow, sidelocks with hair tubes, detached bell sleeves, pleated skirt and gohei. 20-bone rig. 11 animations: idle, run, roll, attack1–3, hurt, death, heal, cast, spell. The attack contact frames match the gameplay hit timings. |
| **Misty Lake kit** `assets/models/environment/misty_lake/*.glb` | `tools/blender/build_misty_lake_kit.py` | Great torii, broken torii, stone lantern, hokora checkpoint shrine, the Wayside God stone, 3 dead trees, 2 ink pines, 3 rocks, reeds. |

In-game, Reimu uses toon diffuse/specular, a rim light and an inverted-hull ink outline
(`scripts/toon.gd`). The level falls back to primitives if an asset is missing.

**Next for Reimu (hand work in Blender):**
- a sculpt/retopo pass on the face and hands;
- painted textures instead of flat colours;
- secondary-motion bones for the hair, sleeves and skirt;
- animation polish: anticipation and follow-through, plus hit-stop on contact.

Rebuild an asset with:

```sh
blender --background --python tools/blender/build_reimu.py
blender --background --python tools/blender/build_misty_lake_kit.py
```

## 9. Audio direction

- **Music: undecided.** Options for later are arrangements of canon themes (e.g. Cirno's
  「おてんば恋娘」), original compositions in a Touhou idiom, or a mix of both. Check any
  arrangement against the Steam permission terms.
- **Placeholder music (in the build now):** `scripts/music.gd` synthesises a slow minor
  ambient loop for exploration and a driving loop for boss fights, and crossfades between
  them. To replace a track, assign an audio stream to it; nothing else changes.
- **SFX:** synthesised placeholders at runtime (`scripts/sfx.gd`).

## 10. Technology

- **Godot 4.3**, GDScript, Forward+ renderer (volumetric fog, glow, SSAO). The
  Compatibility renderer also runs (used for the screenshots), minus volumetric fog.
- Input: keyboard/mouse and gamepad, registered in `scripts/input_setup.gd`.
- Bullets are managed centrally (`scripts/bullet_manager.gd`) with distance checks, not
  physics bodies, so hundreds can be on screen.
- Headless smoke test: `godot --headless --path . -s tests/smoke_test.gd`.
- Steam integration (later): the GodotSteam extension for achievements, cloud saves and
  Steam Input. Export targets are Windows and Linux (Steam Deck).

## 11. Release: Steam

Target: **Steam**, Windows first, with Steam Deck support.

**Permission comes first.** Releasing a Touhou fan game on a platform like Steam needs
permission from the rights holder, beyond the general fan-work guidelines. Before we
make a Steam store page, check the current official process on the Touhou Project
official site and apply with a playable demo. The design must also:

- follow ZUN's *東方Projectの二次創作ガイドライン* and label the game as a fan work with the
  credit line above;
- use no official assets ripped from the games (sprites, music files, art). Everything is
  original or made in-house;
- include no content that damages the image of Touhou or its characters. The dark tone
  is about atmosphere and loss, not degrading the cast.

**Steam readiness checklist (later milestones):** full controller support (done in
prototype), rebindable input, settings menu (graphics, audio, accessibility), save
system with Steam Cloud, achievements, a 60 fps target on Steam Deck, store assets
(capsule art, trailer, screenshots), and the content-rating questionnaire.

## 12. Roadmap

1. **M0 (this PR):** design doc + playable greybox slice with Cirno, dark look,
   placeholder music.
2. **M1:** in-house Reimu (first pass done) and Cirno models and animations; toon/ink shaders; hit-stop,
   camera polish, rumble; Faith drop on death; first hollowed-fairy enemy.
3. **M2:** Misty Lake as a full area with the Wayside God NPC; save system and menus;
   **demo build for the Steam permission application.**
4. **M3:** Scarlet Devil Mansion (Meiling, Sakuya), progression (levelling, weapons,
   player spell cards).
5. **M4:** Steam page, achievements, Steam Deck verification.

## 13. Open decisions

- Music direction (deferred).
- Price on Steam: free or paid. This depends on what the permission allows.
- Which OC proposals in §6 to keep.
