# Mango model experiments

Compare architectures and datasets through shared loaders, training, and evaluation code. This is a scaffold, not an implemented training framework.

## Layout

Keep data/ and models/ side by side. models/ contains architecture code, not weights. datasets/ contains loaders and transforms. training/ and evaluation/ contain reusable execution code. configs/ selects what to run; runs/ stores generated outputs; exports/ stores selected inference artifacts.

A separate mini-project per architecture or dataset encourages duplicated pipelines. Start with individual model files and add subfolders only when necessary.

## Workflow and fair comparisons

1. Place original datasets in data/raw/<dataset>/<version>/ and document sources, licenses, labels, sample IDs, and tree/specimen IDs in data/manifests/.
2. Create fixed split lists in data/splits/. Keep the same tree/specimen, duplicate images, and augmented variants together. Check overlap when combining datasets.
3. Implement reusable loaders in datasets/, architecture definitions in models/, and shared training/evaluation logic in their respective folders.
4. Save experiment configs with dataset/version, split ID, label mapping, input modalities, architecture, input size, augmentation, hyperparameters, and seed.
5. Store each execution in runs/<run-id>/ with its resolved config, code commit, environment/package versions, metrics, checkpoints, and class mapping. Never silently overwrite another run.
6. Compare validation scores in reports/. Repeat promising configurations with multiple seeds. Evaluate the held-out test set after choosing the model/settings.
7. Export the chosen artifact with preprocessing requirements and class mapping for server integration.

Compare architectures using consistent splits, labels, preprocessing policies, and metrics. Fit learned preprocessing only on training data. Different datasets or label sets are separate benchmarks, not a directly comparable leaderboard. Track fruit-only, leaf-only, and combined-input experiments separately.

Record accuracy, macro F1, per-class precision/recall, confusion matrices, inference time, and model size. Add top-k accuracy where appropriate, with k no greater than the class count.

## Git and storage

Commit code, configs, small manifests/splits, tests, and selected reports. Datasets, generated runs, and exports are ignored except for their folder readme.txt files. Share large assets through agreed external storage; record locations and checksums in manifests or reports. Keep credentials and private data out of manifests.

No ML framework has been selected. Add a pinned dependency environment with the first training implementation.

## References

- https://cookiecutter-data-science.drivendata.org/
- https://scikit-learn.org/stable/common_pitfalls.html
