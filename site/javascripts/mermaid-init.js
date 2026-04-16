// Initialize Mermaid for Material for MkDocs
document$.subscribe(() => {
  mermaid.initialize({
    startOnLoad: true,
    theme: 'default',
    securityLevel: 'loose',
    flowchart: {
      htmlLabels: true,
      curve: 'basis'
    }
  });
  
  // Re-render mermaid diagrams on page navigation
  mermaid.contentLoaded();
});
