过去的在信息检索方面的数据集主要是同源的数据集。比如全部来自于wiki，这样训练出来的模型泛化性比较差。



<img src="mdPICs/image-20220714203221885.png" alt="image-20220714203221885" style="zoom:50%;" />



在第一个MS MARCO数据集上训练出来的模型，然后在下面17个数据集上直接进行推理。

<img src="mdPICs/image-20220714204431210.png" alt="image-20220714204431210" style="zoom: 67%;" />



计算了领域相似度

<img src="mdPICs/image-20220714204607073.png" alt="image-20220714204607073" style="zoom:50%;" />



检索延迟和索引开销

<img src="mdPICs/image-20220714205119187.png" alt="image-20220714205119187" style="zoom:50%;" />



分析数据集差异

<img src="mdPICs/image-20220714205243461.png" alt="image-20220714205243461" style="zoom:50%;" />



分析领域偏移

<img src="mdPICs/image-20220714205559444.png" alt="image-20220714205559444" style="zoom:50%;" />



结论

<img src="mdPICs/image-20220714205506557.png" alt="image-20220714205506557" style="zoom:50%;" />