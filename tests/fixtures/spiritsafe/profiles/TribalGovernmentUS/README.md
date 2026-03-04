# Federally Recognized Tribe

This profile represents a Native American tribe formally recognized by the United States Bureau of Indian Affairs. It provides a comprehensive structure for documenting tribal nomenclature, federal recognition, governmental structure, leadership, geographic information, and cultural attributes.

For detailed guidance on structure, statements, usage patterns, and integration with related profiles, see the [GKC Profiles documentation](https://datadistillery.org/gkc/profiles/).

## Profile Contents

- **profile.yaml** – Entity profile schema defining structure, statements, and validation rules
- **metadata.yaml** – Profile metadata including version and governance information
- **CHANGELOG.md** – Record of profile changes and version history
- **queries/** – SPARQL queries for populating controlled vocabularies (allowed-items lists)

## Known Issues and Limitations

- **Sitelinks**: Currently support English Wikipedia only; future versions may expand to other language editions
- **Geographic coordinates**: Precision constraints are defined but may need adjustment based on tribal privacy policies
- **Tribal subdivisions**: No explicit support for bands, clans, or subdivisions yet

---

## Future Enhancements

Planned additions for future versions:

- Support for historical tribal names and reorganizations
- Properties for treaty relationships and land cessions
- Enhanced support for tribal language and cultural heritage attributes
- Integration with additional external identifiers (Library of Congress, tribal catalogs)

---

## Contributing

To propose changes to this profile:

1. **Fork** the SpiritSafe repository
2. **Create a feature branch**: `git checkout -b profile/tribal-government-update`
3. **Edit** `profiles/TribalGovernmentUS/profile.yaml` and update this README accordingly
4. **Update** `CHANGELOG.md` with a description of your changes
5. **Increment version** in `metadata.yaml` following semantic versioning
6. **Submit a pull request** with a clear explanation of the proposed changes
7. **Await maintainer review** and address feedback

For questions or discussion, open an issue in the [SpiritSafe issue tracker](https://github.com/skybristol/SpiritSafe/issues).

---

## License

This profile is released under the same license as the SpiritSafe repository. Profile structure and documentation are dedicated to the public domain or available under CC0 1.0 Universal where applicable.
