import numpy as np
import os
import torch
import torchvision
import torch.nn as nn
import torch.nn.functional as F

class ConvBlock(nn.Module):
    def __init__(self, args, in_ch, out_ch, bias = False, type = 'up'):
        super().__init__()

        layers = []

        # up or down or same
        if type == 'up':
            if args.generator_upsample:
                layers.append(nn.Upsample(scale_factor = 2))
                layers.append(nn.Conv2d(in_ch, out_ch, 3, 1, 1, bias = bias))
            else:
                layers.append(nn.ConvTranspose2d(in_ch, out_ch, 4, 2, 1, bias = bias))

            # normalization
            if args.normalization == 'inorm':
                layers.append(nn.InstanceNorm2d(out_ch, affine = True, track_running_stats = True))
            elif args.normalization == 'bnorm':
                layers.append(nn.BatchNorm2d(out_ch))

        elif type == 'down':
            layers.append(nn.Conv2d(in_ch, out_ch, 4, 2, 1, bias = bias))

        elif type == 'same':
            layers.append(nn.Conv2d(in_ch, out_ch, 3, 1, 1, bias = bias))

            # normalization
            if args.normalization == 'inorm':
                layers.append(nn.InstanceNorm2d(out_ch, affine = True, track_running_stats = True))
            elif args.normalization == 'bnorm':
                layers.append(nn.BatchNorm2d(out_ch))

        if args.nonlinearity == 'leakyrelu':
            layers.append(nn.LeakyReLU(args.slope))
        else:
            layers.append(nn.ReLU())

        self.main = nn.Sequential(*layers)

    def forward(self, x):
        return self.main(x)




class Generator(nn.Module):
    def __init__(self, configs, in_ch = 128):
        super(Generator, self).__init__()

        self.latent_dim = configs.latent_dim
        self.in_ch = in_ch
        
        layers = []
        # 128
        layers.append(nn.Conv2d(self.latent_dim, self.in_ch, 1, 1,  bias = False))
        layers.append(nn.LeakyReLU(0.02))

        # channel up
        # 256, 512
        for i in range(4):
            out_ch = in_ch * 2 if i<2 else in_ch
            layers.append(ConvBlock(args = configs, in_ch = in_ch, out_ch = out_ch, bias = False, type = 'up'))
            in_ch = out_ch
        
        # channel down
        # 512
        for i in range(3):
            out_ch = in_ch // 2 if i > 1 else in_ch
            layers.append(ConvBlock(args = configs, in_ch = in_ch, out_ch = out_ch, bias = False, type = 'up'))
            in_ch = out_ch
        
        # To RGB
        # 3
        layers.append(nn.Conv2d(out_ch, 3, kernel_size=7, stride=1, padding=3, bias = False))
        layers.append(nn.Tanh())
    
        self.main = nn.Sequential(*layers)
    
    def forward(self, z):
        
        z_tensor = z.view(-1, self.in_ch, 1, 1)
        out = self.main(z_tensor)
        return out        


class Generator_up(nn.Module):
    def __init__(self, configs, in_ch = 128):
        super(Generator_up, self).__init__()
        
        self.latent_dim = configs.latent_dim
        self.in_ch = in_ch
        
        layers = []

        layers.append(ConvBlock(args = configs, in_ch = self.latent_dim, out_ch = in_ch, bias = False, type = 'up'))
        
        # channel up
        # 256, 512, 512, 256, 128, 64
        for out_ch in [128, 256, 512, 512, 256, 128]:
            layers.append(ConvBlock(args = configs, in_ch = in_ch, out_ch = out_ch, bias = False, type = 'up'))
            layers.append(ConvBlock(args = configs, in_ch = out_ch, out_ch = out_ch, bias = False, type = 'same'))
            layers.append(nn.Conv2d(out_ch, out_ch, 3, 1, 1, bias = False))
            in_ch = out_ch
        
        # To RGB
        layers.append(nn.Conv2d(out_ch, 3, kernel_size=7, stride=1, padding=3, bias = False))
        layers.append(nn.Tanh())
    
        self.main = nn.Sequential(*layers)
    
    def forward(self, z):
        z_tensor = z.view(-1, self.latent_dim, 1, 1)
        out = self.main(z_tensor)
        return out




class Discriminator(nn.Module):
    def __init__(self, configs, out_ch = 64):
        super(Discriminator, self).__init__()
        
        layers = []
        layers.append(ConvBlock(args = configs, in_ch = 3, out_ch = 64, bias = True, type = 'down'))
        
        in_ch = out_ch
        # channel up
        for i in range(6):
            out_ch = in_ch * 2 if out_ch < 512 else out_ch
            layers.append(ConvBlock(args = configs, in_ch = in_ch, out_ch = out_ch, bias = True, type = 'down'))
            in_ch = out_ch
        
        # layers.append(nn.Conv2d(cur_ch, cur_ch//2, 1, 1))
        layers.append(nn.Conv2d(in_ch, 1, 1, 1, bias = False))
        
        self.main = nn.Sequential(*layers)
        
    def forward(self, x):
        batch_size = x.size(0)
        out = self.main(x)
        
        return out
        