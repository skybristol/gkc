# Profiles API

## Status

The historical `gkc.profiles` package is a legacy surface.

For current runtime workflows, JSON Entity Profiles materialized from DD Wikibase semantics are the canonical contract.

Those workflows are owned by:

- `gkc.spirit_safe` for profile artifact loading/materialization.
- `gkc.still_charger` for packet scaffold assembly and charging.
- `gkc.fermenter` for validation/coercion/conformance.
- `gkc.wizard` for interactive wizard runtime.

## Contract Direction

The YAML-era `gkc.profiles` loader/generator/validator path is superseded and targeted for removal unless an explicit retained consumer is approved.

This includes:

- YAML profile loaders.
- YAML form schema generators.
- YAML-first validation pathways.

Do not build new runtime integrations on top of these legacy surfaces.

## Future Scope for a Reimagined Profiles Module

If a future `profiles` module is reintroduced, it should focus on reverse-engineering and profile design support, not runtime validation ownership.

Example future scope:

- Analyze uncovered statements from fermenter outputs.
- Suggest profile extensions toward `GKCEntityProfile` and `GKCEntityStatement` JSON contracts.
- Assist DD Wikibase profile authoring workflows.

## See Also

- [Spirit Safe API](spirit_safe.md)
- [Still Charger API](still_charger.md)
- [Fermenter API](fermenter.md)
- [Wizard Commands](../cli/wizard.md)
- [Module Contracts](../../architecture/module-contracts.md)
