# Mango Variety Identification

This project is building an end-to-end mango variety identification system. The `client/` directory contains the Next.js web interface, while `server/` is reserved for the prediction API and application backend.

The `ml-models/` directory contains the machine-learning work: data ingestion, cleaning, manifests, experiments, training, evaluation, and exported model artifacts. The project combines a Hugging Face mango dataset with UF SharePoint mango images, preserving raw data outside Git and generating reproducible transformed datasets for transfer-learning image classifiers.
