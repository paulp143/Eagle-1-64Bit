# Add power-up and special weapon system

## Summary

This adds a power-up system and a special-weapon mechanic to the game. Players can now collect temporary power-ups from pickups in the level and trigger a special weapon when the power meter is charged. The change introduces spawning/collection logic, UI feedback for power meter and active power-ups, and the gameplay behavior for one or more special weapons.

## Why this change

- Adds player progression and tactical options during combat.
- Provides variety and memorable moments (special-weapon usage) while supporting Helldivers on the ground.
- Prepares the codebase for additional power-up types and future balance tweaks.

## What changed (high-level)

- Power-up pickup spawning and lifetime: pickups spawn in the world, have a short lifetime, and can be collected by the player.
- Player power-state and meter: collects/increments a power meter; meter decays or resets on use/death as appropriate.
- Special weapon activation: when the power meter is full (or a threshold reached), player can activate a special weapon (projectile, area effect, or stat buff).
- Effects and balancing: basic damage/area-of-effect and cooldown handling for the special weapon plus temporary stat modifiers for power-ups.
- UI: in-game indicator for current power meter, active power-up icons, and a prompt for activation.
- Spawn tuning and asset placeholders: basic art/sound hooks added for pickup and weapon effects; can be swapped for final assets.
- Tests: added basic playtest hooks and debug logging to exercise spawn/collect/activate flows.

## Implementation notes for reviewers

- Focused on modularity so new power-up types can be added with minimal changes (a power-up registry or class per type).
- Special weapon logic is isolated behind an activation function on the player controller so it can be triggered by input or scripts.
- UI elements are implemented as minimal overlays with hooks to update from the player state.
- No breaking changes to existing player controls; activation uses a new input binding that does not conflict with existing inputs.
- Performance: pickup spawn volume and special-weapon effects are capped; profiling has been considered but not exhaustively performed.

## How to test

1. Start the game and enter a play level where pickups can spawn.
2. Verify pickups appear and expire if uncollected.
3. Move the player over a pickup and confirm:
   - Pickup disappears
   - Power meter increases
   - UI updates (meter fill and/or active power-up icon)
   - Debug log prints a collect event (if dev mode enabled)
4. Fill the power meter to threshold and press the special-weapon input:
   - Special weapon activates (visual/sound feedback)
   - Expected damage/effect occurs on enemies in range
   - Power meter resets or enters cooldown as described in the UI
5. Validate edge cases:
   - Activating when meter not full should do nothing and not crash
   - Player death resets meter/active power-ups as intended
   - Multiple pickups before activation stack appropriately or follow designed behavior
6. Run any new unit or integration tests included in the branch (if applicable).

## Notes for playtesters / balance

- Default damage/radius/duration numbers are conservative — please playtest and provide balance feedback.
- Consider adding rarer/stronger pickups or longer charge mechanics if the special weapon feels too common.

## Files touched (guidance for reviewers)

- Review player input / controller code for activation logic.
- Review spawn logic for pickup lifecycle.
- Review UI code for HUD integration and potential layout conflicts.

If you want, I can list the exact files changed from the branch and include code snippets in this file.

## Checklist before merge

- [ ] Playtested basic pickup → activation flow
- [ ] No obvious performance regressions in pickup-heavy scenes
- [ ] New input binding documented or added to controls settings
- [ ] Art/sound assets finalized or placeholders clearly noted
- [ ] Changelog/README updated with the new feature
- [ ] Any new unit tests added and passing

## Screenshots / GIFs

(Optional) Add a short GIF showing a pickup being collected and the special weapon triggering.

## Changelog entry (suggested)

- Added: Power-up pickups and a special-weapon system that can be charged and activated by the player.
