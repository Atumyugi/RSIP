import datetime
import os
import os.path as osp
import re
import traceback
import shutil

from osgeo import gdal,ogr

from PyQt5.QtCore import Qt, QPoint,QThread,pyqtSignal,QVariant
from PyQt5.QtWidgets import QApplication, QDialog, QHBoxLayout, QVBoxLayout
from qgis.core import QgsCoordinateReferenceSystem,QgsRasterLayer,QgsVectorLayer,QgsProject,QgsCoordinateTransform,QgsGeometry,QgsFeature,QgsVectorDataProvider,QgsField

from yoyiUtils.qtTriggeredCommon import qtTriggeredCommonDialog
from yoyiUtils.yoyiFile import checkTifList,createDir,saveSampleWorkYaml
from yoyiUtils.qgisFunction import saveShpFunc,createFishNet,createFishNetByXYInterval
from yoyiUtils.gdalCommon import createEmptyShapefile,raster2shp
from yoyiUtils.yoyiDataSet import yoyiDataSetProducer
from yoyiUtils.rs_clsfy import MleClsfyRsInference
from appConfig import *

PROJECT = QgsProject.instance()

class createLocalProjectRunClass(QThread):
    signal_over = pyqtSignal(str)
    def __init__(self,tifPath,outDir,segSize,mosaicPath,extraShp,parent=None):
        super().__init__(parent)
        self.tifPath = tifPath
        self.outDir = outDir
        self.segSize = segSize
        self.mosaicPath = mosaicPath
        self.extraShp = extraShp

    def run(self):
        try:
            createFishNet(self.tifPath, self.segSize, osp.join(self.outDir, "fishNet.gpkg"),driverName="GPKG")
            if self.mosaicPath:
                mosaicALayer = QgsVectorLayer(self.mosaicPath)
                tempFishNetLayer = QgsVectorLayer(osp.join(self.outDir, "fishNet.gpkg"))
                if mosaicALayer.crs() != tempFishNetLayer.crs():
                    crsSrc = mosaicALayer.crs()
                    crsDest = tempFishNetLayer.crs()
                    transformContext = PROJECT.transformContext()
                    ct = QgsCoordinateTransform(crsSrc, crsDest, transformContext)
                    saveShpFunc(osp.join(self.outDir, "tileA.gpkg"), mosaicALayer, ct=ct,driverName="GPKG")
                else:
                    saveShpFunc(osp.join(self.outDir, "tileA.gpkg"), mosaicALayer,driverName="GPKG")

                mergeAGeo: QgsGeometry = None
                for feature in mosaicALayer.getFeatures():
                    feature: QgsFeature
                    if mergeAGeo == None:
                        mergeAGeo = feature.geometry()
                    else:
                        mergeAGeo = mergeAGeo.combine(feature.geometry())

                tempFishNetLayer.startEditing()
                ids = []
                for feature in tempFishNetLayer.getFeatures():
                    feature: QgsFeature
                    beDel = False
                    if mergeAGeo and mergeAGeo.isGeosValid() and not mergeAGeo.intersects(feature.geometry()):
                        beDel = True
                    if beDel:
                        ids.append(feature.id())
                tempFishNetLayer.deleteFeatures(ids)
                tempFishNetLayer.commitChanges()

            if self.extraShp:
                tempTifLayer = QgsRasterLayer(self.tifPath)
                tempExtraShpLayer = QgsVectorLayer(self.extraShp)
                transformContext = PROJECT.transformContext()
                ct = QgsCoordinateTransform(tempExtraShpLayer.crs(), tempTifLayer.crs(), transformContext)
                saveShpFunc(osp.join(self.outDir, "defaultWork.shp"), tempExtraShpLayer,ct=ct)

            self.signal_over.emit(self.outDir)

        except Exception as e:
            self.signal_over.emit(traceback.format_exc()[-1000:] if len(traceback.format_exc()>1000) else traceback.format_exc())


class createWmsProjectRunClass(QThread):
    signal_over = pyqtSignal(str)
    def __init__(self, shpPath, outDir, xSegNum,ySegNum, extraShp, parent=None):
        super().__init__(parent)
        self.shpPath = shpPath
        self.outDir = outDir
        self.xSegNum = xSegNum
        self.ySegNum = ySegNum
        self.extraShp = extraShp

    def run(self):
        try:
            shpLayer = QgsVectorLayer(self.shpPath)
            ct = QgsCoordinateTransform(shpLayer.crs(), QgsCoordinateReferenceSystem('EPSG:3857'),
                                        PROJECT.transformContext())
            resExtentShp = osp.join(self.outDir, "extent.gpkg")
            saveShpFunc(resExtentShp,shpLayer,ct,driverName="GPKG")
            createFishNetByXYInterval(resExtentShp,osp.join(self.outDir, "fishNet.gpkg"),self.xSegNum,self.ySegNum)

            if self.extraShp:
                tempExtraShpLayer = QgsVectorLayer(self.extraShp)
                transformContext = PROJECT.transformContext()
                ct = QgsCoordinateTransform(tempExtraShpLayer.crs(), shpLayer.crs(), transformContext)
                saveShpFunc(osp.join(self.outDir, "defaultWork.gpkg"), tempExtraShpLayer,ct=ct,driverName="GPKG")

            self.signal_over.emit(self.outDir)
        except:
            self.signal_over.emit(traceback.format_exc()[-1000:] if len(traceback.format_exc() > 1000) else traceback.format_exc())


class createLocalDirProjectRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)
    def __init__(self,tifList,outDir,pixelMap,nodataValue=0,labelDir="",labelPost="",lateImgDir="",parent=None):
        super().__init__(parent)
        self.tifList = tifList
        self.outDir = outDir
        self.pixelMap : dict = pixelMap
        self.nodataValue = nodataValue
        self.labelDir = labelDir
        self.labelPost = labelPost
        self.lateImgDir = lateImgDir

    def run(self):
        try:
            shpDir = osp.join(self.outDir,"vector")
            tifLen = len(self.tifList)
            createDir(shpDir)

            if osp.exists(self.labelDir):
                importLabel = True
            else:
                importLabel = False
            if osp.exists(self.lateImgDir):
                changeDetecMode = True
            else:
                changeDetecMode = False
            for index,tif in enumerate(self.tifList):
                tempTifDs : gdal.Dataset = gdal.Open(tif)
                if tempTifDs.GetGeoTransform() == (0,1,0,0,0,1):
                    tempTifDs.SetGeoTransform(EXAMPLE_PNG_GEOTRANSFORM)
                if tempTifDs.GetProjection() is None or tempTifDs.GetProjection() == "":
                    tempTifDs.SetProjection(EXAMPLE_PNG_PROJECTION)
                
                tempWkt = tempTifDs.GetProjection()
                #print(tempWkt)
                
                tempShpPath = osp.join(shpDir,osp.basename(tif).split(".")[0]+".shp")
                tempLateImgPath = osp.join(self.lateImgDir,osp.basename(tif))
                if changeDetecMode:
                    tempLateImgDs : gdal.Dataset = gdal.Open(tempLateImgPath)
                    tempLateImgDs.SetGeoTransform(tempTifDs.GetGeoTransform())
                    tempLateImgDs.SetProjection(tempTifDs.GetProjection())
                    del tempLateImgDs
                if importLabel and osp.exists(tempLabelPath:=osp.join(self.labelDir,osp.basename(tif).split(".")[0]+"."+self.labelPost)):
                    tempLabelDs : gdal.Dataset = gdal.Open(tempLabelPath)
                    tempLabelDs.SetGeoTransform(tempTifDs.GetGeoTransform())
                    tempLabelDs.SetProjection(tempTifDs.GetProjection())
                    del tempLabelDs
                    raster2shp(tempLabelPath,tempShpPath,"value",noData=self.nodataValue,fieldIsString=True)
                    swapped_pixelMap = {value: key for key, value in self.pixelMap.items()} # 反转字典为： {1:"耕地"}
                    first_mapAttr = list(self.pixelMap.keys())[0] 
                    tempLayer = QgsVectorLayer(tempShpPath)
                    if changeDetecMode:
                        tempLayer.dataProvider().addAttributes([QgsField("QDLDM", QVariant.String),QgsField("HDLDM", QVariant.String)])
                        tempLayer.updateFields()  # 告诉矢量图层从提供者获取更改
                        tempLayer.startEditing()
                        for feature in tempLayer.getFeatures():
                            tempValue = int(feature.attribute('value'))
                            if tempValue in swapped_pixelMap.keys():
                                featureLabel = swapped_pixelMap[tempValue]
                                if len(self.pixelMap) > 1:
                                    preValue,postValue = featureLabel.split(STRING_Right)
                                else:
                                    preValue,postValue = featureLabel,featureLabel
                                attrs = {0:featureLabel,1:preValue,2:postValue}
                            else:
                                if len(self.pixelMap) > 1:
                                    attrs = {0:first_mapAttr+STRING_Right+first_mapAttr,1:first_mapAttr,2:first_mapAttr}
                                else:
                                    attrs = {0:first_mapAttr,1:first_mapAttr,2:first_mapAttr}
                            
                            tempLayer.changeAttributeValues(feature.id(),attrs)
                        tempLayer.commitChanges()
                    else:
                        tempLayer.startEditing()
                        for feature in tempLayer.getFeatures():
                            tempValue = int(feature.attribute('value'))
                            if tempValue in swapped_pixelMap.keys():
                                tempLayer.changeAttributeValue(feature.id(),0, swapped_pixelMap[tempValue])
                            else:
                                tempLayer.changeAttributeValue(feature.id(),0,first_mapAttr)
                        tempLayer.commitChanges()
                    del tempLayer
                else:
                    if changeDetecMode:
                        fieldDict = {
                            'value':ogr.OFTString,
                            'QDLDM':ogr.OFTString,
                            'HDLDM':ogr.OFTString
                                     }
                        createEmptyShapefile(tempShpPath,tempWkt,fieldDict=fieldDict,post="shp")
                    else:
                        createEmptyShapefile(tempShpPath,tempWkt,post="shp")
                del tempTifDs

                self.signal_process.emit(index / tifLen * 100)

            self.signal_over.emit(self.outDir)

        except Exception as e:
            self.signal_over.emit(traceback.format_exc()[-1000:] if len(traceback.format_exc())>1000 else traceback.format_exc())

class updateDataSetRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)
    def __init__(self,label_dir_path,label_shp_path,img_dir_path,pixel_map,attr_field,img_post,label_post,parent=None):
        super().__init__(parent)
        self.label_dir_path = label_dir_path
        self.label_shp_path = label_shp_path
        self.img_dir_path = img_dir_path
        self.pixel_map = pixel_map
        self.attr_field = attr_field
        self.img_post = img_post
        self.label_post = label_post

    def updateProcess(self,process):
        self.signal_process.emit(process)

    def run(self):
        try:
            yoyiDataSetProducer().update_segment_sample_by_multi_shp(
                label_dir_path=self.label_dir_path,
                label_shp_path=self.label_shp_path,
                img_dir_path=self.img_dir_path,
                pixel_map=self.pixel_map,
                attr_field=self.attr_field,
                img_post=self.img_post,
                label_post=self.label_post,
                callback=self.updateProcess
            )

            self.signal_over.emit(self.label_dir_path)
        except Exception as e:
            self.signal_over.emit(e)
        
class pixelClsfyRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(list)

    def __init__(self,imgPath,shpPath,resultPath,fieldName,attrMapping,mode,parent=None):
        super().__init__(parent)
        self.imgPath = imgPath
        self.shpPath = shpPath
        self.resultPath = resultPath
        self.fieldName = fieldName
        self.attrMapping = attrMapping
        self.mode =mode
    
    def updateProcess(self,process):
        self.signal_process.emit(process)

    def run(self):
        try:
            mleInfer = MleClsfyRsInference(512)
            mleInfer.infer_tif(self.imgPath,
                               self.resultPath,
                               self.shpPath,
                               self.fieldName,
                               self.attrMapping,
                               callback=self.updateProcess)
            del mleInfer
            self.signal_over.emit([self.resultPath,self.attrMapping])
        except Exception as e:
            print(traceback.format_exc())
            self.signal_over.emit([e,self.attrMapping])


class calFieldUniqueValuesRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(list)

    def __init__(self,shpPathList,fieldName,maxLen=50,extraFieldName=None,parent=None):
        super().__init__(parent)
        self.shpPathList = shpPathList
        self.fieldName = fieldName
        self.maxLen = maxLen
        self.extraFieldName = extraFieldName
    
    def updateProcess(self,process):
        self.signal_process.emit(process)

    def run(self):
        try:
            uniqueList = []
            for shpPath in self.shpPathList:
                shpLayer = QgsVectorLayer(shpPath)
                for feat in shpLayer.getFeatures():
                    tempValue = feat.attribute(self.fieldName)
                    if tempValue == None:
                        self.signal_over.emit(["字段中有空值",[]])
                        return 
                    if tempValue not in uniqueList:
                        if len(uniqueList) > self.maxLen:
                            self.signal_over.emit(["字段唯一值过多！！！",[]])
                            return 
                        else:
                            uniqueList.append(tempValue)
                    if self.extraFieldName:
                        extraValue = feat.attribute(self.extraFieldName)
                        if tempValue == None:
                            self.signal_over.emit(["字段中有空值",[]])
                            return
                        if extraValue not in uniqueList:
                            if len(uniqueList) > self.maxLen:
                                self.signal_over.emit(["字段唯一值过多！！！",[]])
                                return 
                            else:
                                uniqueList.append(extraValue)
                del shpLayer

            self.signal_over.emit(["",uniqueList])


        except Exception as e:
            print(traceback.format_exc())
            self.signal_over.emit(["未知报错",[]])
