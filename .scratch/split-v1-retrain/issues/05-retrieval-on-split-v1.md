# 05: Retrieval on split_v1 for both views

**What to build:** Frozen DINOv2 runs for exterior and leaf, gallery = train originals only, querying val (and later test), writing scored shortlists labelled "frozen DINOv2, originals only, no augmentation".

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] Retrieval reads split_v1 incl. the val split
- [ ] Exterior and leaf runs with scored val shortlists
- [ ] Reports carry the frozen/unaugmented label
