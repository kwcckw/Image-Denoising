import torch
import torchvision
from torch import nn
from PNGAN.util import utility
from PNGAN.util.option import args
from PNGAN.model import ridnet
from torch.nn import DataParallel


class AlignmentLoss(nn.Module):
    def __init__(self, lambda_p=6e-3, lambda_ra=8e-4):
        super(AlignmentLoss, self).__init__()

        self.lambda_p = lambda_p
        self.lambda_ra = lambda_ra

        checkpoint = utility.checkpoint(args)
        ridnet_model = ridnet.Model(args, checkpoint)
        self.ridnet = DataParallel(ridnet_model)
        self.ridnet.eval()

        self.vgg = torchvision.models.vgg16(pretrained=True)
        self.vgg.eval()

        self.loss_l1 = nn.L1Loss(reduction='sum')
        self.loss_l2 = nn.MSELoss(reduction='sum')
        self.sigmoid = nn.Sigmoid()

        self.l1_loss = None
        self.ld_loss = None
        self.lg_loss = None
        self.lp_loss = None

    def forward(self, real_image, fake_image, cd_rn, cd_fn):
        ird = self.ridnet(real_image, 0)
        ifd = self.ridnet(fake_image, 0)
        self.l1_loss = self.loss_l1(ird, ifd)

        dra_rn = self.sigmoid(cd_rn - torch.mean(cd_fn, dim=0))
        dra_fn = self.sigmoid(cd_fn - torch.mean(cd_rn, dim=0))

        self.ld_loss = -torch.mean(torch.mean(torch.log(dra_rn), dim=0) + torch.mean(torch.log(1 - dra_fn)))
        self.lg_loss = -torch.mean(torch.mean(torch.log(1 - dra_rn), dim=0) + torch.mean(torch.log(dra_fn)))
        self.lp_loss = self.loss_l2(self.vgg(ifd), self.vgg(ird))

        return self.l1_loss + self.lambda_p * self.lp_loss + self.lambda_ra * (self.ld_loss + self.lg_loss)