import os
import os.path as osp
from datetime import datetime
import traceback
import shutil

from PyQt5.QtCore import QThread,pyqtSignal
from qgis.core import QgsProject,QgsProcessingFeedback,QgsCoordinateReferenceSystem,\
            QgsCoordinateTransform,QgsVectorLayer,QgsRasterLayer,QgsRectangle
from qgis.analysis import QgsRasterCalculator
from qgis import processing

import numpy as np
import appConfig

from yoyiUtils.yoyiFile import createDir,makeFileUnique,deleteDir
from yoyiUtils.gdalCommon import raster2shp,calNormalizedIII,calNormalizedIV,mergeTifs,clipTifByOutBounds,uint16to8
from yoyiUtils.qgisFunction import shpCommonProcess,createFishNetByExtent,createFishNet,createFishNetByXYExtent,shpChangeAnalysis,saveShpFunc
from yoyiUtils.buildOrthogo import shp_orthogo_process
from yoyiUtils.yoyiDataSet import yoyiDataSetProducer,splitDataset
# 栅格处理

PROJECT = QgsProject.instance()

class YoyiFeedBack(QgsProcessingFeedback):
    def __init__(self) -> None:
        super().__init__()
        self.errorMsg = None
    def reportError(self, error, fatalError=True):
        if ("ERROR" in error) and fatalError==True:
            self.errorMsg = error
        print(f"影响运行？{fatalError}",error)

class raster2ShpBatchRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)
    def __init__(self,tifList,resDir,rtsFieldName,postName,rtsBandIndex=1,rtsDriver="ESRI Shapefile",rts8Connect=0,parent=None):
        super(raster2ShpBatchRunClass ,self).__init__(parent)
        self.tifList = tifList
        self.resDir = resDir
        self.rtsFieldName = rtsFieldName
        self.postName = postName
        self.rtsBandIndex = rtsBandIndex
        self.rtsDriver = rtsDriver
        self.rts8Connect = rts8Connect

    def updateProcessSingle(self,a, b, c):
        # print("a",a,"b",b,"c",c)
        self.signal_process.emit(a * 100)

    def updateProcessMulti(self,process):
        self.signal_process.emit(process*100)

    def run(self):
        if len(self.tifList) == 1:
            resShp = osp.join(self.resDir, osp.basename(self.tifList[0]).split(".")[0] + self.postName + ".shp" )
            res = raster2shp(self.tifList[0],resShp,self.rtsFieldName,self.rtsBandIndex,self.rtsDriver,self.rts8Connect,callback=self.updateProcessSingle)
            if res == 0:
                self.signal_over.emit(resShp)
            else:
                self.signal_over.emit("error： Trans Failed")

        else:
            for index in range(len(self.tifList)):

                tempResShp = osp.join(self.resDir, osp.basename(self.tifList[index]).split(".")[0] + self.postName + ".shp" )

                raster2shp(self.tifList[index],tempResShp,self.rtsFieldName,self.rtsBandIndex,self.rtsDriver,self.rts8Connect,callback=None)

                self.updateProcessMulti((index + 1) / len(self.tifList))

            self.signal_over.emit(self.resDir)

class raster16to8BatchRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)
    def __init__(self,tifList,resDir,clipPercent,postName,parent=None):
        super(raster16to8BatchRunClass ,self).__init__(parent)
        self.tifList = tifList
        self.resDir = resDir
        self.clipPercent = clipPercent
        self.postName = postName
    
    def updateProcessSingle(self,a):
        self.signal_process.emit(a)

    def updateProcessMulti(self,process):
        self.signal_process.emit(process)
    
    def run(self):
        lowPercent = self.clipPercent
        highPercent = 1 - self.clipPercent
        if len(self.tifList) == 1:
            try:
                resTif = osp.join(self.resDir, osp.basename(self.tifList[0]).split(".")[0] + self.postName + ".tif")
                uint16to8(self.tifList[0],resTif,lowPercent,highPercent,callback=self.updateProcessSingle)
                self.signal_over.emit(resTif)
            except:
                print(traceback.format_exc())
                self.signal_over.emit("error： Trans Failed")
        else:
            for index in range(len(self.tifList)):
                tempResTif = osp.join(self.resDir, osp.basename(self.tifList[index]).split(".")[0] + self.postName + ".tif")
                uint16to8(self.tifList[index],tempResTif,lowPercent,highPercent,callback=self.updateProcessMulti)
            self.signal_over(self.resDir)


class rasterCalNormBatchRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)
    def __init__(self,tifList,resDir,postName,calBandType,calAlgoName,parent=None):
        super(rasterCalNormBatchRunClass ,self).__init__(parent)
        self.tifList = tifList
        self.resDir = resDir
        self.postName = postName
        self.calBandType = calBandType
        self.calAlgoName = calAlgoName

    def updateProcess(self,process):
        self.signal_process.emit(process)

    def run(self):
        if len(self.tifList) == 1:
            resShpName = osp.basename(self.tifList[0]).split(".")[0] + self.postName + ".tif"
            if self.calBandType == 3:
                res = calNormalizedIII(self.tifList[0],self.resDir,resShpName,self.calAlgoName,callback=self.updateProcess)
            else:
                res = calNormalizedIV(self.tifList[0],self.resDir,resShpName,self.calAlgoName,callback=self.updateProcess)
            if res == 0:
                self.signal_over.emit(osp.join(self.resDir,resShpName))
            else:
                self.signal_over.emit("error：计算失败")

        else:
            for index in range(len(self.tifList)):
                tempResShpName = osp.basename(self.tifList[index]).split(".")[0] + self.postName + ".tif"
                if self.calBandType == 3:
                    calNormalizedIII(self.tifList[index], self.resDir, tempResShpName, self.calAlgoName)
                else:
                    calNormalizedIV(self.tifList[index], self.resDir, tempResShpName, self.calAlgoName)
                self.updateProcess((index + 1) / len(self.tifList)*100)

            self.signal_over.emit(self.resDir)

class rasterZonalStaticRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)
    def __init__(self,inputTif,inputShp,outPath,parent=None):
        super(rasterZonalStaticRunClass ,self).__init__(parent)
        self.inputTif = inputTif
        self.inputShp = inputShp
        self.outPath = outPath

    def updateProcess(self,process):
        self.signal_process.emit(process)

    def run(self):
        try:
            f = YoyiFeedBack()
            f.progressChanged.connect(self.updateProcess)
            res = processing.run("native:zonalstatisticsfb", {
                'INPUT': self.inputShp,
                'INPUT_RASTER': self.inputTif,
                'RASTER_BAND': 1, 'COLUMN_PREFIX': '_', 'STATISTICS': [9],
                'OUTPUT': self.outPath}, feedback=f)
            if f.errorMsg:
                self.signal_over.emit(f.errorMsg)
            else:
                self.signal_over.emit(res['OUTPUT'])
        except Exception as e:
            self.signal_over.emit(traceback.format_exc())

class rasterRecombineRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)

    def __init__(self,tifPath,recombineList,resPath,parent=None):
        super(rasterRecombineRunClass ,self).__init__(parent)
        self.tifPath = tifPath
        self.recombineList = recombineList
        self.resPath = resPath
    
    def updateProcess(self,process):
        self.signal_process.emit(process)

    def run(self):
        f = YoyiFeedBack()
        f.progressChanged.connect(self.updateProcess)
        # print(processing.algorithmHelp("gdal:rearrange_bands"))
        res = processing.run("gdal:rearrange_bands", 
                       {'INPUT':self.tifPath,
                        'BANDS':self.recombineList,
                        'OPTIONS':'',
                        'DATA_TYPE':0,
                        'OUTPUT':self.resPath},feedback=f)
        if f.errorMsg:
            self.signal_over.emit(f.errorMsg)
        else:
            self.signal_over.emit(res['OUTPUT'])

class rasterExportRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)
    def __init__(self,tifPath,resPath,parent=None):
        super(rasterExportRunClass ,self).__init__(parent)
        self.tifPath = tifPath
        self.resPath = resPath
    def updateProcess(self,process):
        self.signal_process.emit(process)
    
    def run(self):
        shutil.copyfile(self.tifPath,self.resPath)
        self.signal_over.emit(self.resPath)

class rasterBuildOverviewRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)

    def __init__(self,tifPath,buildIn,clean,parent=None):
        super(rasterBuildOverviewRunClass ,self).__init__(parent)
        self.tifPath = tifPath
        self.buildIn = buildIn
        self.clean = clean
        print("self.tifPath",self.tifPath)
        print("self.buildIn",self.buildIn)
        print("self.clean",self.clean)
    
    def updateProcess(self,process):
        self.signal_process.emit(process)

    def run(self):
        if self.buildIn:
            buildFormat = 0
        else:
            buildFormat = 1
        f = YoyiFeedBack()
        f.progressChanged.connect(self.updateProcess)
        # print(processing.algorithmHelp("gdal:rearrange_bands"))
        res = processing.run("gdal:overviews", 
                             {'INPUT':self.tifPath,
                              'CLEAN':self.clean,
                              'LEVELS':'',
                              'RESAMPLING':None,
                              'FORMAT':buildFormat,
                              'EXTRA':''},feedback=f)
        if f.errorMsg:
            self.signal_over.emit(f.errorMsg)
        else:
            self.signal_over.emit(res['OUTPUT'])

class rasterClipByExtentRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)

    def __init__(self,tifPath,resPath,extent,parent=None):
        super(rasterClipByExtentRunClass ,self).__init__(parent)
        self.tifPath = tifPath
        self.resPath = resPath
        self.extent = extent
    
    def updateProcess(self,process):
        self.signal_process.emit(process)

    def run(self):
        f = YoyiFeedBack()
        f.progressChanged.connect(self.updateProcess)
        res = processing.run("gdal:cliprasterbyextent", 
                             {'INPUT':self.tifPath,
                              'PROJWIN':self.extent,
                              'OVERCRS':False,
                              'NODATA':None,
                              'OPTIONS':'',
                              'DATA_TYPE':0,
                              'EXTRA':'',
                              'OUTPUT':self.resPath},feedback=f)
        if f.errorMsg:
            self.signal_over.emit(f.errorMsg)
        else:
            self.signal_over.emit(res['OUTPUT'])

class rasterClipByMaskRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)
    def __init__(self,tifPath,resPath,maskPath,expandMask,parent=None):
        super(rasterClipByMaskRunClass ,self).__init__(parent)
        self.tifPath = tifPath
        self.resPath = resPath
        self.maskPath = maskPath
        self.expandMask = expandMask
    
    def updateProcess(self,process):
        self.signal_process.emit(process)

    def run(self):
        f = YoyiFeedBack()
        f.progressChanged.connect(self.updateProcess)
        res = processing.run("gdal:cliprasterbymasklayer", 
                            {'INPUT': self.tifPath,
                            'MASK':self.maskPath,
                            'SOURCE_CRS':None,
                            'TARGET_CRS':None,
                            'NODATA':None,
                            'ALPHA_BAND':False,
                            'CROP_TO_CUTLINE':self.expandMask,
                            'KEEP_RESOLUTION':False,
                            'SET_RESOLUTION':False,
                            'X_RESOLUTION':None,
                            'Y_RESOLUTION':None,
                            'MULTITHREADING':False,
                            'OPTIONS':'',
                            'DATA_TYPE':0,
                            'EXTRA':'',
                            'OUTPUT':self.resPath},feedback=f)
        if f.errorMsg:
            self.signal_over.emit(f.errorMsg)
        else:
            self.signal_over.emit(res['OUTPUT'])

class rasterReprojectRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)

    def __init__(self,tifPath,resPath,targetCrs,resampleMode,parent=None):
        super(rasterReprojectRunClass ,self).__init__(parent)
        self.tifPath = tifPath
        self.resPath = resPath
        self.targetCrs = targetCrs
        self.resampleMode = resampleMode
    
    def updateProcess(self,process):
        self.signal_process.emit(process)

    def run(self):
        f = YoyiFeedBack()
        f.progressChanged.connect(self.updateProcess)
        res = processing.run("gdal:warpreproject", 
                             {'INPUT':self.tifPath,
                              'SOURCE_CRS':None,
                              'TARGET_CRS':QgsCoordinateReferenceSystem(self.targetCrs),
                              'RESAMPLING':self.resampleMode,
                              'NODATA':None,
                              'TARGET_RESOLUTION':None,
                              'OPTIONS':'',
                              'DATA_TYPE':0,
                              'TARGET_EXTENT':None,
                              'TARGET_EXTENT_CRS':None,
                              'MULTITHREADING':False,
                              'EXTRA':'',
                              'OUTPUT':self.resPath},feedback=f)
        if f.errorMsg:
            self.signal_over.emit(f.errorMsg)
        else:
            self.signal_over.emit(res['OUTPUT'])

class rasterMergeRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)

    def __init__(self,tifList,resampleIndex,resPath,parent=None):
        super(rasterMergeRunClass ,self).__init__(parent)
        self.tifList = tifList
        self.resampleIndex = resampleIndex
        self.resPath = resPath
    
    def updateProcess(self,process,b,c):
        self.signal_process.emit(float(process*100))

    def run(self):
        try:
            mergeTifs(self.tifList,self.resPath,self.resampleIndex,callback=self.updateProcess)
            self.signal_over.emit(self.resPath)
        except:
            print(traceback.format_exc())
            self.signal_over.emit("merge error")

class rasterCalcRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)

    def __init__(self,expression,resPath,format,extent,crs,outWidth,outHeight,entryList,parent=None):
        super(rasterCalcRunClass ,self).__init__(parent)
        self.expression = expression
        self.resPath = resPath
        self.format = format
        self.extent = extent
        self.crs = crs
        self.outWidth = outWidth
        self.outHeight = outHeight
        self.entryList = entryList
    
    def updateProcess(self,process):
        self.signal_process.emit(process)

    def run(self):
        try:
            f = YoyiFeedBack()
            f.progressChanged.connect(self.updateProcess)
            # print(processing.algorithmHelp("gdal:rearrange_bands"))
            calc = QgsRasterCalculator(
                self.expression,
                self.resPath,
                self.format,
                self.extent,
                self.crs,
                self.outWidth,
                self.outHeight,
                self.entryList,
                PROJECT.transformContext()
            )
            res = calc.processCalculation(feedback=f)
            print("resCode:",res)
            print("lastError:",calc.lastError())
            if f.errorMsg:
                self.signal_over.emit(f.errorMsg)
            else:
                self.signal_over.emit(self.resPath)
        except Exception as e:
            print(e)
            print(traceback.format_exc())
            self.signal_over.emit(traceback.format_exc())

#  矢量处理
class shp2RasterRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)

    def __init__(self,shpPath,fieldName,pixelWidth,pixelHeight,dataType,resPath,parent=None):
        super(shp2RasterRunClass ,self).__init__(parent)
        self.shpPath = shpPath
        self.fieldName = fieldName
        self.pixelWidth = pixelWidth
        self.pixelHeight = pixelHeight
        self.dataType = dataType
        self.resPath = resPath
    
    def updateProcess(self,process):
        self.signal_process.emit(process)

    def run(self):
        f = YoyiFeedBack()
        f.progressChanged.connect(self.updateProcess)
        res = processing.run("gdal:rasterize", {'INPUT':self.shpPath,
                                                'FIELD':self.fieldName,
                                                'BURN':0,'USE_Z':False,'UNITS':0,
                                                'WIDTH':self.pixelWidth,'HEIGHT':self.pixelHeight,
                                                'EXTENT':None,'NODATA':0,'OPTIONS':'',
                                                'DATA_TYPE':self.dataType,'INIT':None,'INVERT':False,
                                                'EXTRA':'','OUTPUT':self.resPath},feedback=f)
        if f.errorMsg:
            self.signal_over.emit(f.errorMsg)
        else:
            self.signal_over.emit(res['OUTPUT'])

class shpExportRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)

    def __init__(self,shpLayerName,targetCrs,onlyExportSelected,encoding,resPath,parent=None):
        super(shpExportRunClass ,self).__init__(parent)
        self.shpLayerName = shpLayerName
        self.targetCrs = targetCrs
        self.onlyExportSelected = onlyExportSelected
        self.encoding = encoding
        self.resPath = resPath
    
    def updateProcess(self,process):
        self.signal_process.emit(float(process*100))

    def run(self):
        try:
            currentLayer : QgsVectorLayer = PROJECT.mapLayersByName(self.shpLayerName)[0]
            crsSrc = currentLayer.crs()
            crsDest = QgsCoordinateReferenceSystem(self.targetCrs)
            ct = QgsCoordinateTransform(crsSrc, crsDest, PROJECT.transformContext())
            saveShpFunc(self.resPath,currentLayer,
                        ct=ct,onlySelectedFeatures=self.onlyExportSelected,
                        fileEncoding=self.encoding)
            self.signal_over.emit(self.resPath)
        except Exception as e:
            print(traceback.format_exc())
            self.signal_over.emit("export error")
    
class shapeFileFixGeometryRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)
    def __init__(self,shpList,resDir,postName,parent=None):
        super(shapeFileFixGeometryRunClass ,self).__init__(parent)
        self.shpList = shpList
        self.resDir = resDir
        self.postName = postName

    def updateProcess(self,process):
        self.signal_process.emit(process)

    def run(self):
        try:
            if len(self.shpList) == 1:
                resShpName = osp.basename(self.shpList[0]).split(".")[0] + self.postName + ".shp"
                resPath = osp.join(self.resDir,resShpName)
                f = YoyiFeedBack()
                f.progressChanged.connect(self.updateProcess)
                res = processing.run("native:fixgeometries", {
                    'INPUT':self.shpList[0],
                    'OUTPUT':resPath}, feedback=f)
                self.signal_over.emit(res['OUTPUT'])
            else:
                for index in range(len(self.shpList)):
                    resShpName = osp.basename(self.shpList[index]).split(".")[0] + self.postName + ".shp"
                    resPath = osp.join(self.resDir, resShpName)
                    processing.run("native:fixgeometries", {
                        'INPUT': self.shpList[index],
                        'OUTPUT': resPath})
                    self.updateProcess((index + 1) / len(self.shpList) * 100)
                self.signal_over.emit(self.resDir)
        except Exception as e:
            self.signal_over.emit(traceback.format_exc())

class shpClipByExtentRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)
    def __init__(self,shpPath,resPath,extent,parent=None):
        super(shpClipByExtentRunClass,self).__init__(parent)
        self.shpPath = shpPath
        self.resPath = resPath
        self.extent = extent
    
    def updateProcess(self,process):
        self.signal_process.emit(process)

    def run(self):
        f = YoyiFeedBack()
        f.progressChanged.connect(self.updateProcess)
        res = processing.run("gdal:clipvectorbyextent", 
                             {'INPUT':self.shpPath,
                              'EXTENT':self.extent,
                              'OPTIONS':'',
                              'OUTPUT':self.resPath},feedback=f)
        if f.errorMsg:
            self.signal_over.emit(f.errorMsg)
        else:
            self.signal_over.emit(res['OUTPUT'])

class shpClipByMaskRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)
    def __init__(self,shpPath,resPath,maskPath,parent=None):
        super(shpClipByMaskRunClass ,self).__init__(parent)
        self.shpPath = shpPath
        self.resPath = resPath
        self.maskPath = maskPath
    
    def updateProcess(self,process):
        self.signal_process.emit(process)

    def run(self):
        f = YoyiFeedBack()
        f.progressChanged.connect(self.updateProcess)
        res = processing.run("gdal:clipvectorbypolygon", 
                             {'INPUT':self.shpPath,
                              'MASK':self.maskPath,
                              'OPTIONS':'',
                              'OUTPUT':self.resPath},feedback=f)
        if f.errorMsg:
            self.signal_over.emit(f.errorMsg)
        else:
            self.signal_over.emit(res['OUTPUT'])
            
class shpEraseRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)
    def __init__(self,shpPath,resPath,erasePath,parent=None):
        super(shpEraseRunClass ,self).__init__(parent)
        self.shpPath = shpPath
        self.resPath = resPath
        self.erasePath = erasePath
    def updateProcess(self,process):
        self.signal_process.emit(process)
    def run(self):
        f = YoyiFeedBack()
        f.progressChanged.connect(self.updateProcess)
        res = processing.run("native:difference", 
                             {'INPUT':self.shpPath,
                              'OVERLAY':self.erasePath,
                              'OUTPUT':self.resPath},feedback=f)
        if f.errorMsg:
            self.signal_over.emit(f.errorMsg)
        else:
            self.signal_over.emit(res['OUTPUT'])

class shpSimplyRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)

    def __init__(self, shpPath, resPath,tolerance, parent=None):
        super(shpSimplyRunClass, self).__init__(parent)
        self.shpPath = shpPath
        self.resPath = resPath
        self.tolerance = tolerance

    def updateProcess(self, process):
        self.signal_process.emit(process)

    def run(self):
        f = YoyiFeedBack()
        f.progressChanged.connect(self.updateProcess)
        res = processing.run("native:simplifygeometries", 
                                {'INPUT':self.shpPath,
                                'METHOD':0,
                                'TOLERANCE':self.tolerance,
                                'OUTPUT':self.resPath},feedback=f)
        if f.errorMsg:
            self.signal_over.emit(f.errorMsg)
        else:
            self.signal_over.emit(res['OUTPUT'])

class shpBufferRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)

    def __init__(self, shpPath, resPath,distance,segments,endStyle,joinStyle,miterLimit,dissolve, parent=None):
        super(shpBufferRunClass, self).__init__(parent)
        self.shpPath = shpPath
        self.resPath = resPath
        self.distance = distance
        self.segments = segments
        self.endStyle = endStyle
        self.joinStyle = joinStyle
        self.miterLimit = miterLimit
        self.dissolve = dissolve

    def updateProcess(self, process):
        self.signal_process.emit(process)

    def run(self):
        f = YoyiFeedBack()
        f.progressChanged.connect(self.updateProcess)
        res = processing.run("native:buffer", 
                                {'INPUT':self.shpPath,
                                'DISTANCE':self.distance,
                                'SEGMENTS':self.segments,
                                'END_CAP_STYLE':self.endStyle,
                                'JOIN_STYLE':self.joinStyle,
                                'MITER_LIMIT':self.miterLimit,
                                'DISSOLVE':self.dissolve,
                                'OUTPUT':self.resPath},feedback=f)
        if f.errorMsg:
            self.signal_over.emit(f.errorMsg)
        else:
            self.signal_over.emit(res['OUTPUT'])

class shpIntersectionRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)
    def __init__(self,shpPath,resPath,intersectShp,prefix,parent=None):
        super(shpIntersectionRunClass,self).__init__(parent)
        self.shpPath = shpPath
        self.resPath = resPath
        self.intersectShp = intersectShp
        self.prefix = prefix
    
    def updateProcess(self,process):
        self.signal_process.emit(process)

    def run(self):
        f = YoyiFeedBack()
        f.progressChanged.connect(self.updateProcess)
        res = processing.run("native:intersection",
                             {'INPUT':self.shpPath,
                              'OVERLAY':self.intersectShp,
                              'INPUT_FIELDS':[],
                              'OVERLAY_FIELDS':[],
                              'OVERLAY_FIELDS_PREFIX':self.prefix,
                              'OUTPUT':self.resPath},feedback=f)
        if f.errorMsg:
            self.signal_over.emit(f.errorMsg)
        else:
            self.signal_over.emit(res['OUTPUT'])

class shpOrthogoRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)
    def __init__(self,shpPath,resPath,parent=None):
        super(shpOrthogoRunClass,self).__init__(parent)
        self.shpPath = shpPath
        self.resPath = resPath
    
    def updateProcess(self,process):
        self.signal_process.emit(process)

    def run(self):
        try:
            shp_orthogo_process(input=self.shpPath,output=self.resPath)
            self.signal_over.emit(self.resPath)
        except Exception as e:
            print(traceback.format_exc())
            self.signal_over.emit("unknown error")

class shpCalCentroidRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)
    def __init__(self,shpPath,resPath,allPart,parent=None):
        super(shpCalCentroidRunClass ,self).__init__(parent)
        self.shpPath = shpPath
        self.resPath = resPath
        self.allPart = allPart
    
    def updateProcess(self,process):
        self.signal_process.emit(process)

    def run(self):
        f = YoyiFeedBack()
        f.progressChanged.connect(self.updateProcess)
        res = processing.run("native:centroids", {'INPUT': self.shpPath,
                                                  'ALL_PARTS':self.allPart,
                                                  'OUTPUT':self.resPath},feedback=f)
        if f.errorMsg:
            self.signal_over.emit(f.errorMsg)
        else:
            self.signal_over.emit(res['OUTPUT'])

class shpCalAreaRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)
    def __init__(self,shpPath,resPath,fieldName,fieldLength,fieldPrecision,parent=None):
        super(shpCalAreaRunClass ,self).__init__(parent)
        self.shpPath = shpPath
        self.resPath = resPath
        self.fieldName = fieldName
        self.fieldLength = fieldLength
        self.fieldPrecision = fieldPrecision
    
    def updateProcess(self,process):
        self.signal_process.emit(process)

    def run(self):
        f = YoyiFeedBack()
        f.progressChanged.connect(self.updateProcess)
        res = processing.run("native:fieldcalculator", {'INPUT':self.shpPath,
                                                        'FIELD_NAME':self.fieldName,
                                                        'FIELD_TYPE':0,
                                                        'FIELD_LENGTH':self.fieldLength,
                                                        'FIELD_PRECISION':self.fieldPrecision,
                                                        'FORMULA':' $area ',
                                                        'OUTPUT':self.resPath},feedback=f)
        if f.errorMsg:
            self.signal_over.emit(f.errorMsg)
        else:
            self.signal_over.emit(res['OUTPUT'])
    
class shp2SinglepartsRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)
    def __init__(self,shpPath,resPath,parent=None):
        super(shp2SinglepartsRunClass ,self).__init__(parent)
        self.shpPath = shpPath
        self.resPath = resPath
    
    def updateProcess(self,process):
        self.signal_process.emit(process)

    def run(self):
        f = YoyiFeedBack()
        f.progressChanged.connect(self.updateProcess)
        res = processing.run("native:multiparttosingleparts", 
                             {'INPUT':self.shpPath,
                              'OUTPUT':self.resPath},feedback=f)
        if f.errorMsg:
            self.signal_over.emit(f.errorMsg)
        else:
            self.signal_over.emit(res['OUTPUT'])

class shpSmoothRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)
    def __init__(self,shpPath,resPath,iterNum,offset,maxAngle,parent=None):
        super(shpSmoothRunClass ,self).__init__(parent)
        self.shpPath = shpPath
        self.resPath = resPath
        self.iterNum = iterNum # 1 10 1
        self.offset = offset  # 0 0.5 0.25
        self.maxAngle = maxAngle #0 180 180
    
    def updateProcess(self,process):
        self.signal_process.emit(process)

    def run(self):
        f = YoyiFeedBack()
        f.progressChanged.connect(self.updateProcess)
        res = processing.run("native:smoothgeometry", {'INPUT':self.shpPath,
                                                       'ITERATIONS':self.iterNum,
                                                       'OFFSET':self.offset,
                                                       'MAX_ANGLE':self.maxAngle,
                                                       'OUTPUT':self.resPath},feedback=f)
        if f.errorMsg:
            self.signal_over.emit(f.errorMsg)
        else:
            self.signal_over.emit(res['OUTPUT'])

class shpMergeRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)

    def __init__(self,shpList,resPath,crs,parent=None):
        super(shpMergeRunClass ,self).__init__(parent)
        self.shpList = shpList
        self.resPath = resPath
        self.crs = crs
    
    def updateProcess(self,process):
        self.signal_process.emit(process)

    def run(self):
        if self.crs == "":
            params = {'LAYERS':self.shpList,
                      'OUTPUT':self.resPath}
        else:
            params = {'LAYERS':self.shpList,
                      'CRS':QgsCoordinateReferenceSystem(self.crs),
                      'OUTPUT':self.resPath}
        f = YoyiFeedBack()
        f.progressChanged.connect(self.updateProcess)
        res = processing.run("native:mergevectorlayers", params,feedback=f)
        if f.errorMsg:
            self.signal_over.emit(f.errorMsg)
        else:
            self.signal_over.emit(res['OUTPUT'])

class shpDissolveRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)

    def __init__(self,shpPath,resPath,fields,parent=None):
        super(shpDissolveRunClass ,self).__init__(parent)
        self.shpPath = shpPath
        self.resPath = resPath
        self.fields = fields
    
    def updateProcess(self,process):
        self.signal_process.emit(process)

    def run(self):
        f = YoyiFeedBack()
        f.progressChanged.connect(self.updateProcess)
        res = processing.run("native:dissolve", 
                             {'INPUT':self.shpPath,
                              'FIELD':self.fields,
                              'OUTPUT':self.resPath},feedback=f,)
        if f.errorMsg:
            self.signal_over.emit(f.errorMsg)
        else:
            self.signal_over.emit(res['OUTPUT'])

class shpReprojectRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)
    def __init__(self,shpPath,resPath,targetCrs,parent=None):
        super(shpReprojectRunClass ,self).__init__(parent)
        self.shpPath = shpPath
        self.resPath = resPath
        self.targetCrs = targetCrs
    
    def updateProcess(self,process):
        self.signal_process.emit(process)

    def run(self):
        f = YoyiFeedBack()
        f.progressChanged.connect(self.updateProcess)
        res = processing.run("native:reprojectlayer", 
                             {'INPUT': self.shpPath,
                              'TARGET_CRS':QgsCoordinateReferenceSystem(self.targetCrs),
                              'OUTPUT':self.resPath},feedback=f)
        if f.errorMsg:
            self.signal_over.emit(f.errorMsg)
        else:
            self.signal_over.emit(res['OUTPUT'])

class shpRemoveAreaRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)
    def __init__(self,shpPath,resPath,minArea,parent=None):
        super(shpRemoveAreaRunClass ,self).__init__(parent)
        self.shpPath = shpPath
        self.resPath = resPath
        self.minArea = minArea

    
    def updateProcess(self,process):
        self.signal_process.emit(process)

    def run(self):
        try:
            f = YoyiFeedBack()
            f.progressChanged.connect(self.updateProcess)
            res = processing.run("native:fieldcalculator", {'INPUT':self.shpPath,
                                                            'FIELD_NAME':'otempareao',
                                                            'FIELD_TYPE':0,
                                                            'FIELD_LENGTH':10,
                                                            'FIELD_PRECISION':2,
                                                            'FORMULA':' $area ',
                                                            'OUTPUT':self.resPath},feedback=f)
            if f.errorMsg:
                self.signal_over.emit(f.errorMsg)
            else:
                outLayer = QgsVectorLayer(res['OUTPUT'])
                outLayer.startEditing()
                outLayer.selectByExpression(f" \"otempareao\" < {self.minArea} or \"otempareao\" is None",QgsVectorLayer.SetSelection)
            
                outLayer.deleteSelectedFeatures()
                outLayer.commitChanges()
                del outLayer
                self.signal_over.emit(res['OUTPUT'])
        except Exception as e:
            self.signal_over.emit("Error: unknown error")

class shpDeleteholesRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)
    def __init__(self,shpPath,resPath,minArea,parent=None):
        super(shpDeleteholesRunClass ,self).__init__(parent)
        self.shpPath = shpPath
        self.resPath = resPath
        self.minArea = minArea
    
    def updateProcess(self,process):
        self.signal_process.emit(process)

    def run(self):
        f = YoyiFeedBack()
        f.progressChanged.connect(self.updateProcess)
        res = processing.run("native:deleteholes", 
                             {'INPUT':self.shpPath,
                              'MIN_AREA':self.minArea,
                              'OUTPUT':self.resPath},feedback=f)
        if f.errorMsg:
            self.signal_over.emit(f.errorMsg)
        else:
            self.signal_over.emit(res['OUTPUT'])

class shpChangeAnalysisRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)
    def __init__(self,preShpPath,lastShpPath,resPath,tempDir,parent=None):
        super(shpChangeAnalysisRunClass ,self).__init__(parent)
        self.preShpPath = preShpPath
        self.lastShpPath = lastShpPath
        self.resPath = resPath
        self.tempDir = tempDir
        
    def updateProcess(self,process):
        self.signal_process.emit(process)

    def run(self):
        try:
            tempDir = osp.join(self.tempDir,f"temp_{datetime.now().strftime('%Y%m%d%H%M%S%f')}")
            createDir(tempDir)
            shpChangeAnalysis(self.preShpPath,self.lastShpPath,tempDir,self.resPath,callback=self.updateProcess)
            self.signal_over.emit(self.resPath)
            deleteDir(tempDir)
        except Exception as e:
            print(traceback.format_exc())
            self.signal_over.emit(traceback.format_exc())

class shpExportExcelRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)
    def __init__(self,pointExcelPath,shpPath,savePath,riskField,changeTypeField,highLevel,mediumLevel,lowLevel,extraTifLayer,extraDangduanPath,parent=None):
        super(shpExportExcelRunClass ,self).__init__(parent)
        self.pointExcelPath = pointExcelPath
        self.shpPath = shpPath
        self.savePath = savePath
        self.riskField = riskField
        self.changeTypeField = changeTypeField
        self.highLevel = highLevel
        self.mediumLevel = mediumLevel
        self.lowLevel = lowLevel
        self.extraTifLayer = extraTifLayer
        self.extraDangduanPath = extraDangduanPath
    
    def updateProcess(self,process):
        self.signal_process.emit(process)
    
    def run(self):
        try:
            searchRiskForExcel(self.pointExcelPath,self.shpPath,self.savePath,
                               self.riskField,self.changeTypeField,self.highLevel,self.mediumLevel,self.lowLevel,
                               self.extraTifLayer,self.extraDangduanPath,
                               callback=self.updateProcess)
            self.signal_over.emit(self.savePath)
        except Exception as e:
            print(traceback.format_exc())
            self.signal_over.emit(traceback.format_exc())


class excelTransLineShpRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)
    def __init__(self,excelPath,shpPath,lineNameField,pointIdField,xField,yField,parent=None):
        super(excelTransLineShpRunClass ,self).__init__(parent)
        self.excelPath = excelPath
        self.shpPath = shpPath
        self.lineNameField = lineNameField
        self.pointIdField = pointIdField
        self.xField = xField
        self.yField = yField
    
    def updateProcess(self,process):
        self.signal_process.emit(process)
    
    def run(self):
        try:
            excelTransLineShp(excelPath=self.excelPath,
                              shpPath=self.shpPath,
                              lineNameField=self.lineNameField,
                              pointIdField=self.pointIdField,
                              xField=self.xField,
                              yField=self.yField,
                              callback=self.updateProcess)
            self.signal_over.emit(self.shpPath)
        except Exception as e:
            print(traceback.format_exc())
            self.signal_over.emit(traceback.format_exc())



# 创建数据集
# 创建语义分割数据集
class createCgwxSegmentSample(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)
    def __init__(self, tifPathList,resDir,shpPathList,
                 needTransRgb,overlap,imgSize,dropZero,generatePost,
                 shpField,shpPixelMapping,diyPixelValue,classDict,mosaicShp,mosaicShpImgidField,
                 imgIdTime,sampleName,sampleDescription,sampleBuilder,
                 imageAreaId,filePre,initIndex,parent=None):
        super().__init__(parent)
        self.tifPathList = tifPathList
        self.resDir = resDir
        self.shpPathList = shpPathList
        self.needTransRgb = needTransRgb
        self.overlap = overlap
        self.imgSize = imgSize
        self.dropZero = dropZero
        self.generatePost = generatePost
        self.shpField = shpField
        self.shpPixelMapping = shpPixelMapping
        self.diyPixelValue = diyPixelValue
        self.classDict = classDict
        self.mosaicShp = mosaicShp
        self.mosaicShpImgidField = mosaicShpImgidField
        self.imgIdTime = imgIdTime
        self.sampleName = sampleName
        self.sampleDescription = sampleDescription
        self.sampleBuilder = sampleBuilder
        self.imageAreaId = imageAreaId
        self.filePre = filePre
        self.initIndex = initIndex

        self.sampleResDir = osp.join(self.resDir,"Img")
        self.labelDir = osp.join(self.resDir,"Label")
        self.jsonDir = osp.join(self.resDir,"Json")
    
    def updateProcessSingle(self,a):
        self.signal_process.emit(a)

    def run(self):
        try:
            yoyiDsp = yoyiDataSetProducer()
            if len(self.tifPathList) == 1:
                yoyiDsp.generate_cgwx_segment_sample_by_single_tif(
                    tif_path=self.tifPathList[0],res_dir=self.sampleResDir,shp_path=self.shpPathList[0],
                    extra_label_dir=self.labelDir,json_dir=self.jsonDir,
                    need_trans_rgb=self.needTransRgb,overlap=self.overlap,
                    img_size=self.imgSize,drop_zero=self.dropZero,generate_post=self.generatePost,
                    extra_shp_field=self.shpField,extra_shp_pixel_mapping=self.shpPixelMapping,extra_diy_pixel_value=self.diyPixelValue,
                    class_dict=self.classDict,mosaic_shp=self.mosaicShp,mosaic_shp_imgid_field=self.mosaicShpImgidField,
                    imgid_time=self.imgIdTime,sample_name=self.sampleName,sample_description=self.sampleDescription,
                    sample_builder=self.sampleBuilder,image_area_id=self.imageAreaId,file_pre=self.filePre,
                    extra_generate_file_index=self.initIndex,callback=self.updateProcessSingle
                )
            else:
                tempIndex = self.initIndex
                for i in range(len(self.tifPathList)):
                    tifPath = self.tifPathList[i]
                    shpPath = self.shpPathList[i]
                    self.updateProcessSingle( (i+1)/len(self.tifPathList)*100 )
                    index,_ = yoyiDsp.generate_cgwx_segment_sample_by_single_tif(
                        tif_path=tifPath,res_dir=self.sampleResDir,shp_path=shpPath,
                        extra_label_dir=self.labelDir,json_dir=self.jsonDir,
                        need_trans_rgb=self.needTransRgb,overlap=self.overlap,
                        img_size=self.imgSize,drop_zero=self.dropZero,generate_post=self.generatePost,
                        extra_shp_field=self.shpField,extra_shp_pixel_mapping=self.shpPixelMapping,extra_diy_pixel_value=self.diyPixelValue,
                        class_dict=self.classDict,mosaic_shp=self.mosaicShp,mosaic_shp_imgid_field=self.mosaicShpImgidField,
                        imgid_time=self.imgIdTime,sample_name=self.sampleName,sample_description=self.sampleDescription,
                        sample_builder=self.sampleBuilder,image_area_id=self.imageAreaId,file_pre=self.filePre,
                        extra_generate_file_index=tempIndex,callback=None
                        )
                    tempIndex = index

            self.signal_over.emit(self.resDir)
        except Exception as e:
            print(traceback.format_exc())
            self.signal_over.emit("生成数据集失败")

# 创建目标检测数据集
class createCgwxODSample(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)
    def __init__(self, tifPathList,resDir,shpPathList,
                 needTransRgb,overlap,imgSize,generatePost,
                 shpField,shpPixelMapping,classDict,mosaicShp,mosaicShpImgidField,
                 imgIdTime,sampleName,sampleDescription,sampleBuilder,
                 imageAreaId,isObb,clipMinAreaPer,filePre,initIndex,parent=None):
        super().__init__(parent)
        self.tifPathList = tifPathList
        self.resDir = resDir
        self.shpPathList = shpPathList
        self.needTransRgb = needTransRgb
        self.overlap = overlap
        self.imgSize = imgSize
        self.generatePost = generatePost
        self.shpField = shpField
        self.shpPixelMapping = shpPixelMapping 
        self.classDict = classDict
        self.mosaicShp = mosaicShp
        self.mosaicShpImgidField = mosaicShpImgidField
        self.imgIdTime = imgIdTime
        self.sampleName = sampleName
        self.sampleDescription = sampleDescription
        self.sampleBuilder = sampleBuilder
        self.imageAreaId = imageAreaId
        self.isObb = isObb
        self.clipMinAreaPer = clipMinAreaPer
        self.filePre = filePre
        self.initIndex = initIndex

        self.sampleResDir = osp.join(self.resDir,"Img")
        self.labelDir = osp.join(self.resDir,"Label")
        self.jsonDir = osp.join(self.resDir,"Json")
    
    def updateProcessSingle(self,a):
        self.signal_process.emit(a)
    
    def run(self):
        try:
            yoyiDsp = yoyiDataSetProducer()
            if len(self.tifPathList) == 1:
                yoyiDsp.generate_cgwx_objectDetecion_sample_by_single_tif(
                    tif_path=self.tifPathList[0],res_dir=self.sampleResDir,shp_path=self.shpPathList[0],
                    extra_label_dir=self.labelDir,json_dir=self.jsonDir,
                    need_trans_rgb=self.needTransRgb,overlap=self.overlap,img_size=self.imgSize,
                    generate_post=self.generatePost,extra_shp_field=self.shpField,
                    extra_shp_pixel_mapping=self.shpPixelMapping,class_dict=self.classDict,
                    mosaic_shp=self.mosaicShp,mosaic_shp_imgid_field=self.mosaicShpImgidField,
                    imgid_time=self.imgIdTime,sample_name=self.sampleName,sample_description=self.sampleDescription,
                    sample_builder=self.sampleBuilder,image_area_id=self.imageAreaId,
                    is_obb=self.isObb,clip_min_area_per=self.clipMinAreaPer,
                    file_pre=self.filePre,extra_generate_file_index=self.initIndex,callback=self.updateProcessSingle
                )
            else:
                tempIndex = self.initIndex
                for i in range(len(self.tifPathList)):
                    tifPath = self.tifPathList[i]
                    shpPath = self.shpPathList[i]
                    self.updateProcessSingle( (i+1)/len(self.tifPathList)*100 )
                    index,_ = yoyiDsp.generate_cgwx_objectDetecion_sample_by_single_tif(
                                tif_path=tifPath,res_dir=self.sampleResDir,shp_path=shpPath,
                                extra_label_dir=self.labelDir,json_dir=self.jsonDir,
                                need_trans_rgb=self.needTransRgb,overlap=self.overlap,img_size=self.imgSize,
                                generate_post=self.generatePost,extra_shp_field=self.shpField,
                                extra_shp_pixel_mapping=self.shpPixelMapping,class_dict=self.classDict,
                                mosaic_shp=self.mosaicShp,mosaic_shp_imgid_field=self.mosaicShpImgidField,
                                imgid_time=self.imgIdTime,sample_name=self.sampleName,sample_description=self.sampleDescription,
                                sample_builder=self.sampleBuilder,image_area_id=self.imageAreaId,
                                is_obb=self.isObb,clip_min_area_per=self.clipMinAreaPer,
                                file_pre=self.filePre,extra_generate_file_index=tempIndex
                            )
                    tempIndex = index
            self.signal_over.emit(self.resDir)
        except Exception as e:
            print(traceback.format_exc())
            self.signal_over.emit("生成数据集失败")

# 创建变化检测数据集
class createCgwxCDSample(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)
    def __init__(self, tifPathList,tifPathListII,resDir,shpPathList,
                 needTransRgb,overlap,imgSize,dropZero,generatePost,
                 shpField,shpFieldII,shpPixelMapping,diyPixelValue,classDict,
                 mosaicShp,mosaicShpII,mosaicShpImgidField,mosaicShpImgidFieldII,
                 imgIdTime,imgIdTimeII,sampleName,sampleDescription,sampleBuilder,
                 imageAreaId,filePre,initIndex,parent=None):
        super().__init__(parent)
        self.tifPathList = tifPathList
        self.tifPathListII = tifPathListII
        self.resDir = resDir
        self.shpPathList = shpPathList
        self.needTransRgb = needTransRgb
        self.overlap = overlap
        self.imgSize = imgSize
        self.dropZero = dropZero
        self.generatePost = generatePost
        self.shpField = shpField
        self.shpFieldII = shpFieldII
        self.shpPixelMapping = shpPixelMapping
        self.diyPixelValue = diyPixelValue
        self.classDict = classDict
        self.mosaicShp = mosaicShp
        self.mosaicShpII = mosaicShpII
        self.mosaicShpImgidField = mosaicShpImgidField
        self.mosaicShpImgidFieldII = mosaicShpImgidFieldII
        self.imgIdTime = imgIdTime
        self.imgIdTimeII = imgIdTimeII
        self.sampleName = sampleName
        self.sampleDescription = sampleDescription
        self.sampleBuilder = sampleBuilder
        self.imageAreaId = imageAreaId
        self.filePre = filePre
        self.initIndex = initIndex

        self.sampleResDir = osp.join(self.resDir,"Img1")
        self.sampleResDirII = osp.join(self.resDir,"Img2")
        self.labelDir = osp.join(self.resDir,"Label1")
        self.labelDirII = osp.join(self.resDir,"Label2")
        self.jsonDir = osp.join(self.resDir,"Json")
    def updateProcessSingle(self,a):
        self.signal_process.emit(a*0.5)
    
    def updateProcessSingleII(self,a):
        self.signal_process.emit(50 + a*0.5)
    
    def updataProcess(self,a):
        self.signal_process.emit(a)
    
    def run(self):
        try:
            yoyiDsp = yoyiDataSetProducer()
            if len(self.tifPathList) == 1:
                yoyiDsp.generate_cgwx_changeDetection_sample_by_single_tif(
                    tif_path=self.tifPathList[0],tif_path_II=self.tifPathListII[0],
                    res_dir=self.sampleResDir,res_dir_II=self.sampleResDirII,
                    json_dir=self.jsonDir,shp_path=self.shpPathList[0],
                    extra_label_dir=self.labelDir,extra_label_dir_II=self.labelDirII,
                    need_trans_rgb=self.needTransRgb,overlap=self.overlap,
                    img_size=self.imgSize,drop_zero=self.dropZero,
                    generate_post=self.generatePost,extra_shp_field=self.shpField,
                    extra_shp_field_II=self.shpFieldII,extra_shp_pixel_mapping=self.shpPixelMapping,
                    extra_diy_pixel_value=self.diyPixelValue,class_dict=self.classDict,
                    mosaic_shp=self.mosaicShp,mosaic_shp_II=self.mosaicShpII,
                    mosaic_shp_imgid_field=self.mosaicShpImgidField,mosaic_shp_imgid_field_II=self.mosaicShpImgidFieldII,
                    imgid_time=self.imgIdTime,imgid_time_II=self.imgIdTimeII,
                    sample_name=self.sampleName,sample_description=self.sampleDescription,
                    sample_builder=self.sampleBuilder,image_area_id=self.imageAreaId,
                    file_pre=self.filePre,extra_generate_file_index=self.initIndex,callback=self.updateProcessSingle,
                    callbackII=self.updateProcessSingleII,
                )
            else:
                tempIndex = self.initIndex
                for i in range(len(self.tifPathList)):
                    tifPath = self.tifPathList[i]
                    tifPathII = self.tifPathListII[i]
                    shpPath = self.shpPathList[i]
                    self.updataProcess( (i+1)/len(self.tifPathList)*100 )
                    index,_ = yoyiDsp.generate_cgwx_changeDetection_sample_by_single_tif(
                                tif_path=tifPath,tif_path_II=tifPathII,
                                res_dir=self.sampleResDir,res_dir_II=self.sampleResDirII,
                                json_dir=self.jsonDir,shp_path=shpPath,
                                extra_label_dir=self.labelDir,extra_label_dir_II=self.labelDirII,
                                need_trans_rgb=self.needTransRgb,overlap=self.overlap,
                                img_size=self.imgSize,drop_zero=self.dropZero,
                                generate_post=self.generatePost,extra_shp_field=self.shpField,
                                extra_shp_field_II=self.shpFieldII,extra_shp_pixel_mapping=self.shpPixelMapping,
                                extra_diy_pixel_value=self.diyPixelValue,class_dict=self.classDict,
                                mosaic_shp=self.mosaicShp,mosaic_shp_II=self.mosaicShpII,
                                mosaic_shp_imgid_field=self.mosaicShpImgidField,mosaic_shp_imgid_field_II=self.mosaicShpImgidFieldII,
                                imgid_time=self.imgIdTime,imgid_time_II=self.imgIdTimeII,
                                sample_name=self.sampleName,sample_description=self.sampleDescription,
                                sample_builder=self.sampleBuilder,image_area_id=self.imageAreaId,
                                file_pre=self.filePre,extra_generate_file_index=tempIndex
                            )
                    tempIndex = index
            self.signal_over.emit(self.resDir)
        except Exception as e:
            print(traceback.format_exc())
            self.signal_over.emit("生成数据集失败")

# 划分数据集
class splitDatasetRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)
    def __init__(self, imgDir,labelDir,imgDirPost,labelDirPost,
                 resDir,validRatio,testRatio,shuffleOrder,
                 trainDirName,validDirName,testDirName,
                 imageDirName,labelDirName,parent=None):
        super().__init__(parent)
        self.imgDir = imgDir
        self.labelDir = labelDir
        self.imgDirPost = imgDirPost
        self.labelDirPost = labelDirPost
        self.resDir = resDir
        self.validRatio = validRatio
        self.testRatio = testRatio
        self.shuffleOrder = shuffleOrder
        self.trainDirName = trainDirName
        self.validDirName = validDirName
        self.testDirName = testDirName
        self.imageDirName = imageDirName
        self.labelDirName = labelDirName

    def callbackSignal(self, process):
        self.signal_process.emit(process)

    def run(self):
        try:
            splitDataset(imgDir=self.imgDir,
                         labelDir=self.labelDir,
                         imgDirPost=self.imgDirPost,
                         labelDirPost=self.labelDirPost,
                         resDir=self.resDir,
                         validRatio=self.validRatio,
                         testRatio=self.testRatio,
                         shuffleOrder=self.shuffleOrder,
                         trainDirName=self.trainDirName,
                         validDirName=self.validDirName,
                         testDirName=self.testDirName,
                         imageDirName=self.imageDirName,
                         labelDirName=self.labelDirName,
                         callback=self.callbackSignal)
            self.signal_over.emit(self.resDir)
        except:
            print(traceback.format_exc())
            self.signal_over.emit(traceback.format_exc())

# 创建渔网
class createFishNetRunClass(QThread):
    signal_process = pyqtSignal(float)
    signal_over = pyqtSignal(str)
    def __init__(self, tifPath,fishNetSize,outShpPath,extent=None,parent=None):
        super(createFishNetRunClass, self).__init__(parent)
        self.tifPath = tifPath
        self.fishNetSize = fishNetSize
        self.outShpPath = outShpPath
        self.extent = extent

    def run(self):
        try:
            if self.extent:
                createFishNetByExtent(self.tifPath,self.fishNetSize,
                                      self.outShpPath,self.extent[0],self.extent[1],self.extent[2],self.extent[3])
            else:
                createFishNet(self.tifPath,self.fishNetSize,self.outShpPath)
            self.signal_over.emit(self.outShpPath)
        except:
            print(traceback.format_exc())
            self.signal_over.emit(traceback.format_exc())

class createFishNetByXYIntervalRunClass(QThread):
    signal_process = pyqtSignal(int)
    signal_over = pyqtSignal(str)
    def __init__(self, crs,extent,outShpPath,xSegNum,ySegNum,parent=None):
        super(createFishNetByXYIntervalRunClass, self).__init__(parent)
        self.crs = crs
        self.extent = extent
        self.outShpPath = outShpPath
        self.xSegNum = xSegNum
        self.ySegNum = ySegNum

    def callbackSignal(self, process):
        self.signal_process.emit(process)

    def run(self):
        try:
            createFishNetByXYExtent(self.crs,self.extent,self.outShpPath,self.xSegNum,self.ySegNum)
            self.signal_over.emit(self.outShpPath)
        except:
            print(traceback.format_exc())
            self.signal_over.emit(traceback.format_exc())