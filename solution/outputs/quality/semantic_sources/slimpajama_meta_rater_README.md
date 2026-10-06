---
task_categories:
- text-generation
language:
- en
tags:
- pretrain
size_categories:
- 100B<n<1T
---

# Annotated SlimPajama Dataset

## Dataset Description

This dataset contains the **first fully annotated SlimPajama dataset** with comprehensive quality metrics for data-centric large language model research. The dataset includes approximately **580 billion tokens** from the training set of the original SlimPajama dataset, annotated across **25 different quality dimensions**.

**Note**: This dataset contains only the training set portion of the original SlimPajama dataset, which is why the token count is approximately 580B rather than the full 627B tokens.


## Dataset Statistics

- **Total samples**: ~580B tokens from SlimPajama training set
- **Quality metrics**: 25 dimensions across 3 categories
- **Domains**: 7 domains (CommonCrawl, C4, GitHub, Books, ArXiv, Wikipedia, StackExchange)
- **Annotation coverage**: 100% of the training set

## Quality Metrics

The dataset includes 25 quality scores across three main categories:

### 1. Natural Language Quality Signals (11 metrics)
Rule-based measures from RedPajama indicating text naturalness:
- `rps_doc_frac_no_alph_words`: Fraction of words with no alphabetical characters
- `rps_doc_mean_word_length`: Mean word length after normalization
- `rps_doc_frac_unique_words`: Fraction of unique words (degeneracy measure)
- `rps_doc_unigram_entropy`: Entropy of unigram distribution
- `rps_doc_word_count`: Number of words after normalization
- `rps_lines_ending_with_terminal_punctution_mark`: Lines ending with terminal punctuation
- `rps_lines_numerical_chars_fraction`: Ratio of numerical to total characters
- `rps_lines_uppercase_letter_fraction`: Ratio of uppercase to total characters
- `rps_doc_num_sentences`: Number of sentences in content
- `rps_doc_frac_chars_top_2gram`: Fraction of characters in top word 2-gram
- `rps_doc_frac_chars_top_3gram`: Fraction of characters in top word 3-gram

### 2. Data Importance Scores (3 metrics)
DSIR-based importance weights measuring similarity to high-quality domains:
- `dsir_books`: Importance score relative to Books domain
- `dsir_wiki`: Importance score relative to Wikipedia domain
- `dsir_math`: Importance score relative to AutoMathText domain

### 3. Model-based Quality Ratings (11 metrics)

#### Existing Metrics:
- `fineweb_edu`: Educational value (from FineWeb-Edu) - single value in list format
- `ad_en`: Advertisement detection (from WanjuanCC) - logits for binary classification [label_0, label_1]
- `fluency_en`: Fluency assessment (from WanjuanCC) - logits for binary classification [label_0, label_1]
- `qurater`: QuRating scores as a list [Writing Style, Required Expertise, Facts and Trivia, Educational Value]

#### PRRC Framework (Our Contribution):
- `modernbert_professionalism`: Professionalism logits for 6 levels (0-5 scale) - use argmax() to get rating
- `modernbert_readability`: Readability logits for 6 levels (0-5 scale) - use argmax() to get rating
- `modernbert_reasoning`: Reasoning logits for 6 levels (0-5 scale) - use argmax() to get rating
- `modernbert_cleanliness`: Cleanliness logits for 6 levels (0-5 scale) - use argmax() to get rating

## PRRC Framework Details

Our **PRRC** framework introduces four novel dimensions for comprehensive data quality assessment:

- **Professionalism**: Measures the degree of expertise and prerequisite knowledge required to comprehend the text
- **Readability**: Evaluates text clarity, coherence, and ease of understanding
- **Reasoning**: Assesses the complexity of logical reasoning and analytical thinking required
- **Cleanliness**: Evaluates text formatting, completeness, and absence of noise/irrelevant content

Each PRRC dimension uses a 5-point additive rating system, with models achieving F1 scores of 87-92% on test sets.

## Dataset Structure

The dataset structure for each example:

```python
{
    "id": "unique_document_id",
    "content": "Main text content of the document",
    "sub_path": "domain_name",  # e.g., "arxiv", "github", "wikipedia", etc.
    
    # Natural Language Quality Signals (RedPajama-style metrics)
    "rps_doc_frac_no_alph_words": float,
    "rps_doc_mean_word_length": float,
    "rps_doc_frac_unique_words": float,
    "rps_doc_unigram_entropy": float,
    "rps_doc_word_count": int,
    "rps_lines_ending_with_terminal_punctution_mark": float,
    "rps_lines_numerical_chars_fraction": float,
    "rps_lines_uppercase_letter_fraction": float,
    "rps_doc_num_sentences": int,
    "rps_doc_frac_chars_top_2gram": float,
    "rps_doc_frac_chars_top_3gram": float,
    
    # Data Importance Scores (DSIR)
    "dsir_books": float,
    "dsir_wiki": float,
    "dsir_math": float,
    
    # Model-based Quality Ratings
    "fineweb_edu": [float],  # Single value in list
    "ad_en": [float, float],  # [has_ad_logit, no_ad_logit] - use argmax() to get 0-1 rating
    "fluency_en": [float, float],  # [not_fluent_logit, fluent_logit] - use argmax() to get 0-1 rating
    "qurater": [float, float, float, float],  # [Writing Style, Required Expertise, Facts and Trivia, Educational Value]
    
    # PRRC Framework (Our Contribution) - all contain 6 logits for levels 0-5
    "modernbert_professionalism": [float, float, float, float, float, float],  # Use argmax() to get 0-5 rating
    "modernbert_readability": [float, float, float, float, float, float],     # Use argmax() to get 0-5 rating
    "modernbert_reasoning": [float, float, float, float, float, float],       # Use argmax() to get 0-5 rating
    "modernbert_cleanliness": [float, float, float, float, float, float]      # Use argmax() to get 0-5 rating
}
```

## Usage

### Loading the Dataset

```python
from datasets import load_dataset

# Load the full dataset
dataset = load_dataset("opendatalab/SlimPajama-627B-Annotated")

# Load a specific split if available
train_dataset = load_dataset("opendatalab/SlimPajama-627B-Annotated", split="train")
```

### Data Processing and Selection Example

```python
import pandas as pd
import numpy as np
from datasets import load_dataset

# Load dataset
dataset = load_dataset("opendatalab/SlimPajama-627B-Annotated", split="train")

# Convert to pandas for easier manipulation
df = dataset.to_pandas()

# Process PRRC scores (convert logits to ratings using argmax)
df['professionalism_score'] = df['modernbert_professionalism'].apply(lambda x: np.argmax(x))
df['readability_score'] = df['modernbert_readability'].apply(lambda x: np.argmax(x))
df['reasoning_score'] = df['modernbert_reasoning'].apply(lambda x: np.argmax(x))
df['cleanliness_score'] = df['modernbert_cleanliness'].apply(lambda x: np.argmax(x))

# Process binary classification scores
df['advertisement_score'] = df['ad_en'].apply(lambda x: np.argmax(x))  # 0 = has ad, 1 = no ad
df['fluency_score'] = df['fluency_en'].apply(lambda x: np.argmax(x))  # 0 = not fluent, 1 = fluent

# Extract QuRating scores
df['writing_style'] = df['qurater'].apply(lambda x: x[0])
df['required_expertise'] = df['qurater'].apply(lambda x: x[1])
df['facts_trivia'] = df['qurater'].apply(lambda x: x[2])
df['educational_value'] = df['qurater'].apply(lambda x: x[3])

# Extract FineWeb-Edu score
df['fineweb_educational'] = df['fineweb_edu'].apply(lambda x: x[0])


# Example: Multi-dimensional quality score combination (Meta-rater approach)
# Using the learned weights from the Meta-rater paper
weights = {
    'educational_value': 0.0564,  # From qurater[3]
    'rps_doc_frac_no_alph_words': 0.0493,
    'fineweb_educational': 0.0493,
    'rps_lines_uppercase_letter_fraction': 0.0488,
    'facts_trivia': 0.0477,  # From qurater[2]
    'rps_doc_frac_chars_top_3gram': 0.0473,
    'rps_lines_ending_with_terminal_punctution_mark': 0.0473,
    'rps_doc_frac_chars_top_2gram': 0.0471,
    'dsir_wiki': 0.0469,
    'rps_lines_numerical_chars_fraction': 0.0460,
    'rps_doc_num_sentences': 0.0458,
    'dsir_math': 0.0448,
    'reasoning_score': 0.0444,
    'rps_doc_frac_unique_words': 0.0432,
    'rps_doc_word_count': 0.0423,
    'rps_doc_unigram_entropy': 0.0422,
    'dsir_books': 0.0414,
    'professionalism_score': 0.0405,
    'fluency_score': 0.0402,
    'readability_score': 0.0393,
    'required_expertise': 0.0373,  # From qurater[1]
    'advertisement_score': 0.0368,
    'cleanliness_score': 0.0117,
    'rps_doc_mean_word_length': 0.0065,
    'writing_style': 0.0005,  # From qurater[0]
}

# Calculate weighted quality score
quality_score = np.zeros(len(df))
for metric, weight in weights.items():
    if metric in df.columns:
        quality_score += df[metric].values * weight

# Select top-k samples based on quality score
top_k = 10000
top_k_indices = np.argsort(quality_score)[-top_k:]
selected_data = df.iloc[top_k_indices]

print(f"Selected top {top_k} samples using Meta-rater weights")
```


## Applications

This annotated dataset enables:

1. **Data-Centric LLM Research**: Study the impact of different quality dimensions on model performance
2. **Multi-dimensional Data Selection**: Implement sophisticated data selection strategies beyond single-metric approaches
3. **Quality Score Analysis**: Analyze correlations and relationships between different quality metrics
4. **Benchmark Development**: Create standardized benchmarks for data quality assessment
5. **Efficient Pre-training**: Select high-quality subsets for more efficient model training
6. **Domain-specific Analysis**: Compare quality distributions across different domains (ArXiv, GitHub, Wikipedia, etc.)

## Annotation Process

The quality scores were generated using:
- **Rule-based metrics**: Extracted using established heuristics from RedPajama and DSIR
- **Existing model-based ratings**: Applied pre-trained classifiers from FineWeb-Edu, WanjuanCC, and QuRating
- **PRRC ratings**: Generated using Llama-3.3-70B-Instruct for annotation, followed by fine-tuned ModernBERT models for efficient scoring

## 📚 Citation

If you use Meta-rater in your research, please cite our paper:

```bibtex
@article{zhuang2025meta,
  title={Meta-rater: A Multi-dimensional Data Selection Method for Pre-training Language Models},
  author={Zhuang, Xinlin and Peng, Jiahui and Ma, Ren and Wang, Yinfan and Bai, Tianyi and Wei, Xingjian and Qiu, Jiantao and Zhang, Chi and Qian, Ying and He, Conghui},
  journal={arXiv preprint arXiv:2504.14194},
  year={2025}
}
```

## 📄 License

This dataset is released under the same license as the original SlimPajama dataset. Please refer to the original SlimPajama repository for licensing details.

## 🤝 Acknowledgments

This work builds upon:
- **SlimPajama**: The original dataset from Cerebras
- **RedPajama**: Natural language quality signals
- **DSIR**: Data importance scoring methodology  
- **FineWeb-Edu**: Educational value assessment
- **WanjuanCC**: Advertisement and fluency detection
- **QuRating**: Multi-dimensional quality rating framework

## 📞 Contact

- **Project Lead**: Ren Ma (maren@pjlab.org.cn)
- **Corresponding Author**: Conghui He (heconghui@pjlab.org.cn)
- **Issues**: Please use [GitHub Issues](https://github.com/opendatalab/Meta-rater/issues) for questions.

---

<div align="center">

**⭐ Star us on GitHub and HuggingFace if you find Meta-rater useful! ⭐**

Made with ❤️ by the OpenDataLab team

</div>