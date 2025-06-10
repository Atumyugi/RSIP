'''
author:        yoyi <464566016@qq.com>
date:          2024-03-19 09:21:05
'''
from abc import abstractmethod
import os
import os.path as osp
import numpy as np
import json

try:
    import torch
    import onnxruntime
except Exception as e:
    pass

import rasterio
from rasterio.windows import Window
from scipy.ndimage import zoom

import appConfig
    
class YoyiRsDataSet:
    def __init__(self, images_path, patch=512, overlap=0.1):
        self.images_path = images_path
        self.patchSize = patch
        self.overlap = overlap
        self._get_patch_index()
    
    def __len__(self):
        return len(self.x_y_index_list)

    def __getitem__(self, item):
        img = self.dataset.read(
            window=Window(self.x_y_index_list[item][0], self.x_y_index_list[item][1], self.patchSize, self.patchSize))
        if img.max() > 0:
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
            images = np.stack(images,axis=0)
            return images, labels
        else:
            return [], []

class RsInferChangeDataSet(YoyiRsDataSet):
    def __init__(self, images_path,post_images_path, patch=512, overlap=0.1):
        self.images_path = images_path
        self.post_images_path = post_images_path
        self.patchSize = patch
        self.overlap = overlap
        self._get_patch_index()

    def __len__(self):
        return len(self.x_y_index_list)

    def __getitem__(self, item):
        img = self.dataset.read(
            window=Window(self.x_y_index_list[item][0], self.x_y_index_list[item][1], self.patchSize, self.patchSize))
        img_post = self.dataset_post.read(
            window=Window(self.x_y_index_list[item][0], self.x_y_index_list[item][1], self.patchSize, self.patchSize))
        if img.max() > 0 and img_post.max() > 0:
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

class YoyiRsDataloader:
    def __init__(self,dataset:YoyiRsDataSet,batch_size):
        self.dataset = dataset
        self.batch_size = batch_size
        self.count = self.dataset.__len__()
        self.index = 0

    def __len__(self):
        return self.count//self.batch_size

    def __iter__(self):
        return self

    def __next__(self):
        if self.index >= self.count:
            raise StopIteration
        
        datas = []
        for i in range(self.batch_size):
            if self.index < self.count:
                tempData = self.dataset.__getitem__(self.index)
                datas.append(tempData)
                self.index += 1
        
        return self.dataset.collate_fn(datas)
    
class YoyiRsInference:
    def __init__(self,class_num=2,patch=512,overlap=0.1,batch_size=8,nodata=0):
        self.class_num = class_num
        self.patch = patch
        self.overlap = overlap
        self.batch_size = batch_size
        self.nodata = nodata
    
    def _generate_infer_image(self, infer_path):
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
    
    def _init_dataset_dataloader(self,image_path):
        self.rs_dataset = YoyiRsDataSet(image_path,self.patch,self.overlap)
        self.rs_dataset_loader = YoyiRsDataloader(self.rs_dataset,self.batch_size)
    
    @abstractmethod
    def _init_model(self,config,checkpoint,channel_type='rgb',type_name="infer",gpuId=0):
        pass
    
    @abstractmethod
    def _init_path(self, image_path, result_dir):
        pass

    @abstractmethod
    def infer_tif(self, image_path, result_dir,callback=None,logback=None):
        pass

class OnnxSegRsInference(YoyiRsInference):
    def __init__(self, class_num=2, 
                 patch=512, 
                 overlap=0.1,
                 batch_size=8, 
                 nodata=0,
                 mean=[123.675, 116.28, 103.53],
                 std=[58.395, 57.12, 57.375]):
        super().__init__(class_num, patch, overlap, batch_size, nodata)
        self.mean = mean
        self.std = std
    
    def _init_model(self,checkpoint, channel_type='rgb', type_name="infer", gpuId=0):
        device = [('CUDAExecutionProvider', {'device_id': gpuId,"cudnn_conv_algo_search": "DEFAULT"}), 'CPUExecutionProvider']
        self.ort_session = onnxruntime.InferenceSession(checkpoint, providers=device)
        self.type_name = type_name
        self.channel_type = channel_type
    
    def _init_path(self, image_path, result_dir):
        self.image_path = image_path
        self.result_path = osp.join(result_dir, osp.basename(image_path).split(".")[0]+"_"+self.type_name+".tif")

    def infer_tif(self, image_path, result_dir, callback=None):
        self._init_dataset_dataloader(image_path)
        self._init_path(image_path,result_dir)
        self._generate_infer_image(self.result_path)
        dst1 = rasterio.open(self.result_path, 'r+')
        infer_len = len(self.rs_dataset_loader)
        for data,index in zip(self.rs_dataset_loader,range(infer_len)):
            if callback:
                callback( (index+1)/infer_len*100 )
                print( (index+1)/infer_len*100,"%" )
            else:
                print( (index+1)/infer_len*100,"%" )
            
            images, labels = data

            if len(labels) == 0: 
                continue
            if self.channel_type == 'rgb' and images.shape[1] == 4:
                images = np.stack([i[:, :, ::-1][:, :, 1:4] for i in images.transpose((0, 2, 3, 1))], axis=0)
                images = images.transpose((0, 3, 1, 2))

            images = images.transpose((0, 2, 3, 1))
            images = np.stack([(i - self.mean) / self.std for i in images], axis=0).astype('float16')
            images = images.transpose((0, 3, 1, 2))
            ort_inputs = {'input': images}
            results = self.ort_session.run(['output'], ort_inputs)[0]
            
            for i, image in enumerate(results):
                    y1 = image[0, :, :]
                    dst1.write(y1[labels[i][2][1]:, labels[i][2][0]:],
                               window=Window(labels[i][0][0], labels[i][0][1], labels[i][1][0], labels[i][1][1]), indexes=1)
        del self.ort_session
        dst1.close()
        return self.result_path
        
class OnnxInsSegRsInference(YoyiRsInference):
    def __init__(self, class_num=2, 
                 patch=512, 
                 overlap=0.1, 
                 batch_size=8, 
                 nodata=0, 
                 mean=[123.675, 116.28, 103.53],
                 std=[58.395, 57.12, 57.375],
                 score_thresh=0.5
                 ):
        self.mean = mean
        self.std = std
        self.score_thresh = score_thresh
        super().__init__(class_num,patch,overlap,batch_size,nodata)

    def _init_model(self,checkpoint, channel_type='rgb', type_name="infer", gpuId=0):
        device = [('CUDAExecutionProvider', {'device_id': gpuId,"cudnn_conv_algo_search": "DEFAULT"}), 'CPUExecutionProvider']
        sessionOp = onnxruntime.SessionOptions()
        sessionOp.register_custom_ops_library(appConfig.ONNX_EXTRA_DLL)
        self.ort_session = onnxruntime.InferenceSession(checkpoint,sess_options=sessionOp, providers=device)
        print(self.mean)
        print(self.std)
        self.type_name = type_name
        self.channel_type = channel_type
    
    def _init_path(self, image_path, result_dir):
        self.image_path = image_path
        self.result_path = osp.join(result_dir, osp.basename(image_path).split(".")[0]+"_"+self.type_name+".tif")
    
    def nms(self,mask_logit,cls_logit):
        """
        score_thresh : 0-1
        mask_logits : [100,patch,patch]
        cls_logits : [100,class_num]
        """
        mask_logit = mask_logit*cls_logit
        mask_logit = np.sum(mask_logit, axis=0)
        mask_logit[mask_logit >0] = 1
        return mask_logit

    def infer_tif(self, image_path, result_dir, callback=None, logback=None):
        self._init_dataset_dataloader(image_path)
        self._init_path(image_path,result_dir)
        self._generate_infer_image(self.result_path)
        
        dst1 = rasterio.open(self.result_path, 'r+')

        infer_len = len(self.rs_dataset_loader)
        for data,index in zip(self.rs_dataset_loader,range(infer_len)):
            if callback:
                print( (index+1)/infer_len*100,"%" )
                callback( (index+1)/infer_len*100 )
            else:
                print( (index+1)/infer_len*100,"%" )
            
            images, labels = data

            if len(labels) == 0: 
                continue
            #images = images.numpy()
            #images_mask = [i[0,:,:] != 0 for i in images.numpy()]
            if self.channel_type == 'rgb' and images.shape[1] == 4:
                images = np.stack([i[:, :, ::-1][:, :, 1:4] for i in images.transpose((0, 2, 3, 1))], axis=0)
                images = images.transpose((0, 3, 1, 2))

            images = images.transpose((0, 2, 3, 1))
            images = np.stack([(i - self.mean) / self.std for i in images], axis=0).astype('float32')
            images = images.transpose((0, 3, 1, 2))
            ort_inputs = {'input': images}
            mask_logits,cls_logits = self.ort_session.run(['mask_logits','cls_logits'], ort_inputs)
            mask_logits[mask_logits<0] = 0
            mask_logits[mask_logits>0] = 1
            cls_logits = torch.from_numpy(cls_logits)
            cls_logits = torch.sigmoid(cls_logits).numpy()
            cls_logits = np.max(cls_logits,axis=2)
            cls_logits[cls_logits<self.score_thresh] = 0
            cls_logits[cls_logits>=self.score_thresh] = 1
            cls_logits = np.expand_dims( np.expand_dims(cls_logits ,axis=2),axis=3)
            for i,mask_logit,cls_logit in zip(range(self.batch_size),mask_logits,cls_logits):
                tempmask = self.nms(mask_logit,cls_logit)
                dst1.write(tempmask[labels[i][2][1]:, labels[i][2][0]:],
                                window=Window(labels[i][0][0], labels[i][0][1], labels[i][1][0], labels[i][1][1]), indexes=1)
        del self.ort_session
        dst1.close()
        return self.result_path

class OnnxChangeDetecRsInference(YoyiRsInference):
    def __init__(self, class_num=2, 
                 patch=512, 
                 overlap=0.1, 
                 batch_size=8, 
                 nodata=0, 
                 mean=[123.675, 116.28, 103.53,123.675, 116.28, 103.53],
                 std=[58.395, 57.12, 57.375,58.395, 57.12, 57.375]
                 ):
        self.mean = mean
        self.std = std
        super().__init__(class_num,patch,overlap,batch_size,nodata)

    def _init_model(self,checkpoint, channel_type='rgb', type_name="infer", gpuId=0):
        device = [('CUDAExecutionProvider', {'device_id': gpuId,"cudnn_conv_algo_search": "DEFAULT"}), 'CPUExecutionProvider']
        self.ort_session = onnxruntime.InferenceSession(checkpoint, providers=device)
        print(self.mean)
        print(self.std)
        self.type_name = type_name
        self.channel_type = channel_type
    
    def _init_dataset_dataloader(self,image_path,post_image_path):
        self.rs_dataset = RsInferChangeDataSet(image_path,
                                               post_image_path, 
                                               self.patch, 
                                               self.overlap)
        self.rs_dataset_loader = YoyiRsDataloader(self.rs_dataset,self.batch_size)

    def _init_path(self, image_path, result_dir):
        self.image_path = image_path
        self.result_path = os.path.join(result_dir, osp.basename(image_path).split(".")[0]+"_"+self.type_name+".tif")
    
    def infer_tif(self,image_path,result_dir,post_image_path, callback=None, logback=None):
        self._init_dataset_dataloader(image_path,post_image_path)
        self._init_path(post_image_path,result_dir)
        self._generate_infer_image(self.result_path)
        dst1 = rasterio.open(self.result_path, 'r+')

        infer_len = len(self.rs_dataset_loader)
        for data,index in zip(self.rs_dataset_loader,range(infer_len)):
            if callback:
                callback( (index+1)/infer_len*100 )
            else:
                print( (index+1)/infer_len*100,"%" )
            
            x1,x2, labels = data
            if len(labels) == 0:
                continue
            x1,x2 = x1.numpy(),x2.numpy()
            if self.channel_type == 'rgb' and x1.shape[1] == 4:
                x1 = np.stack([i[:, :, ::-1][:, :, 1:4] for i in x1.transpose((0, 2, 3, 1))], axis=0)
                x1 = x1.transpose((0, 3, 1, 2))
                x2 = np.stack([i[:, :, ::-1][:, :, 1:4] for i in x2.transpose((0, 2, 3, 1))], axis=0)
                x2 = x2.transpose((0, 3, 1, 2))

            images = np.concatenate([x1,x2],axis=1)
            
            images = images.transpose((0, 2, 3, 1))
            images = np.stack([(i - self.mean) / self.std for i in images], axis=0).astype('float32')
            images = images.transpose((0, 3, 1, 2))
            ort_inputs = {'images': images}
            results = self.ort_session.run(['output'], ort_inputs)[0]
            results = np.argmax(results,axis=1)[0]
            # 1=bilinear，3=bicubic
            results = zoom(results,zoom=(4,4),order=1)
            dst1.write(results[labels[0][2][1]:, labels[0][2][0]:],
                            window=Window(labels[0][0][0], labels[0][0][1], labels[0][1][0], labels[0][1][1]), indexes=1)
        del self.ort_session
        dst1.close()
        return self.result_path
