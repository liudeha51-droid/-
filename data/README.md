# Content data

Pure content for *Touhou: Hollow Faith* (東方虚信録): numbers, names, text and cross-references.
It holds no gameplay code. Every file is UTF-8 JSON with a top-level `"version": 1`.
The canon behind this data is [docs/GAME_DESIGN.md](../docs/GAME_DESIGN.md) and
[docs/STORY_AND_CHARACTERS.md](../docs/STORY_AND_CHARACTERS.md). If the data and the docs
disagree, the docs win and the data should be fixed.

| File | What it holds |
|---|---|
| `areas.json` | The hub and the eight areas in play order: shrines, sub-zones, spawns, bosses, connections, pickups |
| `enemies.json` | The Faithless roster |
| `bosses.json` | Every boss, the Former Shrine Maiden's appearances, and her (hidden) name |
| `items.json` | Currencies, status effects, items, shops, Rinnosuke's forge, the Collector's trades |
| `weapons.json` | Weapon types, upgrade paths and weapons |
| `spell_cards.json` | Player-equippable spell cards |
| `progression.json` | Faith levelling: formula, level table 1–60, stat curves, offering rules |
| `blessings.json` | Roguelike layer: omikuji fortunes, elite affixes, blessings and curses (lost on each fall) |
| `dialogue.json` | Speakers and dialogue trees |
| `lore.json` | Codex entries |
| `endings.json` | The state catalogue (stats, flags, derived flags) and the three endings |

## Conventions

**Ids** are lower `snake_case` and unique within their collection. Cross-file references
always use ids, never names.

| Kind | Pattern | Example |
|---|---|---|
| Area | place name | `misty_lake`, `scarlet_devil_mansion` |
| Sub-zone | unique across all areas | `frozen_lake`, `pillar_beneath` |
| Shrine (checkpoint) | `shrine_<area-ish>_<place>` | `shrine_misty_lake_wayside` |
| Spawn group | `<area abbrev>_<place>` | `ml_causeway`, `fh_core` |
| Enemy | what it is | `hollow_fairy`, `masked_tengu_scout` |
| Boss (canon) | full romanised name | `hong_meiling`, `fujiwara_no_mokou` |
| Boss (Former Shrine Maiden) | `former_maiden_<where>` | `former_maiden_road`, `former_maiden_saigyou`, `former_maiden_pillar` |
| Item | what it is; groups use prefixes | `relic_*`, `name_fragment_*`, `memento_<boss short name>` |
| Weapon | `<type>_<name>` | `gohei_hakurei`, `sword_pruning_blade`, `amulet_boundary_ribbon` |
| Spell card | `sc_<name>` | `sc_fantasy_seal` |
| Boss spell card / attack | local to the boss, not global | `perfect_freeze`, `swing` |
| Dialogue tree | NPC id, or `boss_<boss id>` | `wayside_god`, `boss_cirno` |
| Dialogue node | `<tree prefix>_<beat>` (unique within its tree) | `wg_menu`, `col_page_offer`, `fm_name_spoken` |
| Lore entry | `lore_<topic>`; areas `lore_area_<area>`; endings `lore_<ending id>` | `lore_area_netherworld` |
| Ending | `ending_<name>` | `ending_returned_name` |
| Flag | a past-tense fact | `saw_maiden_glimpse`, `returned_maiden_name` |
| Boss defeat flag | `defeated_<boss id>`, generated for every boss | `defeated_cirno` |
| Music cue (placeholder) | `mus_<area>_explore`, `mus_boss_<name>` | `mus_boss_cirno` |
| Model | path under `assets/models/` without `.glb` | `characters/faithless/hollow_fairy` |

**Text.** English is the primary text (`*_en`). Japanese (`*_ja`) is written as natural
Japanese, and is allowed to be shorter than the English. Where a field has only `lore_en`,
the Japanese is still to be written. Spell card names follow the Touhou form
`符名「カード名」` / `Sign "Card Name"`.

**Units.** Seconds (`*_s`), metres (`*_m`), percentages as 0–100 (`*_pct`), multipliers as floats.
HP, damage, poise and Faith are plain numbers on the prototype's scale (player HP 100 at
level 1; Cirno 700 HP).

**Damage types:** `slash`, `strike`, `pierce`, `spirit`, `fire`, `ice` (listed in
`enemies.json`). **Status effects:** `frost`, `burn`, `dread` (listed in `items.json`).

### Condition strings

Anything named `condition`, `conditions`, `trigger`, `unlock`, `when` or `rule` holds a
condition string. An empty string means "always".

| Form | Meaning |
|---|---|
| `flag:<id>` / `!flag:<id>` | a story flag is set / not set (see `endings.json` `flags`) |
| `item:<id>` / `!item:<id>` | the player holds / does not hold an item |
| `stat:<id><op><number>` | compare a world stat (`endings.json` `stats`); ops `< <= == >= >` |
| `trade:<trade id>` | the player has made that Collector trade |

A list of conditions (`conditions: [...]`) means all of them must hold.

### Dialogue actions

Actions on a dialogue node run when the node is shown. Form: `name` or `name:arg`.

| Action | Argument |
|---|---|
| `open_level_up`, `open_offering` | none |
| `open_shop:<id>` | a `shops` or `trades` id from `items.json` |
| `open_forge:<id>` | a `forges` id from `items.json` |
| `give_item:<item>`, `take_item:<item>` | an item id |
| `start_boss:<boss>` | a boss id |
| `open_phase:<n>` | a phase number of the current boss (used for the Former Shrine Maiden's phase 3) |
| `modify_stat:<stat>:<delta>` | a stat id and a signed number |
| `play_ending:<ending>` | an ending id |

## areas.json

`areas[]`, sorted by `play_order` (0 is the hub).

| Field | Notes |
|---|---|
| `id`, `play_order`, `kind` | `kind` is `hub` or `main` |
| `names.en` / `names.ja` | |
| `theme`, `time_of_day`, `mood` | art and tone direction |
| `environment_kit` | `{id, status, path}`. `status` is `built` if the kit's folder exists under `assets/models/environment/`, otherwise `planned` |
| `music_cues` | `{explore, boss}` placeholder cue ids |
| `sub_zones[]` | `{id, names, description}`; boss arenas and pickups point at these |
| `shrines[]` | checkpoints: `{id, names, sub_zone, initial}` |
| `spawn_groups[]` | `{id, sub_zone, condition?, enemies: [{enemy, count}]}` |
| `bosses[]` | boss ids fought in this area |
| `connections.required[]` / `.optional[]` | `{to, via, condition}`. Required links form the critical path; optional ones are shortcuts |
| `item_pickups[]` | `{item, count, sub_zone, condition?, note?}` |
| `weapon_pickups[]` | `{weapon, sub_zone, condition?, note?}` |
| `lore_en`, `lore_ja` | one paragraph |

## enemies.json

`damage_types[]`, then `enemies[]`:

| Field | Notes |
|---|---|
| `id`, `names`, `areas[]` | every listed area has a spawn group containing this enemy |
| `model`, `model_status` | `built` if the `.glb` exists |
| `stats` | `{hp, poise, damage, faith_drop}`. `damage` is the typical contact hit |
| `attacks[]` | `{id, name, type, damage, windup_s, recovery_s, description}`; `type` is `melee`, `bullet` or `pattern`. Bullet and pattern damage is per bullet |
| `weaknesses[]`, `resistances[]` | damage types |
| `status_inflicted` | `{status: buildup per hit}` (optional) |
| `behavior_tags[]` | free-form AI hints; `lured_by:<item>`, `disabled_by:<item>` and `bows_to:<npc>` are checked references |
| `lore_en`, `lore_ja` | |

## bosses.json

`bosses[]`, `former_maiden_appearances[]`, and `former_maiden_name`.

| Field | Notes |
|---|---|
| `id`, `kind` | `main` or `former_maiden`; the maiden's three fights also carry `encounter` 1–3 |
| `names` | `{en, ja, title_en, title_ja}` |
| `area`, `sub_zone` | the arena |
| `model`, `model_status`, `music_cue` | |
| `required`, `marisa_summonable` | |
| `hp_total`, `hp_per_phase[]`, `poise`, `stagger_s` | `hp_per_phase` sums to `hp_total`. An ally phase (below) has its own opponent HP and no entry here |
| `revives` | Mokou only: each phase is a new life at full HP |
| `mirror_rules` | Former Shrine Maiden only: she uses the player's stamina, graze and dodge rules |
| `phases[]` | `{phase, starts_at_hp_pct, trigger?, transition?, description, attacks[], spell_cards[]}`. `starts_at_hp_pct` is the boss's remaining HP when the phase begins. `trigger` is `revive` or a condition |
| `phases[].spell_cards[]` | `{id, name_ja, name_en, variant, damage, windup_s, duration_s, recovery_s, description}`. `variant` is `canon` (a canonical card name), `hollowed` (a new card for this story's hollowed version) or `original` (the Former Shrine Maiden's) |
| `phases[].name_prompt` | pillar fight: when the player may speak the predecessor's name |
| `phases[].ally_phase`, `opponent` | pillar fight phase 3: she fights beside Reimu against the Collapsing Seal |
| `arena` | arena description |
| `intro_lines[]`, `defeat_lines[]` | `{speaker, text_en, text_ja, condition?}` barks in the arena |
| `earned_spell_card`, `earned_condition?` | a `spell_cards.json` id |
| `faith_reward`, `drops[]` | item ids |
| `dialogue_tree` | the approach and revisit conversation |
| `sets_flags[]` | always includes `defeated_<id>` |
| `on_defeat`, `leads_to` | story hooks |
| `reflect_stance?` | `true`: the boss periodically raises a mirror that turns Reimu's shots back, then releases what it caught as a ring (Utsushimi) |
| `lore_en`, `lore_ja` | |

Cirno's data mirrors the prototype exactly: 700 HP, poise 70, phase 2 at 50%, action ids
`swing`, `dash`, `ring`, `spiral`, `aimed`, `icicle_fall`, `perfect_freeze`, and the
prototype's damage and timing numbers.

`former_maiden_appearances[]` is her whole story arc in order, both fights and non-combat
beats: `{id, order, combat, boss?, area, sub_zone, trigger, description, sets_flags, dialogue: {tree, node}}`.

`former_maiden_name` holds her name. **The game must never show it** until
`returned_maiden_name` is set (see `display_rule`). It is a placeholder for the script, and
it is kept in this one place so it is easy to change.

## items.json

| Section | Notes |
|---|---|
| `currencies[]` | `faith`, and `faith_remnant` (Faith dropped on death, recoverable once) |
| `status_effects[]` | `frost`, `burn`, `dread` |
| `items[]` | `{id, category, names, stack_max, effect?, description, lore_en, lore_ja?}` |
| `shops[]` | `{id, npc, kind, currency, sub_zone, inventory: [{item, price, stock?, condition?}]}` |
| `forges[]` | Rinnosuke turns a boss memento into a weapon: `{memento, weapon, faith}` |
| `trades[]` | the Collector of Names: `offers[] {id, give[], receive[], line_en}`; each entry is `{kind: item or lore, id, count?}` |

Item `category`: `consumable`, `key`, `relic` (the Former Shrine Maiden's belongings),
`name_fragment`, `upgrade_material` (with `tier` 1–4; 0 for gourd upgrades), `memento` (one
per canon boss). `ibuki_gourd` is the Estus equivalent: 3 charges, 45 HP each, refilled at
shrines, upgraded by `oni_sake_lees` (charges) and `ibuki_undiluted` (potency).

A name fragment has a `return_target` (`{kind: area or npc, id}`). The player can return it
there, or trade it to the Collector. Returning one adds 1500 to `faith_offered_total` and
1 to `fragments_returned`. `description` is short UI text; `lore_*` is the item-description
text.

## weapons.json

| Section | Notes |
|---|---|
| `scaling_grades` | letter → coefficient |
| `damage_formula` | how base damage, motion value, scaling grade and the progression bonus tables combine |
| `weapon_types[]` | `gohei`, `sword`, `amulet` with base stamina cost and Spirit per hit |
| `upgrade_paths[]` | `{id, max_level, damage_growth_per_level, levels: [{to, materials: [{item, count}], faith}]}` |
| `weapons[]` | `{id, type, names, source, base_damage, poise_damage, reach_m, scaling: {power, spirit}, upgrade_path, passive?, moveset, lore_en}` |

`source.kind` is `starting`, `pickup` (placed in that area's `weapon_pickups`), `forge`
(from a memento) or `npc_gift`. The `moveset` has `light[]` (the combo), `heavy`, `running`,
`rolling` and `art` (the weapon skill, which costs Spirit). Each move has a `motion_value`
multiplier. `gohei_hakurei` matches the prototype: 14 damage, a 3-hit combo at
1.0 / 1.0 / 1.857 (14 / 14 / 26) with hits at 0.17 / 0.17 / 0.3 s.

## spell_cards.json

`slots` (1 at the start, up to 3, opened by flags) and `spell_cards[]`:
`{id, name_ja, name_en, source, spirit_cost, effect, description, lore_en}`.
`source` is `{kind: "reimu", unlock}` (her own cards; `unlock` is `start` or a condition) or
`{kind: "boss", boss, condition?}`. Every boss's `earned_spell_card` points back here.
`sc_fantasy_seal` costs 100 Spirit, as in the prototype.

## blessings.json

The roguelike layer. A run lasts from one fall to the next, and every blessing is lost
on a fall.

| Field | Notes |
|---|---|
| `fortunes[]` | omikuji results `{id, ja, en, weight, result, luck, text_en}`. `result` is `choose_3`, `random_1` or `curse`; `luck` (0..1) tilts the draw toward rare blessings |
| `elite_affixes[]` | `{id, ja, en, text_en, hp_mult, poise_mult?, speed_mult?}`: swift, armored, mirrored, splitting, zealous |
| `blessings[]` | `{id, rarity, unique?, names, effects[{effect, value}], text_en, lore_en}`. `rarity` is `common`, `rare`, `legendary` or `curse` (curses only come from 凶). Values of the same effect add up |

Effect keys: `max_hp`, `max_stamina`, `max_spirit`, `extra_gourd`, `damage_mult`,
`ofuda_pierce`, `ofuda_count`, `ofuda_cost`, `homing_ofuda`, `swing_reach`,
`cancel_spirit`, `cancel_heal`, `graze_spirit`, `graze_heal`, `dodge_ward`,
`reflect_power`, `spell_cost`, `faith_gain`, `second_wind`, `enemy_damage`,
`elite_chance`.

## progression.json

| Field | Notes |
|---|---|
| `level_formula` | cost from level L to L+1: `round(200 + 40L + 3.5L² + 0.08L³)` |
| `level_rules` | every stat starts at rank 1; level = sum of ranks − 3; one rank per level; rank cap 40 |
| `base_values` | HP 100, Stamina 100, Spirit 100 (the prototype values), plus regen and graze constants |
| `stats[]` | HP, Stamina, Spirit, Power, with soft caps at ranks 15 and 30 |
| `stat_tables` | 40 values each, indexed by rank − 1: `hp`, `stamina`, `spirit` (absolute) and `power_bonus`, `spirit_bonus` (added to the damage multiplier through weapon scaling) |
| `wayside_offering` | offering rules and the true-ending ratio |
| `level_table[]` | levels 1–60: `{level, cost_to_next, cumulative_to_reach}`. Level 60 has no `cost_to_next` |

## dialogue.json

`speakers` maps speaker id → display names. `name_fades: true` marks Reimu, whose displayed
name smudges as `reimu_name_fade` rises. `npc_models` gives model ids for the NPCs.
`trees[]`:

| Field | Notes |
|---|---|
| `id`, `npc` | |
| `entry` | the node to start at normally |
| `first_meeting_entry`, `first_meeting_flag` | start here instead while the flag is unset |
| `entry_by_shrine` | Wayside God only: shrine id → that shrine's greeting node. Every shrine has one |
| `event_entries` | event name → node, for nodes the game triggers directly (story beats, summons, mid-fight prompts). The Former Shrine Maiden's appearances point here |
| `nodes[]` | see below |

A **line node** is `{id, speaker, text_en, text_ja, next | choices, conditions?, set_flags?, actions?, once?}`.
`next: null` ends the conversation. `choices[]` are `{text_en, text_ja, next, conditions?}`;
a choice whose conditions fail is hidden. A node's `conditions` gate whether the game may
play it. `set_flags` and `actions` apply when the node is shown. `once: true` means its
actions run only once per save.

A **branch node** is `{id, branches: [{condition, next}]}`. The first branch whose
condition holds is taken, and the last branch is always the default `""`.

The Wayside God's menu branches on `stat:wayside_fade` into four stages that get shorter,
down to a silent stone at 5. Its per-shrine greetings also shorten along the play order.

## lore.json

`categories[]` and `entries[]`: `{id, category, title_en, title_ja, unlock, text_en, text_ja, related: [{kind, id}], trigger_flags?}`.
`related.kind` is one of `area`, `boss`, `enemy`, `item`, `weapon`, `spell_card`, `ending`.
The three ending entries carry `trigger_flags`, which match `endings.json` exactly.

## endings.json

| Section | Notes |
|---|---|
| `stats[]` | world stats used by `stat:` conditions: `{id, range, start, description}` |
| `stat_rules[]` | `{stat, change, when}`: how story events and offerings move the stats |
| `flags[]` | the registry of every story flag: `{id, description}` |
| `flag_patterns[]` | generated flags (`defeated_<boss id>`) |
| `derived_flags[]` | flags the game computes: `{flag, rule, evaluated}` |
| `endings[]` | `{id, names, kind, priority, requires_flags, forbids_flags, consumes_items, text_en[], text_ja[], variants[], final_shot, unlocks}` |

An ending plays when all `requires_flags` hold and no `forbids_flags` do. The player picks
it at the pillar (`fm_ending_choice` in `dialogue.json`); the true-ending choice is shown only
when its conditions hold. `variants[]` either replace a paragraph (`replaces_paragraph`,
0-based, into both `text_en` and `text_ja`) or append one (`appends: true`) when their
`condition` holds.

The true ending needs:
- `returned_maiden_name`: her name was spoken in the pillar.
- `wayside_god_endured`: `wayside_fade <= 3` on reaching the pillar.
- `faith_shared`: at least 20% of all Faith spent at shrines was offered rather than levelled.
