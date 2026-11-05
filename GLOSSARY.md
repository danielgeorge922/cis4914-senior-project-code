# Mango cultivar ID

Identifying which cultivar a mango tree is from photos of its fruit and leaves.

## Language

**Tree**:
One mango plant; the thing a user photographs and wants identified.
_Avoid_: Plant, sample

**Cultivar**:
The named variety a tree belongs to (e.g. Alphonso, Kent); the label the models predict. Many trees share one cultivar.
_Avoid_: Class, variety, label

**View**:
What a photo shows: exterior (outside of the fruit), interior (cut fruit), or leaf.
_Avoid_: Part, kind, organ

**Specimen**:
One original photo together with all its copies (augmented copies, Roboflow copies, burst shots of the same fruit). A specimen is never split across train, validation and test.

**Augmented copy**:
A modified copy of a train photo (flip, rotation, color shift). Only train has them.

**Shortlist**:
The ranked top-k cultivars a model returns for one photo.

**Gallery**:
The train photos retrieval compares a new photo against.
