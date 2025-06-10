
import os
import os.path as osp
import math

from qgis.core import QgsMapLayer,QgsRasterLayer,QgsVectorLayer,QgsProject,QgsRasterDataProvider,QgsVectorDataProvider,QgsFeature,QgsRectangle,QgsCoordinateReferenceSystem,QgsWkbTypes
from qgis.gui import QgsMapCanvas

from qfluentwidgets import MessageBox

import requests

from yoyiUtils.yoyiTranslate import yoyiTrans
from appConfig import yoyiSetting,Jl1TileUrlDict,SourceReplaceList

PROJECT = QgsProject.instance()

def getFileSize(filePath):
    try:
        fsize = osp.getsize(filePath)  # 返回的是字节大小

        if fsize < 1024:
            return f"{round(fsize, 2)}Byte"
        else:
            KBX = fsize / 1024
            if KBX < 1024:
                return f"{round(KBX, 2)}Kb"
            else:
                MBX = KBX / 1024
                if MBX < 1024:
                    return f"{round(MBX, 2)}Mb"
                else:
                    return f"{round(MBX/1024,2)}Gb"
    except Exception as e:
        return "无数据"

def addMapLayer(layer:QgsMapLayer,mapCanvas:QgsMapCanvas,yoyiTrs:yoyiTrans,firstAddLayer=False,needShowNovalidMsg=True,parent=None):
    if layer.isValid():
        if firstAddLayer:
            #PROJECT.setCrs(layer.crs(),True)
            print("first")
            mapCanvas.setDestinationCrs(layer.crs())

        while(PROJECT.mapLayersByName(layer.name())):
            layer.setName(layer.name()+"_1")

        PROJECT.addMapLayer(layer)
        #layers = [PROJECT.mapLayer(i) for i in PROJECT.mapLayers()]

        if firstAddLayer:
            print(layer.extent())
            mapCanvas.setExtent(layer.extent())
        mapCanvas.refresh()
    else:
        if needShowNovalidMsg:
            MessageBox(yoyiTrs._translate('警告'), yoyiTrs._translate('图层无效'),parent=parent).exec_()


def readRasterFile(rasterFilePath):
    rasterLayer = QgsRasterLayer(rasterFilePath,osp.basename(rasterFilePath))
    for i in range(rasterLayer.bandCount()):
        rasterLayer.dataProvider().setNoDataValue(i+1,0)
    return rasterLayer

def readVectorFile(vectorFilePath):
    # ,"ogr"
    vectorLayer = QgsVectorLayer(vectorFilePath,osp.basename(vectorFilePath))
    #vectorLayer.setProviderEncoding('utf-8')
    return vectorLayer

qgisDataTypeDict = {
    0 : "UnknownDataType",
    1 : "Uint8",
    2 : "UInt16",
    3 : "Int16",
    4 : "UInt32",
    5 : "Int32",
    6 : "Float32",
    7 : "Float64",
    8 : "CInt16",
    9 : "CInt32",
    10 : "CFloat32",
    11 : "CFloat64",
    12 : "ARGB32",
    13 : "ARGB32_Premultiplied"
}

def getRasterLayerAttrs(rasterLayer:QgsRasterLayer):
    
    rdp : QgsRasterDataProvider = rasterLayer.dataProvider()
    crs : QgsCoordinateReferenceSystem = rasterLayer.crs()
    extent: QgsRectangle = rasterLayer.extent()
    if "http" in rasterLayer.source():
        
        needReplace = False
        for content in SourceReplaceList:
            if content in rasterLayer.source():
                needReplace = True
                break

        resDict = {
            "name" : rasterLayer.name(),
            "source" : "***************" if needReplace else rasterLayer.source(),
            "memory" : "???",
            "extent" : f"min:[{extent.xMinimum():.6f},{extent.yMinimum():.6f}]; max:[{extent.xMaximum():.6f},{extent.yMaximum():.6f}]",
            "width" : "???",
            "height" : "???",
            "dataType" : "???",
            "bands" : "???",
            "crs" : crs.description()
        }
    else:
        resDict = {
            "name" : rasterLayer.name(),
            "source" : rasterLayer.source(),
            "memory" : getFileSize(rasterLayer.source()),
            "extent" : f"min:[{extent.xMinimum():.6f},{extent.yMinimum():.6f}]; max:[{extent.xMaximum():.6f},{extent.yMaximum():.6f}]",
            "width" : f"{rasterLayer.width()}",
            "height" : f"{rasterLayer.height()}",
            "dataType" : qgisDataTypeDict[rdp.dataType(1)],
            "bands" : f"{rasterLayer.bandCount()}",
            "crs" : f"{crs.description()}-{crs.authid()}"
        }
    return resDict

def getVectorLayerAttrs(vectorLayer:QgsVectorLayer):
    vdp : QgsVectorDataProvider = vectorLayer.dataProvider()
    crs: QgsCoordinateReferenceSystem = vectorLayer.crs()
    extent: QgsRectangle = vectorLayer.extent()
    if vectorLayer.featureCount() == 0:
        extentContent = "Unknown"
    else:
        extentContent = f"min:[{extent.xMinimum():.6f},{extent.yMinimum():.6f}]; max:[{extent.xMaximum():.6f},{extent.yMaximum():.6f}]"
        if len(extentContent) > 40:
            extentContent = "Unknwon"
    resDict = {
        "name" : vectorLayer.name(),
        "source" : vectorLayer.source(),
        "memory": getFileSize(vectorLayer.source()),
        "extent" : extentContent,
        "geoType" : QgsWkbTypes.geometryDisplayString(vectorLayer.geometryType()),
        "featureNum" : f"{vectorLayer.featureCount()}",
        "encoding" : vdp.encoding(),
        "crs" : f"{crs.description()}-{crs.authid()}",
        "dpSource" : vdp.description()
    }
    return resDict

# 从字符串或者txt读取wms图层
def loadWmsasLayer(content,layerName,isTxt=False,max17=False):
    if isTxt:
        with open(content,'r') as f:
            httpStr = f.readline()
        if max17:
            wmsContent = f"type=xyz&url={requests.utils.quote(httpStr)}&zmax=17&zmin=0"
        else:
            wmsContent = f"type=xyz&url={requests.utils.quote(httpStr)}"
    else:
        netMode = yoyiSetting().configSettingReader.value('netMode',type=int)
        if netMode > 0:
            content = content.replace(Jl1TileUrlDict[0],Jl1TileUrlDict[netMode])
        if max17:
            wmsContent = f"type=xyz&url={requests.utils.quote(content)}&zmax=17&zmin=0"
        else:
            wmsContent = f"type=xyz&url={requests.utils.quote(content)}"
    print(wmsContent)
    
    resLayer = QgsRasterLayer(wmsContent,layerName,'wms')

    return resLayer
 

# 给定一个矢量文件，得到一个FID的list列表文件
def getFIDlist(layer:QgsVectorLayer,transStr=True):
    resList = []
    for feature in layer.getFeatures():
        feature : QgsFeature
        #print(feature.attributes())
        resList.append(feature.attribute("FID"))
    #resList.sort()
    if transStr:
        for i in range(len(resList)):
            resList[i] = str(resList[i])
    return resList

# 将figList N等分
def assignFIDlist(fidList,assignTifNum):
    assignLen = math.ceil(len(fidList) / assignTifNum)
    for i in range(0,len(fidList),assignLen):
        yield fidList[i:i+assignLen]