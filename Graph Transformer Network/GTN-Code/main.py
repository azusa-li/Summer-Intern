import torch
import numpy as np
import torch.nn as nn
import torch.nn.functional as F
from model import GTN
import pdb
import pickle
import argparse
from utils import f1_score

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', type=str, default='ACM',
                        help='Dataset')
    parser.add_argument('--epoch', type=int, default=40,
                        help='Training Epochs')
    parser.add_argument('--node_dim', type=int, default=64,
                        help='Node dimension')
    parser.add_argument('--num_channels', type=int, default=2,
                        help='number of channels')
    parser.add_argument('--lr', type=float, default=0.005,
                        help='learning rate')
    parser.add_argument('--weight_decay', type=float, default=0.001,
                        help='l2 reg')
    parser.add_argument('--num_layers', type=int, default=2,
                        help='number of layer')
    parser.add_argument('--norm', type=str, default='true',
                        help='normalization')
    parser.add_argument('--adaptive_lr', type=str, default='false',
                        help='adaptive learning rate')

    args = parser.parse_args()
    print(args)
    epochs = args.epoch
    node_dim = args.node_dim
    num_channels = args.num_channels
    lr = args.lr
    weight_decay = args.weight_decay
    num_layers = args.num_layers
    norm = args.norm
    adaptive_lr = args.adaptive_lr

    with open('data/' + args.dataset + '/node_features.pkl', 'rb') as f:
        node_features = pickle.load(f)  # (8994, 1902)
    with open('data/' + args.dataset + '/edges.pkl', 'rb') as f:  # 多个异构图的邻接矩阵
        edges = pickle.load(f)
    with open('data/' + args.dataset + '/labels.pkl', 'rb') as f:
        labels = pickle.load(f)
    num_nodes = edges[0].shape[0]
    # 每一个邻接矩阵边的长度是节点总数 有四种边 所以有四个边的邻接矩阵
    # labels 由3个矩阵组成 分别代表训练集验证集测试集 labels一共只有3025个 因为半监督学习就是 一部分数据有标签 大部分没有 通过有的去划分训练集验证集和测试集

    # 将edges组合成一个张量
    for i, edge in enumerate(edges):
        if i == 0:
            A = torch.from_numpy(edge.todense()).type(torch.FloatTensor).unsqueeze(-1)
        else:
            A = torch.cat([A, torch.from_numpy(edge.todense()).type(torch.FloatTensor).unsqueeze(-1)], dim=-1)  # 把四个邻接矩阵按照最后一维拼接起来
    A = torch.cat([A, torch.eye(num_nodes).type(torch.FloatTensor).unsqueeze(-1)], dim=-1)  # 再拼接一个单位阵
    # 相当于A是由五个矩阵拼接起来的张量 torch.Size([8994, 8994, 5])

    node_features = torch.from_numpy(node_features).type(torch.FloatTensor)  # 特征维度1902维
    train_node = torch.from_numpy(np.array(labels[0])[:, 0]).type(torch.LongTensor)
    train_target = torch.from_numpy(np.array(labels[0])[:, 1]).type(torch.LongTensor)
    valid_node = torch.from_numpy(np.array(labels[1])[:, 0]).type(torch.LongTensor)
    valid_target = torch.from_numpy(np.array(labels[1])[:, 1]).type(torch.LongTensor)
    test_node = torch.from_numpy(np.array(labels[2])[:, 0]).type(torch.LongTensor)
    test_target = torch.from_numpy(np.array(labels[2])[:, 1]).type(torch.LongTensor)

    num_classes = torch.max(train_target).item() + 1
    final_f1 = 0
    for l in range(1):
        model = GTN(num_edge=A.shape[-1],  # 边的种类 4+1
                    num_channels=num_channels,
                    w_in=node_features.shape[1],  # 节点特征维数 1902
                    w_out=node_dim,  # 隐层输出维度 64
                    num_class=num_classes,
                    num_layers=num_layers,  # 层数
                    norm=norm)
        if adaptive_lr == 'false':
            optimizer = torch.optim.Adam(model.parameters(), lr=0.005, weight_decay=0.001)
        else:
            optimizer = torch.optim.Adam([{'params': model.weight},
                                          {'params': model.linear1.parameters()},
                                          {'params': model.linear2.parameters()},
                                          {"params": model.layers.parameters(), "lr": 0.5}
                                          ], lr=0.005, weight_decay=0.001)
        loss = nn.CrossEntropyLoss()
        # Train & Valid & Test
        best_val_loss = 10000
        best_test_loss = 10000
        best_train_loss = 10000
        best_train_f1 = 0
        best_val_f1 = 0
        best_test_f1 = 0

        for i in range(epochs):
            for param_group in optimizer.param_groups:
                if param_group['lr'] > 0.005:
                    param_group['lr'] = param_group['lr'] * 0.9
            print('Epoch:  ', i + 1)
            model.zero_grad()
            model.train()  # A (8994, 8994, 5)
            loss, y_train, Ws = model(A, node_features, train_node, train_target)
            train_f1 = torch.mean(
                f1_score(torch.argmax(y_train.detach(), dim=1), train_target, num_classes=num_classes)).cpu().numpy()
            print('Train - Loss: {}, Macro_F1: {}'.format(loss.detach().cpu().numpy(), train_f1))
            loss.backward()
            optimizer.step()
            model.eval()
            # Valid
            with torch.no_grad():
                val_loss, y_valid, _ = model.forward(A, node_features, valid_node, valid_target)
                val_f1 = torch.mean(
                    f1_score(torch.argmax(y_valid, dim=1), valid_target, num_classes=num_classes)).cpu().numpy()
                print('Valid - Loss: {}, Macro_F1: {}'.format(val_loss.detach().cpu().numpy(), val_f1))
                test_loss, y_test, W = model.forward(A, node_features, test_node, test_target)
                test_f1 = torch.mean(
                    f1_score(torch.argmax(y_test, dim=1), test_target, num_classes=num_classes)).cpu().numpy()
                print('Test - Loss: {}, Macro_F1: {}\n'.format(test_loss.detach().cpu().numpy(), test_f1))
            if val_f1 > best_val_f1:
                best_val_loss = val_loss.detach().cpu().numpy()
                best_test_loss = test_loss.detach().cpu().numpy()
                best_train_loss = loss.detach().cpu().numpy()
                best_train_f1 = train_f1
                best_val_f1 = val_f1
                best_test_f1 = test_f1
        print('---------------Best Results--------------------')
        print('Train - Loss: {}, Macro_F1: {}'.format(best_train_loss, best_train_f1))
        print('Valid - Loss: {}, Macro_F1: {}'.format(best_val_loss, best_val_f1))
        print('Test - Loss: {}, Macro_F1: {}'.format(best_test_loss, best_test_f1))
        final_f1 += best_test_f1
