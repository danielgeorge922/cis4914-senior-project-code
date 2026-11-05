# 02: Clean split_v1 manifest

**What to build:** Rebuilding split_v1 from Kyle's folders gives a manifest where every specimen (original + augmented copies + Roboflow copies + burst shots within 10 s in the same cultivar folder) sits in exactly one of train/val/test; val is ~10% of train specimens per cultivar; val/test score originals only; spelling variants are merged; cultivars failing Daniel's rule (>=4 photos, >=3 specimens, present in all three splits) are dropped and listed; the build fails on any leak.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Burst shots, `.rf.` copies and `(N)` copies share a specimen
- [ ] `val` split exists, drawn from train with a fixed seed
- [ ] Copies in val/test are excluded from scoring
- [ ] Dropped cultivars written out
- [ ] Build errors on a specimen in two splits
- [ ] Test on a tiny fake folder tree covers the above
