# cython:language_level=3
# -*- coding: utf-8 -*-
import random

import numpy as np
from sklearn.model_selection import train_test_split
from osgeo import gdal, ogr, gdalnumeric,gdalconst
import os
import shutil
import os.path as osp
import time
from datetime import datetime
import yaml
import traceback
import json

from PyQt5.QtCore import QVariant 
from qgis.core import QgsProject,QgsRasterLayer,QgsVectorLayer,QgsField,QgsFeature,QgsSpatialIndex,QgsCoordinateReferenceSystem,QgsCoordinateTransform,QgsGeometry,QgsRectangle

from appConfig import *
from yoyiUtils.qgisFunction import saveShpFunc
from yoyiUtils.yoyiFile import createDir,checkTifList,deleteDir,checkAllFileList,checkPostFileList

PROJECT = QgsProject.instance()

def vector2raster(inputfilePath, outputfile, templatefile,fieldName,pixel_value=1,tempDir="",checkRasterSize=-1):
    inputfilePath = inputfilePath
    outputfile = outputfile
    templatefile = templatefile
    outDir = osp.dirname(outputfile)

    data : gdal.Dataset = gdal.Open(templatefile, gdalconst.GA_ReadOnly)
    x_res = data.RasterXSize
    y_res = data.RasterYSize
    if checkRasterSize>0:
        if x_res!=checkRasterSize or y_res!=checkRasterSize:
            print(f"{inputfilePath} skip...")
            return -1
    dataBand = data.RasterCount
    vector = ogr.Open(inputfilePath)
    print(inputfilePath)

    if osp.basename(outputfile).split(".")[-1] in ["png","jpg"]:
        outputfile_temp = osp.join(tempDir,osp.basename(outputfile).split(".")[0]+".tif")
        layer = vector.GetLayer()
        targetDataset : gdal.Dataset = gdal.GetDriverByName('GTiff').Create(outputfile_temp, x_res, y_res, 1, gdal.GDT_Byte,
                                                            options=["COMPRESS=LZW", "TILED=YES"])
        targetDataset.SetGeoTransform(data.GetGeoTransform())
        targetDataset.SetProjection(data.GetProjection())
        band = targetDataset.GetRasterBand(1)
        NoData_value = 0
        band.SetNoDataValue(NoData_value)
        band.FlushCache()
        if fieldName:
            gdal.RasterizeLayer(targetDataset, [1], layer, options=[f"ATTRIBUTE={fieldName}", "CHUNKYSIZE=4096"])
        else:
            gdal.RasterizeLayer(targetDataset, [1], layer,burn_values=[pixel_value], options=["CHUNKYSIZE=4096"])

        trueDriver = gdal.GetDriverByName("PNG" if osp.basename(outputfile).split(".")[-1] == "png" else "JPEG") 
        trueDriver.CreateCopy(outputfile,targetDataset)
        del targetDataset
        del trueDriver
        #os.remove(outputfile_temp)
    else:
        layer = vector.GetLayer()
        targetDataset : gdal.Dataset = gdal.GetDriverByName('GTiff').Create(outputfile, x_res, y_res, 1, gdal.GDT_Byte,
                                                            options=["COMPRESS=LZW", "TILED=YES"])
        targetDataset.SetGeoTransform(data.GetGeoTransform())
        targetDataset.SetProjection(data.GetProjection())
        band = targetDataset.GetRasterBand(1)
        NoData_value = 0
        band.SetNoDataValue(NoData_value)
        band.FlushCache()
        if fieldName:
            gdal.RasterizeLayer(targetDataset, [1], layer, options=[f"ATTRIBUTE={fieldName}", "CHUNKYSIZE=4096"])
        else:
            gdal.RasterizeLayer(targetDataset, [1], layer,burn_values=[pixel_value], options=["CHUNKYSIZE=4096"])

    return dataBand


    # gdal.RasterizeLayer(targetDataset, [1], layer, options=["ATTRIBUTE=class"])
def ComputeBlockByGeneratePairData(H, W, block_size, overlap_size):
    subIm_index = []
    for r in range(0, H - block_size, overlap_size):
        for c in range(0, W - block_size, block_size):
            subIm_index.append([r, r + block_size, c, c + block_size])
        subIm_index.append([r, r + block_size, W - block_size, W])  # 右侧边界
    for c in range(0, W - block_size, block_size):  # 下侧边界
        subIm_index.append([H - block_size, H, c, c + block_size])
    subIm_index.append([H - block_size, H, W - block_size, W])  # 右下角
    return subIm_index

def generate_pair_data(imagePath,outputDir,band=3,overlapRatio=0.9,block_size=512,dropAllZero=True):
    label_name = os.path.splitext(os.path.basename(imagePath))[0]
    block_size = block_size
    mask_folder = os.path.join(outputDir, 'mask')
    img_folder = os.path.join(outputDir, 'img')
    if ~os.path.exists(mask_folder):
        os.makedirs(mask_folder, exist_ok=True)
    if ~os.path.exists(img_folder):
        os.makedirs(img_folder, exist_ok=True)
    image_result_path = os.path.join(os.path.join(img_folder, label_name))
    label_result_path = os.path.join(os.path.join(mask_folder, label_name))
    dataset : gdal.Dataset = gdal.Open(imagePath)
    datasetlabel = gdal.Open(os.path.join(
        outputDir, "shp2mask", label_name + "_mask.tif"))
    # datasetlabel_max = np.max(datasetlabel.ReadAsArray())
    # if 0 == datasetlabel_max:
    #     print("影像数据区域均为nodata 跳过处理")
    #     return
    print(os.path.join(outputDir, label_name + ".tif"))
    W = dataset.RasterXSize
    H = dataset.RasterYSize
    if W < block_size or H < block_size:
        print("*******影像过小******", imagePath)
        return
    else:
        overlap_size = int(overlapRatio * block_size)
        print("overlap_size:",overlap_size)
        subIm_index = ComputeBlockByGeneratePairData(H, W, block_size, overlap_size)
        index = 0
        print(subIm_index)
        print("==>分块个数", len(subIm_index))
        for coord in subIm_index:
            index = index + 1
            label_ = datasetlabel.ReadAsArray(
                coord[2], coord[0], block_size, block_size)
            img_ = dataset.ReadAsArray(
                coord[2], coord[0], block_size, block_size)[:, :, :]
            print(np.max(label_))
            if np.max(img_[0]) == dataset.GetRasterBand(1).GetNoDataValue():
                print("影像无效空值跳过：",index)
                continue
            if dropAllZero and np.max(label_) == 0:
                # print("空值跳过：",index)
                continue
            else:
                save_file_path = image_result_path + "_" + str(index) + "_" + str(coord[2]) + "_" + str(
                    coord[0]) + ".tif"
                if os.path.exists(save_file_path):
                    print("已存在文件：", save_file_path)
                    continue
                else:
                    out_img = dataset.GetDriver().Create(save_file_path, block_size, block_size, band, gdal.GDT_Byte,
                                                         options=["COMPRESS=LZW"])
                    for i in range(band):
                        out_img_band = out_img.GetRasterBand(i + 1)
                        out_img_band.WriteArray(img_[i], 0, 0)
                save_file_path = label_result_path + "_" + str(index) + "_" + str(coord[2]) + "_" + str(
                    coord[0]) + ".tif"
                if os.path.exists(save_file_path):
                    print("已存在文件：", save_file_path)
                    continue
                else:
                    out_laebl = dataset.GetDriver().Create(save_file_path, block_size, block_size, 1, gdal.GDT_Byte)
                    out_label_band = out_laebl.GetRasterBand(1)
                    out_label_band.WriteArray(label_, 0, 0)

def createDataSetMuitiTifVsSingleShp(tifDir,shpPath,fieldName="value"):
    tifList = checkTifList(tifDir)
    labelDir = osp.join(tifDir,"label")
    for tifPath in tifList:
        outputMaskFile = osp.join(labelDir,osp.basename(tifPath))
        vector2raster(shpPath,outputMaskFile,tifPath,fieldName,checkRasterSize=512)


def splitDataset(imgDir,labelDir,imgDirPost,labelDirPost,resDir,
                 validRatio=0.1,testRatio=0.1,shuffleOrder=True,
                 trainDirName='train',validDirName='valid',testDirName='test',
                 imageDirName='img',labelDirName='label',callback=None):

    trainDir = osp.join(resDir,trainDirName)
    validDir = osp.join(resDir,validDirName)
    testDir = osp.join(resDir,testDirName)

    trainImgDir = osp.join(trainDir,imageDirName)
    trainLabelDir = osp.join(trainDir,labelDirName)

    validImgDir = osp.join(validDir,imageDirName)
    validLabelDir = osp.join(validDir,labelDirName)

    testImgDir = osp.join(testDir,imageDirName)
    testLabelDir = osp.join(testDir,labelDirName)

    createDir(resDir)
    createDir(trainDir)
    createDir(validDir)
    createDir(testDir)

    createDir(trainImgDir)
    createDir(trainLabelDir)
    createDir(validImgDir)
    createDir(validLabelDir)
    createDir(testImgDir)
    createDir(testLabelDir)

    imgList = checkPostFileList(imgDir,[imgDirPost],True)
    labelList = checkPostFileList(labelDir,[labelDirPost],True)

    imgLabelIntersectSet = set([i.split(".")[0] for i in imgList]) & set([i.split(".")[0] for i in labelList])
    imgLabelIntersectList = list(imgLabelIntersectSet)
    
    trainNameList,validNameList = train_test_split(imgLabelIntersectList,test_size=validRatio,shuffle=shuffleOrder)
    trainNameList,testNameList = train_test_split(trainNameList,test_size=testRatio/(1-validRatio),shuffle=shuffleOrder)
    
    if callback:
        callback(20)
    for trainName in trainNameList:
        crsImgFile = osp.join(imgDir,trainName+"."+imgDirPost)
        dstImgFile = osp.join(trainImgDir,trainName+"."+imgDirPost)
        shutil.copy2(crsImgFile,dstImgFile)
        crsLabelFile = osp.join(labelDir,trainName+"."+labelDirPost)
        dstLabelFile = osp.join(trainLabelDir,trainName+"."+labelDirPost)
        shutil.copy2(crsLabelFile,dstLabelFile)
    
    if callback:
        callback(40)
    print("分割train完成")
    
    for validName in validNameList:
        crsImgFile = osp.join(imgDir,validName+"."+imgDirPost)
        dstImgFile = osp.join(validImgDir,validName+"."+imgDirPost)
        shutil.copy2(crsImgFile,dstImgFile)
        crsLabelFile = osp.join(labelDir,validName+"."+labelDirPost)
        dstLabelFile = osp.join(validLabelDir,validName+"."+labelDirPost)
        shutil.copy2(crsLabelFile,dstLabelFile)
    
    if callback:
        callback(70)
    print("分割valid完成")
    
    for testName in testNameList:
        crsImgFile = osp.join(imgDir,testName+"."+imgDirPost)
        dstImgFile = osp.join(testImgDir,testName+"."+imgDirPost)
        shutil.copy2(crsImgFile,dstImgFile)
        crsLabelFile = osp.join(labelDir,testName+"."+labelDirPost)
        dstLabelFile = osp.join(testLabelDir,testName+"."+labelDirPost)
        shutil.copy2(crsLabelFile,dstLabelFile)
    
    if callback:
        callback(100)
    print("分割test完成")



class yoyiDataSetProducer:
    def __init__(self) -> None:
        pass
    
    def geo2imagexy(self, x, y,trans):
        a = np.array([[trans[1], trans[2]], [trans[4], trans[5]]])
        b = np.array([x - trans[0], y - trans[3]])
        res = np.asarray(np.linalg.solve(a, b),dtype=int).tolist()
        return res

    def _compute_block_by_generate_pair(self,H, W, block_size, overlap_size):
        """
        根据切割尺寸计算index
        """
        subIm_index = []
        for r in range(0, H - block_size, overlap_size):
            for c in range(0, W - block_size, block_size):
                subIm_index.append([r, r + block_size, c, c + block_size])
            subIm_index.append([r, r + block_size, W - block_size, W])  # 右侧边界
        for c in range(0, W - block_size, block_size):  # 下侧边界
            subIm_index.append([H - block_size, H, c, c + block_size])
        subIm_index.append([H - block_size, H, W - block_size, W])  # 右下角
        return subIm_index
    
    def shp_pixel_mapping(self,shp_path,shp_field,mapping:dict,new_path):
        sourceLayer = QgsVectorLayer(shp_path)
        saveShpFunc(new_path,sourceLayer)
        del sourceLayer
        newLayer = QgsVectorLayer(new_path)
        newLayer.dataProvider().addAttributes([QgsField("tpixmap", QVariant.Int)])
        newLayer.updateFields()  # 告诉矢量图层从提供者获取更改
        newLayer.startEditing()
        for feature in newLayer.getFeatures():
            feature : QgsFeature
            tempAttr = feature.attribute(shp_field)
            if tempAttr in mapping:
                featureLabel = int(mapping[tempAttr])
            else:
                featureLabel = 1
            feature.setAttribute("tpixmap",featureLabel)
            newLayer.updateFeature(feature)
        newLayer.commitChanges()
        del newLayer


    def generate_segment_sample_by_single_tif(self,tif_path,res_dir,need_trans_rgb=True,overlap=0.9,img_size=512,generate_post="png",extra_shp=None,extra_shp_field="value",extra_label_dir=None,callback=None):
        """
        tif_path  镶嵌影像路径
        res_dir  结果路径(生成一堆小图片)
        """
        createDir(res_dir)
        temp_dir = osp.join(res_dir,f"temp_{datetime.now().strftime('%Y%m%d%H%M%S%f')}")
        createDir(temp_dir)
        if extra_shp:
            label_tif_path = osp.join(temp_dir,"label_tif.tif")
            vector2raster(extra_shp,label_tif_path,tif_path,fieldName=extra_shp_field)
            label_tif_ds: gdal.Dataset = gdal.Open(label_tif_path)
            createDir(extra_label_dir)
        tif_ds : gdal.Dataset = gdal.Open(tif_path)
        tif_width = tif_ds.RasterXSize
        tif_height = tif_ds.RasterYSize
        tif_no_data_value = tif_ds.GetRasterBand(1).GetNoDataValue()
        if need_trans_rgb:
            tif_bands = 3
        else:
            tif_bands = tif_ds.RasterCount

        if generate_post == "png":
            src_driver : gdal.Driver = gdal.GetDriverByName("GTiff")
            dst_driver : gdal.Driver = gdal.GetDriverByName("PNG")       
        elif generate_post == "jpg":
            src_driver : gdal.Driver = gdal.GetDriverByName("GTiff")
            dst_driver : gdal.Driver = gdal.GetDriverByName("JPEG")
        elif generate_post == "tif":
            src_driver : gdal.Driver = gdal.GetDriverByName("GTiff")
            dst_driver : gdal.Driver = None

        overlap_size = int(overlap*img_size)
        sub_index = self._compute_block_by_generate_pair(tif_height,tif_width,img_size,overlap_size)
        for index,coord in enumerate(sub_index):
            if callback:
                callback((index+1)/len(sub_index)*100)
            else:
                print((index+1)/len(sub_index)*100)
            
            if need_trans_rgb and tif_ds.RasterCount>=4:
                temp_img_array = tif_ds.ReadAsArray(coord[2],coord[0],img_size,img_size)[[2, 1, 0],:,:]
            else:
                temp_img_array = tif_ds.ReadAsArray(coord[2],coord[0],img_size,img_size)
            
            if extra_shp:
                temp_label_array = label_tif_ds.ReadAsArray(coord[2],coord[0],img_size,img_size)
            
            if np.max(temp_img_array[0]) == tif_no_data_value:
                print("影像无效空值跳过：",index)
                continue
            
            temp_img_path = osp.join(res_dir,f"{index}.{generate_post}")
            temp_label_path = osp.join(extra_label_dir,f"{index}.{generate_post}")

            if generate_post == "tif":
                out_img = src_driver.Create(temp_img_path,img_size,img_size,tif_bands,gdal.GDT_Byte,options=["COMPRESS=LZW"])
                out_img.SetGeoTransform(EXAMPLE_PNG_GEOTRANSFORM)
                out_img.SetProjection(EXAMPLE_PNG_PROJECTION)
                for i in range(tif_bands):
                    out_img_band = out_img.GetRasterBand(i + 1)
                    out_img_band.WriteArray(temp_img_array[i], 0, 0)
                del out_img
                if extra_shp:
                    out_label_img = src_driver.Create(temp_label_path,img_size,img_size,1,gdal.GDT_Byte,options=["COMPRESS=LZW"])
                    out_label_img.SetGeoTransform(EXAMPLE_PNG_GEOTRANSFORM)
                    out_label_img.SetProjection(EXAMPLE_PNG_PROJECTION)
                    out_label_img_band = out_label_img.GetRasterBand(1)
                    out_label_img_band.WriteArray(temp_label_array,0,0)
                    del out_label_img
            else:
                temp_tif_path = osp.join(temp_dir,f"{index}.tif")
                temp_tif_label_path = osp.join(temp_dir,f"{index}_label.tif")
                out_img = src_driver.Create(temp_tif_path,img_size,img_size,tif_bands,gdal.GDT_Byte,options=["COMPRESS=LZW"])
                out_img.SetGeoTransform(EXAMPLE_PNG_GEOTRANSFORM)
                out_img.SetProjection(EXAMPLE_PNG_PROJECTION)
                for i in range(tif_bands):
                    out_img_band = out_img.GetRasterBand(i + 1)
                    out_img_band.WriteArray(temp_img_array[i], 0, 0)
                dst_driver.CreateCopy(temp_img_path,out_img)
                del out_img
                if extra_shp:
                    out_label_img = src_driver.Create(temp_tif_label_path,img_size,img_size,1,gdal.GDT_Byte,options=["COMPRESS=LZW"])
                    out_label_img.SetGeoTransform(EXAMPLE_PNG_GEOTRANSFORM)
                    out_label_img.SetProjection(EXAMPLE_PNG_PROJECTION)
                    out_label_img_band = out_label_img.GetRasterBand(1)
                    out_label_img_band.SetNoDataValue(0)
                    out_label_img_band.WriteArray(temp_label_array,0,0)
                    dst_driver.CreateCopy(temp_label_path,out_label_img)
                    del out_label_img
        deleteDir(temp_dir)
    
    def update_segment_sample_by_multi_shp(self,label_dir_path,label_shp_path,img_dir_path,pixel_map,attr_field,img_post,label_post,callback=None):
        """
        根据矢量更新已有的数据集
        label_dir_path: 数据集的label地址  覆盖保存
        label_shp_path: 数据集的label的矢量地址  
        img_dir_path: 数据集的img地址
        pixel_map: 像素和字段的映射表
        attr_field : 存储信息的字段名
        img_post: img的后缀
        label_post: label的后缀
        """
        temp_pixel_shp_dir = osp.join(label_dir_path,"temp")
        deleteDir(temp_pixel_shp_dir)
        createDir(temp_pixel_shp_dir)

        temp_pixel_raster_dir = osp.join(label_dir_path,"temp_raster")
        deleteDir(temp_pixel_raster_dir)
        createDir(temp_pixel_raster_dir)

        shp_list = checkAllFileList(label_shp_path,"shp")
        print("shp_list:",shp_list)
        for index,temp_draw_shp in enumerate(shp_list) :
            if callback:
                callback( (index+1)/len(shp_list) * 100 )
            else:
                print( (index+1)/len(shp_list) * 100 , "%")
            tempLayer = QgsVectorLayer(temp_draw_shp)
            temp_shp = osp.join(temp_pixel_shp_dir,osp.basename(temp_draw_shp))
            saveShpFunc(temp_shp,tempLayer)
            print("另存矢量成功",temp_shp)
            temp_shp_layer = QgsVectorLayer(temp_shp)
            temp_shp_layer.startEditing()
            for feature in temp_shp_layer.getFeatures():
                pixel = pixel_map[feature.attribute(attr_field)]
                temp_shp_layer.changeAttributeValue(feature.id(),0,pixel)
            temp_shp_layer.commitChanges()
            del tempLayer
            del temp_shp_layer
            # 完成像素值转换 开始进行矢量转栅格

            temp_tif_path = osp.join(img_dir_path,osp.basename(temp_draw_shp).split(".")[0]+"."+img_post)
            if osp.exists(temp_tif_path):
                temp_label_path = osp.join(label_dir_path,osp.basename(temp_draw_shp).split(".")[0]+"."+label_post)
                vector2raster(temp_shp,temp_label_path,temp_tif_path,attr_field,tempDir=temp_pixel_raster_dir)
        
        deleteDir(temp_pixel_shp_dir)
        deleteDir(temp_pixel_raster_dir)
    
    def generate_cgwx_segment_sample_by_single_tif(self,
                                                   tif_path,
                                                   res_dir,
                                                   shp_path,
                                                   extra_label_dir,
                                                   json_dir=None,
                                                   need_trans_rgb=True,
                                                   overlap=0.9,
                                                   img_size=512,
                                                   drop_zero=True,
                                                   drop_no_data=True,
                                                   generate_post="png",
                                                   extra_shp_field=None,
                                                   extra_shp_pixel_mapping=None,
                                                   extra_diy_pixel_value=1,
                                                   class_dict=None,
                                                   mosaic_shp=None,
                                                   mosaic_shp_imgid_field="ImageSourc",
                                                   imgid_time=None,
                                                   sample_name=None,
                                                   sample_description=None,
                                                   sample_builder=None,
                                                   image_area_id=None,
                                                   file_pre="LC_01",
                                                   extra_generate_file_index=0,
                                                   is_Change_detec=False,
                                                   change_detec_tif_path=None,
                                                   imgid_time_II=None,
                                                   change_detec_mosaic_shp=None,
                                                   change_detec_mosaic_shp_imgid_field=None,
                                                   extra_sub_index=None,
                                                   callback=None):
        """
        tif_path  镶嵌影像路径 \n
        res_dir  img结果路径(生成一堆小图片) \n
        json_dir 存放json的路径 \n
        shp_path 矢量路径 \n
        extra_label_dir label的结果路径(生成一堆小图片) \n
        need_trans_rgb 是否需要转为三波段 \n
        overlap 重叠率 \n
        img_size 切片大小 \n
        drop_zero 舍弃标签全为0的切片 \n
        generate_post 生成类型 \n
        extra_shp_field 矢量属性存储字段 如果为None 则会全部设为像素1 \n
        extra_shp_pixel_mapping 矢量的属性映射表（中文：数字）  \n
        class_dict 存在json的字典
        mosaic_shp 镶嵌线 存储景ID \n
        mosaic_shp_imgid_field 镶嵌线存储景ID的字段 \n
        imgid 景ID 和镶嵌线二选一 \n
        sample_name json存储Name \n
        sample_description json存储Description \n
        sample_builder json存储Builder \n
        image_area_id 县区号，可以直接给，如果没给，会自动计算 \n
        file_pre 文件的前缀 \n
        extra_generate_file_index 创建文件的开始索引，在同时生成多个样本时有用 \n
        """
        # 0 文件夹前置处理 -- 创建临时文件夹 res_dir
        createDir(res_dir)
        temp_dir = osp.join(res_dir,f"temp_{datetime.now().strftime('%Y%m%d%H%M%S%f')}")
        createDir(temp_dir)
        if json_dir:
            createDir(json_dir)

        # 1 前置处理 -- 矢量转栅格 并创建 extra_label_dir
        label_shp_qlayer = QgsVectorLayer(shp_path)
        try:
            img_epsg_id = label_shp_qlayer.crs().authid().split(":")[1]
            if img_epsg_id == "4326":
                xform = None
            else:
                crsDest = QgsCoordinateReferenceSystem("EPSG:4326")
                xform = QgsCoordinateTransform(label_shp_qlayer.crs(),crsDest,PROJECT.transformContext())
        except Exception as e:
            img_epsg_id = None
        del label_shp_qlayer

        label_tif_path = osp.join(temp_dir,"label_tif.tif")
        if extra_shp_field and extra_shp_pixel_mapping:
            temp_shpmapping_path = osp.join(temp_dir,"label_temp_mapping.shp")
            self.shp_pixel_mapping(shp_path,extra_shp_field,extra_shp_pixel_mapping,temp_shpmapping_path)
            shp_path = temp_shpmapping_path
            extra_shp_field = "tpixmap"
        vector2raster(shp_path,label_tif_path,tif_path,fieldName=extra_shp_field,pixel_value=extra_diy_pixel_value)
        label_tif_ds: gdal.Dataset = gdal.Open(label_tif_path)
        createDir(extra_label_dir)

        
        # 1 前置处理2 -- 镶嵌线相关
        if imgid_time:
            useDiyImgid = True
            mosaic_shp_layer = None
        elif mosaic_shp and mosaic_shp_imgid_field:
            useDiyImgid = False
            mosaic_shp_layer = QgsVectorLayer(mosaic_shp)
            mosaic_shp_layer_spatialIndex = QgsSpatialIndex(mosaic_shp_layer.getFeatures())
            if change_detec_mosaic_shp:
                mosaic_shp_layer_II = QgsVectorLayer(change_detec_mosaic_shp)
                mosaic_shp_layer_spatialIndex_II = QgsSpatialIndex(mosaic_shp_layer_II.getFeatures())
        else:
            useDiyImgid = True
            mosaic_shp_layer = None
            
        
        # 1 前置处理3 -- 区号相关
        if image_area_id:
            useDiyImgAreaId = True
            area_layer = None
        else:
            useDiyImgAreaId = False
            area_layer = QgsVectorLayer(County_Boundary_Path)
            area_layer_spatialIndex = QgsSpatialIndex(area_layer.getFeatures())
        
        # 1 前置处理4 -- json相关
        now_time_strf = datetime.now().strftime("%Y-%m-%d %H:%M")
        class_num = len(extra_shp_pixel_mapping) if extra_shp_pixel_mapping else 1

        # 2 获取影像信息
        tif_ds : gdal.Dataset = gdal.Open(tif_path)
        tif_width = tif_ds.RasterXSize
        tif_height = tif_ds.RasterYSize
        tif_no_data_value = tif_ds.GetRasterBand(1).GetNoDataValue()
        tif_geoTrans = tif_ds.GetGeoTransform()
        tif_proj = tif_ds.GetProjection()
        if tif_geoTrans == (0,1,0,0,0,1):
            needUseDefaultGeoTrans = True
        else:
            needUseDefaultGeoTrans = False
        if tif_proj is None or tif_proj == "":
            needUseDefaultProj = True
        else:
            needUseDefaultProj = False

        if need_trans_rgb:
            tif_bands = 3
        else:
            tif_bands = tif_ds.RasterCount

        if generate_post == "png":
            src_driver : gdal.Driver = gdal.GetDriverByName("GTiff")
            dst_driver : gdal.Driver = gdal.GetDriverByName("PNG")       
        elif generate_post == "jpg":
            src_driver : gdal.Driver = gdal.GetDriverByName("GTiff")
            dst_driver : gdal.Driver = gdal.GetDriverByName("JPEG")
        elif generate_post == "tif":
            src_driver : gdal.Driver = gdal.GetDriverByName("GTiff")
            dst_driver : gdal.Driver = None

        # 3 获取制作样本的信息
        overlap_size = int(overlap*img_size)
        if extra_sub_index:
            sub_index = extra_sub_index
        else:
            sub_index = self._compute_block_by_generate_pair(tif_height,tif_width,img_size,overlap_size)
        generate_file_index = extra_generate_file_index
        return_sub_index = []
        # 4 开始循环
        for index,coord in enumerate(sub_index):
            if callback:
                callback((index+1)/len(sub_index)*100)
            else:
                print((index+1)/len(sub_index)*100)
            
            top_leftX = tif_geoTrans[0] + coord[2]*tif_geoTrans[1]
            top_leftY = tif_geoTrans[3] + coord[0]*tif_geoTrans[5]

            bottom_rightX = tif_geoTrans[0] + coord[3]*tif_geoTrans[1]
            bottom_rightY = tif_geoTrans[3] + coord[1]*tif_geoTrans[5]

            tempRec = QgsRectangle(top_leftX,bottom_rightY,bottom_rightX,top_leftY)

            transTemp = (top_leftX,tif_geoTrans[1],tif_geoTrans[2],top_leftY,tif_geoTrans[4],tif_geoTrans[5])
            if need_trans_rgb and tif_ds.RasterCount>=4:
                temp_img_array = tif_ds.ReadAsArray(coord[2],coord[0],img_size,img_size)[[2, 1, 0],:,:]
            else:
                temp_img_array = tif_ds.ReadAsArray(coord[2],coord[0],img_size,img_size)
            
            temp_label_array = label_tif_ds.ReadAsArray(coord[2],coord[0],img_size,img_size)
            if drop_zero and np.max(temp_label_array) == 0:
                print("标签全为0跳过：",index)
                continue
            
            if drop_no_data and np.max(temp_img_array[0]) == tif_no_data_value:
                print("影像无效空值跳过：",index)
                continue
            
            temp_img_path = osp.join(res_dir,f"{file_pre}_{generate_file_index:06d}.{generate_post}")
            temp_label_path = osp.join(extra_label_dir,f"{file_pre}_{generate_file_index:06d}.{generate_post}")
            if json_dir:
                temp_json_path = osp.join(json_dir,f"{file_pre}_{generate_file_index:06d}.json")
            

            if generate_post == "tif":
                out_img = src_driver.Create(temp_img_path,img_size,img_size,tif_bands,gdal.GDT_Byte,options=["COMPRESS=LZW"])
                if needUseDefaultGeoTrans:
                    out_img.SetGeoTransform(EXAMPLE_PNG_GEOTRANSFORM)
                else:
                    out_img.SetGeoTransform(transTemp)
                if needUseDefaultProj:
                    out_img.SetProjection(EXAMPLE_PNG_PROJECTION)
                else:
                    out_img.SetProjection(tif_proj)
                for i in range(tif_bands):
                    out_img_band = out_img.GetRasterBand(i + 1)
                    out_img_band.WriteArray(temp_img_array[i], 0, 0)
                del out_img
                if shp_path:
                    out_label_img = src_driver.Create(temp_label_path,img_size,img_size,1,gdal.GDT_Byte,options=["COMPRESS=LZW"])
                    if needUseDefaultGeoTrans:
                        out_label_img.SetGeoTransform(EXAMPLE_PNG_GEOTRANSFORM)
                    else:
                        out_label_img.SetGeoTransform(transTemp)
                    if needUseDefaultProj:
                        out_label_img.SetProjection(EXAMPLE_PNG_PROJECTION)
                    else:
                        out_label_img.SetProjection(tif_proj)
                        
                    out_label_img_band = out_label_img.GetRasterBand(1)
                    out_label_img_band.WriteArray(temp_label_array,0,0)
                    del out_label_img
            else:
                temp_tif_path = osp.join(temp_dir,f"{index}.tif")
                temp_tif_label_path = osp.join(temp_dir,f"{index}_label.tif")
                out_img = src_driver.Create(temp_tif_path,img_size,img_size,tif_bands,gdal.GDT_Byte,options=["COMPRESS=LZW"])

                if needUseDefaultGeoTrans:
                    out_img.SetGeoTransform(EXAMPLE_PNG_GEOTRANSFORM)
                else:
                    out_img.SetGeoTransform(transTemp)
                if needUseDefaultProj:
                    out_img.SetProjection(EXAMPLE_PNG_PROJECTION)
                else:
                    out_img.SetProjection(tif_proj)
                for i in range(tif_bands):
                    out_img_band = out_img.GetRasterBand(i + 1)
                    out_img_band.WriteArray(temp_img_array[i], 0, 0)
                dst_driver.CreateCopy(temp_img_path,out_img)
                del out_img
                if shp_path:
                    out_label_img = src_driver.Create(temp_tif_label_path,img_size,img_size,1,gdal.GDT_Byte,options=["COMPRESS=LZW"])
                    if needUseDefaultGeoTrans:
                        out_label_img.SetGeoTransform(EXAMPLE_PNG_GEOTRANSFORM)
                    else:
                        out_label_img.SetGeoTransform(transTemp)
                    if needUseDefaultProj:
                        out_label_img.SetProjection(EXAMPLE_PNG_PROJECTION)
                    else:
                        out_label_img.SetProjection(tif_proj)
                    out_label_img_band = out_label_img.GetRasterBand(1)
                    out_label_img_band.SetNoDataValue(0)
                    out_label_img_band.WriteArray(temp_label_array,0,0)
                    dst_driver.CreateCopy(temp_label_path,out_label_img)
                    del out_label_img
            
            if json_dir:
                if img_epsg_id:
                    tempGeo =QgsGeometry.fromRect(tempRec)
                    if xform:
                        tempGeo.transform(xform)

                    if not useDiyImgid:
                        try:
                            nearestMosaicIdList = mosaic_shp_layer_spatialIndex.nearestNeighbor(tempGeo,neighbors=1)
                            trueMosaicId = nearestMosaicIdList[0]
                            for id in nearestMosaicIdList:
                                tempMosaicFeat = mosaic_shp_layer.getFeature(id)
                                if tempMosaicFeat.geometry().intersects(tempGeo):
                                    trueMosaicId = id
                                    break
                            mosaic_img_id = str(mosaic_shp_layer.getFeature(trueMosaicId)[mosaic_shp_imgid_field])
                            _,_,mosaic_img_id_time,_,_,_,_,_ = mosaic_img_id.split("_")
                            mosaic_img_id_time_sfrt = f"{mosaic_img_id_time[0:4]}-{mosaic_img_id_time[4:6]}-{mosaic_img_id_time[6:8]}"
                        except Exception as e:
                            mosaic_img_id_time_sfrt = "0000-00-00"
                        if change_detec_mosaic_shp:
                            try:
                                nearestMosaicIdList_II = mosaic_shp_layer_spatialIndex_II.nearestNeighbor(tempGeo,neighbors=1)
                                trueMosaicId_II = nearestMosaicIdList_II[0]
                                for id in nearestMosaicIdList_II:
                                    tempMosaicFeat = mosaic_shp_layer_II.getFeature(id)
                                    if tempMosaicFeat.geometry().intersects(tempGeo):
                                        trueMosaicId_II = id
                                        break
                                mosaic_img_id_II = str(mosaic_shp_layer_II.getFeature(trueMosaicId_II)[change_detec_mosaic_shp_imgid_field])
                                _,_,mosaic_img_id_time_II,_,_,_,_,_ = mosaic_img_id_II.split("_")
                                mosaic_img_id_time_sfrt_II = f"{mosaic_img_id_time_II[0:4]}-{mosaic_img_id_time_II[4:6]}-{mosaic_img_id_time_II[6:8]}"
                            except Exception as e:
                                mosaic_img_id_time_sfrt_II = "0000-00-00"
                        else:
                            mosaic_img_id_time_sfrt_II = "0000-00-00"
                    
                    if not useDiyImgAreaId:
                        try:
                            nearestAreaIdList = area_layer_spatialIndex.nearestNeighbor(tempGeo,neighbors=1)
                            trueAreaId = nearestAreaIdList[0]
                            for id in nearestAreaIdList:
                                tempAreaFeat = area_layer.getFeature(id)
                                if tempAreaFeat.geometry().intersects(tempGeo):
                                    trueAreaId = id
                                    break
                            search_area_id = area_layer.getFeature(trueAreaId)[County_Boundary_Field]
                        except Exception as e:
                            search_area_id = "43"
                else:
                    mosaic_img_id_time_sfrt = "0000-00-00"
                    mosaic_img_id_time_sfrt_II = "0000-00-00"
                    search_area_id = "43"
                            


                json_info = {
                    "Name" : sample_name,
                    "Class" : "Change Detection" if is_Change_detec else "Landcover Classification",
                    "Description" : sample_description,
                    "Builder" : sample_builder,
                    "Creation_Time" : now_time_strf,
                    "Class_Num" : class_num,
                    "Class_Dict" : class_dict,
                    
                    "Image_File_Name" : osp.basename(temp_img_path),
                    "Image_File_Path" : "",
                    "Image_After_File_Name" : osp.basename(temp_img_path) if is_Change_detec else "",
                    "Image_After_File_Path" : "",
                    "Image_Size_Width" : img_size,
                    "Image_Size_Height" : img_size,
                    "Image_Band" : tif_bands,

                    "Origin_Image_File_Name" : osp.basename(tif_path),
                    "Origin_Image_File_Path" : tif_path,
                    "Origin_Image_After_File_Name" : osp.basename(change_detec_tif_path) if change_detec_tif_path else "",
                    "Origin_Image_After_File_Path" : change_detec_tif_path if change_detec_tif_path else "",

                    "Image_Transfomers" : EXAMPLE_PNG_GEOTRANSFORM if needUseDefaultGeoTrans else transTemp,
                    "Image_Projection" : EXAMPLE_PNG_PROJECTION if needUseDefaultProj else tif_proj,
                    "Image_Projection_EPSG" : img_epsg_id,

                    "Label_File_Name" : osp.basename(temp_label_path),
                    "Label_File_Path" : "",
                    "Label_After_File_Name" : osp.basename(temp_label_path),
                    "Label_After_File_Path" : "",

                    "Origin_Shp_File_Name" : osp.basename(shp_path) if shp_path else "",
                    "Origin_Shp_File_Path" : shp_path if shp_path else "",

                    "Image_Time" : imgid_time if useDiyImgid else mosaic_img_id_time_sfrt,
                    "Image_After_Time" : imgid_time_II if useDiyImgid else mosaic_img_id_time_sfrt_II,
                    "Image_Area" : f"{image_area_id if useDiyImgAreaId else search_area_id}",
                }
                with open(temp_json_path,'w',encoding='utf-8') as jf:
                    json.dump(json_info,jf,ensure_ascii=False,indent=4)
            generate_file_index += 1
            return_sub_index.append(coord)
        if label_tif_ds:
            del label_tif_ds
        if mosaic_shp_layer:
            del mosaic_shp_layer
        if area_layer:
            del area_layer
        #deleteDir(temp_dir)

        return generate_file_index,return_sub_index

    def generate_cgwx_changeDetection_sample_by_single_tif(self,
                                                           tif_path,
                                                           tif_path_II,
                                                           res_dir,
                                                           res_dir_II,
                                                           json_dir,
                                                           shp_path,
                                                           extra_label_dir,
                                                           extra_label_dir_II,
                                                           need_trans_rgb=True,
                                                           overlap=0.9,
                                                           img_size=512,
                                                           drop_zero=True,
                                                           generate_post="png",
                                                           extra_shp_field=None,
                                                           extra_shp_field_II=None,
                                                           extra_shp_pixel_mapping=None,
                                                           extra_diy_pixel_value=1,
                                                           class_dict=None,
                                                           mosaic_shp=None,
                                                           mosaic_shp_II=None,
                                                           mosaic_shp_imgid_field="ImageSourc",
                                                           mosaic_shp_imgid_field_II="ImageSourc",
                                                           imgid_time=None,
                                                           imgid_time_II=None,
                                                           sample_name=None,
                                                           sample_description=None,
                                                           sample_builder=None,
                                                           image_area_id=None,
                                                           file_pre="LC_01",
                                                           extra_generate_file_index=0,
                                                           callback=None,
                                                           callbackII=None,
                                                           ):
        
        _,sub_index = self.generate_cgwx_segment_sample_by_single_tif(
                                                        tif_path=tif_path,
                                                        res_dir=res_dir,
                                                        shp_path=shp_path,
                                                        extra_label_dir=extra_label_dir,
                                                        json_dir=json_dir,
                                                        need_trans_rgb=need_trans_rgb,
                                                        overlap=overlap,
                                                        img_size=img_size,
                                                        drop_zero=drop_zero,
                                                        drop_no_data=True,
                                                        generate_post=generate_post,
                                                        extra_shp_field=extra_shp_field,
                                                        extra_shp_pixel_mapping=extra_shp_pixel_mapping,
                                                        extra_diy_pixel_value=extra_diy_pixel_value,
                                                        class_dict=class_dict,
                                                        mosaic_shp=mosaic_shp,
                                                        mosaic_shp_imgid_field=mosaic_shp_imgid_field,
                                                        imgid_time=imgid_time,
                                                        sample_name=sample_name,
                                                        sample_description=sample_description,
                                                        sample_builder=sample_builder,
                                                        image_area_id=image_area_id,
                                                        file_pre=file_pre,
                                                        extra_generate_file_index=extra_generate_file_index,
                                                        is_Change_detec=True,
                                                        change_detec_tif_path=tif_path_II,
                                                        imgid_time_II=imgid_time_II,
                                                        change_detec_mosaic_shp=mosaic_shp_II,
                                                        change_detec_mosaic_shp_imgid_field=mosaic_shp_imgid_field_II,
                                                        extra_sub_index=None,
                                                        callback=callback
                                                        )
            
        generate_file_index,_ = self.generate_cgwx_segment_sample_by_single_tif(
                                                        tif_path=tif_path_II,
                                                        res_dir=res_dir_II,
                                                        shp_path=shp_path,
                                                        extra_label_dir=extra_label_dir_II,
                                                        json_dir=None,
                                                        need_trans_rgb=need_trans_rgb,
                                                        overlap=overlap,
                                                        img_size=img_size,
                                                        drop_zero=False,
                                                        drop_no_data=False,
                                                        generate_post=generate_post,
                                                        extra_shp_field=extra_shp_field_II,
                                                        extra_shp_pixel_mapping=extra_shp_pixel_mapping,
                                                        extra_diy_pixel_value=extra_diy_pixel_value,
                                                        class_dict=class_dict,
                                                        mosaic_shp=None,
                                                        mosaic_shp_imgid_field=None,
                                                        imgid_time=None,
                                                        sample_name=None,
                                                        sample_description=None,
                                                        sample_builder=None,
                                                        image_area_id="",
                                                        file_pre=file_pre,
                                                        extra_generate_file_index=extra_generate_file_index,
                                                        is_Change_detec=False,
                                                        change_detec_tif_path=None,
                                                        imgid_time_II=None,
                                                        change_detec_mosaic_shp=None,
                                                        extra_sub_index=sub_index,
                                                        callback=callbackII
        )

        return generate_file_index,None
        
    def generate_cgwx_objectDetecion_sample_by_single_tif(self,
                                                          tif_path,
                                                          res_dir,
                                                          shp_path,
                                                          extra_label_dir,
                                                          json_dir,
                                                          need_trans_rgb=True,
                                                          overlap=0.9,
                                                          img_size=512,
                                                          generate_post="png",
                                                          extra_shp_field=None,
                                                          extra_shp_pixel_mapping:dict=None,
                                                          class_dict=None,
                                                          mosaic_shp=None,
                                                          mosaic_shp_imgid_field="ImageSourc",
                                                          imgid_time=None,
                                                          sample_name=None,
                                                          sample_description=None,
                                                          sample_builder=None,
                                                          image_area_id=None,
                                                          is_obb=False,
                                                          clip_min_area_per=0.1,
                                                          extra_generate_file_index=0,
                                                          file_pre="OD_01",
                                                          extra_sub_index=None,
                                                          callback=None,
                                                          ):
        
        # 0 文件夹前置处理 -- 创建临时文件夹 res_dir
        createDir(res_dir)
        temp_dir = osp.join(res_dir,f"temp_{datetime.now().strftime('%Y%m%d%H%M%S%f')}")
        createDir(temp_dir)
        if json_dir:
            createDir(json_dir)
        createDir(extra_label_dir)
        
        # 1 前置处理 获取矢量信息 并创建索引
        shp_layer = QgsVectorLayer(shp_path)
        shp_layer_spatialIndex = QgsSpatialIndex(shp_layer.getFeatures())
        try:
            img_epsg_id = shp_layer.crs().authid().split(":")[1]
            if img_epsg_id == "4326":
                xform = None
            else:
                crsDest = QgsCoordinateReferenceSystem("EPSG:4326")
                xform = QgsCoordinateTransform(shp_layer.crs(),crsDest,PROJECT.transformContext())
        except Exception as e:
            img_epsg_id = None
        
        # 1 前置处理2 -- 镶嵌线相关
        if imgid_time:
            useDiyImgid = True
            mosaic_shp_layer = None
        elif mosaic_shp and mosaic_shp_imgid_field:
            useDiyImgid = False
            mosaic_shp_layer = QgsVectorLayer(mosaic_shp)
            mosaic_shp_layer_spatialIndex = QgsSpatialIndex(mosaic_shp_layer.getFeatures())
        else:
            useDiyImgid = True
            mosaic_shp_layer = None
            
        
        # 1 前置处理3 -- 区号相关
        if image_area_id:
            useDiyImgAreaId = True
            area_layer = None
        else:
            useDiyImgAreaId = False
            area_layer = QgsVectorLayer(County_Boundary_Path)
            area_layer_spatialIndex = QgsSpatialIndex(area_layer.getFeatures())
        
        # 1 前置处理4 -- json相关
        now_time_strf = datetime.now().strftime("%Y-%m-%d %H:%M")
        class_num = len(extra_shp_pixel_mapping) if extra_shp_pixel_mapping else 1

        if extra_shp_pixel_mapping:
            extra_shp_mapping_key_list = list(extra_shp_pixel_mapping.keys())
        else:
            extra_shp_mapping_key_list = ['object']
        
        # 2 获取影像信息
        tif_ds : gdal.Dataset = gdal.Open(tif_path)
        tif_width = tif_ds.RasterXSize
        tif_height = tif_ds.RasterYSize
        tif_no_data_value = tif_ds.GetRasterBand(1).GetNoDataValue()
        tif_geoTrans = tif_ds.GetGeoTransform()
        tif_proj = tif_ds.GetProjection()
        if tif_geoTrans == (0,1,0,0,0,1):
            needUseDefaultGeoTrans = True
        else:
            needUseDefaultGeoTrans = False
        if tif_proj is None or tif_proj == "":
            needUseDefaultProj = True
        else:
            needUseDefaultProj = False

        if need_trans_rgb:
            tif_bands = 3
        else:
            tif_bands = tif_ds.RasterCount

        if generate_post == "png":
            src_driver : gdal.Driver = gdal.GetDriverByName("GTiff")
            dst_driver : gdal.Driver = gdal.GetDriverByName("PNG")       
        elif generate_post == "jpg":
            src_driver : gdal.Driver = gdal.GetDriverByName("GTiff")
            dst_driver : gdal.Driver = gdal.GetDriverByName("JPEG")
        elif generate_post == "tif":
            src_driver : gdal.Driver = gdal.GetDriverByName("GTiff")
            dst_driver : gdal.Driver = None
            
        # 3 获取制作样本的信息
        overlap_size = int(overlap*img_size)
        if extra_sub_index:
            sub_index = extra_sub_index
        else:
            sub_index = self._compute_block_by_generate_pair(tif_height,tif_width,img_size,overlap_size)

        generate_file_index = extra_generate_file_index
        return_sub_index = []
        
        # 4 开始循环
        for index,coord in enumerate(sub_index):
            if callback:
                callback((index+1)/len(sub_index)*100)
            else:
                print((index+1)/len(sub_index)*100,"%")
            
            top_leftX = tif_geoTrans[0] + coord[2]*tif_geoTrans[1]
            top_leftY = tif_geoTrans[3] + coord[0]*tif_geoTrans[5]

            bottom_rightX = tif_geoTrans[0] + coord[3]*tif_geoTrans[1]
            bottom_rightY = tif_geoTrans[3] + coord[1]*tif_geoTrans[5]

            transTemp = (top_leftX,tif_geoTrans[1],tif_geoTrans[2],top_leftY,tif_geoTrans[4],tif_geoTrans[5])

            if need_trans_rgb and tif_ds.RasterCount>=4:
                temp_img_array = tif_ds.ReadAsArray(coord[2],coord[0],img_size,img_size)[[2, 1, 0],:,:]
            else:
                temp_img_array = tif_ds.ReadAsArray(coord[2],coord[0],img_size,img_size)
            
            if np.max(temp_img_array[0]) == tif_no_data_value:
                print("影像无效空值跳过：",index)
                continue
            
            temp_img_path = osp.join(res_dir,f"{file_pre}_{generate_file_index:06d}.{generate_post}")
            temp_label_path = osp.join(extra_label_dir,f"{file_pre}_{generate_file_index:06d}.txt")
            temp_json_path = osp.join(json_dir,f"{file_pre}_{generate_file_index:06d}.json")

            tempRec = QgsRectangle(top_leftX,bottom_rightY,bottom_rightX,top_leftY)
            tempRecGeo = QgsGeometry.fromRect(tempRec)

            intersect_feature_ids = shp_layer_spatialIndex.intersects(tempRec)

            

            txt_contents = []
            for feature_id in intersect_feature_ids:
                temp_feature = shp_layer.getFeature(feature_id)
                if extra_shp_field:
                    temp_attr = str(temp_feature.attribute(extra_shp_field))
                    temp_attr_index = 0
                    if extra_shp_pixel_mapping:
                        print(extra_shp_mapping_key_list)
                        temp_attr_index = extra_shp_mapping_key_list.index(temp_attr)
                        temp_attr = extra_shp_pixel_mapping[temp_attr]
                else:
                    temp_attr = "object"
                    temp_attr_index = 0
                temp_feature_geo = temp_feature.geometry()
                if temp_feature_geo.intersects(tempRec):
                    temp_inter_geo = temp_feature_geo.intersection(tempRecGeo)
                    if (temp_inter_geo.area() / temp_feature_geo.area()) >= clip_min_area_per:
                        if is_obb:
                            temp_inter_boundingBox,a,b,c,d = temp_inter_geo.orientedMinimumBoundingBox()
                            if temp_inter_boundingBox.wkbType() == 3:
                                temp_inter_boundingBox_polygon = temp_inter_boundingBox.asPolygon()[0]
                                x1 = temp_inter_boundingBox_polygon[0].x()
                                y1 = temp_inter_boundingBox_polygon[0].y()
                                x1,y1 = self.geo2imagexy(x1,y1,transTemp)

                                x2 = temp_inter_boundingBox_polygon[1].x()
                                y2 = temp_inter_boundingBox_polygon[1].y()
                                x2,y2 = self.geo2imagexy(x2,y2,transTemp)

                                x3 = temp_inter_boundingBox_polygon[2].x()
                                y3 = temp_inter_boundingBox_polygon[2].y()
                                x3,y3 = self.geo2imagexy(x3,y3,transTemp)

                                x4 = temp_inter_boundingBox_polygon[3].x()
                                y4 = temp_inter_boundingBox_polygon[3].y()
                                x4,y4 = self.geo2imagexy(x4,y4,transTemp)

                                txt_contents.append(f"{x1} {y1} {x2} {y2} {x3} {y3} {x4} {y4} {temp_attr} \n")

                        else:
                            temp_inter_boundingBox = temp_inter_geo.boundingBox()
                            temp_left_up_in_matrix = self.geo2imagexy(temp_inter_boundingBox.xMinimum(),temp_inter_boundingBox.yMaximum(),transTemp)
                            temp_right_down_in_matrix = self.geo2imagexy(temp_inter_boundingBox.xMaximum(),temp_inter_boundingBox.yMinimum(),transTemp)
                            xMin_matrix = temp_left_up_in_matrix[0] / img_size
                            xMax_matrix = temp_right_down_in_matrix[0] / img_size
                            yMin_matrix = temp_left_up_in_matrix[1] / img_size
                            yMax_matrix = temp_right_down_in_matrix[1] / img_size
                            w_matrix = xMax_matrix - xMin_matrix
                            h_matrix = yMax_matrix - yMin_matrix
                            x_center_matrix = (xMax_matrix + xMin_matrix) / 2
                            y_center_matrix = (yMax_matrix + yMin_matrix) / 2
                            txt_contents.append(f"{temp_attr_index} {x_center_matrix} {y_center_matrix} {w_matrix} {h_matrix} \n")

            if len(txt_contents) == 0:
                continue

            if generate_post == "tif":
                out_img = src_driver.Create(temp_img_path,img_size,img_size,tif_bands,gdal.GDT_Byte,options=["COMPRESS=LZW"])
                if needUseDefaultGeoTrans:
                    out_img.SetGeoTransform(EXAMPLE_PNG_GEOTRANSFORM)
                else:
                    out_img.SetGeoTransform(transTemp)
                if needUseDefaultProj:
                    out_img.SetProjection(EXAMPLE_PNG_PROJECTION)
                else:
                    out_img.SetProjection(tif_proj)
                for i in range(tif_bands):
                    out_img_band = out_img.GetRasterBand(i + 1)
                    out_img_band.WriteArray(temp_img_array[i], 0, 0)
                del out_img
            else:
                temp_tif_path = osp.join(temp_dir,f"{index}.tif")
                out_img = src_driver.Create(temp_tif_path,img_size,img_size,tif_bands,gdal.GDT_Byte,options=["COMPRESS=LZW"])

                if needUseDefaultGeoTrans:
                    out_img.SetGeoTransform(EXAMPLE_PNG_GEOTRANSFORM)
                else:
                    out_img.SetGeoTransform(transTemp)
                if needUseDefaultProj:
                    out_img.SetProjection(EXAMPLE_PNG_PROJECTION)
                else:
                    out_img.SetProjection(tif_proj)
                for i in range(tif_bands):
                    out_img_band = out_img.GetRasterBand(i + 1)
                    out_img_band.WriteArray(temp_img_array[i], 0, 0)
                dst_driver.CreateCopy(temp_img_path,out_img)
                del out_img

            with open(temp_label_path,'w') as f:
                for content in txt_contents:
                    f.write(content)
            
            if img_epsg_id:
                tempGeo =QgsGeometry.fromRect(tempRec)
                if xform:
                    tempGeo.transform(xform)
                if not useDiyImgid:
                    try:
                        nearestMosaicIdList = mosaic_shp_layer_spatialIndex.nearestNeighbor(tempGeo,neighbors=1)
                        trueMosaicId = nearestMosaicIdList[0]
                        for id in nearestMosaicIdList:
                            tempMosaicFeat = mosaic_shp_layer.getFeature(id)
                            if tempMosaicFeat.geometry().intersects(tempGeo):
                                trueMosaicId = id
                                break
                        mosaic_img_id = str(mosaic_shp_layer.getFeature(trueMosaicId)[mosaic_shp_imgid_field])
                        _,_,mosaic_img_id_time,_,_,_,_,_ = mosaic_img_id.split("_")
                        mosaic_img_id_time_sfrt = f"{mosaic_img_id_time[0:4]}-{mosaic_img_id_time[4:6]}-{mosaic_img_id_time[6:8]}"
                    except Exception as e:
                        mosaic_img_id_time_sfrt = "0000-00-00"
                
                if not useDiyImgAreaId:
                    try:
                        nearestAreaIdList = area_layer_spatialIndex.nearestNeighbor(tempGeo,neighbors=1)
                        trueAreaId = nearestAreaIdList[0]
                        for id in nearestAreaIdList:
                            tempAreaFeat = area_layer.getFeature(id)
                            if tempAreaFeat.geometry().intersects(tempGeo):
                                trueAreaId = id
                                break
                        search_area_id = area_layer.getFeature(trueAreaId)[County_Boundary_Field]
                    except Exception as e:
                        search_area_id = "43"
            else:
                mosaic_img_id_time_sfrt = "0000-00-00"
                search_area_id = "43"
            

            json_info = {
                    "Name" : sample_name,
                    "Class" : "Object Detectuib",
                    "Description" : sample_description,
                    "Builder" : sample_builder,
                    "Creation_Time" : now_time_strf,
                    "Class_Num" : class_num,
                    "Class_Dict" : class_dict,
                    
                    "Image_File_Name" : osp.basename(temp_img_path),
                    "Image_File_Path" : "",
                    "Image_After_File_Name" : "",
                    "Image_After_File_Path" : "",
                    "Image_Size_Width" : img_size,
                    "Image_Size_Height" : img_size,
                    "Image_Band" : tif_bands,

                    "Origin_Image_File_Name" : osp.basename(tif_path),
                    "Origin_Image_File_Path" : tif_path,
                    "Origin_Image_After_File_Name" : "",
                    "Origin_Image_After_File_Path" : "",

                    "Image_Transfomers" : EXAMPLE_PNG_GEOTRANSFORM if needUseDefaultGeoTrans else transTemp,
                    "Image_Projection" : EXAMPLE_PNG_PROJECTION if needUseDefaultProj else tif_proj,
                    "Image_Projection_EPSG" : img_epsg_id,

                    "Label_File_Name" : osp.basename(temp_label_path),
                    "Label_File_Path" : "",
                    "Label_After_File_Name" : osp.basename(temp_label_path),
                    "Label_After_File_Path" : "",

                    "Origin_Shp_File_Name" : osp.basename(shp_path) if shp_path else "",
                    "Origin_Shp_File_Path" : shp_path if shp_path else "",

                    "Image_Time" : imgid_time if useDiyImgid else mosaic_img_id_time_sfrt,
                    "Image_After_Time" : "",
                    "Image_Area" : f"{image_area_id if useDiyImgAreaId else search_area_id}",
                }
            with open(temp_json_path,'w',encoding='utf-8') as jf:
                json.dump(json_info,jf,ensure_ascii=False,indent=4)
            
            generate_file_index += 1
 
        if not is_obb:
            with open(osp.join(extra_label_dir,"classes.txt"),'w',encoding='utf-8') as f:
                for key in extra_shp_mapping_key_list:
                    f.write(f"{key} \n")
                
        if shp_layer:
            del shp_layer
        
        deleteDir(temp_dir)
        return generate_file_index,None

            

        
if __name__ == "__main__":
    
    x = [1,2,3,4,5,6,7,8,9,10]

    res = train_test_split(x,test_size=0.1,shuffle=False)
    print(res)
    


