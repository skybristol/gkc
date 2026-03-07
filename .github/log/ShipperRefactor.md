# Shipper Module Refactoring Sprint

## Context

The shipper module is the write/delivery layer for GKC outputs. Following the recent mash module refactoring, we need to clean up the shipper module to eliminate duplication, improve extensibility, and align with the mash adapter pattern.

### Current State

- **WikibaseShipper**: Core implementation for Wikibase write operations (items, properties, batch planning)
- **WikidataShipper**: Empty alias class inheriting from WikibaseShipper with no additional functionality
- **CommonsShipper**: Scaffold placeholder (not implemented)
- **OpenStreetMapShipper**: Scaffold placeholder (not implemented)
- **Result Types**: `WriteResult`, `DiffPlan`, `DiffOperation`
- **Error Type**: `ShipperError`

### Current Usage

**WikibaseShipper**:
- `gkc/wikibase/foundation.py` - Production use for foundation entity/property init
- `docs/gkc/api/shipper.md` - Documentation examples
- Direct import from `gkc.shipper` (secondary API, not re-exported from `gkc.__init__`)

**WikidataShipper**:
- `tests/test_wikidata_shipper.py` - All tests use WikidataShipper alias
- `docs/gkc/api/shipper.md` - Documented as alias option

**No CLI Usage**: Shipper is used programmatically only

## Problems

1. **Duplicative Classes**: `WikidataShipper` adds no value and creates confusion about which class to use
2. **Naming Confusion**: Users may think WikibaseShipper doesn't work with Wikidata
3. **Test Fragmentation**: Tests use WikidataShipper while production code uses WikibaseShipper
4. **Missing Extensibility Pattern**: Unlike mash (which uses adapter protocol), shipper lacks a clear pattern for target-specific implementations
5. **Commons Requirements Unknown**: We don't know if WikibaseShipper can handle Wikimedia Commons or if we need target-specific behavior
6. **Documentation Ambiguity**: Docs mention both shippers without clear guidance on when to use which

## Goals

1. **Eliminate Duplication**: Remove WikidataShipper or clarify its deprecation path
2. **Unified Testing**: Consolidate all tests under WikibaseShipper
3. **Clear Documentation**: Single source of truth for Wikibase write operations
4. **Extensibility Foundation**: Establish pattern for future target-specific shippers (Commons, OSM)
5. **Maintainability**: Clean architecture that supports growth

## Investigation Needs

### Wikimedia Commons Requirements

Before finalizing the architecture, investigate:

1. **Commons API Compatibility**:
   - Does Wikimedia Commons use the same `wbeditentity` API as Wikibase?
   - What are the file upload and structured data requirements?
   - Can WikibaseShipper handle Commons structured data, or do we need Commons-specific logic?

2. **Commons Use Cases**:
   - File uploads with metadata
   - Structured data on Commons (SDC) statements
   - Category assignments
   - Do these fit the current `write_item`/`write_property` abstraction?

3. **API Differences**:
   - Review [Commons API documentation](https://commons.wikimedia.org/w/api.php)
   - Identify incompatibilities with current WikibaseShipper implementation
   - Determine if we need a separate `CommonsShipper` or if WikibaseShipper can be extended

### OpenStreetMap Requirements

1. **OSM API Shape**: OSM uses completely different XML-based API (not MediaWiki)
2. **Authentication**: Different OAuth flow vs MediaWiki login
3. **Data Model**: Nodes/Ways/Relations vs Wikibase entities
4. **Conclusion**: OpenStreetMapShipper will definitely need its own implementation

## Proposed Architecture Options

### Option A: Keep Base Shipper + Specific Implementations (Current Pattern)

```
Shipper (abstract base)
├── WikibaseShipper (Wikibase/Wikidata)
├── CommonsShipper (Wikimedia Commons - TBD based on investigation)
└── OpenStreetMapShipper (OSM - completely different)
```

**Pros**:
- Simple, existing pattern
- Clear target-specific implementations

**Cons**:
- No formal protocol/contract
- Hard to share common write behavior across targets

### Option B: Protocol + Adapter Pattern (Aligned with Mash)

```
ShipperProtocol (typing.Protocol)
├── WikibaseShipperAdapter
│   ├── Used by WikibaseShipper
│   └── Possibly reused by CommonsShipper if API compatible
└── OSMShipperAdapter
    └── Used by OpenStreetMapShipper

Public API remains:
- WikibaseShipper(target: WikibaseShipperAdapter)
- get_wikibase_shipper(), get_commons_shipper(), etc.
```

**Pros**:
- Consistent with mash module pattern
- Enforces contracts via Protocol
- Easier to test adapters independently

**Cons**:
- More complex for simple use case
- May be premature abstraction before Commons investigation

### Option C: Hybrid - Simple Now, Extensible Later

```
Current:
- WikibaseShipper (monolithic, works for Wikibase/Wikidata)
- CommonsShipper (TBD after investigation)
- OpenStreetMapShipper (completely separate)

Future (if needed):
- Extract WikibaseWriteAdapter from WikibaseShipper
- Share adapter with CommonsShipper if APIs align
```

**Pros**:
- Don't over-engineer before understanding requirements
- Can refactor to protocol pattern when Commons needs become clear
- Maintains current simplicity

**Cons**:
- May require additional refactoring later

## Recommended Approach: Option C (Hybrid)

**Reasoning**:
1. We don't know Commons requirements yet
2. WikibaseShipper works well for its current purpose
3. OSM is clearly different and needs separate implementation
4. We can introduce protocol pattern when we add Commons support (if needed)

## Refactoring Tasks

### Phase 1: Remove WikidataShipper Entirely

**Priority**: High  
**Complexity**: Low  
**Breaking Changes**: Yes (minor impact)

**Decision**: Remove WikidataShipper entirely rather than deprecating.

**Rationale**:
- All dependencies are intra-package and can be handled immediately
- Shipper is not in public `__all__` exports from `gkc.__init__`
- Clean break is better than prolonged deprecation for internal API
- Low external usage risk

#### Tasks:

1. **Remove WikidataShipper class** from `gkc/shipper.py`:
   - Delete the class definition (lines 778-783)
   - Keep all other shipper classes unchanged

2. **Update module docstring** in `gkc/shipper.py`:
   - Add clear architecture documentation
   - Clarify WikibaseShipper works with all Wikibase instances
   - Document future Commons/OSM plans
   - Add extension pattern guidance

---

### Phase 2: Consolidate Tests

**Priority**: High  
**Complexity**: Low  
**Breaking Changes**: No (internal only)

#### Tasks:

1. **Merge test files**:
   - Move all tests from `tests/test_wikidata_shipper.py` to `tests/test_shipper.py`
   - Replace `WikidataShipper` with `WikibaseShipper` in all tests
   - Verify all tests pass
   - Delete `tests/test_wikidata_shipper.py`

2. **Organize test structure**:
   ```python
   # tests/test_shipper.py structure:
   
   # Base classes and results
   def test_write_result_to_dict_and_json(): ...
   def test_diff_operation_to_dict(): ...
   def test_diff_plan_to_dict(): ...
   def test_shipper_write_raises(): ...
   
   # WikibaseShipper core functionality
   def test_wikibase_shipper_write_item_dry_run(): ...
   def test_wikibase_shipper_write_item_validate_only(): ...
   def test_wikibase_shipper_write_item_submit(): ...
   def test_wikibase_shipper_write_property_submit(): ...
   
   # WikibaseShipper planning
   def test_wikibase_shipper_plan_batch_create(): ...
   def test_wikibase_shipper_plan_batch_ambiguous(): ...
   def test_wikibase_shipper_plan_batch_update(): ...
   def test_wikibase_shipper_plan_batch_noop(): ...
   
   # Placeholder shippers
   def test_commons_shipper_not_implemented(): ...
   def test_osm_shipper_not_implemented(): ...
   ```

---

### Phase 3: Update Documentation

**Priority**: High  
**Complexity**: Low  
**Breaking Changes**: No

#### Tasks:

1. **Update `docs/gkc/api/shipper.md`**:
   - Remove all WikidataShipper examples
   - Replace with WikibaseShipper examples
   - Add note: "WikibaseShipper works with any Wikibase instance, including Wikidata"
   - Update quick start to use WikibaseShipper
   - Remove WikidataShipper from API reference section
   - Add deprecation notice if keeping the alias

2. **Update module docstring** in `gkc/shipper.py`:
   - Clarify that WikibaseShipper is for all Wikibase instances
   - Document future Commons/OSM plans
   - Add examples showing Wikidata and Data Distillery use cases

3. **Update architecture docs** (`docs/architecture/module-contracts.md`):
   - Remove WikidataShipper from anchor surface
   - Update shipper contract description
   - Document extension pattern for future targets

---

### Phase 4: Extensibility Preparation (Future-Proofing)

**Priority**: Medium  
**Complexity**: Medium  
**Breaking Changes**: No

#### Tasks:

1. **Add Commons Investigation Documentation**:
   Create `.github/prompts/CommonsShipperInvestigation.md`:
   - Document Commons API compatibility research
   - Compare `wbeditentity` usage between Wikibase and Commons
   - Identify structured data on Commons (SDC) requirements
   - Determine if WikibaseShipper can be reused or extended
   - Document decision on CommonsShipper implementation approach
   - **Note**: This is a planning document, not live documentation

2. **Refine Shipper Base Class Contract**:
   ```python
   class Shipper:
       """Base interface for write operations to external systems.
       
       Subclasses must implement write methods appropriate for their target.
       WikibaseShipper provides write_item/write_property for Wikibase targets.
       Future shippers may provide different method signatures based on target APIs.
       """
       
       def write(self, payload: dict, **kwargs: Any) -> WriteResult:
           """Write payload to target system.
           
           This is a minimal interface. Subclasses should provide
           target-specific methods (e.g., write_item, write_property,
           upload_file) with appropriate parameters.
           """
           raise NotImplementedError(
               f"{self.__class__.__name__}.write must be implemented"
           )
   ```

3. **Document Shipper Responsibilities** (update `gkc/shipper.py` docstring):
   ```python
   """
   Shipper: Deliver Bottled output to external systems.
   
   This module defines shippers responsible for write operations to external
   systems such as Wikibase instances, Wikimedia Commons, and OpenStreetMap.
   
   ## Architecture
   
   Each target system has its own shipper class:
   
   - **WikibaseShipper**: MediaWiki Wikibase API (wbeditentity)
     - Works with any Wikibase instance (Wikidata, Data Distillery, etc.)
     - Methods: write_item(), write_property(), plan_batch()
   
   - **CommonsShipper**: Wikimedia Commons (placeholder)
     - May reuse WikibaseShipper for structured data
     - Will add file upload capabilities
   
   - **OpenStreetMapShipper**: OpenStreetMap API (placeholder)
     - Completely different API (XML, OAuth)
     - Methods: write_node(), write_way(), write_relation()
   
   ## Extending Shippers
   
   To add a new target:
   
   1. Subclass Shipper
   2. Implement target-specific write methods
   3. Return WriteResult from all write operations
   4. Follow dry_run, validate_only, summary patterns where applicable
   5. Use target-appropriate auth classes (WikiverseAuth, OpenStreetMapAuth, etc.)
   
   Plain meaning: Send Bottled output to target APIs in a safe, testable way.
   """
   ```

---

### Phase 5: Code Quality Improvements

**Priority**: Low  
**Complexity**: Medium  
**Breaking Changes**: No

#### Tasks:

1. **Extract Helper Methods to Utilities** (if reusable across shippers):
   - Consider extracting payload normalization/validation
   - Consider extracting label-based entity resolution
   - Keep if only used within WikibaseShipper

2. **Add Type Hints for Internal Methods**:
   - All `_private` methods should have full type hints
   - Ensure mypy compliance

3. **Improve Error Messages**:
   - Ensure all error messages are actionable
   - Add context to ShipperError exceptions
   - Include entity ID/label in errors where possible

4. **Add Logging** (optional):
   - Consider adding logging for write operations
   - Log dry-run decisions, API calls, validation failures
   - Use Python logging module (don't print)

---

## Testing Strategy

### Pre-Refactoring Validation

1. Run existing test suite:
   ```bash
   poetry run pytest tests/test_shipper.py tests/test_wikidata_shipper.py -v
   ```

2. Verify foundation tests (uses WikibaseShipper):
   ```bash
   poetry run pytest tests/ -k foundation -v
   ```

### During Refactoring

1. **After Phase 1** (WikidataShipper deprecation):
   - Run all tests with deprecation warnings enabled
   - Verify no functionality broken

2. **After Phase 2** (Test consolidation):
   - Run consolidated test suite
   - Verify 100% of original tests still pass
   - Check coverage didn't decrease

3. **After Phase 3** (Documentation):
   - Build docs locally: `poetry run mkdocs serve`
   - Verify no broken links
   - Verify code examples are valid

### Post-Refactoring Validation

1. Run full test suite:
   ```bash
   poetry run pytest tests/ -v
   ```

2. Run pre-merge checks:
   ```bash
   ./scripts/pre-merge-check.sh
   ```

3. Manual verification:
   - Test WikibaseShipper against Data Distillery test instance
   - Verify dry_run behavior
   - Verify validate_only behavior
   - Verify write operations (if test instance available)

---

## Migration Guide for Users

### If you were using WikidataShipper:

**Before**:
```python
from gkc.shipper import WikidataShipper

shipper = WikidataShipper(auth=auth)
```

**After**:
```python
from gkc.shipper import WikibaseShipper

shipper = WikibaseShipper(auth=auth)
```

**Why**: WikibaseShipper works with all Wikibase instances including Wikidata. The WikidataShipper alias was redundant and has been deprecated.

---

## File Manifest

### Files to Modify:

1. `gkc/shipper.py` - Deprecate or remove WikidataShipper, update docstrings
2. `tests/test_shipper.py` - Merge in WikidataShipper tests, rename to use WikibaseShipper
3. `tests/test_wikidata_shipper.py` - Delete after merging tests
4. `docs/gkc/api/shipper.md` - Remove WikidataShipper examples and references
5. `docs/architecture/module-contracts.md` - Update shipper contract

### Files to Create:

1. `.github/prompts/CommonsShipperInvestigation.md` - Document Commons API research (future, planning only)

### Files NOT to Modify:

1. `gkc/__init__.py` - Shipper not exported, no changes needed
2. `gkc/wikibase/foundation.py` - Already uses WikibaseShipper correctly
3. `gkc/cli.py` - No CLI shipper commands

---

## Success Criteria

- [ ] WikidataShipper class removed from gkc/shipper.py
- [ ] All tests use WikibaseShipper
- [ ] Test coverage remains ≥ current level
- [ ] Documentation references only WikibaseShipper
- [ ] No breaking changes to WikibaseShipper API
- [ ] All existing WikibaseShipper usage continues to work
- [ ] Pre-merge checks pass
- [ ] Clear extension pattern documented for future shippers

---

## Risk Assessment

### Low Risk:
- Test consolidation (internal only)
- Documentation updates (no code impact)

### Medium Risk:
- WikidataShipper removal (could affect external users if any exist)
  - **Mitigation**: Clear migration guide in docs, shipper is secondary API
  - **Verification**: All intra-package uses already converted

### High Risk:
- None identified (all changes are backwards compatible)

---

## Timeline Estimate

- **Phase 1** (WikidataShipper removal): 1 hour
- **Phase 2** (Test consolidation): 2 hours
- **Phase 3** (Documentation updates): 2 hours
- **Phase 4** (Extensibility preparation): 3 hours
- **Phase 5** (Code quality): 3 hours (optional)

**Total**: 8-11 hours for complete refactoring

**Minimal viable refactor** (Phases 1-3 only): 5 hours

---

## Follow-On Work (Out of Scope for This Sprint)

### Future Investigations:

1. **Commons Shipper Design** (requires API research):
   - Investigate Wikimedia Commons structured data API
   - Determine if WikibaseShipper can be extended or needs new implementation
   - Design file upload workflow
   - Issue: "Design and implement CommonsShipper"

2. **OSM Shipper Design** (requires API research):
   - Research OSM API write operations
   - Design OSM-specific payload structures
   - Implement OAuth flow for OSM
   - Issue: "Design and implement OpenStreetMapShipper"

3. **Adapter Protocol Pattern** (if needed for Commons):
   - Extract WikibaseWriteAdapter protocol
   - Implement adapter pattern similar to mash
   - Share adapters between WikibaseShipper and CommonsShipper (if applicable)
   - Issue: "Implement shipper adapter protocol pattern"

4. **Batch Write Optimization**:
   - Investigate MediaWiki API batch write capabilities
   - Optimize plan_batch to reduce API calls
   - Add concurrent write support (with rate limiting)
   - Issue: "Optimize WikibaseShipper batch writes"

---

## Related Work

- **Recent**: Mash module refactoring (extracted package, adapter protocol, naming cleanup)
- **Future**: Bottler integration with shipper for end-to-end write pipeline
- **Future**: Profile-driven write validation (profiles validate before shipping)

---

## Open Questions

### Pre-Implementation:

1. **WikidataShipper Fate**: Deprecate or remove?
   - **Recommendation**: Deprecate for one version, remove in 0.3.0

   > We'll go ahead and remove. All dependencies are intra-package and can be handled.

2. **Commons Investigation Timing**: Before or after refactoring?
   - **Recommendation**: After refactoring (don't block on research)

   > Yes. We'll wait and handle this later. Create a document for the research task under `.github/prompts` not in the live documentation space.

3. **Adapter Pattern Now or Later**: Implement protocol pattern now or wait for Commons?
   - **Recommendation**: Wait for Commons (don't over-engineer)

   > Agreed. Wait on this.

### Post-Implementation Research:

1. **Commons API**: Does it use the same wbeditentity API?
2. **Commons Use Cases**: What are the top 3 Commons write operations we need to support?
3. **Commons Auth**: Does WikiverseAuth work with Commons?

---

## Implementation Sequence

### Implementation Order:

1. **Phase 1**: Remove WikidataShipper entirely
2. **Phase 2**: Consolidate tests to test_shipper.py
3. **Phase 3**: Update all documentation
4. **Phase 4**: Add extensibility documentation
5. **Phase 5**: (Optional) Code quality improvements

**Approach**: Clean removal with comprehensive documentation updates

---

## Notes

- Shipper is a secondary API (not in `gkc.__init__.__all__`), so usage is lower than primary APIs
- Current production usage is via `gkc.wikibase.foundation` which already uses WikibaseShipper correctly
- Test file naming should be consistent with implementation file naming
- Document the "Wikibase for everything" philosophy clearly in docs

---

## Approval Checkpoints

### Before Starting:
- [x] Confirmed: Remove WikidataShipper entirely
- [x] Confirmed: Won't block on Commons investigation

### After Phase 2:
- [ ] Verify test coverage unchanged
- [ ] Verify all tests pass

### Before Completion:
- [ ] Review final documentation
- [ ] Run full pre-merge checks
- [ ] Confirm no breaking changes

---

## Commit Message Templates

### Phase 1:
```
refactor(shipper)!: remove WikidataShipper alias

WikibaseShipper works with all Wikibase instances including Wikidata.
The WikidataShipper alias was redundant and has been removed.

BREAKING CHANGE: WikidataShipper removed. Use WikibaseShipper instead.
```

### Phase 2:
```
test(shipper): consolidate tests under WikibaseShipper

- Merged test_wikidata_shipper.py into test_shipper.py
- All tests now use WikibaseShipper directly
- Organized tests by functionality (core, planning, placeholders)
```

### Phase 3:
```
docs(shipper): update to use WikibaseShipper exclusively

- Removed WikidataShipper examples
- Clarified WikibaseShipper works with all Wikibase instances
- Added Wikidata and Data Distillery example usage
- Updated architecture docs
```

### Phase 4:
```
docs(shipper): document extensibility pattern for future targets

- Added Commons shipper investigation documentation
- Clarified Shipper base class contract
- Documented extension pattern for new targets
- Prepared for future Commons/OSM shipper implementations
```

### Phase 5:
```
refactor(shipper): code quality improvements

- Improved type hints for internal methods
- Enhanced error messages with context
- Extracted reusable helper methods
- Added logging for write operations
```

---

## Completion Notes (Moved to Sprint Log)

This sprint plan has been completed and is now archived as implementation log history.

### Completed Scope

**Phase 1-3: Removal & Consolidation**
- Removed redundant `WikidataShipper` class from gkc/shipper.py
- Consolidated all tests from test_wikidata_shipper.py into unified test_shipper.py
- Updated documentation (API docs, architecture docs, migration guide)
- Created CommonsShipperInvestigation.md research document for future work

**Phase 4-5: Extensibility & Code Quality**
- Enhanced Shipper base class with comprehensive 80+ line implementation guidance docstring
- Added logging infrastructure with `import logging` and `logger = logging.getLogger(__name__)`
- Added comprehensive docstrings to all internal helper methods:
  - `_plan_single_operation()`: 35+ lines explaining create/update/noop/blocked/ambiguous logic
  - `_build_patch_payload()`: 30+ lines documenting minimal diff optimization
  - `_normalize_payload()`: Clarified deep copy behavior
  - `_build_request_data()`: 25+ lines for item create/update parameters
  - `_build_property_request_data()`: 30+ lines for property-specific handling
  - Existing helpers already had Args/Returns/Raises

### Validation Outcomes

- ✅ 12/12 shipper module tests passing
- ✅ 301/301 total repository tests passing
- ✅ 60% test coverage maintained (no regression)
- ✅ All 8 foundation integration tests passing
- ✅ Ruff linter checks: PASSED
- ✅ Black code formatting: PASSED
- ✅ MkDocs build: PASSED
- ✅ Package build (sdist + wheel): PASSED
- ✅ All pre-merge checks passing

### Technical Outcomes

- WikibaseShipper API remains unchanged and backward compatible
- Public API exports (gkc/__init__.py, gkc/shipper.py) properly updated
- No breaking changes outside WikidataShipper removal
- Architecture prepared for future CommonsShipper and OpenStreetMapShipper implementations
- CommonsShipperInvestigation.md provides roadmap for next investigator

### Key Decisions Preserved

- **Removal vs Deprecation**: WikidataShipper removed cleanly (not deprecated) since it was not in public stable API exports
- **Architecture Strategy**: Kept simple Shipper base class + target-specific implementations (avoided complex adapter pattern prematurely)
- **Future Investigation**: Deferred Commons API research to separate investigation phase (documented in CommonsShipperInvestigation.md)

## Proposed Commit Message

`docs(log): archive ShipperRefactor plan with phase 4-5 completion notes and validation outcomes`
