# Copyright 2019 Xilinx Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# PART OF THIS FILE AT ALL TIMES.

import math

import torch.nn as nn
import torch.utils.model_zoo as model_zoo

__all__ = ['ResNet', 'resnet18', 'resnet34', 'resnet50', 'resnet101',
           'resnet152', 'Quant_ResNet', 'Quant_resnet18']

model_urls = {
    'resnet18': 'https://download.pytorch.org/models/resnet18-5c106cde.pth',
    'resnet34': 'https://download.pytorch.org/models/resnet34-333f7ec4.pth',
    'resnet50': 'https://download.pytorch.org/models/resnet50-19c8e357.pth',
    'resnet101': 'https://download.pytorch.org/models/resnet101-5d3b4d8f.pth',
    'resnet152': 'https://download.pytorch.org/models/resnet152-b121ed2d.pth',
}


def conv3x3(in_planes, out_planes, stride=1):
    "3x3 convolution with padding"
    return nn.Conv2d(in_planes, out_planes, kernel_size=3, stride=stride,
                     padding=1, bias=False)


class BasicBlock(nn.Module):
    expansion = 1

    def __init__(self, inplanes, planes, stride=1, downsample=None):
        super(BasicBlock, self).__init__()
        self.conv1 = conv3x3(inplanes, planes, stride)
        self.bn1 = nn.BatchNorm2d(planes)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = conv3x3(planes, planes)
        self.bn2 = nn.BatchNorm2d(planes)
        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        residual = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)

        if self.downsample is not None:
            residual = self.downsample(x)

        out += residual
        out = self.relu(out)

        return out


class Quant_BasicBlock(nn.Module):
    expansion = 1

    def __init__(self, k1, k2, act_clip_val, inplanes, planes, stride=1, downsample=False, expansion=1):
        super(Quant_BasicBlock, self).__init__()
        self.conv1 = conv3x3(inplanes, planes, stride)
        self.bn1 = nn.BatchNorm2d(planes)

        self.fold1 = SimulatedFoldedBatchNorm(k1, self.conv1, self.bn1, 2.0, 2.0)

        self.relu1 = QuantizekReLU(k2, init_act_clip_val=act_clip_val, dequantize=True, inplace=False, signed=False)

        self.conv2 = conv3x3(planes, planes)
        self.bn2 = nn.BatchNorm2d(planes)
        self.fold2 = SimulatedFoldedBatchNorm(k2, self.conv2, self.bn2, 2.0, 2.0)
        self.relu2 = QuantizekReLU(8, init_act_clip_val=act_clip_val, dequantize=True, inplace=False, signed=True)
        self.relu3 = QuantizekReLU(k2, init_act_clip_val=act_clip_val, dequantize=True, inplace=False, signed=True)
        self.relu4 = QuantizekReLU(8, init_act_clip_val=act_clip_val, dequantize=True, inplace=False, signed=True)
        self.relu5 = QuantizekReLU(7, init_act_clip_val=act_clip_val, dequantize=True, inplace=False, signed=False)
        self.downsample_phase = (stride != 1 or inplanes != planes * expansion)
        if downsample and self.downsample_phase:
            self.downConv = nn.Conv2d(inplanes, planes * expansion, kernel_size=1, stride=stride, bias=False)
            self.downBN = nn.BatchNorm2d(planes * expansion)
            self.downsample = SimulatedFoldedBatchNorm(k1, self.downConv, self.downBN, 2.0, 2.0)
        self.stride = stride

    def forward(self, x):
        residual = x
        x0 = self.relu3(x)
        out = self.fold1(x0)
        out = self.relu1(out)

        out = self.fold2(out)
        out = self.relu2(out)

        # pdb.set_trace()
        # if self.downsample is not None:
        if self.downsample_phase:
            x1 = self.downsample(x0)
            residual = self.relu4(x1)

        out += residual
        out = self.relu5(out)

        return out


class Bottleneck(nn.Module):
    expansion = 4

    def __init__(self, inplanes, planes, stride=1, downsample=None):
        super(Bottleneck, self).__init__()
        self.conv1 = nn.Conv2d(inplanes, planes, kernel_size=1, bias=False)
        self.bn1 = nn.BatchNorm2d(planes)
        self.conv2 = nn.Conv2d(planes, planes, kernel_size=3, stride=stride,
                               padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(planes)
        self.conv3 = nn.Conv2d(planes, planes * 4, kernel_size=1, bias=False)
        self.bn3 = nn.BatchNorm2d(planes * 4)
        self.relu = nn.ReLU(inplace=True)
        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        residual = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)
        out = self.relu(out)

        out = self.conv3(out)
        out = self.bn3(out)

        if self.downsample is not None:
            residual = self.downsample(x)

        out += residual
        out = self.relu(out)

        return out


class ResNet(nn.Module):

    def __init__(self, block, layers, num_classes=1000):
        self.inplanes = 64
        super(ResNet, self).__init__()
        self.conv1 = nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3,
                               bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu = nn.ReLU(inplace=True)
        self.maxpool = nn.MaxPool2d(kernel_size=2, stride=2, padding=0)
        self.layer1 = self._make_layer(block, 64, layers[0])
        self.layer2 = self._make_layer(block, 128, layers[1], stride=2)
        self.layer3 = self._make_layer(block, 256, layers[2], stride=2)
        self.layer4 = self._make_layer(block, 512, layers[3], stride=2)
        self.avgpool = nn.AvgPool2d(7, stride=1)
        self.fc = nn.Linear(512 * block.expansion, num_classes)

        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                m.weight.data.normal_(0, math.sqrt(2. / n))
            elif isinstance(m, nn.BatchNorm2d):
                m.weight.data.fill_(1)
                m.bias.data.zero_()

    def _make_layer(self, block, planes, blocks, stride=1):
        downsample = None
        if stride != 1 or self.inplanes != planes * block.expansion:
            downsample = nn.Sequential(
                nn.Conv2d(self.inplanes, planes * block.expansion,
                          kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(planes * block.expansion),
            )

        layers = []
        layers.append(block(self.inplanes, planes, stride, downsample))
        self.inplanes = planes * block.expansion
        for i in range(1, blocks):
            layers.append(block(self.inplanes, planes))

        return nn.Sequential(*layers)

    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)

        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)

        x = self.avgpool(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)

        return x


class Quant_ResNet(nn.Module):

    def __init__(self, k1, k2, act_clip_val, block, layers, num_classes=1000):
        self.inplanes = 64
        super(Quant_ResNet, self).__init__()
        # self.relu0 = QuantizekReLU(k2, init_act_clip_val=1.4, dequantize=True, inplace=False, signed=True)
        self.relu0 = QuantizekReLU(8, init_act_clip_val=1.4, dequantize=True, inplace=False, signed=True)
        self.conv1 = nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3,
                               bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.fold1 = SimulatedFoldedBatchNorm(k1, self.conv1, self.bn1, 2.0, 2.0)
        self.relu = QuantizekReLU(k2, init_act_clip_val=1.4, dequantize=True, inplace=False, signed=False)
        self.maxpool = nn.MaxPool2d(kernel_size=2, stride=2, padding=0)

        self.layer1 = self.Quant_make_layer(block, k1, k2, act_clip_val, 64, layers[0])
        self.layer2 = self.Quant_make_layer(block, k1, k2, act_clip_val, 128, layers[1], stride=2)
        self.layer3 = self.Quant_make_layer(block, k1, k2, act_clip_val, 256, layers[2], stride=2)
        self.layer4 = self.Quant_make_layer(block, k1, k2, act_clip_val, 512, layers[3], stride=2)
        self.avgpool = nn.AvgPool2d(7, stride=1)
        self.relu_pool = QuantizekReLU(8, init_act_clip_val=1.4, dequantize=True, inplace=False, signed=True)
        self.fc = QuantizekLinear(8.0, 2., 2, 512 * block.expansion, num_classes)
        self.relu_last = QuantizekReLU(8.0, init_act_clip_val=act_clip_val, dequantize=True, inplace=False, signed=True)

        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                m.weight.data.normal_(0, math.sqrt(2. / n))
            elif isinstance(m, nn.BatchNorm2d):
                m.weight.data.fill_(1)
                m.bias.data.zero_()

    def Quant_make_layer(self, block, k1, k2, act_clip_val, planes, blocks, stride=1):
        downsample = False
        if stride != 1 or self.inplanes != planes * block.expansion:
            #    downsample = nn.Sequential(
            #        nn.Conv2d(self.inplanes, planes * block.expansion,
            #                  kernel_size=1, stride=stride, bias=False),
            #        nn.BatchNorm2d(planes * block.expansion),
            #    )
            downsample = True
        #            downsample_fold = SimulatedFoldedBatchNorm(k1, downsample[0], downsample[1], 2.0, 2.0)

        layers = []
        layers.append(block(k1, k2, act_clip_val, self.inplanes, planes, stride, downsample, block.expansion))
        self.inplanes = planes * block.expansion
        for i in range(1, blocks):
            layers.append(block(k1, k2, act_clip_val, self.inplanes, planes))

        return nn.Sequential(*layers)

    def forward(self, x):
        x = self.relu0(x)
        # pdb.set_trace()
        x = self.fold1(x)
        x = self.relu(x)
        x = self.maxpool(x)
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)

        x = self.avgpool(x)
        x = self.relu_pool(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)
        x = self.relu_last(x)

        return x


def Quant_resnet18(k1, k2, act_clip_val, pretrained=False, **kwargs):
    """Constructs a ResNet-18 model.

    Args:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
    """
    model = Quant_ResNet(k1, k2, act_clip_val, Quant_BasicBlock, [2, 2, 2, 2], **kwargs)
    if pretrained:
        model.load_state_dict(model_zoo.load_url(model_urls['resnet18'],map_location=lambda storage, loc: storage.cuda()))
    return model


def resnet18(pretrained=False, **kwargs):
    """Constructs a ResNet-18 model.

    Args:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
    """
    model = ResNet(BasicBlock, [2, 2, 2, 2], **kwargs)
    if pretrained:
        model.load_state_dict(model_zoo.load_url(model_urls['resnet18'],map_location=lambda storage, loc: storage.cuda()))
    return model


def resnet34(pretrained=False, **kwargs):
    """Constructs a ResNet-34 model.

    Args:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
    """
    model = ResNet(BasicBlock, [3, 4, 6, 3], **kwargs)
    if pretrained:
        model.load_state_dict(model_zoo.load_url(model_urls['resnet34'],map_location=lambda storage, loc: storage.cuda()))
    return model


def resnet50(pretrained=False, **kwargs):
    """Constructs a ResNet-50 model.

    Args:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
    """
    model = ResNet(Bottleneck, [3, 4, 6, 3], **kwargs)
    if pretrained:
        model.load_state_dict(model_zoo.load_url(model_urls['resnet50'],map_location=lambda storage, loc: storage.cuda()))
    return model


def resnet101(pretrained=False, **kwargs):
    """Constructs a ResNet-101 model.

    Args:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
    """
    model = ResNet(Bottleneck, [3, 4, 23, 3], **kwargs)
    if pretrained:
        model.load_state_dict(model_zoo.load_url(model_urls['resnet101'],map_location=lambda storage, loc: storage.cuda()))
    return model


def resnet152(pretrained=False, **kwargs):
    """Constructs a ResNet-152 model.

    Args:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
    """
    model = ResNet(Bottleneck, [3, 8, 36, 3], **kwargs)
    if pretrained:
        model.load_state_dict(model_zoo.load_url(model_urls['resnet152'],map_location=lambda storage, loc: storage.cuda()))
    return model
