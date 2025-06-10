import traceback
import math

from osgeo import gdal, osr, ogr
import rasterio
from rasterio.mask import mask
from rasterio.windows import Window
from shapely.geometry import mapping
from shapely import wkt

from scipy import stats
import lightgbm
import numpy as np

from qgis.core import QgsVectorLayer, QgsProject,QgsField,QgsFeature,QgsVectorFileWriter,QgsVectorDataProvider,QgsGeometry,QgsFields
from PyQt5.QtCore import Qt,QThread, pyqtSignal

from yoyiUtils.rs_infer import YoyiRsInference

PROJECT = QgsProject.instance()

# 制作最大似然数据集
def getTrainData(inTifPath,samplePath,attr="Id",attrMapping=None):
    layer = QgsVectorLayer(samplePath)
    #print(layer.extent())
    with rasterio.open(inTifPath) as src:
        src : rasterio.io.DatasetReader
        bandCount = src.count
        dataX = np.array([], dtype=int).reshape(bandCount, 0)
        labelY = np.array([], dtype=int)
        for field in layer.getFeatures():
            field : QgsFeature
            geoFeature = [mapping(field.geometry())]
            # 将面矢量里面的像素和属性表联系起来
            clipRaster = mask(src,geoFeature,crop=True)[0]
            clipRasterNoZero = clipRaster[:,~np.all(clipRaster == 0,axis= 0 )]
            if attrMapping:
                labelY = np.append(labelY, [attrMapping[field.attribute(attr)]] * clipRasterNoZero.shape[1])
            else:
                labelY = np.append(labelY, [field.attribute(attr)] * clipRasterNoZero.shape[1])
            dataX = np.hstack((dataX, clipRasterNoZero))
    return dataX,labelY


class MleClsfyRsInference(YoyiRsInference):
    def __init__(self,
                 patch=512, 
                 overlap=0.1,
                 nodata=0):
        batch_size = 1
        class_num = -1
        super().__init__(class_num,patch,overlap,batch_size,nodata)
    
    def _init_path(self, image_path, result_path):
        self.image_path = image_path
        self.result_path = result_path

    def _init_model(self,labelShpPath,fieldName,attrMapping=None):
        trainX,trainY = getTrainData(self.image_path,labelShpPath,fieldName,attrMapping=attrMapping)
        classNum = len(np.unique(trainY))  # 待分类类别个数
        classLabel = np.unique(trainY)  # 待分类类别标签
        bands = trainX.shape[0]  # 波段数
        print(classNum,classLabel,bands)
        # 1 计算每个类别数据期望和协方差矩阵
        u, c = [], []
        for i in classLabel:
            label_index = np.argwhere(trainY == i)
            label_index = label_index.flatten()
            iTrainX = trainX[:, label_index]
            u_i = np.mean(iTrainX, axis=1)
            u_i = u_i.tolist()
            c_i = np.cov(iTrainX)
            u.append(u_i)
            c.append(c_i)
        # 假设协方差阵相同
        c_all = 0
        for i in range(classNum):
            c_all += c[i]
        # 2 计算每个类别的判别函数参量
        self.model = []
        for i in range(classNum):
            C_i = np.dot(np.linalg.inv(c_all), np.array(u[i]))  # size:(3,1)
            C_oi = -0.5 * np.dot(np.array(u[i]).reshape(1, -1), C_i)  # size:(1,1)
            self.model.append([C_i, C_oi])

        self.class_num = classNum
        self.class_label = classLabel
        print("初始化最大似然函数完成")
        
    
    def infer_tif(self,image_path,result_path,label_shp,field_name,attrMapping=None,callback=None):
        self._init_dataset_dataloader(image_path)
        self._init_path(image_path,result_path)
        self._generate_infer_image(self.result_path)
        self._init_model(labelShpPath=label_shp,fieldName=field_name,attrMapping=attrMapping)
        dst1 = rasterio.open(self.result_path, 'r+')
        infer_len = len(self.rs_dataset_loader)
        for data,index in zip(self.rs_dataset_loader,range(infer_len)):
            if callback:
                callback( (index+1)/infer_len*100 )
            else:
                print( (index+1)/infer_len*100,"%" )
            
            images, labels = data
            if len(labels) == 0: 
                continue
            tempData = images[0,:,:,:].transpose((1, 2, 0))
            rs_data = np.zeros((self.class_num, 512, 512))
            for i in range(self.class_num):
                rs_i = np.dot(tempData,self.model[i][0])
                rs_i = rs_i + self.model[i][1]
                rs_data[i,:,:] = rs_i
        
            rs_index = np.argmax(rs_data,axis=0)
            label_dict = dict(zip(np.array([i for i in range(self.class_num)]), self.class_label))
            rs_label = np.vectorize(label_dict.get)(rs_index)
            dst1.write(rs_label[labels[0][2][1]:,labels[0][2][0]:],
                       window=Window(labels[0][0][0], labels[0][0][1], labels[0][1][0], labels[0][1][1]), 
                       indexes=1)



class RandomForestRsInference(YoyiRsInference):
    pass



        


        