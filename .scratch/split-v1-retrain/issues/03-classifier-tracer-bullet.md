# 03: Classifier tracer bullet: exterior fruit, EfficientNetB0

**What to build:** One classifier trained from split_v1 exterior (train originals + saved augmented copies, online random transforms off, GPU when present) writes a val shortlist that the shortlist report scores with Daniel's metric list (incl. inference time and model size).

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] Classifier training accepts the split_v1 manifest and a view
- [ ] Uses CUDA when available, else CPU
- [ ] No online augmentation when manifest supplies augmented copies
- [ ] Val and test shortlists written per run
- [ ] Shortlist report test with hand-computed top-1/top-k/macro F1
