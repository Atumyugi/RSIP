# cython:language_level=3
# -*- coding: utf-8 -*-
from osgeo import gdal,osr
import numpy as np
import os
from random import shuffle
import csv

class LonlatTool:
    def __init__(self,tifPath):
        self.tifPath = tifPath
        self.tifDs : gdal.Dataset = gdal.Open(self.tifPath)

    def getProjectNGeoSrs(self):
        """
        获得tifDs的投影参考系和地理参考系
        """
        prosrs = osr.SpatialReference()
        prosrs.ImportFromWkt(self.tifDs.GetProjection())
        geosrs = prosrs.CloneGeogCS()
        return prosrs, geosrs

    def getXYSize(self):
        return self.tifDs.RasterXSize,self.tifDs.RasterYSize

    def getWkt(self):
        return self.tifDs.GetProjection()

    def geo2lonlat(self, x, y):
        '''
        将投影坐标转为经纬度坐标（具体的投影坐标系由给定数据确定）
        :param x: 投影坐标x
        :param y: 投影坐标y
        :return: 投影坐标(x, y)对应的经纬度坐标(lon, lat)
        '''
        prosrs, geosrs = self.getProjectNGeoSrs()
        ct = osr.CoordinateTransformation(prosrs, geosrs)
        coords = ct.TransformPoint(x, y)
        return coords[:2]

    def lonlat2geo(self,lon, lat):
        '''
        将经纬度坐标转为投影坐标（具体的投影坐标系由给定数据确定）
        :param lon: 地理坐标lon经度
        :param lat: 地理坐标lat纬度
        :return: 经纬度坐标(lon, lat)对应的投影坐标
        '''
        prosrs, geosrs = self.getProjectNGeoSrs()
        ct = osr.CoordinateTransformation(geosrs, prosrs)
        coords = ct.TransformPoint(lon, lat)
        return coords[:2]

    def imagexy2geo(self,col,row,extraTransform = None):
        '''
        根据GDAL的六参数模型将影像图上坐标（行列号）转为投影坐标或地理坐标（根据具体数据的坐标系统转换）
        :param row: 像素的行号
        :param col: 像素的列号
        :return: 行列号(row, col)对应的投影坐标或地理坐标(x, y)
        '''
        if extraTransform:
            trans = extraTransform
        else:
            trans = self.tifDs.GetGeoTransform()
        px = trans[0] + col * trans[1] + row * trans[2]
        py = trans[3] + col * trans[4] + row * trans[5]
        return px, py

    def geo2imagexy(self, x, y,extraTransform=None):
        '''
        根据GDAL的六 参数模型将给定的投影或地理坐标转为影像图上坐标（行列号）
        :param x: 投影或地理坐标x
        :param y: 投影或地理坐标y
        :return: 影坐标或地理坐标(x, y)对应的影像图上行列号(row, col)
        '''
        if extraTransform:
            trans = extraTransform
        else:
            trans = self.tifDs.GetGeoTransform()
        a = np.array([[trans[1], trans[2]], [trans[4], trans[5]]])
        b = np.array([x - trans[0], y - trans[3]])
        res = np.asarray(np.linalg.solve(a, b),dtype=int).tolist()
        return res # 使用numpy的linalg.solve进行二元一次方程的求解

    def geos2imagexy(self,xys,extraTransform=None):
        res = []
        for xy in xys:
            px,py = self.geo2imagexy(xy[0],xy[1],extraTransform)
            res.append([int(px),int(py)])
        return res

class LonlatToolGiveDs:
    def __init__(self,tifDs):
        self.tifDs : gdal.Dataset = tifDs

    def getProjectNGeoSrs(self):
        """
        获得tifDs的投影参考系和地理参考系
        """
        prosrs = osr.SpatialReference()
        prosrs.ImportFromWkt(self.tifDs.GetProjection())
        geosrs = prosrs.CloneGeogCS()
        return prosrs, geosrs

    def getXYSize(self):
        return self.tifDs.RasterXSize,self.tifDs.RasterYSize

    def getWkt(self):
        return self.tifDs.GetProjection()

    def geo2lonlat(self, x, y):
        '''
        将投影坐标转为经纬度坐标（具体的投影坐标系由给定数据确定）
        :param x: 投影坐标x
        :param y: 投影坐标y
        :return: 投影坐标(x, y)对应的经纬度坐标(lon, lat)
        '''
        prosrs, geosrs = self.getProjectNGeoSrs()
        ct = osr.CoordinateTransformation(prosrs, geosrs)
        coords = ct.TransformPoint(x, y)
        return coords[:2]

    def lonlat2geo(self,lon, lat):
        '''
        将经纬度坐标转为投影坐标（具体的投影坐标系由给定数据确定）
        :param lon: 地理坐标lon经度
        :param lat: 地理坐标lat纬度
        :return: 经纬度坐标(lon, lat)对应的投影坐标
        '''
        prosrs, geosrs = self.getProjectNGeoSrs()
        ct = osr.CoordinateTransformation(geosrs, prosrs)
        coords = ct.TransformPoint(lon, lat)
        return coords[:2]

    def imagexy2geo(self,col,row,extraTransform = None):
        '''
        根据GDAL的六参数模型将影像图上坐标（行列号）转为投影坐标或地理坐标（根据具体数据的坐标系统转换）
        :param row: 像素的行号
        :param col: 像素的列号
        :return: 行列号(row, col)对应的投影坐标或地理坐标(x, y)
        '''
        if extraTransform:
            trans = extraTransform
        else:
            trans = self.tifDs.GetGeoTransform()
        px = trans[0] + col * trans[1] + row * trans[2]
        py = trans[3] + col * trans[4] + row * trans[5]
        return px, py

    def geo2imagexy(self, x, y,extraTransform=None):
        '''
        根据GDAL的六 参数模型将给定的投影或地理坐标转为影像图上坐标（行列号）
        :param x: 投影或地理坐标x
        :param y: 投影或地理坐标y
        :return: 影坐标或地理坐标(x, y)对应的影像图上行列号(row, col)
        '''
        if extraTransform:
            trans = extraTransform
        else:
            trans = self.tifDs.GetGeoTransform()
        a = np.array([[trans[1], trans[2]], [trans[4], trans[5]]])
        b = np.array([x - trans[0], y - trans[3]])
        res = np.asarray(np.linalg.solve(a, b),dtype=int).tolist()
        return res # 使用numpy的linalg.solve进行二元一次方程的求解

    def geos2imagexy(self,xys,extraTransform=None):
        res = []
        for xy in xys:
            px,py = self.geo2imagexy(xy[0],xy[1],extraTransform)
            res.append([int(px),int(py)])
        return res

def field3_3(row, col):
    """Returns
        返回当前点坐标为中心的3邻域范围的坐标集合
    """
    content = []
    for i in range(row - 1, row + 2):
        for j in range(col - 1, col + 2):
            content.append([i, j])
    return content

def patch_margin(width_index, height_index,PATCH_SIZE,PATCH_IDX,dataset,stats_file,band):
    #上一步骤已进行判断，直接取块
    patches = dataset.ReadAsArray(width_index-PATCH_IDX, height_index-PATCH_IDX, PATCH_SIZE, PATCH_SIZE)
    patch = np.transpose(patches, (1, 2, 0))
    patch=patch.astype(np.float32)
    #归一化操作
    for i in range(band):
        patch[:, :, i] -= float(stats_file[i][0])
        patch[:, :, i] /= float(stats_file[i][1])
    return patch

def processing(BAND,dataset, log_dir):
    stats_file=[]
    out_file = open(os.path.join(log_dir, "temp.csv"), 'w', newline='')
    csv_write = csv.writer(out_file)
    for i in range(BAND):
        source_band = dataset.GetRasterBand(i + 1)
        stats = source_band.GetStatistics(0, 1) # gdal band类的获取统计信息函数
        print("波段：",i,"[极小值，极大值，均值，方差]：",stats)
        csv_write.writerow([stats[0], stats[1]])
        stats_file.append([stats[0], stats[1]])
    return stats_file


def oversample(truth, train_patch, train_labels, count,OUTPUT_CLASSES,PATCH_SIZE,BAND):
    if truth:
        for i in range(OUTPUT_CLASSES):
            if len(train_patch[i]) < count:
                tmp = train_patch[i]
                for j in range(int(count / len(train_patch[i]))):
                    shuffle(train_patch[i])
                    train_patch[i] = train_patch[i] + tmp
            shuffle(train_patch[i])
            train_patch[i] = train_patch[i][:count]
            train_labels.extend(np.full(len(train_patch[i]), i, dtype=int))
        train_patch = np.array(train_patch, dtype='float32')
        train_patch = train_patch.reshape((-1,PATCH_SIZE, PATCH_SIZE,BAND))  # 注意需要修改band number
    else:
        tmp = []
        for i in range(OUTPUT_CLASSES):
            shuffle(train_patch[i])
            tmp += train_patch[i]
            train_labels.extend(np.full(len(train_patch[i]), i, dtype=int))
        train_patch = np.array(tmp, dtype='float32')

    return train_patch, train_labels