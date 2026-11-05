Status: ready-for-agent

# Retrain on split_v1 and compare classifier, retrieval and Gemini

## Problem Statement

We have new preprocessed and augmented photos for fruit and leaves (Kyle's train/test folders), but none of our models use them. The classifier still trains on the old SharePoint data with its own split and only knows fruit. Retrieval has never been run on the new split. The Gemini trait re-rank has never been scored. There is no leaf model, so the server sends leaf photos to the fruit model. Kyle's test folder also contains Roboflow copies and burst shots of the same fruit, so any score on it today is inflated. We can't say which model is best, and we can't ship a leaf model.

## Solution

One clean split (split_v1) that follows Daniel's benchmarking standard, used by every model. Retrain the classifier on it for both views (exterior fruit and leaf) with all three backbones, run frozen retrieval on it, score Gemini on it, and compare everything with one report. The best classifier per view goes live in the server as the fruit and leaf model.

## User Stories

1. As an ML developer, I want one split shared by every model, so that scores are comparable.
2. As an ML developer, I want every specimen (an original photo plus its augmented copies, Roboflow copies and burst shots) kept in one split, so that no model is tested on a near copy of a train photo.
3. As an ML developer, I want burst shots taken within 10 seconds of each other in the same cultivar folder grouped into one specimen, so that Kyle's test set stops leaking.
4. As an ML developer, I want Roboflow `.rf.` copies treated as copies of their original, so that test is scored on originals only.
5. As an ML developer, I want a validation split carved from train (about 10% of specimens per cultivar), so that I choose models without touching test.
6. As an ML developer, I want validation and test scored on originals only, so that augmented copies never inflate scores.
7. As an ML developer, I want Kyle's train/test assignment kept, so that results stay comparable with his work.
8. As an ML developer, I want cultivar spelling variants merged before splitting, so that one cultivar isn't counted as two.
9. As an ML developer, I want Daniel's rule applied (a cultivar needs at least 4 photos and at least 3 specimens, and must appear in train, validation and test), so that every cultivar can actually be measured.
10. As an ML developer, I want dropped cultivars listed in the report, so that readers know what the benchmark leaves out.
11. As an ML developer, I want the manifest build to stop if any specimen lands in two splits, so that leakage can't slip in silently.
12. As an ML developer, I want the classifier to read split_v1, so that it uses the new data.
13. As an ML developer, I want the classifier to train a leaf view as well as exterior fruit, so that we finally have a leaf model.
14. As an ML developer, I want the classifier trained on originals plus the 12 saved augmented copies with its own random training changes turned off, so that photos aren't modified twice.
15. As an ML developer, I want all three backbones (ResNet50, VGG16, EfficientNetB0) trained per view, so that I can pick the best.
16. As an ML developer, I want training to use a GPU automatically when one is present, so that I can run it on Colab without editing code.
17. As an ML developer, I want to run training on Google Colab, so that 243k images per epoch is practical.
18. As an ML developer, I want retrieval run on split_v1 per view with a gallery of train originals only, so that it's scored on the same split.
19. As a report reader, I want every retrieval result labelled "frozen DINOv2, originals only, no augmentation", so that I don't assume it benefited from augmented data.
20. As an ML developer, I want the Gemini trait re-rank scored on fruit with the main model's top 5, unchanged from how it works today, so that it gets a fair test.
21. As a report reader, I want Gemini shown as its own row in the comparison, so that I can see whether it helps or hurts.
22. As an ML developer, I want every model's output in the same shortlist CSV format, so that one script scores them all.
23. As a report reader, I want each model reported with accuracy, macro F1, per-class precision and recall, confusion matrix, top-k accuracy, inference time and model size, so that the comparison follows Daniel's standard.
24. As a report reader, I want fruit and leaf on separate leaderboards, so that different label sets aren't compared directly.
25. As an ML developer, I want models chosen on validation and test scored once at the end, so that test stays honest.
26. As an app user, I want leaf photos sent to a real leaf model, so that leaf photos actually help identify my tree.
27. As a maintainer, I want the best classifier per view exported as the server's fruit and leaf model, so that the server serves the winners.
28. As a teammate, I want the split and evaluation decisions written in one decision record, so that I can read why things are the way they are.

## Implementation Decisions

- **Split manifest builder (modify).** It builds split_v1 from Kyle's train/test folders. Changes:
  - Specimen key = cultivar + original photo name, after stripping augmented suffixes, Roboflow `.rf.` suffixes and `(N)` copy suffixes.
  - Burst grouping: photos named `IMG_<date>_<time>` in the same cultivar folder and taken within 10 seconds of each other form one specimen.
  - Adds a validation split: about 10% of train specimens per cultivar, with a fixed seed.
  - Validation and test rows that are copies (augmented or Roboflow) are marked so that scoring skips them, or are removed.
  - Applies Daniel's 3plus rule per view: at least 4 photos and at least 3 specimens per cultivar, with every kept cultivar present in all three splits.
  - Writes the list of dropped cultivars.
  - Stops with an error on any specimen leakage across splits.
  - Output columns stay as today, with `val` added as a split value.
- **Classifier training (modify).**
  - Gains a manifest input that reads split_v1 instead of building its own SharePoint split.
  - Supports the leaf view.
  - Trains on train originals plus augmented copies.
  - Online training transforms are off when the manifest already supplies augmented copies.
  - Selects CUDA when available, otherwise CPU.
  - Trains all three backbones per view.
  - Saves runs as today, with the class mapping.
- **Classifier shortlist (unchanged interface).** Writes validation and test shortlists for a run.
- **Retrieval (already in the uncommitted diff).**
  - Reads split_v1 per view.
  - The gallery is train originals only; augmented rows are dropped.
  - Queries validation or test.
  - Writes a shortlist CSV.
  - The Triton export takes a name per view.
- **Gemini trait re-rank (unchanged).** Fruit only, top 5 from the main model, with traits from the reference traits file.
- **Shortlist report (unchanged interface).**
  - Input: query, true, shortlist.
  - Output: Daniel's metric list.
  - Adds inference time and model size if they aren't already reported.
- **Comparison report.** One results summary with fruit and leaf as separate tables. It has rows for each classifier backbone, retrieval and Gemini, and lists the dropped cultivars.
- **Server.** The best classifier per view by validation top-1 is exported to the fruit and leaf model slots. The kind-to-model mapping stops sending leaf photos to the fruit model. Retrieval and Gemini are not wired in.
- **Docs.** The domain terms (tree, cultivar, view, specimen, augmented copy, shortlist, gallery) live in the glossary. A decision record covers the split_v1 evaluation protocol.

## Testing Decisions

- Tests check external behavior only: given input files, what comes out. They don't check internal helpers.
- **Manifest test.** Build split_v1 from a tiny fake folder tree. Check that:
  - Burst shots, `.rf.` copies and augmented copies end up in one specimen.
  - Validation and test contain originals only.
  - A cultivar with fewer than 4 photos or fewer than 3 specimens is dropped and listed.
  - Every kept cultivar appears in all three splits.
  - A forced leak makes the build fail.
- **Shortlist report test.** Score a tiny hand-made shortlist CSV and check top-1, top-k and macro F1 against hand-computed values.
- Prior art: the existing mango_transfer tests in the ml-models tests folder.

## Out of Scope

- Training or fine-tuning the retrieval model (projection head or full DINOv2 fine-tune).
- Wiring retrieval or Gemini into the server.
- Gemini for leaves (there are no leaf traits).
- Combining fruit and leaf scores beyond the server's current per-photo averaging.
- The interior view.
- Getting more of Kyle's data from SharePoint.
- A GPU path for the local AMD integrated graphics.

## Further Notes

- The AMD card on the dev laptop is integrated graphics, so training happens on Colab. The data has to be uploaded to Drive first.
- The old photo-only Gemini re-rank lowered top-1 (26.5% to 21.5%). If the trait version also lowers validation top-1, report that and drop it.
- The old 78-cultivar classifier results are a different benchmark and must not be compared with split_v1 results.
