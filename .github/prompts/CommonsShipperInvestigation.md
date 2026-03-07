# Wikimedia Commons Shipper Investigation

## Purpose

This document outlines the research and investigation needed to implement `CommonsShipper` for writing to Wikimedia Commons, including structured data on Commons (SDC) and file uploads.

## Status

**Not Started** - Planning document for future implementation

## Investigation Questions

### 1. Commons API Compatibility

**Question**: Does Wikimedia Commons use the same `wbeditentity` API as Wikibase?

**Why This Matters**:
- If yes, `WikibaseShipper` might work directly or with minor extensions
- If no, we need a completely separate implementation

**Research Tasks**:
- [ ] Review [Commons API documentation](https://commons.wikimedia.org/w/api.php?action=help&modules=wbeditentity)
- [ ] Test `wbeditentity` requests against Commons API
- [ ] Compare request/response schemas with Wikibase
- [ ] Identify Commons-specific parameters or constraints

### 2. Structured Data on Commons (SDC)

**Question**: What are the requirements for writing structured data statements to Commons files?

**Research Tasks**:
- [ ] Review [SDC documentation](https://commons.wikimedia.org/wiki/Commons:Structured_data)
- [ ] Understand the entity model for Commons media files (M-namespace)
- [ ] Map SDC properties to Wikidata properties
- [ ] Identify differences from standard Wikibase item structure
- [ ] Test structured data write operations

### 3. File Upload Workflow

**Question**: How do file uploads integrate with structured data writes?

**Research Tasks**:
- [ ] Review [Commons upload API](https://commons.wikimedia.org/w/api.php?action=help&modules=upload)
- [ ] Understand file upload + metadata workflow
- [ ] Determine if file upload is required before SDC writes
- [ ] Identify file format restrictions and requirements
- [ ] Test upload workflow from Python

### 4. Authentication Requirements

**Question**: Does `WikiverseAuth` work with Commons, or are there special requirements?

**Research Tasks**:
- [ ] Test `WikiverseAuth` login against Commons
- [ ] Check if OAuth is required or optional
- [ ] Identify any Commons-specific authentication scopes
- [ ] Review rate limiting and bot policies

### 5. Commons-Specific Features

**Question**: What Commons-specific capabilities need to be supported?

**Research Tasks**:
- [ ] Category assignments
- [ ] Template usage
- [ ] File page wikitext
- [ ] License metadata requirements
- [ ] Geographic coordinates (if relevant)
- [ ] Captions in multiple languages

## Top 3 Commons Write Operations

Based on GKC use cases, identify the top 3 write operations we need to support:

1. **TBD** - To be determined during investigation
2. **TBD** - To be determined during investigation
3. **TBD** - To be determined during investigation

## API Investigation Checklist

### WikibaseShipper Reusability

- [ ] Can `WikibaseShipper.write_item()` work with M-namespace entities?
- [ ] Can `WikibaseShipper.write_property()` work with Commons properties?
- [ ] Can `WikibaseShipper.plan_batch()` work with Commons entities?
- [ ] Are there Commons-specific validation requirements?

### New Functionality Needed

- [ ] File upload method
- [ ] File metadata handling
- [ ] Category assignment
- [ ] Template application
- [ ] License selection/validation
- [ ] Caption/description in multiple languages

## Architecture Options

### Option A: Extend WikibaseShipper

If Commons API is Wikibase-compatible:

```python
class CommonsShipper(WikibaseShipper):
    """Shipper for Wikimedia Commons writes.
    
    Extends WikibaseShipper for SDC operations and adds file upload.
    """
    
    def upload_file(
        self,
        file_path: str,
        filename: str,
        description: str,
        license: str,
        **kwargs
    ) -> WriteResult:
        """Upload a file to Commons with metadata."""
        # Implementation TBD
    
    def write_file_data(
        self,
        media_id: str,
        payload: dict,
        summary: str,
        **kwargs
    ) -> WriteResult:
        """Write structured data for an M-namespace entity."""
        # Might delegate to write_item() if compatible
```

### Option B: Standalone Implementation

If Commons API is significantly different:

```python
class CommonsShipper(Shipper):
    """Shipper for Wikimedia Commons writes.
    
    Standalone implementation for Commons-specific API.
    """
    
    def upload_file(self, ...) -> WriteResult:
        """Upload a file to Commons."""
    
    def write_structured_data(self, ...) -> WriteResult:
        """Write structured data to a media file."""
    
    def write_categories(self, ...) -> WriteResult:
        """Update category assignments."""
```

### Option C: Hybrid Approach

Use WikibaseShipper for SDC writes, add file-specific methods:

```python
class CommonsShipper:
    """Facade for Wikimedia Commons operations."""
    
    def __init__(self, auth: WikiverseAuth):
        self.auth = auth
        self._sdc_shipper = WikibaseShipper(auth=auth)
    
    def upload_file(self, ...) -> WriteResult:
        """Upload file via Commons API."""
    
    def write_structured_data(self, media_id: str, payload: dict, summary: str) -> WriteResult:
        """Delegate to WikibaseShipper for SDC."""
        return self._sdc_shipper.write_item(
            payload=payload,
            summary=summary,
            entity_id=media_id,
        )
```

## Success Criteria

Investigation is complete when we can answer:

- [ ] Can WikibaseShipper handle SDC writes with no changes?
- [ ] What Commons-specific methods do we need to add?
- [ ] Which architecture option is most appropriate?
- [ ] What are the top 3-5 use cases to implement first?
- [ ] Are there any blocking technical limitations?

## Timeline

**Estimated Research Time**: 8-12 hours

**Breakdown**:
- API documentation review: 2-3 hours
- Hands-on testing with Commons API: 3-4 hours
- SDC-specific investigation: 2-3 hours
- Architecture decision and documentation: 1-2 hours

## Next Steps

1. **Start Investigation**: When GKC needs Commons write capability
2. **Create Test Commons Account**: For API experimentation
3. **Run API Experiments**: Test key operations
4. **Document Findings**: Update this document with results
5. **Design CommonsShipper**: Based on investigation findings
6. **Implement**: Create new issue and PR for implementation

## References

- [Commons API](https://commons.wikimedia.org/w/api.php)
- [Structured Data on Commons](https://commons.wikimedia.org/wiki/Commons:Structured_data)
- [MediaWiki Upload API](https://www.mediawiki.org/wiki/API:Upload)
- [Commons Bot Policy](https://commons.wikimedia.org/wiki/Commons:Bots)
- [Wikibase Data Model](https://www.mediawiki.org/wiki/Wikibase/DataModel)

## Related Work

- **WikibaseShipper**: Current implementation for Wikibase writes
- **MashSourceAdapter**: Pattern for pluggable source implementations
- **Shipper Refactoring**: This investigation emerged from shipper cleanup sprint
