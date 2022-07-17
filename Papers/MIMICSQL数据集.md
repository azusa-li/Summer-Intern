# 论文

MIMICSQL是针对在WikiSQL和Spider上训练的模型在specific domain上泛化性能差提出的。

- 对于Spider数据集，目前的Question-to-SQL生成任务侧重于生成没有实际值的 "WHERE "条件的SQL查询，这意味着模型只需要预测SQL结构和解析相应的表和列名。然而，即使一个模型能够产生高质量的SQL结构和列，条件值的生成仍然可能是产生正确和可执行的SQL查询的瓶颈。（条件值应该说是某一个属性的具体值的大小的问题。）
- dev和test set的大多数词都出现在train set上，因此泛化到其他领域效果会很差，

因此，将在Spider数据集上训练的模型应用于其他一些领域，如化学、生物和医疗领域，是不可行的。具体到医疗领域，针对EMR数据的Question-to-SQL生成仍未被充分开发。有三个主要挑战：

- 医疗术语缩写。由于医疗术语缩写的广泛使用（有时是错别字），很难将问题中的关键词与数据库模式和表内容中的关键词相匹配
-  条件值的解析和恢复。从问题中提取条件值并根据表内容恢复条件值仍然是一项具有挑战性的工作，特别是在出现医学缩写的情况下。
-  缺少大规模的医疗问题到SQL的数据集。目前，在医疗领域还没有可用于Question-to-SQL任务的数据集。



MIMICSQL的贡献：

- 提出一个两阶段的TRanslate-Edit Model for Question-to-SQL (TREQS)生成模型，它包括三个主要部分。(1)使用基于Seq2Seq的模型将输入的问题翻译成SQL查询，(2)使用关注复制机制编辑生成的查询，以及(3)使用特定任务的查找表进一步编辑。

- 为医疗保健领域的Question-to-SQL任务创建一个大规模的数据集。MIMICSQL有两个子集，其中第一集由模板问题（机器生成）组成，而第二集由自然语言问题（人类注释）组成。据我们所知，这是第一个在多关系表的EMR数据上进行医疗问题回答的数据集。

- 在MIMICSQL数据集上对模板问题和自然语言问题进行了广泛的实验，以证明所提出的模型的有效性。定性和定量的结果都表明，它优于几种基线方法。



MIMICSQL的生成方式：

- 机器生成

  - 问题模板

    - 检索问题是为了直接从表中检索特定的病人信息。两个主要用于检索问题的通用模板包括：
      - 病人Pat（或疾病D，或手术Pro，或处方Pre，或实验室测试L）的H1和H2是什么？
      - 列出所有病人（或疾病，或程序，或药物，或实验室测试）的H1 O1 V1和H2 O2 V2。
    - 推理题是通过结合五个表格的不同组成部分来间接收集病人信息。主要用于推理题的模板包：
      - H1 O1 V1和H2 O2 V2的病人有多少？
      - H2 O2 V2和H3 O3 V3的病人的最大（或最小，或平均）H1是多少？

  - 在问题生成过程中，每个问题的相应SQL查询也同时生成。为了在不改变查询结构的情况下对所有问题做出反应，并方便对问题到SQL模型的SQL预测，我们采用了一个通用的SQL模板 `SELECT $AGG_OP ($AGG_COLUMN)+ FROM $TABLE WHERE ($COND_COLUMN $COND_OP $COND_VAL)+`。这里，上标 "+"表示它允许一个或多个项目。AGG_OP是用于选定的AGG_COLUMN的操作，并且是五个值中的一个，包括 "NULL"（代表没有聚合操作），"COUNT"，"MAX"，"MIN "和 "AVG"。

    AGG_COLUMN是我们对每个问题感兴趣的问题主题，并作为列头存储在表格中。由于一个给定的问题有可能与一个以上的表相关，这里使用的TABLE可以是一个单一的表，也可以是通过连接不同的表得到的新表。WHERE后面的部分代表问题中存在的各种条件，每个条件的形式为`($COND_COLUMN $COND_OP $COND_VAL)`。在查询生成过程中，我们主要考虑五个不同的条件操作，包括"="、">"、"<"、">="和"<="。

- 人工过滤和解析

  - 在三个步骤中对模板问题进行过滤和解析。(1) 为了确保生成的问题在医疗领域是现实的，每个机器生成的问题都要经过验证，以忽略不合理的模板问题。(2) 每个被选中的模板问题都被重新表述为其对应的自然语言（NL）问题。(3) 重新措辞的问题被进一步验证，以确保它们与原始模板问题具有相同的含义。



# 数据

Data Quality:

数据是否是自然的，并且是由领域专家撰写的高质量的。

- 数据来自哪里？如何收集？

- 这些问题和学术问题相似吗?

包含10000个question-sql对 

来自于公开数据集MIMIC III。先机器生成，然后再由八位具有医学专业知识的人来人工过滤。



```sql
question:
Count the number of unmarried patients with a primary disease of acidosis.

sql:
SELECT COUNT ( DISTINCT DEMOGRAPHIC."SUBJECT_ID" ) 
FROM DEMOGRAPHIC 
WHERE DEMOGRAPHIC."MARITAL_STATUS" = "SINGLE" 
	AND DEMOGRAPHIC."DIAGNOSIS" = "ACIDOSIS"
```

domain knowledge:

When asked for the number of patients, return the different ID that match the request?

前面将近170条数据都是这个类型。



**如果不考虑说一些医学方面的专有名词，个人感觉前面问number of patients的问题都不需要domain knowledge，基本上where后面的condition都是问题中的原词，不存在说一个语义的转换。**



```sql
question:
Provide me the birth date and gender for the patient with patient id 17570.

sql:
SELECT DEMOGRAPHIC."DOB",DEMOGRAPHIC."GENDER" 
FROM DEMOGRAPHIC 
WHERE DEMOGRAPHIC."SUBJECT_ID" = "17570"
```

在前面问完number of patients之后就是这样的问题



```sql
question:
Tell me the time of admission and primary disease for the patient with patient id 53707.

sql:
SELECT DEMOGRAPHIC."DIAGNOSIS",DEMOGRAPHIC."ADMITTIME" 
FROM DEMOGRAPHIC 
WHERE DEMOGRAPHIC."SUBJECT_ID" = "53707"
```

when ask about the primary disease, return the diagnosis of patient?