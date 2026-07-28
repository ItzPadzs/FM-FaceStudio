from __future__ import annotations

import argparse
import json
from pathlib import Path


def _torch():
    try:
        import torch
        from torch import nn
        from torch.utils.data import DataLoader, Dataset
        from torchvision import transforms
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Install the training extra: python -m pip install -e .[training]") from exc
    return torch, nn, DataLoader, Dataset, transforms, Image


def build_generator():
    torch, nn, *_ = _torch()

    class Block(nn.Module):
        def __init__(self, a, b, down=True, dropout=False):
            super().__init__()
            op = nn.Conv2d(a, b, 4, 2, 1, bias=False) if down else nn.ConvTranspose2d(a, b, 4, 2, 1, bias=False)
            layers = [op, nn.BatchNorm2d(b), nn.LeakyReLU(0.2, True) if down else nn.ReLU(True)]
            if dropout:
                layers.append(nn.Dropout(0.5))
            self.net = nn.Sequential(*layers)
        def forward(self, x): return self.net(x)

    class Generator(nn.Module):
        def __init__(self):
            super().__init__()
            self.e1 = nn.Sequential(nn.Conv2d(3, 64, 4, 2, 1), nn.LeakyReLU(0.2, True))
            self.e2, self.e3, self.e4 = Block(64,128), Block(128,256), Block(256,512)
            self.e5, self.e6 = Block(512,512), Block(512,512)
            self.d1, self.d2 = Block(512,512,False,True), Block(1024,512,False,True)
            self.d3, self.d4 = Block(1024,256,False), Block(512,128,False)
            self.d5 = Block(256,64,False)
            self.out = nn.Sequential(nn.ConvTranspose2d(128,3,4,2,1), nn.Tanh())
        def forward(self,x):
            e1=self.e1(x); e2=self.e2(e1); e3=self.e3(e2); e4=self.e4(e3); e5=self.e5(e4); e6=self.e6(e5)
            d1=self.d1(e6); d2=self.d2(torch.cat([d1,e5],1)); d3=self.d3(torch.cat([d2,e4],1))
            d4=self.d4(torch.cat([d3,e3],1)); d5=self.d5(torch.cat([d4,e2],1))
            return self.out(torch.cat([d5,e1],1))
    return Generator()


def train(dataset: Path, output: Path, epochs: int, batch_size: int, image_size: int) -> None:
    torch, nn, DataLoader, Dataset, transforms, Image = _torch()
    pairs = json.loads((dataset / "pairs.json").read_text(encoding="utf-8"))
    if len(pairs) < 2:
        raise ValueError("At least two reviewed portrait/UV pairs are required")
    tfm = transforms.Compose([transforms.Resize((image_size,image_size)), transforms.ToTensor(), transforms.Normalize((.5,)*3,(.5,)*3)])
    class Pairs(Dataset):
        def __len__(self): return len(pairs)
        def __getitem__(self,i):
            p=pairs[i]
            return tfm(Image.open(dataset/p["portrait"]).convert("RGB")), tfm(Image.open(dataset/p["uv"]).convert("RGB"))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model=build_generator().to(device); opt=torch.optim.Adam(model.parameters(),lr=2e-4,betas=(.5,.999)); loss_fn=nn.L1Loss()
    loader=DataLoader(Pairs(),batch_size=batch_size,shuffle=True,num_workers=0)
    output.mkdir(parents=True,exist_ok=True)
    for epoch in range(1,epochs+1):
        model.train(); total=0.0
        for portrait,target in loader:
            portrait,target=portrait.to(device),target.to(device); opt.zero_grad(set_to_none=True)
            loss=loss_fn(model(portrait),target); loss.backward(); opt.step(); total += float(loss.item())
        print(f"epoch {epoch}/{epochs} l1={total/max(1,len(loader)):.5f}")
        torch.save({"model":model.state_dict(),"image_size":image_size,"epoch":epoch}, output/"portrait-uv-latest.pt")
    manifest={"format":"facestudio-portrait-uv-v1","checkpoint":"portrait-uv-latest.pt","image_size":image_size,"pairs":len(pairs)}
    (output/"model-manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")


def main() -> int:
    p=argparse.ArgumentParser(description="Train FaceStudio portrait-to-FM-UV model")
    p.add_argument("dataset",type=Path); p.add_argument("--output",type=Path,required=True)
    p.add_argument("--epochs",type=int,default=100); p.add_argument("--batch-size",type=int,default=2); p.add_argument("--image-size",type=int,default=512)
    a=p.parse_args(); train(a.dataset,a.output,a.epochs,a.batch_size,a.image_size); return 0

if __name__ == "__main__": raise SystemExit(main())
