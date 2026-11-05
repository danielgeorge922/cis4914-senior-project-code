# split_v1: one split, grouped by specimen, scored on originals

Every model (classifier, retrieval, Gemini re-rank) is trained and scored on one split built from Kyle's train/test folders, following Daniel's benchmarking standard in `ml-models/README.md`. Kyle split photo by photo, which put Roboflow copies and burst shots of the same fruit on both sides, so scores on his test folder were inflated by near-duplicates.

The rules:

- **The unit is the specimen**: one photo, its augmented and Roboflow copies, its ` (N)` download copies, and burst shots (`IMG_<date>_<time>`, each within 10 seconds of the previous shot, same cultivar folder). A specimen sits in exactly one of train, val and test. Where Kyle split a specimen, it moves to the side holding most of its originals.
- **Val is about 10% of each cultivar's train specimens** (fixed seed). Models and settings are chosen on val; test is scored once, at the end.
- **Val and test are scored on originals only.** Augmented copies are training data.
- **Daniel's 3plus rule**: a cultivar stays only with at least 4 photos and at least 3 specimens, and must appear in all three splits. Dropped cultivars are listed next to the manifest.
- **Fruit (exterior) and leaf are separate leaderboards**, since their cultivar lists differ.
- **The classifier trains on the 12 saved augmented copies with its own random changes turned off**, so no photo is changed twice.
- **Retrieval stays frozen DINOv2 with a gallery of train originals only**, and every retrieval result says so. Augmented copies in the gallery would make val photos match copies of train photos rather than other fruit.

## Considered Options

- Keeping Kyle's photo-by-photo split as is: rejected because of the near-duplicate leakage above.
- Fine-tuning retrieval on augmented copies: deferred; the frozen version is the baseline.
