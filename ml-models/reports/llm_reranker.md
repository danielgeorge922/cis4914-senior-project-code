# rerank gemini.py
Passes top 5 prediction data from a csv file (`runs/retrieval-dinov2-masked/top20/predictions.csv`) with (`query, true, rank, top10, best_match, best_match_cultivar, candidates`; `candidates` is a JSON list of the top 10, each with `cultivar`, `score` and `photo`. The only confidence weight is `score`, the cosine similarity of that cultivar's best-matching photo from another tree, between 0 and 1. It is not a probability, and it is not sent to Gemini; Gemini only gets the top 5 names in order), passes photos of mangos (the masked query photo plus one masked reference photo per candidate, each shrunk to 512 px JPEG), passes cultivars.jsonl mangpo data firectory (`data/reference/cultivar_traits.json`) (empty) for now, and sends to gemini (with what prompt /format exactly: one request per photo, made of the text below, then the query photo, then for each candidate a line `Candidate 1: SAIGON` followed by its reference photo; Gemini must answer as JSON `{"ranking": [5 names]}`, and any names it leaves out get added back in the original order)

> The first photo is a mango of unknown cultivar. After it are 5 candidate cultivars, each shown with a photo of a mango of that cultivar from a different tree. Compare fruit shape, size, skin color, blush, spots and beak. Rank all 5 candidate names from most to least likely to match the first mango. Use the names exactly as given.


## NOTE FOR NOW
asking to rerank the mango outputs with model `gemini-3.5-flash-lite`, output is actually worse than with only the base model as can be seen in `runs/rerank-gemini/metrics.json` (181 photos: top-1 26.5% → 21.5%, top-3 45.9% → 41.4%; Gemini fixed 7 answers and broke 16)


