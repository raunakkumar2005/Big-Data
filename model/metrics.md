# Model results

Dataset: Sentiment140, 600,931 de-duplicated tweets (train 421,089 / validation 59,869 / test 119,973).
Features: unigrams + bigrams, vocabulary 83,808, TF-IDF. Deployed classifier: **Logistic Regression**.

## Test-set comparison

| Classifier | Accuracy | Precision | Recall | F1 | AUC | Train time (s) | Tuned |
|---|---|---|---|---|---|---|---|
| Logistic Regression | 0.776 | 0.7761 | 0.776 | 0.7759 | 0.8458 | 34.9 | regParam=3e-05 |
| Linear SVM | 0.7765 | 0.7769 | 0.7765 | 0.7764 | 0.8446 | 66.2 | regParam=3e-05 |
| Naive Bayes | 0.7699 | 0.77 | 0.7699 | 0.7699 | 0.8356 | 1.1 | smoothing=1 |

## Neutral band (deployed classifier)

| margin | neutral_if_p_between | coverage | accuracy_on_covered |
|---|---|---|---|
| 0.0 | 0.50 - 0.50 | 1.0 | 0.776 |
| 0.05 | 0.45 - 0.55 | 0.9528 | 0.7885 |
| 0.1 | 0.40 - 0.60 | 0.9028 | 0.8018 |
| 0.15 | 0.35 - 0.65 | 0.8415 | 0.8153 |
| 0.2 | 0.30 - 0.70 | 0.7876 | 0.8276 |
| 0.25 | 0.25 - 0.75 | 0.7289 | 0.8394 |
| 0.3 | 0.20 - 0.80 | 0.6648 | 0.851 |

## Hyper-parameter search (validation F1)

| classifier | regParam | val_f1 | fit_seconds | smoothing |
|---|---|---|---|---|
| Logistic Regression | 1e-06 | 0.7604 | 38.9 | nan |
| Logistic Regression | 3e-06 | 0.763 | 37.6 | nan |
| Logistic Regression | 1e-05 | 0.769 | 36.2 | nan |
| Logistic Regression | 3e-05 | 0.7772 | 34.9 | nan |
| Linear SVM | 1e-06 | 0.7718 | 70.1 | nan |
| Linear SVM | 3e-06 | 0.7734 | 67.9 | nan |
| Linear SVM | 1e-05 | 0.7754 | 67.7 | nan |
| Linear SVM | 3e-05 | 0.7766 | 66.2 | nan |
| Naive Bayes | nan | 0.77 | 2.4 | 0.1 |
| Naive Bayes | nan | 0.7702 | 1.1 | 0.3 |
| Naive Bayes | nan | 0.7709 | 1.1 | 1.0 |

## Confusion matrices (rows = true, columns = predicted; negative, positive)

- Logistic Regression: [[45380, 14229], [12649, 47715]]
- Linear SVM: [[45016, 14593], [12219, 48145]]
- Naive Bayes: [[46299, 13310], [14290, 46074]]

Batch scoring on the training machine: 31,010.1 rows/s (119,973 rows in 3.87 s).
