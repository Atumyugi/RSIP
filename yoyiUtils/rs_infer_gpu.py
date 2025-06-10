'''
_______________#########_______________________ 
______________############_____________________ 
______________#############____________________ 
_____________##__###########___________________ 
____________###__######_#####__________________ 
____________###_#######___####_________________ 
___________###__##########_####________________ 
__________####__###########_####_______________ 
________#####___###########__#####_____________ 
_______######___###_########___#####___________ 
_______#####___###___########___######_________ 
______######___###__###########___######_______ 
_____######___####_##############__######______ 
____#######__#####################_#######_____ 
____#######__##############################____ 
___#######__######_#################_#######___ 
___#######__######_######_#########___######___ 
___#######____##__######___######_____######___ 
___#######________######____#####_____#####____ 
____######________#####_____#####_____####_____ 
_____#####________####______#####_____###______ 
______#####______;###________###______#________ 
________##_______####________####______________ 

Author: yoyi
Date: 2024-03-09 13:46:29
LastEditors: yoyi
Description: 解译通用类
'''

from abc import abstractmethod
import albumentations
from albumentations.pytorch import ToTensorV2
from torch.utils.data import Dataset, DataLoader
import torch
from torchvision import transforms
import rasterio
from rasterio.windows import Window
import numpy as np



class RsInferDataSet(Dataset):
    """自定义数据集"""
    def __init__(self, images_path, patch=512, overlap=0.1, transform=None):
        self.images_path = images_path
        self.patchSize = patch
        self.overlap = overlap
        self.img_transform = transform
        self._get_patch_index()

    def __len__(self):
        return len(self.x_y_index_list)

    def __getitem__(self, item):
        img = self.dataset.read(
            window=Window(self.x_y_index_list[item][0], self.x_y_index_list[item][1], self.patchSize, self.patchSize))
        if img.max() > 0:
            if self.img_transform is not None:
                img = self.img_transform(img.transpose((1, 2, 0)))
            return img, [self.result_index_list[item], self.result_size_list[item], self.patch_index_list[item]]
        else:
            return 0
        
    def _get_patch_index(self):
        self.dataset = rasterio.open(self.images_path, sharing=True)
        self.height = self.dataset.height
        self.width = self.dataset.width
        self.coor_transform = self.dataset.transform
        print([self.coor_transform[0],self.coor_transform[1],self.coor_transform[2],self.coor_transform[3],self.coor_transform[4],self.coor_transform[5]])
        self.crs = self.dataset.crs
        stride = int(self.patchSize * (1 - self.overlap))
        h_step = (self.height - self.patchSize) // stride + 1
        w_step = (self.width - self.patchSize) // stride + 1
        h_index_list = [stride * i for i in range(h_step)]
        w_index_list = [stride * i for i in range(w_step)]
        if (self.height - self.patchSize) % stride > 0:
            h_index_list.append(self.height - self.patchSize)
        if (self.width - self.patchSize) % stride > 0:
            w_index_list.append(self.width - self.patchSize)
        self.x_y_index_list = [[x, y] for y in h_index_list for x in w_index_list]
        # 推理后写入切片的左上角索引，和写入大小
        self.result_index_list = []
        self.result_size_list = []
        self.patch_index_list = []
        overlap_pixel = int(self.overlap / 2 * self.patchSize)
        for index in self.x_y_index_list:
            y = index[1]
            x = index[0]
            if y == 0:
                if x == 0:
                    self.result_index_list.append([0, 0])
                    self.result_size_list.append([self.patchSize, self.patchSize])
                    self.patch_index_list.append([0, 0])
                else:
                    self.result_index_list.append([x + overlap_pixel, 0])
                    self.result_size_list.append([self.patchSize - overlap_pixel, self.patchSize])
                    self.patch_index_list.append([overlap_pixel, 0])
            else:
                if x == 0:
                    self.result_index_list.append([0, y + overlap_pixel])
                    self.result_size_list.append([self.patchSize, self.patchSize - overlap_pixel])
                    self.patch_index_list.append([0, overlap_pixel])
                else:
                    self.result_index_list.append([x + overlap_pixel, y + overlap_pixel])
                    self.result_size_list.append([self.patchSize - overlap_pixel, self.patchSize - overlap_pixel])
                    self.patch_index_list.append([overlap_pixel, overlap_pixel])

    @staticmethod
    def collate_fn(batch):
        batch = [i for i in batch if i != 0]
        if len(batch) > 0:
            images, labels = tuple(zip(*batch))
            try:
                images = torch.stack(images, dim=0)
            except:
                images = torch.stack([torch.Tensor(i) for i in images], dim=0)
            return images, labels
        else:
            return [], []
        
class RsInferChangeDataSet(RsInferDataSet):
    def __init__(self, images_path,post_images_path, patch=512, overlap=0.1):
        self.images_path = images_path
        self.post_images_path = post_images_path
        self.patchSize = patch
        self.overlap = overlap
        self.img_transform = albumentations.Compose([
            albumentations.Normalize(),
            ToTensorV2(),
        ], additional_targets={'image_2': 'image'})
        self._get_patch_index()

    def __len__(self):
        return len(self.x_y_index_list)

    def __getitem__(self, item):
        img = self.dataset.read(
            window=Window(self.x_y_index_list[item][0], self.x_y_index_list[item][1], self.patchSize, self.patchSize))
        img_post = self.dataset_post.read(
            window=Window(self.x_y_index_list[item][0], self.x_y_index_list[item][1], self.patchSize, self.patchSize))
        if img.max() > 0 and img_post.max() > 0:
            img = img.transpose((1, 2, 0))
            img_post = img_post.transpose((1, 2, 0))
            transformed_data = self.img_transform(image=img, image_2=img_post)
            img, img_post = transformed_data['image'], transformed_data['image_2']
            return img, img_post, [self.result_index_list[item], self.result_size_list[item], self.patch_index_list[item]]
        else:
            return 0

    def _get_patch_index(self):
        self.dataset = rasterio.open(self.images_path, sharing=True)
        self.dataset_post = rasterio.open(self.post_images_path,sharing=True)
        self.height = self.dataset.height
        self.width = self.dataset.width
        self.coor_transform = self.dataset.transform
        self.crs = self.dataset.crs
        stride = int(self.patchSize * (1 - self.overlap))
        h_step = (self.height - self.patchSize) // stride + 1
        w_step = (self.width - self.patchSize) // stride + 1
        h_index_list = [stride * i for i in range(h_step)]
        w_index_list = [stride * i for i in range(w_step)]
        if (self.height - self.patchSize) % stride > 0:
            h_index_list.append(self.height - self.patchSize)
        if (self.width - self.patchSize) % stride > 0:
            w_index_list.append(self.width - self.patchSize)
        self.x_y_index_list = [[x, y] for y in h_index_list for x in w_index_list]
        # 推理后写入切片的左上角索引，和写入大小
        self.result_index_list = []
        self.result_size_list = []
        self.patch_index_list = []
        overlap_pixel = int(self.overlap / 2 * self.patchSize)
        for index in self.x_y_index_list:
            y = index[1]
            x = index[0]
            if y == 0:
                if x == 0:
                    self.result_index_list.append([0, 0])
                    self.result_size_list.append([self.patchSize, self.patchSize])
                    self.patch_index_list.append([0, 0])
                else:
                    self.result_index_list.append([x + overlap_pixel, 0])
                    self.result_size_list.append([self.patchSize - overlap_pixel, self.patchSize])
                    self.patch_index_list.append([overlap_pixel, 0])
            else:
                if x == 0:
                    self.result_index_list.append([0, y + overlap_pixel])
                    self.result_size_list.append([self.patchSize, self.patchSize - overlap_pixel])
                    self.patch_index_list.append([0, overlap_pixel])
                else:
                    self.result_index_list.append([x + overlap_pixel, y + overlap_pixel])
                    self.result_size_list.append([self.patchSize - overlap_pixel, self.patchSize - overlap_pixel])
                    self.patch_index_list.append([overlap_pixel, overlap_pixel])

    @staticmethod
    def collate_fn(batch):
        batch = [i for i in batch if i != 0]
        if len(batch) > 0:
            images,images_post, labels = tuple(zip(*batch))
            try:
                images = torch.stack(images, dim=0)
            except:
                images = torch.stack([torch.Tensor(i) for i in images], dim=0)
            try:
                images_post = torch.stack(images_post, dim=0)
            except:
                images_post = torch.stack([torch.Tensor(i) for i in images_post], dim=0)
            return images,images_post, labels
        else:
            return [],[],[]

class RsInference:
    def __init__(self,
                 class_num=2,  # 包含背景
                 patch=512,
                 overlap=0.1,
                 batch_size=8,
                 num_workers=0,
                 need_probability_map: bool = False,
                 need_save_hard:bool = False,
                 nodata=0,  # nodata=None
                 transform={'mean': (0.709, 0.381, 0.224), 'std': ((0.127, 0.079, 0.043))}):
        self.patch = patch
        self.overlap = overlap
        self.batch_size = batch_size
        self.num_workers = num_workers
        if transform:
            self.data_transform = transforms.Compose([transforms.ToTensor(),
                                             transforms.Normalize(mean=transform['mean'], std=transform['std'])])
        else:
            self.data_transform = None 
        self.class_num = class_num
        self.need_probability_map = need_probability_map
        self.need_save_hard = need_save_hard
        self.entropy_info_img = [] #记录本地影像的熵值
        self.nodata = nodata

    
    def _generate_infer_image(self, infer_path, need_probability_map):
        # Register GDAL format drivers and configuration options with a
        # context manager.
        with rasterio.Env():
            profile = self.rs_dataset.dataset.profile
            profile.update(
                dtype=rasterio.uint8,
                count=1,
                nodata=self.nodata,
                tiled=True,
                BIGTIFF='YES',
                compress='lzw')
            with rasterio.open(infer_path, 'w', **profile) as dst:
                dst.write(np.zeros((100, 100), dtype=rasterio.uint8), window=Window(0, 0, 100, 100), indexes=1)
            if need_probability_map:
                profile.update(
                    dtype=rasterio.float32,
                    count=self.class_num)
                with rasterio.open(self.uncertain_path, 'w', **profile) as dst:
                    dst.write(np.zeros((self.class_num, 100, 100), dtype=rasterio.float32), window=Window(0, 0, 100, 100))

    def _init_dataset_dataloader(self,image_path):
        self.rs_dataset = RsInferDataSet(image_path, self.patch, self.overlap, transform=self.data_transform)
        self.rs_dataset_loader = DataLoader(self.rs_dataset,
                                            batch_size=self.batch_size,
                                            shuffle=False,
                                            num_workers=self.num_workers,
                                            collate_fn=self.rs_dataset.collate_fn)
    
    def _calEntropy(self, seg_logits):
        """
        calculate entropy for the infer img
        :param seg_logits:
        :return:
        """
        seg_logits = torch.softmax(seg_logits, dim=0)
        entropy = torch.mean(sum(-seg_logits*torch.log2(seg_logits+0.00001)).cpu()).item()
        return entropy
    
    def clearEntropy(self):
        self.entropy_info_img = []  #清空本地影像的熵值

    @abstractmethod
    def _init_model(self,config,checkpoint,channel_type='rgb',type_name="infer",gpuId=0):
        pass
    
    @abstractmethod
    def _init_path(self, image_path, result_dir):
        pass

    @abstractmethod
    def infer_tif(self, image_path, result_dir,callback=None,logback=None):
        pass


