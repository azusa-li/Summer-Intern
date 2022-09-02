import json

import datasets
import os
# import nltk

_CITATION = """\
@article{chen2021finqa,
  title={FinQA: A Dataset of Numerical Reasoning over Financial Data},
  author={Chen, Zhiyu and Chen, Wenhu and Smiley, Charese and Shah, Sameena and Borova, Iana and Langdon, Dylan and Moussa, Reema and Beane, Matt and Huang, Ting-Hao and Routledge, Bryan and Wang, William Yang},
  journal={Proceedings of EMNLP 2021},
  year={2021}
}
"""

_DESCRIPTION = """\
This dataset is obtained from the official release of the FinQA.
"""

_HOMEPAGE = "https://github.com/wenhuchen/HybridQA"

_LICENSE = "MIT License"

_URL = "https://raw.githubusercontent.com/czyssrs/FinQA/main/dataset/"
_TRAINING_FILE = "train.json"
_DEV_FILE = "dev.json"
_TEST_FILE = "test.json"
_PRIVATE_TEST_FILE = "private_test.json"

_URLS = {
    "train": f"{_URL}{_TRAINING_FILE}",
    "dev": f"{_URL}{_DEV_FILE}",
    "test": f"{_URL}{_TEST_FILE}",
    "private_test": f"{_URL}{_PRIVATE_TEST_FILE}"
}

WINDOW_SIZE = 3

class FinQA(datasets.GeneratorBasedBuilder):
    """The FinQA dataset"""

    def _info(self):
        return datasets.DatasetInfo(
            description=_DESCRIPTION,
            features=datasets.Features(
                {
                    "id": datasets.Value("string"),
                    "pre_text": datasets.features.Sequence(datasets.Value("string")),
                    "post_text": datasets.features.Sequence(datasets.Value("string")),
                    "table": {"header": datasets.features.Sequence(datasets.Value("string")),
                              "rows": datasets.features.Sequence(datasets.features.Sequence(datasets.Value("string")))},
                    "qa": {
                        "question": datasets.Value("string"),
                        "answer": datasets.Value("string"),
                        "explanation": datasets.Value("string"),
                        "program": datasets.Value("string"),
                        "gold_inds": datasets.features.Sequence(datasets.Value("string")),
                    },
                }
            ),
            supervised_keys=None,
            homepage=_HOMEPAGE,
            license=_LICENSE,
            citation=_CITATION,
        )

    def _split_generators(self, dl_manager):
        """Returns SplitGenerators."""
        # downloaded_files = dl_manager.download_and_extract(_URLS)
        downloaded_files = {
            "train": "data/FinQA-main/dataset/train.json",
            'dev': "data1/FinQA-main/dataset/dev.json",
            'test': "data/FinQA-main/dataset/test.json",
            'private_test': "data/FinQA-main/dataset/private_test.json",
        }

        return [
            datasets.SplitGenerator(
                name=datasets.Split.TRAIN,
                gen_kwargs={"filepath": downloaded_files["train"]}),
            datasets.SplitGenerator(
                name=datasets.Split.VALIDATION,
                gen_kwargs={"filepath": downloaded_files["dev"]}),
            datasets.SplitGenerator(
                name=datasets.Split.TEST,
                gen_kwargs={"filepath": downloaded_files["test"]}),
        ]

    def _generate_examples(self, filepath):
        """Yields examples."""
        # data_id, question, table_id, gold_result_str
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
            for idx, example in enumerate(data):
                yield idx, {
                    "id": example["id"],
                    "pre_text": example['pre_text'],
                    "post_text": example['post_text'],
                    "table": {"header": example['table'][0],
                              "rows": example['table'][1:]},
                    "qa": {
                        "question": example['qa']['question'],
                        "answer": example['qa']['answer'],
                        "explanation": example['qa']['explanation'],
                        "program": example['qa']['program'],
                        "gold_inds": example['qa']['gold_inds'],
                    },
                }