# 東方虚信録 ~ Touhou: Hollow Faith — Game Design Document (v0.1)

> Working title. A non-commercial Touhou Project fan work (東方Project二次創作).
> Touhou Project and all its characters belong to ZUN / Team Shanghai Alice (上海アリス幻樂団).

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
3. **Gensokyo is beautiful and melancholy.** Dusk light, mist, shrines, lanterns. The
   world should feel like the games' music sounds.
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

Progression: Faith (currency) levels HP / Stamina / Spirit / Power; new **gohei, sword
and amulet** weapon types; spell cards collected from defeated bosses become equippable
player spell cards.

## 7. Art direction

- Stylised anime realism: cel-leaning shading on characters with soft PBR environments
  (think Genshin-level character fidelity in a Souls-lit world).
- Colour script per area; Misty Lake is dusk-pink sky, cold blue ice, warm lantern light.
- Bullets are always the brightest thing on screen (unshaded + glow) for readability.
- **Placeholder policy:** every model in the prototype is built from primitives in code
  (`scripts/*_build_model`). Replacing one means swapping that function for an imported
  scene; gameplay code doesn't reference meshes.

**3D model pipeline (planned):** Blender → glTF 2.0 (`.glb`) → `assets/models/`.
Characters: ~40–60k tris, humanoid rig compatible with Godot's retargeting, separate
cloth/hair bones for secondary motion, toon + outline material.

## 8. Audio direction

- Boss themes: arrangements of the character's canonical theme (e.g. Cirno's
  「おてんば恋娘」) are the most Touhou move, and fan arrangements are allowed under the
  guidelines with credit. They need a composer/arranger.
- Area music: original ambient pieces in a Touhou idiom (piano, strings, trumpet leads).
- SFX: the prototype synthesises placeholder SFX at runtime (`scripts/sfx.gd`); no audio
  files are shipped yet.

## 9. Technology

- **Godot 4.3**, GDScript, Forward+ renderer (volumetric fog, glow, SSAO). The
  Compatibility renderer also runs (used for the screenshots), minus volumetric fog.
- Input: keyboard/mouse and gamepad, registered in `scripts/input_setup.gd`.
- Bullets are managed centrally (`scripts/bullet_manager.gd`) with distance checks, not
  physics bodies, so hundreds can be on screen.
- Headless smoke test: `godot --headless --path . -s tests/smoke_test.gd`.

## 10. Fan-work guidelines

The project should follow ZUN's published *東方Projectの二次創作ガイドライン*:

- Non-commercial (or doujin-scale) and clearly labelled as fan work, with the credit line
  above. Commercial release on platforms such as Steam goes through the separate
  permission process described in the guidelines.
- No official assets ripped from the games (sprites, music files, art). Everything is
  made for this project.
- No content that damages the image of Touhou or its characters.
- Check the current guidelines before any public release; they are updated occasionally.

## 11. Roadmap

1. **M0 (this PR):** design doc + playable greybox slice with Cirno.
2. **M1:** real Reimu and Cirno models and animations; Cirno theme arrangement; hit-stop,
   camera polish, controller rumble; Faith drop on death.
3. **M2:** first full area (Scarlet Devil Mansion gate + Meiling, Sakuya), enemy roster of
   hollowed fairies, save system, menus.
4. **M3:** progression (levelling, weapons, player spell cards), second area.

## 12. Open decisions

- Protagonist: Reimu only, Reimu + Marisa, or a custom shrine maiden with Reimu as NPC.
- Tone: faithful-bright Touhou vs. darker "hollow Gensokyo" (current default).
- Art style target and budget: commissioned models, VRoid/MMD-based models (check each
  model's licence), or in-house.
- Music: who arranges, and which themes.
- Distribution: free download (itch.io) vs. applying for commercial permission.
