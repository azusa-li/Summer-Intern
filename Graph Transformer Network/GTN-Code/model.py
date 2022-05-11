import torch
import numpy as np
import torch.nn as nn
import torch.nn.functional as F
import math
from matplotlib import pyplot as plt
import pdb


class GTN(nn.Module):

    def __init__(self, num_edge, num_channels, w_in, w_out, num_class, num_layers, norm):
        super(GTN, self).__init__()
        self.num_edge = num_edge
        self.num_channels = num_channels
        self.w_in = w_in
        self.w_out = w_out
        self.num_class = num_class
        self.num_layers = num_layers
        self.is_norm = norm
        layers = []
        for i in range(num_layers):  # layers是多个GTlayer组成的 表示要聚合几次meta-path
            if i == 0:
                layers.append(GTLayer(num_edge, num_channels, first=True))  # 第一层gt layer
            else:
                layers.append(GTLayer(num_edge, num_channels, first=False))  # 第二层gt layer
        self.layers = nn.ModuleList(layers)  # layers定义完成
        self.weight = nn.Parameter(torch.Tensor(w_in, w_out))  # GCN的参数
        self.bias = nn.Parameter(torch.Tensor(w_out))
        self.loss = nn.CrossEntropyLoss()
        self.linear1 = nn.Linear(self.w_out * self.num_channels, self.w_out)  # 多个channel拼接在一起 (2*64, 64)
        self.linear2 = nn.Linear(self.w_out, self.num_class)  # 最终输出
        self.reset_parameters()

    def reset_parameters(self):
        nn.init.xavier_uniform_(self.weight)  # gloria初始化
        nn.init.zeros_(self.bias)

    def gcn_conv(self, X, H):
        X = torch.mm(X, self.weight)
        H = self.norm(H, add=True)  # 这里的add设置为true 是因为gcn中邻接矩阵要加上I
        return torch.mm(H.t(), X)

    def normalization(self, H):
        for i in range(self.num_channels):   # H的维度是 (2, 8994, 8994) 要对每一个channel的H做归一化
            if i == 0:
                H_ = self.norm(H[i, :, :]).unsqueeze(0)   # 对H[0]做归一化
            else:
                H_ = torch.cat((H_, self.norm(H[i, :, :]).unsqueeze(0)), dim=0)  # 对H[1]做归一化然后再拼接到一起
        return H_

    def norm(self, H, add=False):
        H = H.t()
        if add == False:
            H = H * ((torch.eye(H.shape[0]) == 0).type(torch.FloatTensor))  # 在这里去掉了对角线上的值 即自连接边 因为自连接边的产生是在Q1Q2相乘得到A^(1)的时候产生的 因此是在这里去掉 也就是得到A^(1)之后 与Q3相乘得到A^(2)之前
        else:
            H = H * ((torch.eye(H.shape[0]) == 0).type(torch.FloatTensor)) + torch.eye(H.shape[0]).type(
                torch.FloatTensor)  # 在进入到gcn的运算的时候 add为true 因为gcn中对邻接矩阵要加上一个单位矩阵I
        deg = torch.sum(H, dim=1)  # shape: (8994,)
        deg_inv = deg.pow(-1)  # 得到 D-1 但此时还是一维的 只是数值是D-1
        deg_inv[deg_inv == float('inf')] = 0  # 对角线原来是0取倒数后变为inf 这里重新置为0
        deg_inv = deg_inv * torch.eye(H.shape[0]).type(torch.FloatTensor)  # 重新转成二维的 即真正的D-1
        H = torch.mm(deg_inv, H)
        H = H.t()
        return H

    def forward(self, A, X, target_x, target):
        A = A.unsqueeze(0).permute(0, 3, 1, 2)  # 加一维之后再变换维度 (1, 8994, 8994, 5) -> (1, 5, 8994, 8994) 个人看法认为是因为 后续的卷积层的计算里面 没有一个concat操作
                                                # 也就是说如果这里是三维送进去 出来的是三维的 可以看conv层的forward函数 没有concat操作 是直接和卷积核相乘的 所以在这里预先把A变成四维的
                                                # 不然没法计算 这个1后续通过计算会变成2 也就是output_channel
        Ws = []
        for i in range(self.num_layers):
            if i == 0:
                H, W = self.layers[i](A)
            else:
                H = self.normalization(H)  # 对A^(1)要先归一化 D-1 * A
                H, W = self.layers[i](A, H)
            Ws.append(W)  # Ws是卷积层的参数

        # H,W1 = self.layer1(A)
        # H = self.normalization(H)
        # H,W2 = self.layer2(A, H)
        # H = self.normalization(H)
        # H,W3 = self.layer3(A, H)
        for i in range(self.num_channels):  # 每个channel做一遍gcn
            if i == 0:
                X_ = F.relu(self.gcn_conv(X, H[i]))  # X是节点特征矩阵
            else:
                X_tmp = F.relu(self.gcn_conv(X, H[i]))
                X_ = torch.cat((X_, X_tmp), dim=1)
        X_ = self.linear1(X_)
        X_ = F.relu(X_)
        y = self.linear2(X_[target_x])
        loss = self.loss(y, target)
        return loss, y, Ws


class GTLayer(nn.Module):

    def __init__(self, in_channels, out_channels, first=True):
        super(GTLayer, self).__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.first = first
        if self.first == True:  # 为什么这里有一个判断是否是第一层的变量 因为第一层要分别两次卷积得到两个Q矩阵 而后续只需要得到一个跟上面的结果拼起来就可以了
            self.conv1 = GTConv(in_channels, out_channels)  # W1
            self.conv2 = GTConv(in_channels, out_channels)  # W2
        else:
            self.conv1 = GTConv(in_channels, out_channels)  # W3

    def forward(self, A, H_=None):
        if self.first == True:
            a = self.conv1(A)   # a.shape (2, 8994, 8994)
            b = self.conv2(A)   # b.shape (2, 8994, 8994)
            H = torch.bmm(a, b)  # 第一次矩阵相乘得到A^(1) 批相乘算法 在这里就是每个channel对应做矩阵乘
            W = [(F.softmax(self.conv1.weight, dim=1)).detach(), (F.softmax(self.conv2.weight, dim=1)).detach()]  # s
        else:
            a = self.conv1(A)
            H = torch.bmm(H_, a)
            W = [(F.softmax(self.conv1.weight, dim=1)).detach()]
        return H, W


class GTConv(nn.Module):

    def __init__(self, in_channels, out_channels):
        super(GTConv, self).__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.weight = nn.Parameter(torch.Tensor(out_channels, in_channels, 1, 1))  # 1*1的卷积核 起到降维的作用
        self.bias = None
        self.scale = nn.Parameter(torch.Tensor([0.1]), requires_grad=False)
        self.reset_parameters()

    def reset_parameters(self):
        n = self.in_channels
        nn.init.constant_(self.weight, 0.1)  # 初始化参数为常量
        if self.bias is not None:
            fan_in, _ = nn.init._calculate_fan_in_and_fan_out(self.weight)
            bound = 1 / math.sqrt(fan_in)
            nn.init.uniform_(self.bias, -bound, bound)

    def forward(self, A):
        '''
        0. 对weight(conv)做softmax
        1. 对每个节点在每个edgeType上进行[2, 5, 1, 1]的卷积操作
        2. 对每个edgeType进行加权求和
        # F.softmax(self.weight, dim=1)对self.weight做softmax:[2, 5, 1, 1]
        # A: [1, 5, 8994, 8994] * [2, 5, 1, 1] -> [2, 5, 8994, 8994]
        # sum: [2, 8994, 8994]
        '''
        A = torch.sum(A * F.softmax(self.weight, dim=1), dim=1)  # 对k=5这一维做了softmax操作
        return A
