#!/usr/bin/env python
# encoding: utf-8
"""
Original: https://github.com/SJTU-mxtao/Semantic-Communication-Systems
Original: https://arxiv.org/abs/2205.00271
Revised in 2023/10/01
"""

import os
import imageio

from torch.utils.data import DataLoader
import pandas as pd
import numpy as np
import copy
import torch
from torch import nn

from torch.autograd import Variable
from PIL import Image
import torchvision.transforms as transforms
import torchvision.datasets as datasets

import warnings

import argparse

warnings.filterwarnings("ignore")

epoch_len = 200
compression_rate = 0.3


def get_argparser():
    parser = argparse.ArgumentParser()

    # Dataset Options
    parser.add_argument("--alpha", type=float, default=0.8,
                        help="parameter in loss function")
    parser.add_argument("--pretrain_epoch", type=int, default=0,
                        help='epochs of the pretraining stage')
    parser.add_argument("--random_seed", type=int, default=0,
                        help='seed of random sequence')

    return parser


raw_dim = 28 * 28  # shape of the raw image
manualSeed = 999
batch_size = 32
image_size = 64
nc = 3
nz = 100
ngf = 64
ndf = 64
num_epochs = 100  # number of epochs
lr = 0.0002  # learning rate
beta1 = 0.5
ngpu = 1

os.environ['CUDA_VISIBLE_DEVICES'] = '0'
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

print('device:', device)


def data_tf(x):
    x = x.resize((96, 96), 2)  # shape of x: (96, 96, 3)
    x = np.array(x, dtype='float32') / 255
    x = (x - 0.5) / 0.5
    x = x.transpose((2, 0, 1))
    x = torch.from_numpy(x)
    return x


def conv_relu(in_channels, out_channels, kernel, stride=1, padding=0):
    layer = nn.Sequential(
        nn.Conv2d(in_channels, out_channels, kernel, stride, padding),
        nn.BatchNorm2d(out_channels, eps=1e-3),
        nn.ReLU(True)
    )
    return layer


class inception(nn.Module):
    def __init__(self, in_channel, out1_1, out2_1, out2_3, out3_1, out3_5, out4_1):
        super(inception, self).__init__()
        # the first line
        self.branch1x1 = conv_relu(in_channel, out1_1, 1)

        # the second line
        self.branch3x3 = nn.Sequential(
            conv_relu(in_channel, out2_1, 1),
            conv_relu(out2_1, out2_3, 3, padding=1)
        )

        # the thrid line
        self.branch5x5 = nn.Sequential(
            conv_relu(in_channel, out3_1, 1),
            conv_relu(out3_1, out3_5, 5, padding=2)
        )

        # the fourth line
        self.branch_pool = nn.Sequential(
            nn.MaxPool2d(3, stride=1, padding=1),
            conv_relu(in_channel, out4_1, 1)
        )

    def forward(self, x):
        # forward
        f1 = self.branch1x1(x)
        f2 = self.branch3x3(x)
        f3 = self.branch5x5(x)
        f4 = self.branch_pool(x)
        output = torch.cat((f1, f2, f3, f4), dim=1)
        return output


class googlenet(nn.Module):
    # classifier
    def __init__(self, in_channel, num_classes, verbose=False):
        super(googlenet, self).__init__()
        self.verbose = verbose

        self.block1 = nn.Sequential(
            conv_relu(in_channel, out_channels=64, kernel=7, stride=2, padding=3),
            nn.MaxPool2d(3, 2)
        )
        self.block2 = nn.Sequential(
            conv_relu(64, 64, kernel=1),
            conv_relu(64, 192, kernel=3, padding=1),
            nn.MaxPool2d(3, 2)
        )
        self.block3 = nn.Sequential(
            inception(192, 64, 96, 128, 16, 32, 32),
            inception(256, 128, 128, 192, 32, 96, 64),
            nn.MaxPool2d(3, 2)
        )
        self.block4 = nn.Sequential(
            inception(480, 192, 96, 208, 16, 48, 64),
            inception(512, 160, 112, 224, 24, 64, 64),
            inception(512, 128, 128, 256, 24, 64, 64),
            inception(512, 112, 144, 288, 32, 64, 64),
            inception(528, 256, 160, 320, 32, 128, 128),
            nn.MaxPool2d(3, 2)
        )
        self.block5 = nn.Sequential(
            inception(832, 256, 160, 320, 32, 128, 128),
            inception(832, 384, 182, 384, 48, 128, 128),
            nn.AvgPool2d(2)
        )

        self.classifier = nn.Linear(1024, num_classes)

    def forward(self, x):
        x = self.block1(x)
        if self.verbose:
            print('block 1 output: {}'.format(x.shape))
        x = self.block2(x)
        if self.verbose:
            print('block 2 output: {}'.format(x.shape))
        x = self.block3(x)
        if self.verbose:
            print('block 3 output: {}'.format(x.shape))
        x = self.block4(x)
        if self.verbose:
            print('block 4 output: {}'.format(x.shape))
        x = self.block5(x)
        if self.verbose:
            print('block 5 output: {}'.format(x.shape))

        x = x.view(x.shape[0], -1)
        x = self.classifier(x)
        return x


def get_acc(output, label):
    total = output.shape[0]
    _, pred_label = output.max(1)
    num_correct = (pred_label == label).sum().item()
    return num_correct / total


def merge_images(sources, targets, k=10):
    _, _, h, w = sources.shape
    row = int(np.sqrt(64))
    merged = np.zeros([3, row * h, row * w * 2])

    for idx, (s, t) in enumerate(zip(sources, targets)):
        i = idx // row
        j = idx % row
        merged[:, i * h:(i + 1) * h, (j * 2) * h:(j * 2 + 1) * h] = s
        merged[:, i * h:(i + 1) * h, (j * 2 + 1) * h:(j * 2 + 2) * h] = t

    # matplotlib.pyplot.figure(1)
    # matplotlib.pyplot.imshow(merged.transpose(1, 2, 0) / 2 + 0.5)
    # matplotlib.pyplot.show()
    return merged.transpose(1, 2, 0) / 2 + 0.5  # 逆正则化且改变通道顺序，否则颜色不对


def to_data(x):
    """Converts variable to numpy."""
    if torch.cuda.is_available():
        x = x.cpu()
    return x.data.numpy()


# for rate in range(50):
for lambda_var in range(1):
    opts = get_argparser().parse_args()
    print(opts)
    # torch.manual_seed(opts.random_seed)

    # classifier = get_classifier('googlenet')
    classifier = googlenet(3, 10)
    # classifier.load_state_dict(torch.load('google_net.pkl'))  # load the trained model
    classifier.to(device)
    # SGD or Adam
    optimizer_classifier = torch.optim.Adam(classifier.parameters(), lr=0.01)
    criterion_classifier = nn.CrossEntropyLoss()  # loss of classifier
    for rate in range(1):
        lambda1 = 1 - compression_rate
        lambda2 = compression_rate

        file_path = 'google_net_final-lambda-%.2f.pkl' % lambda1
        if os.path.exists(file_path):
            classifier.load_state_dict(
                torch.load('google_net_final-lambda-%.2f.pkl' % lambda1))
        else:
            classifier.load_state_dict(torch.load('google_net.pkl'))


        class RED_CNN(nn.Module):
            def __init__(self, out_ch=16):
                # coders and AWGN channel
                super(RED_CNN, self).__init__()
                self.conv1 = nn.Conv2d(3, out_ch, kernel_size=2, stride=1, padding=0)
                self.conv2 = nn.Conv2d(out_ch, out_ch, kernel_size=3, stride=2, padding=0)
                self.conv3 = nn.Conv2d(out_ch, out_ch, kernel_size=3, stride=2, padding=0)

                self.tconv3 = nn.ConvTranspose2d(out_ch, out_ch, kernel_size=3, stride=2, padding=0)
                self.tconv4 = nn.ConvTranspose2d(out_ch, out_ch, kernel_size=3, stride=2, padding=0)
                self.tconv5 = nn.ConvTranspose2d(out_ch, 3, kernel_size=2, stride=1, padding=0)

                # self.relu = nn.ReLU()

            def forward(self, x):
                # encoder
                out = self.conv1(x)
                out = self.conv2(out)
                out = self.conv3(out)

                # scale and quantize
                out = out.detach().cpu()
                out_max = torch.max(out)
                out_tmp = copy.deepcopy(torch.div(out, out_max))

                # quantize
                out_tmp = copy.deepcopy(torch.mul(out_tmp, 256))
                out_tmp = copy.deepcopy(out_tmp.clone().type(torch.int))
                out_tmp = copy.deepcopy(out_tmp.clone().type(torch.float32))
                out_tmp = copy.deepcopy(torch.div(out_tmp, 256))

                # print(out_tmp.size())

                out = copy.deepcopy(torch.mul(out_tmp, out_max))

                # add noise
                # out_tmp = out.detach().cpu().numpy()
                # out_square = np.square(out_tmp)
                # aver = np.sum(out_square) / np.size(out_square)

                # snr = 3  # dB
                # snr = 10  # dB
                # aver_noise = aver / 10 ** (snr / 10)
                # noise = torch.randn(size=out.shape) * np.sqrt(aver_noise)

                # out = out + noise

                out = out.to(device)
                out = self.tconv3(out)
                out = self.tconv4(out)
                out = self.tconv5(out)
                return out


        mlp_encoder = RED_CNN()
        file_path = 'semantic_coder.pkl'
        if os.path.exists(file_path):
            mlp_encoder.load_state_dict(torch.load(file_path))
        mlp_encoder.to(device)
        # mlp_mnist = MLP_MNIST()

        transform = transforms.Compose([
            transforms.Resize(image_size),
            transforms.CenterCrop(image_size),
            transforms.ToTensor(),
            transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)),
        ])

        # load data
        train_set = datasets.CIFAR10('./data', train=True, transform=data_tf, download=True)
        train_data = torch.utils.data.DataLoader(train_set, batch_size=64, shuffle=True)
        test_set = datasets.CIFAR10('./data', train=False, transform=data_tf, download=True)
        test_data = torch.utils.data.DataLoader(test_set, batch_size=64, shuffle=False)


        def criterion(x_in, y_in, raw_in):
            out_tmp1 = nn.CrossEntropyLoss()
            out_tmp2 = nn.MSELoss()
            z_in = classifier(x_in)
            # print(x_in.size(), raw_in.size())
            mse_in = lambda2 * out_tmp2(x_in, raw_in)
            # loss_channel = lambda1 * out_tmp1(z_in, y_in) + 5 * lambda2 * mse_in
            loss_channel = opts.alpha * lambda1 * out_tmp1(z_in, y_in) + 5 * lambda2 * mse_in
            # loss_channel = out_tmp2(x_in, raw_in)
            return loss_channel


        def criterion_pretraining(x_in, y_in, raw_in):
            # out_tmp1 = nn.CrossEntropyLoss()
            out_tmp2 = nn.MSELoss()
            z_in = mlp_mnist(x_in)
            mse_in = lambda2 * out_tmp2(x_in, raw_in)
            loss_channel = mse_in
            return loss_channel


        # SGD or Adam
        optimizer = torch.optim.Adam(mlp_encoder.parameters(), 3e-3)

        losses = []
        acces = []
        eval_losses = []
        eval_acces = []
        psnr_all = []
        psnr = None
        acc_real = None

        print('Training Start')
        out = None

        for e in range(opts.pretrain_epoch):
            train_loss = 0
            train_acc = 0
            psnr_aver = 0
            mlp_encoder.train()
            counter = 0
            for im, label in train_data:
                im = Variable(im)
                label = Variable(label)

                im = im.to(device)
                label = label.to(device)
                # classifier = classifier.train()

                out = mlp_encoder(im)
                # print('coding time:', time.process_time())

                out_mnist = classifier(out)
                out_real = classifier(im)

                loss = criterion(out, label, im)
                cr1 = nn.MSELoss()
                mse = cr1(out, im)
                out_np = out.detach().cpu().numpy()

                psnr = 10 * np.log10(1 / mse.detach().cpu().numpy())
                psnr_aver += psnr

                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                # print('optimization time:', time.process_time(), 'counter', counter)

                counter += 1
                if counter >= 32:
                    break

        for e in range(epoch_len):
            train_loss = 0
            train_acc = 0
            psnr_aver = 0
            mlp_encoder.train()
            counter = 0
            for im, label in train_data:
                im = Variable(im)
                label = Variable(label)

                im = im.to(device)
                label = label.to(device)
                # classifier = classifier.train()

                out = mlp_encoder(im)
                # print('coding time:', time.process_time())

                out_mnist = classifier(out)
                out_real = classifier(im)

                loss = criterion(out, label, im)
                cr1 = nn.MSELoss()
                mse = cr1(out, im)
                out_np = out.detach().cpu().numpy()

                psnr = 10 * np.log10(1 / mse.detach().cpu().numpy())
                psnr_aver += psnr

                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                # print('optimization time:', time.process_time(), 'counter', counter)

                counter += 1
                if counter >= 32:
                    break

                train_loss += loss.item()

                # print('shape of out_mnist:', out_mnist.size())
                # print('shape of out_real:', out_real.size())
                _, pred = out_mnist.max(1)
                num_correct = (pred == label).sum().item()
                acc = num_correct / im.shape[0]
                train_acc += acc

                if e % 5 == 0 and counter == 1:
                    im_data = to_data(im)
                    out_data = to_data(out)
                    merged = merge_images(im_data, out_data)
                    # print(merged)

                    # print('lambda 1:', lambda1)
                    # save the images
                    path = os.path.join('images/sample-epoch-%d-lambda-%.2f-%d.png' % (
                        e, lambda1, e))
                    # scipy.misc.imsave(path, merged)

                    imageio.imwrite(path, Image.fromarray(np.uint8(merged * 255)))
                    print('saved %s' % path)

            losses.append(train_loss / counter)
            acces.append(train_acc / counter)
            psnr_all.append(psnr_aver / counter)

            eval_loss = 0
            eval_acc = 0
            mlp_encoder.eval()
            counter = 0
            for im, label in test_data:

                im = Variable(im)
                label = Variable(label)

                im = im.to(device)
                label = label.to(device)

                out = mlp_encoder(im)

                # classifier.eval()
                out_mnist = classifier(out)

                loss = criterion(out, label, im)
                eval_loss += loss.item()

                _, pred = out_mnist.max(1)
                num_correct = (pred == label).sum().item()
                acc = num_correct / im.shape[0]
                eval_acc += acc

                counter += 1
                if counter >= 32:
                    break

            print('epoch: {}, Acc Semantic: {:.6f}, '
                  'PSNR Semantic: {:.6f}'
                  .format(e, eval_acc / counter,
                          psnr_aver / counter))
            if e % 10 == 0:
                torch.save(classifier.state_dict(),
                           'google_net_final-lambda-%.2f.pkl' % lambda1)
                # save the model and results
                torch.save(mlp_encoder.state_dict(), 'semantic_coder.pkl')

        # save the results
        file = ('./CIFAR/MLP_sem_CIFAR/acc_semantic_combining_%.2f_lambda_%.2f.csv' % (
            compression_rate, lambda1))
        data = pd.DataFrame(acces)
        data.to_csv(file, index=False)

        eval_psnr = np.array(psnr_all)
        file = ('./CIFAR/MLP_sem_CIFAR/psnr_semantic_combining_%.2f_lambda_%.2f.csv' % (
            compression_rate, lambda1))
        data = pd.DataFrame(eval_psnr)
        data.to_csv(file, index=False)
