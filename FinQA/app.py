import copy

import streamlit as st
import datasets
from datasets import load_dataset
import pandas as pd
# st.balloons()
import os
import time
import json
import sys
import traceback
# from utils.normalizer import convert_df_type
# from nsql.nsql_exec import NeuralDB, Executor

# Annotation store file.
store_file = "store_file.txt"

st.title("SKG Data Explorer.")

# Select role
st.header("Preparation")
usr_info = st.selectbox(
    'Select a role',
    ('Chengzu', 'Ziming', 'Wei Li'))

st.write('Hi,', usr_info)

# Choose dataset
pretty_name_mapping = {
    "FinQA": "datasets/finqa"
}
dataset_to_load_pretty = st.selectbox(
    'Dataset',
    tuple(pretty_name_mapping.keys()))

st.write('You selected:', dataset_to_load_pretty)
dataset_to_load = pretty_name_mapping[dataset_to_load_pretty]

wt_exp = st.selectbox(
    'Explanation',
    tuple(['With explanation', 'Without explanation']))

@st.cache
def load_data_split(dataset_to_load, split):
    dataset_split_loaded = load_dataset("./{}.py".format(dataset_to_load), cache_dir="datasets/data")[split]
    return dataset_split_loaded


# Show the title
st.header("Annotate {}".format(dataset_to_load_pretty))

# Select split
split_option = st.selectbox(
    'Split',
    ('train', 'validation', 'test'))

st.write('You selected:', split_option)
split = split_option
# Load the dataset_split
# dataset_split_loaded = load_data_split(dataset_to_load, split)
downloaded_files = {
            "train": "datasets/data/FinQA-main/dataset/train.json",
            'validation': "datasets/data/FinQA-main/dataset/dev.json",
            'test': "datasets/data/FinQA-main/dataset/test.json",
            'private_test': "datasets/data/FinQA-main/dataset/private_test.json",
        }
dataset_split_loaded_with_exp = []
with open(downloaded_files[split_option], encoding="utf-8") as f:
    dataset_split_loaded = json.load(f)
    for dataset_split_loaded_item in dataset_split_loaded:
        explanation = dataset_split_loaded_item['qa']['explanation']
        if wt_exp == 'Without explanation':
            if len(explanation) == 0:
                dataset_split_loaded_with_exp.append(dataset_split_loaded_item)
        else:
            if len(explanation) != 0:
                dataset_split_loaded_with_exp.append(dataset_split_loaded_item)

# TODO: with explanation
dataset_split_loaded = dataset_split_loaded_with_exp

# Select index
number = st.number_input('Insert a index: range from ', min_value=0, max_value=len(dataset_split_loaded) - 1)
st.write('The current index is ', number)
data_index = int(number)


data_item = dataset_split_loaded[data_index]

# Show the question/statement
if dataset_to_load_pretty in ["FinQA"]:
    pre_text = data_item['pre_text']
    post_text = data_item['post_text']
    all_text = pre_text + post_text

    file_name = data_item['filename']

    qa = data_item["qa"]
    query = qa['question']
    explanation = qa["explanation"]
    program = qa['program_re']
    ans = qa['answer']
    gold_inds = qa['gold_inds']
    gold_inds_table = list()
    gold_inds_text = list()

    for ind_key in gold_inds.keys():
        if 'table' in ind_key:
            idx = ind_key.strip("table_")
            gold_inds_table.append(int(idx)-1)
        elif 'text' in ind_key:
            idx = ind_key.strip("text_")
            gold_inds_text.append(int(idx))
    #
    # selected_text = []
    # for idx in gold_inds_text:
    #     selected_text.append(all_text[idx])
    #     if idx < len(pre_text):

    st.subheader(f"FileName: {file_name}")
    query = qa["question"]
    st.subheader("Pre Text:")

    # st.write(" ".join(pre_text))
    st.json({"pre_text": pre_text})

    st.subheader("Table:")
    table = data_item['table']
    # header = table['header']
    # rows = table['rows']
    header = table[0]
    i = 0
    normalized_header = []
    for header_item in header:
        if len(header_item) == 0:
            normalized_header.append(f"None_{str(i)}")
            i += 1
        elif header_item in normalized_header:
            normalized_header.append(header_item + f"_{str(i)}")
        else:
            normalized_header.append(header_item)

    rows = table[1:]
    df = pd.DataFrame(rows, columns=normalized_header)

    def highlight(x):
        return ['background-color: lightgreen;']*len(x)

    try:
        # st.dataframe(df.style.applymap(_is_cell_with_link))
        st.dataframe(df.style.apply(highlight, axis=0, subset=(gold_inds_table, slice(None))))
    except st.errors.StreamlitAPIException as e:
        st.text(e)
        st.text(df)

    st.subheader("Post Text:")
    # st.write("".join(post_text))
    st.json({"post_text": post_text})

if dataset_to_load_pretty in ["FinQA"]:
    st.subheader("Question: {}".format(query))

# Show the answer/entailment
if dataset_to_load_pretty in ["FinQA"]:
    st.subheader("Explanation: {}".format(explanation))
    st.subheader("Answer Program: {}".format(program))
    st.subheader("Answer: {}".format(ans))

st.subheader("Gold Inds:")
st.json(qa['gold_inds'])

# Show the dataset json.
st.subheader("Full info for this dataset item(if you need)")
st.json(data_item)

domain_knowledge = st.text_input("Domain Knowledge: ")
link = st.text_input("link from Investopedia: ")
source = st.multiselect("Knowledge source",
                ("Manual",
                 "Investopedia",
                 "Codex",
                 "FinQA"))

if st.button("Submit"):
    annotation_item = {}
    annotation_item['DK'] = domain_knowledge
    annotation_item['link'] = link
    annotation_item['usr_info'] = usr_info
    annotation_item['dataset'] = dataset_to_load
    annotation_item['split'] = split
    annotation_item['data_item_id'] = data_index
    annotation_item['submit_gmt_time'] = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
    annotation_item['filename'] = file_name
    annotation_item['wt_explanation'] = 1 if wt_exp == "With explanation" else 0
    annotation_item['knowledge_source'] = source

    with open(store_file, "a") as f:
        json.dump(annotation_item, f)
        f.write("\n")

        st.success("Annotation submitted!")
        st.balloons()

if os.path.exists(store_file):
    with open(store_file, "r") as f:
        btn = st.download_button(
            label="Download annotations",
            data=f,
            file_name='store.txt',
            mime='text'
        )
