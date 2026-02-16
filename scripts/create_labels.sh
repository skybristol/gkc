#!/bin/bash
# Create distillery stage labels

stages=(
  "mash|Mash tun stage: data ingestion & parsing|F4D4A8"
  "ferment|Fermentation stage: cleaning & normalization|E8D4C4"
  "distill|Distillation stage: reconciliation & linking|DFC0B0"
  "refine|Refinement stage: deduplication & enrichment|D9B8A8"
  "proof|Proofing stage: quality assurance & scoring|CFA89C"
  "blend|Blending stage: multi-source merging|C59890"
  "bottle|Bottling stage: format & export|D4A89C"
)

for stage in "${stages[@]}"; do
  IFS='|' read -r name desc color <<< "$stage"
  echo "Creating label: $name"
  gh label create "$name" --description "$desc" --color "$color"
done

echo "Done! Listing all labels:"
gh label list
