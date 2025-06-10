# cython:language_level=3
# -*- coding: utf-8 -*-
"""
@File    :   gdalCommon.py    
@Contact :   zhijuepeng@foxmail.com
@License :   (C)Copyright 2017-9999,CGWX

@Modify Time      @Author    @Version    @Desciption
------------      -------    --------    -----------
15/7/2021 下午2:17   Yoyi      1.0         None
"""

'''
1 单个栅格转影像 qgisTif2Shp
2 批量栅格转矢量 batchTif2shp
3 读取文件夹中的所有影像 load_tiles
4 面矢量转线矢量 pol2line
5 16位遥感影像 转 8位遥感影像 uint16to8
6 选定裁剪次数，动态裁剪遥感影像 segTif
7 选定裁剪的大致尺寸,动态裁剪遥感影像 segTifByCropSize
8 合并gdalCommon裁剪的栅格影像 combineTif
9 矢量文件转栅格（矢量文件、源栅格、矢量属性表、输出文件） shp2tif 
10 将栅格最小尺寸定位4096 makeTifMin24096
11 批量去碎斑 removeDir
12 计算一个三通道栅格影像的mean 和 std  calMean_Std
13 计算一个栅格影像的mean 和 std calMean_Std_Bychanneltype
14 合并多个影像 mergeTifs
15 计算四波段归一化指数 calNormalizedIV
16 计算三波段归一化指数 calNormalizedIII
17 合并波段 mergeBand
'''
import numpy as np
import os
import os.path as osp
import math
import glob
from osgeo import gdal,osr,ogr,gdalconst,gdal_array
from yoyiUtils.yoyiFile import checkTifList,deleteDir,deleteShp
import ctypes
import sys

# def rasterMerge(tifList,dataType,outFile):


# 栅格转矢量  coverMode -- "sup" 追加   "cover" 直接覆盖
def raster2shp(rtsTifName,rtsShpName,rtsFieldName,rtsBandIndex=1,rtsDriver="ESRI Shapefile",rts8Connect=0,mask='default',noData=None,fieldIsString=False,callback=None):
    frmt = rtsDriver
    options = []
    if rts8Connect == 1:
        print("使用八向连通")
        options.append('8CONNECTED=8')
    src_filename = rtsTifName
    src_band_n = rtsBandIndex
    dst_filename = rtsShpName
    dst_layername = os.path.basename(dst_filename).split(".")[0]
    if osp.exists(dst_filename):
        deleteShp(dst_filename)
    dst_fieldname = rtsFieldName
    dst_field = -1
    # =============================================================================
    # 	Verify we have next gen bindings with the polygonize method.
    # =============================================================================
    try:
        gdal.Polygonize
    except AttributeError:
        print('')
        print('gdal.Polygonize() not available.  You are likely using "old gen"')
        print('bindings or an older version of the next gen bindings.')
        print('')
        return 1

    # =============================================================================
    # Open source file
    # =============================================================================
    src_ds : gdal.Dataset = gdal.Open(src_filename)

    if src_ds is None:
        print('Unable to open %s' % src_filename)
        return 1

    if src_band_n == 'mask':
        srcband = src_ds.GetRasterBand(1).GetMaskBand()
        # Workaround the fact that most source bands have no dataset attached
        options.append('DATASET_FOR_GEOREF=' + src_filename)
    elif isinstance(src_band_n, str) and src_band_n.startswith('mask,'):
        srcband = src_ds.GetRasterBand(int(src_band_n[len('mask,'):])).GetMaskBand()
        # Workaround the fact that most source bands have no dataset attached
        options.append('DATASET_FOR_GEOREF=' + src_filename)
    else:
        srcband = src_ds.GetRasterBand(src_band_n)
        if noData != None:
            srcband.SetNoDataValue(noData)
    if mask == 'default':
        maskband = srcband.GetMaskBand()
    elif mask == 'none':
        maskband = None
    else:
        mask_ds = gdal.Open(mask)
        maskband = mask_ds.GetRasterBand(1).GetMaskBand()

    # =============================================================================
    #       Try opening the destination file as an existing file.
    # =============================================================================

    try:
        gdal.PushErrorHandler('CPLQuietErrorHandler')
        dst_ds = ogr.Open(dst_filename, update=1)
        gdal.PopErrorHandler()
    except:
        dst_ds = None

    # =============================================================================
    # 	Create output file.
    # =============================================================================
    if dst_ds is None:
        drv = ogr.GetDriverByName(frmt)
        dst_ds = drv.CreateDataSource(dst_filename)

    # =============================================================================
    #       Find or create destination layer.
    # =============================================================================

    try:
        dst_layer = dst_ds.GetLayerByName(dst_layername)
    except:
        dst_layer = None

    if dst_layer is None:
        srs = src_ds.GetSpatialRef()
        dst_layer = dst_ds.CreateLayer(dst_layername, geom_type=ogr.wkbPolygon, srs=srs,options=["ENCODING=UTF-8"])

        if dst_fieldname is None:
            dst_fieldname = 'DN'
        if fieldIsString:
            fd = ogr.FieldDefn(dst_fieldname, ogr.OFTString)
            fd.SetWidth(50)
        else:
            fd = ogr.FieldDefn(dst_fieldname,ogr.OFTInteger)
        dst_layer.CreateField(fd)
        dst_field = 0
    else:
        if dst_fieldname is not None:
            dst_field = dst_layer.GetLayerDefn().GetFieldIndex(dst_fieldname)
            if dst_field < 0:
                print("Warning: cannot find field '%s' in layer '%s'" % (dst_fieldname, dst_layername))

    # =============================================================================
    # Invoke algorithm.
    # =============================================================================
    if callback is not None:
        prog_func = callback
    else:
        prog_func = gdal.TermProgress_nocb
    result = gdal.Polygonize(srcband, maskband, dst_layer, dst_field, options,
                             callback=prog_func)
    srcband = None
    src_ds = None
    dst_ds = None
    mask_ds = None

    return(result)


# 批量栅格转矢量
def batchTif2shp(tifFolder):
    for raster in glob.glob(os.path.join(tifFolder, '*.tif')):
        shpName = raster.split(".")[0] + ".shp"
        raster2shp(raster,shpName)

# 读取文件夹中的所有影像
def load_tiles(tiles_path):
    input_path_extension = tiles_path.split(".")[-1]
    if input_path_extension in ["tif", "tiff", "TIF", "TIFF", "png"]:
        return [tiles_path]
    else:
        return (glob.glob(os.path.join(tiles_path, "*.tif")) +
                glob.glob(os.path.join(tiles_path, "*.tiff")))

# 面转线
def pol2line(polyfn, linefn):
    """
        This function is used to make polygon convert to line
    :param polyfn: the path of input, the shapefile of polygon
    :param linefn: the path of output, the shapefile of line
    :return:
    """
    driver = ogr.GetDriverByName('ESRI Shapefile')
    polyds = ogr.Open(polyfn, 0)
    polyLayer = polyds.GetLayer()
    spatialref = polyLayer.GetSpatialRef()
    #创建输出文件
    if os.path.exists(linefn):
        driver.DeleteDataSource(linefn)
    lineds =driver.CreateDataSource(linefn)
    linelayer = lineds.CreateLayer(linefn, srs=spatialref, geom_type=ogr.wkbLineString)
    featuredefn = linelayer.GetLayerDefn()
    #获取ring到几何体
    new_field1 = ogr.FieldDefn("mark_type", ogr.OFTInteger)
    new_field1.SetWidth(32)
    new_field1.SetPrecision(16)
    linelayer.CreateField(new_field1)
    #geomline = ogr.Geometry(ogr.wkbGeometryCollection)
    for feat in polyLayer:
        geom = feat.GetGeometryRef()
        ring = geom.GetGeometryRef(0)
        #geomcoll.AddGeometry(ring)
        outfeature = ogr.Feature(featuredefn)
        outfeature.SetGeometry(ring)
        outfeature.SetField("mark_type", 1)
        linelayer.CreateFeature(outfeature)
        outfeature = None
    del linelayer


def getLowHighClippingValue(ch, total,lowPercent=0.02,highPercent=0.98):
    """
    :param ch: 累计直方图
    :param total: 像素个数
    :return:
    """
    p2 = total * lowPercent
    p98 = total * highPercent
    min2 = 0
    max98 = 65535
    for index, v in enumerate(ch):
        if v > p2:
            min2 = index - 1
            break
    for index, v in enumerate(ch):
        if v > p98:
            max98 = index
            break
    return min2, max98
# 16位遥感影像 转 8位遥感影像
def uint16to8(srcTif,dstTif,lowPercent=0.02, highPercent=0.98,callback=None):
    srcTifDs : gdal.Dataset = gdal.Open(srcTif)
    clippingList = []
    for i in range(srcTifDs.RasterCount):
        if callback:
            callback( (i+1)/srcTifDs.RasterCount*80 )
        bandTemp: gdal.Band = srcTifDs.GetRasterBand(i+1)
        histogramTemp = bandTemp.GetHistogram(-0.5, 65535.5, 65535, 0, 1)
        pixelTotal = sum(histogramTemp)
        cumsum = np.cumsum(histogramTemp) #累计直方图
        lowValue,highValue = getLowHighClippingValue(cumsum,pixelTotal,lowPercent=lowPercent,highPercent=highPercent)
        clippingList.append([lowValue,highValue])
    
    options = f"-of GTiff -ot Byte "
    bandsString = ""
    for i in range(srcTifDs.RasterCount):
        bandsString = bandsString + f"-b {i+1} "
    options = options + bandsString
    for i in range(srcTifDs.RasterCount):
        options = options + f"-scale_{i+1} {clippingList[i][0]} {clippingList[i][1]} 0 254 "
    options = options + "-co BIGTIFF=YES -co COMPRESS=LZW"
    print(options)
    translate_options = gdal.TranslateOptions(options=options)
    gdal.Translate(dstTif, srcTif, options=translate_options)
    if callback:
            callback(100)




# 选定裁剪次数，动态裁剪遥感影像
def segTif(tifPath,resultDir,segNum=6):
    tifDs = gdal.Open(tifPath) #type: gdal.Dataset
    tifGeoTrans = tifDs.GetGeoTransform()
    tifProject = tifDs.GetProjection()
    bandTif = tifDs.RasterCount
    heiTif = tifDs.RasterYSize
    weiTif = tifDs.RasterXSize
    dataType = tifDs.GetRasterBand(1).DataType
    xsize = math.ceil(weiTif / segNum)
    ysize = math.ceil(heiTif / segNum)
    XSegNum = int(weiTif / xsize) if weiTif%xsize == 0 else int(weiTif / xsize)+1
    YSegNum = int(heiTif / ysize) if heiTif%ysize == 0 else int(heiTif / ysize)+1
    num = 0
    print(f"开始进行动态裁剪{tifPath}")
    for y in range(YSegNum):
        for x in range(XSegNum):
            xOff = x*xsize
            yOff = y*ysize
            xSizeTemp = min(weiTif-xOff,xsize)
            ySizeTemp = min(heiTif-yOff,ysize)
            tifTempPath = osp.join(resultDir, f"{bandTif}_{weiTif}_{heiTif}_{dataType}_{xOff}_{xSizeTemp}_{yOff}_{ySizeTemp}_.tif")
            arrayTemp = tifDs.ReadAsArray(xOff,yOff,xSizeTemp,ySizeTemp)
            tempDriver = gdal.GetDriverByName("GTiff") #type: gdal.Driver
            dsTemp = tempDriver.Create(tifTempPath,xSizeTemp,ySizeTemp,bandTif,dataType) #type: gdal.Dataset
            top_leftX = tifGeoTrans[0] + xOff*tifGeoTrans[1]
            top_leftY = tifGeoTrans[3] + yOff*tifGeoTrans[5]
            transTemp = (top_leftX,tifGeoTrans[1],tifGeoTrans[2],top_leftY,tifGeoTrans[4],tifGeoTrans[5])
            dsTemp.SetGeoTransform(transTemp)
            dsTemp.SetProjection(tifProject)
            for b in range(bandTif):
                dsTemp.GetRasterBand(b + 1).WriteArray(arrayTemp[b, :, :])
            dsTemp.FlushCache()
            del dsTemp
            num+=1
    print(f"分割完成，结果文件夹：{resultDir} ... 总分割块数量{num}")
    del tifDs
    return tifGeoTrans,tifProject

# 选定裁剪的大致尺寸,在不偏离这个大致尺寸的情况下进行动态裁剪遥感影像 (注意: 最后裁剪出的影像不一定是选定的尺寸,尺寸参数的意义仅仅是为裁剪次数提供一个大致的参考)
def segTifByCropSize(tifPath,resultDir,xsize=1024,ysize=1024):
    tifDs = gdal.Open(tifPath) #type: gdal.Dataset
    tifGeoTrans = tifDs.GetGeoTransform()
    tifProject = tifDs.GetProjection()
    bandTif = tifDs.RasterCount
    heiTif = tifDs.RasterYSize
    weiTif = tifDs.RasterXSize
    dataType = tifDs.GetRasterBand(1).DataType
    assert heiTif > ysize,"cropSize is too large or tif img size is too small!!!"
    assert weiTif > xsize, "cropSize is too large or tif img size is too small!!!"
    XSegNum = int(weiTif/xsize)
    YSegNum = int(heiTif/ysize)
    xsize = math.ceil(weiTif/XSegNum)
    ysize = math.ceil(heiTif/YSegNum)
    num = 0
    print(f"开始进行动态裁剪{tifPath}")
    for y in range(0,heiTif, ysize):
        if y+ysize>heiTif:
            YclipSize = heiTif-y
        else:
            YclipSize = ysize
        for x in range(0, weiTif, xsize):
            if x+xsize > weiTif:
                XclipSize = weiTif-x
            else:
                XclipSize = xsize
            tifTempPath = osp.join(resultDir,
                                   f"{bandTif}_{weiTif}_{heiTif}_{dataType}_{x}_{XclipSize}_{y}_{YclipSize}_.tif")
            print("裁剪的尺寸:",XclipSize,YclipSize)
            if os.path.exists(tifTempPath):
                continue
            arrayTemp = tifDs.ReadAsArray(x, y, XclipSize, YclipSize)
            tempDriver = gdal.GetDriverByName("GTiff")  # type: gdal.Driver
            dsTemp = tempDriver.Create(tifTempPath,XclipSize,YclipSize,bandTif,dataType) #type: gdal.Dataset
            top_leftX = tifGeoTrans[0] + x*tifGeoTrans[1]
            top_leftY = tifGeoTrans[3] + y*tifGeoTrans[5]
            transTemp = (top_leftX,tifGeoTrans[1],tifGeoTrans[2],top_leftY,tifGeoTrans[4],tifGeoTrans[5])
            dsTemp.SetGeoTransform(transTemp)
            dsTemp.SetProjection(tifProject)
            if bandTif == 1:
                dsTemp.GetRasterBand(1).WriteArray(arrayTemp[:, :])
            else:
                for b in range(bandTif):
                    dsTemp.GetRasterBand(b + 1).WriteArray(arrayTemp[b, :, :])
            dsTemp.FlushCache()
            del dsTemp
            num+=1
    print(f"分割完成，结果文件夹：{resultDir} ... 总分割块数量{num}")
    del tifDs
    return tifGeoTrans,tifProject

# 合并gdalCommon裁剪的栅格影像
def combineTif(tifDir,resultTif):
    tifList = glob.glob(osp.join(tifDir,"*.tif"))
    infoList = osp.basename(tifList[0]).split("_")
    BAND = int(infoList[0])
    XSize = int(infoList[1])
    YSize = int(infoList[2])
    dataType = int(infoList[3])
    tifDriver = gdal.GetDriverByName("GTiff") #type: gdal.Driver
    tifDs = tifDriver.Create(resultTif,XSize,YSize,BAND,dataType) #type: gdal.Dataset
    tempTif = gdal.Open(tifList[0]) #type: gdal.Dataset
    tempNP = tempTif.ReadAsArray()
    tifDataType = tempNP.dtype
    tifGeoTrans = tempTif.GetGeoTransform()
    tifProject = tempTif.GetProjection()
    del tempNP
    del tempTif
    tifNp = np.zeros((BAND,YSize,XSize),dtype=tifDataType)
    for tifTemp in tifList:
        infoList = osp.basename(tifTemp).split("_")
        xOff,xSizeT,yOff,ySizeT = int(infoList[4]),int(infoList[5]),int(infoList[6]),int(infoList[7])
        tempTif = gdal.Open(tifTemp)  # type: gdal.Dataset
        tempNP = tempTif.ReadAsArray()
        #print(BAND,ySizeT,xSizeT)
        #print(tempNP.shape)
        assert tempNP.shape[0] == BAND
        assert tempNP.shape[1] == ySizeT
        assert tempNP.shape[2] == xSizeT
        tifNp[:,yOff:yOff+ySizeT,xOff:xOff+xSizeT] = tempNP
        del tempTif
        del tempNP
    tifDs.SetGeoTransform(tifGeoTrans)
    tifDs.SetProjection(tifProject)
    for b in range(BAND):
        tifDs.GetRasterBand(b + 1).WriteArray(tifNp[b, :, :])
    tifDs.FlushCache()
    del tifDs
    print("已完成栅格影像合并")

# 将矢量文件转为和目标栅格数据空间位置一致且像元大小一致的数据
# 给定 矢量文件、指定空间位置和像元的参考栅格、矢量属性表、输出文件
def shp2tif(shpPath,tifPath,shpAttr,outputPath):
    tifDs = gdal.Open(tifPath,gdalconst.GA_ReadOnly) # type: gdal.Dataset
    shpDs = ogr.Open(shpPath,0) # type: ogr.DataSource
    geoTrans = tifDs.GetGeoTransform()
    cols = tifDs.RasterXSize
    rows = tifDs.RasterYSize

    x_min = geoTrans[0]
    y_min = geoTrans[3]
    pixelWidth = geoTrans[1]

    shpLayer = shpDs.GetLayer(0)

    outputDri = gdal.GetDriverByName('GTiff') #type: gdal.Driver
    outputDs = outputDri.Create(outputPath,xsize=cols,ysize=rows,bands=1,eType=gdal.GDT_Byte) # type: gdal.Dataset
    outputDs.SetGeoTransform(geoTrans)
    outputDs.SetProjection(tifDs.GetProjection())

    outBand = outputDs.GetRasterBand(1) #type: gdal.Band
    outBand.SetNoDataValue(0)
    outBand.FlushCache()
    gdal.RasterizeLayer(outputDs,[1],shpLayer,options=[f"ATTRIBUTE={shpAttr}"])

    del tifDs
    del shpDs
    del outputDs

# 将栅格最小尺寸定位4096
def makeTifMin24096(tifPath):
    tifDs = gdal.Open(tifPath) # type: gdal.Dataset
    tifNp = tifDs.ReadAsArray()
    dataType = tifDs.GetRasterBand(1).DataType
    c,h,w = tifNp.shape
    H,W = h,w
    if h < 4096:
        H = 6000
    if w < 4096:
        W = 6000
    newPath = tifPath[:-4] + "_Bigxiufu.tif"
    tempDriver = gdal.GetDriverByName("GTiff")  # type: gdal.Driver
    dsTemp = tempDriver.Create(newPath, W, H, c, dataType)  # type: gdal.Dataset
    tifGeoTrans = tifDs.GetGeoTransform()
    tifProject = tifDs.GetProjection()
    dsTemp.SetGeoTransform(tifGeoTrans)
    dsTemp.SetProjection(tifProject)
    tempNp = np.zeros((c,H, W))
    tempNp[:,:h,:w] = tifNp[:, :, :]
    #tempNp = tempNp.transpose((0,2,1))
    for b in range(c):
        dsTemp.GetRasterBand(b + 1).WriteArray(tempNp[b,:,:])
    dsTemp.FlushCache()
    del dsTemp
    print(f"图片太小，修复结果位于：{newPath}")
    return newPath

class MethodProducedRemove():
    def __init__(self, RSR_filename,area_delete,RSR_result_file):
        self.RSR_filename=RSR_filename
        self.area_delete=area_delete
        self.RSR_result_file=RSR_result_file

    def run(self, WORKROOT):  # 自动生产
        if sys.platform == 'linux':
            MethodRSR = ctypes.cdll.LoadLibrary('libs/removeSmallRegion20200910/libremoveSmallRegion.so')
            MethodRSR.removeSmallRegion(self.RSR_filename.encode('gb2312'), self.area_delete,
                                        self.RSR_result_file.encode('gb2312'))
        else:
            os.chdir("libs/")
            os.environ['PATH']=os.getcwd()
            MethodRSR = ctypes.cdll.LoadLibrary('removeSmallRegion.dll')
            #MethodRSR.removeSmallRegion(self.RSR_filename,self.area_delete,self.RSR_result_file)
            MethodRSR.removeSmallRegionSingle(self.RSR_filename,self.area_delete,self.RSR_result_file)
            os.chdir(WORKROOT)
WORKROOT = os.getcwd()

# 批量去碎斑
def removeDir(tifDir,area=100):
    for raster in glob.glob(os.path.join(tifDir, '*.tif')):
        resultTemp = raster[:-4] + "_remove.tif"
        remove = MethodProducedRemove(raster.encode('gbk'), area,
                                       resultTemp.encode('gbk'))  # windows 10
        remove.run(WORKROOT)

# 计算一个栅格影像的mean 和 std
def calMean_Std(tifFile):
    img_dataset = gdal.Open(tifFile) # type: gdal.Dataset
    if None == img_dataset:
        print(f"file {img_dataset} can't open")
        return
    img_bands = img_dataset.RasterCount  # 波段数
    temp_mean=[]
    temp_std=[]
    for i in range(img_bands):
        source_band = img_dataset.GetRasterBand(i + 1)
        stats = source_band.GetStatistics(1, 1)
        temp_mean.append(stats[2])
        temp_std.append(stats[3])
    return temp_mean, temp_std

# 计算一个栅格影像的mean 和 std
def calMean_Std_Bychanneltype(tifFile, channel_type):
    img_dataset = gdal.Open(tifFile) # type: gdal.Dataset
    if None == img_dataset:
        print(f"file {img_dataset} can't open")
        return
    img_bands = img_dataset.RasterCount  # 波段数
    temp_mean=[]
    temp_std=[]
    if img_bands == 3:
        r_stats = img_dataset.GetRasterBand(1).GetStatistics(1, 1)
        g_stats = img_dataset.GetRasterBand(2).GetStatistics(1, 1)
        b_stats = img_dataset.GetRasterBand(3).GetStatistics(1, 1)
    elif img_bands == 4:
        b_stats = img_dataset.GetRasterBand(1).GetStatistics(1, 1)
        g_stats = img_dataset.GetRasterBand(2).GetStatistics(1, 1)
        r_stats = img_dataset.GetRasterBand(3).GetStatistics(1, 1)
        n_stats = img_dataset.GetRasterBand(4).GetStatistics(1, 1)
    else: raise ValueError("img bands error")

    if channel_type == "rgb":
        temp_mean = [r_stats[2],g_stats[2],b_stats[2]]
        temp_std = [r_stats[3],g_stats[3],b_stats[3]]
    elif channel_type == "bgrn":
        temp_mean = [b_stats[2], g_stats[2], r_stats[2], n_stats[2]]
        temp_std = [b_stats[3], g_stats[3], r_stats[3], n_stats[3]]
    return temp_mean, temp_std

# 合并多个影像
def mergeTifs(inputTifs,outTif,resampleAlg=0,clipShp="",nodataValue=0,compress=None,callback=None):
    """
    inputTifs : 待拼接影像所在的栅格目录 或 列表
    outTif : 拼接影像输出路径
    resampleAlg : 重采样方法  '0:NearestNeighbour', '1:Bilinear', '2:Cubic'
    clipShp : 一个SHP文件用于裁剪拼接后的栅格影像 默认不使用
    """
    if compress == "LZW":
        createOptionList = ["COMPRESS=LZW","BIGTIFF=YES"]
    elif compress == "LERC":
        createOptionList = ["COMPRESS=LERC","BIGTIFF=YES","MAX_Z_ERROR=0.1"]
    else:
        createOptionList = ["BIGTIFF=YES"]
    if type(inputTifs) == list:
        tifs = inputTifs
    else:
        tifs = os.listdir(inputTifs)
        tifs = list(filter(lambda fileName: fileName.endswith('.tif'), tifs))
        if len(tifs) == 0:
            print("栅格目录为空")
            return
        tifs = [os.path.join(inputTifs, tif) for tif in tifs]
    if clipShp != "" and not osp.exists(clipShp):
        print(f"裁剪SHP文件{clipShp}不存在")
        return
    gdal.AllRegister()
    # 检查这些待拼接影像是否句有相同的空间参考 有点浪费时间
    osrs = []
    for tif in tifs:
        ds : gdal.Dataset = gdal.Open(tif, gdalconst.GA_ReadOnly)
        osr_ = gdal.Dataset.GetSpatialRef(ds)
        osrs.append(osr_)
    osr_ = osrs[0]
    for osri in osrs:
        flag = osr.SpatialReference.IsSame(osr_, osri)
        if not (flag):
            raise '待拼接的栅格影像必须有相同的空间参考！'
    if resampleAlg == 0:
        resampleType = gdalconst.GRA_NearestNeighbour
    elif resampleAlg == 1:
        resampleType = gdalconst.GRA_Bilinear
    else:
        resampleType = gdalconst.GRA_Cubic
    if clipShp != "":
        options = gdal.WarpOptions(
            srcSRS=osr_, dstSRS=osr_, format='GTiff', resampleAlg=resampleType, creationOptions=createOptionList,
            cutlineDSName=clipShp,dstNodata=nodataValue, cropToCutline=True,callback=callback)
    else:
        options = gdal.WarpOptions(
            srcSRS=osr_, dstSRS=osr_, format='GTiff', resampleAlg=resampleType,dstNodata=nodataValue,
            creationOptions=createOptionList,callback=callback)
    #gdal.SetConfigOption("BIGTIFF","YES")
    gdal.Warp(outTif,tifs,options=options)

def getNormNp(tifNp,normalType,b=0,g=1,r=2,n=3,nodata=-999):
    """
    normalType : 1 NDVI  2 NDWI 3 GLI 4 RGBVI 5 NGRDI 6 EXG 7 CIVE 8 VEG 9 EXGR 10 WI 11 COM
    """
    numrgb = tifNp[r, :, :] + tifNp[g, :, :] + tifNp[b, :, :]
    full_999 = np.full((tifNp.shape[1], tifNp.shape[2]), nodata, dtype=float)
    if normalType == "NDVI": # NDVI 4
        numerator = tifNp[n,:,:] - tifNp[r,:,:] # 分子
        denominator = tifNp[n,:,:] + tifNp[r,:,:]  # 分母
        resNp = np.divide(numerator,denominator,out=full_999,where=numrgb != 0)
    elif normalType == "NDWI": #NDWI 4
        numerator = tifNp[g, :, :] - tifNp[n, :, :] # 分子
        denominator = tifNp[g, :, :] + tifNp[n, :, :] # 分母
        resNp = np.divide(numerator, denominator, out=full_999, where=numrgb != 0)
    elif normalType == "GLI": # GLI 3
        numerator = (tifNp[g, :, :] - tifNp[r, :, :]) + (tifNp[g, :, :] - tifNp[b, :, :])  # 分子
        denominator = ( tifNp[g, :, :]*2 + tifNp[r, :, :] + tifNp[b, :, :] ) # 分母
        resNp = np.divide(numerator, denominator, out=full_999, where=numrgb != 0)
    elif normalType == "RGBVI": # RGBVI 3
        numerator = (tifNp[g, :, :]*tifNp[g, :, :]) - (tifNp[r, :, :]*tifNp[b, :, :])  # 分子
        denominator = (tifNp[g, :, :]*tifNp[g, :, :]) + tifNp[r, :, :] + tifNp[b, :, :]  # 分母
        resNp = np.divide(numerator, denominator, out=full_999, where=numrgb != 0)
    elif normalType == "NGRDI": # NGRDI 归一化红绿差分指数 3
        numerator = tifNp[g,:,:] - tifNp[r,:,:]  # 分子
        denominator = tifNp[g,:,:] + tifNp[r,:,:]  # 分母
        resNp = np.divide(numerator, denominator, out=full_999, where=numrgb != 0)
    elif normalType == "EXG": # EXG 超绿指数 3
        numa = tifNp[g,:,:]*2
        numb = tifNp[r,:,:]+tifNp[b,:,:]
        resNp = np.subtract(numa,numb,out=full_999, where=numrgb != 0)
    elif normalType == "CIVE": # CIVE 植被颜色指数 3
        numa = (tifNp[r,:,:]*0.44) - (tifNp[g,:,:]*0.88)
        numb =  (tifNp[b,:,:]*0.39) + 18.79
        resNp = np.add(numa,numb,out=full_999,where=numrgb!=0)
    elif normalType == "VEG": # VEG 光谱植被指数 3
        numerator = tifNp[g,:,:]  # 分子
        denominator = (np.power(tifNp[r,:,:],0.667)*np.power(tifNp[b,:,:],1-0.667))  # 分母
        resNp = np.divide(numerator, denominator, out=full_999, where=numrgb != 0)
    elif normalType == "EXGR": # EXGR 超绿超红差分指数 3
        numa = ((tifNp[g,:,:]*2) - tifNp[r,:,:] - tifNp[b,:,:])
        numb = 1.4*tifNp[r,:,:] + tifNp[g,:,:]
        resNp = np.subtract(numa,numb,out=full_999, where=numrgb != 0)
    elif normalType == "WI": # WI Woebbecke指数 3
        numerator = tifNp[g, :, :] - tifNp[b, :, :]  # 分子
        denominator = tifNp[r, :, :] - tifNp[g, :, :]  # 分母
        resNp = np.divide(numerator, denominator, out=full_999, where=numrgb != 0)
    elif normalType == "COM": # COM 联合指数
        resNp = 0.25*((tifNp[g,:,:]*2) - tifNp[r,:,:] - tifNp[b,:,:]) + \
                0.3*(((tifNp[g,:,:]*2) - tifNp[r,:,:] - tifNp[b,:,:]) - 1.4*tifNp[r,:,:] - tifNp[g,:,:]) + \
                0.33*((tifNp[r,:,:]*0.44) - (tifNp[g,:,:]*0.88) + (tifNp[b,:,:]*0.39) + 18.79) + \
                0.12*((tifNp[g,:,:]) / (np.power(tifNp[r,:,:],0.667)*np.power(tifNp[b,:,:],1-0.667)))
    return resNp

def calNormalizedIV(tifPath,outDir,outName,normalType,b=0,g=1,r=2,n=3,thre="",callback=None):
    """
    计算四波段归一化指数
    tifPath : 要计算指数的影像
    outDir : 输出影像文件夹
    outName : 输出影像名
    normalType : 归一化方式  1 NDVI  2 NDWI
    thre : 阈值 “” -- 不使用阈值  其他值 -- 对应的阈值
    """
    tifDs = gdal.Open(tifPath) #type: gdal.Dataset
    bands = tifDs.RasterCount
    cols = tifDs.RasterXSize  # 列数
    rows = tifDs.RasterYSize  # 行数
    if bands < 4:
        return -1

    # 计算指数
    if cols >= 14000 and rows >= 14000:
        tempOutDir = osp.join(outDir,"tempSegTif")
        tempOutNp = osp.join(outDir, "tempOutTif")
        if not osp.exists(tempOutDir):
            os.mkdir(tempOutDir)
        if not osp.exists(tempOutNp):
            os.mkdir(tempOutNp)
        print("开始分割")
        segTifByCropSize(tifPath,tempOutDir,xsize=10000,ysize=10000)
        tifs = os.listdir(tempOutDir)
        tifs = list(filter(lambda fileName: fileName.endswith('.tif'), tifs))
        tifs = [os.path.join(tempOutDir, tif) for tif in tifs]
        for tif, i in zip(tifs, range(len(tifs))):
            if callback:
                callback((i + 1) / len(tifs) * 90)
            calNormalizedIV(tif,tempOutNp,osp.basename(tif),normalType,b,g,r,n,thre)
        mergeTifs(tempOutNp,osp.join(outDir,outName),nodataValue=-999)
        if callback:
            callback(100)

    else:
        tifNp = tifDs.ReadAsArray().astype(float)
        if callback:
            callback(30)
        NormNp = getNormNp(tifNp,normalType,b,g,r,n)
        if callback:
            callback(60)
        if thre == "":
            geo_transform = tifDs.GetGeoTransform()
            target_ds = gdal.GetDriverByName('GTiff').Create(osp.join(outDir,outName), xsize=cols, ysize=rows, bands=1,
                                                             eType=gdal.GDT_Float32)
            target_ds.SetGeoTransform(geo_transform)
            target_ds.SetProjection(tifDs.GetProjection())
            target_ds.GetRasterBand(1).SetNoDataValue(-999)
            target_ds.GetRasterBand(1).WriteArray(NormNp)
            del target_ds
        else:
            if thre > 0:
                NormNp[NormNp<thre] = 0
                NormNp[NormNp>=thre] = 1
            else:
                NormNp[NormNp>=thre] = 1
                NormNp[NormNp<thre] = 0
            geo_transform = tifDs.GetGeoTransform()
            target_ds = gdal.GetDriverByName('GTiff').Create(osp.join(outDir,outName), xsize=cols, ysize=rows, bands=1,
                                                             eType=gdal.GDT_Byte)
            target_ds.SetGeoTransform(geo_transform)
            target_ds.SetProjection(tifDs.GetProjection())
            target_ds.GetRasterBand(1).WriteArray(NormNp)
            del target_ds
        if callback:
            callback(100)
    return 0

def calNormalizedIII(tifPath,outDir,outName,normalType,b=0,g=1,r=2,thre="",callback=None):
    """
    计算三波段归一化指数
    tifPath : 要计算指数的影像
    outDir : 输出影像文件夹
    outName : 输出影像名
    normalType : 归一化方式  3 GLI 4 RGBVI
    thre : 阈值 “” -- 不使用阈值  其他值 -- 对应的阈值
    """
    tifDs = gdal.Open(tifPath) #type: gdal.Dataset
    bands = tifDs.RasterCount
    cols = tifDs.RasterXSize  # 列数
    rows = tifDs.RasterYSize  # 行数
    if bands < 3:
        return -1
    # 计算指数
    if cols >= 14000 and rows >= 14000:
        tempOutDir = osp.join(outDir, "tempSegTif")
        tempOutNp = osp.join(outDir, "tempOutTif")
        if not osp.exists(tempOutDir):
            os.mkdir(tempOutDir)
        if not osp.exists(tempOutNp):
            os.mkdir(tempOutNp)
        print("开始分割")
        segTifByCropSize(tifPath,tempOutDir,xsize=10000,ysize=10000)
        tifs = os.listdir(tempOutDir)
        tifs = list(filter(lambda fileName: fileName.endswith('.tif'), tifs))
        tifs = [os.path.join(tempOutDir, tif) for tif in tifs]
        for tif,i in zip(tifs,range(len(tifs))):
            if callback:
                callback( (i+1)/len(tifs)*90 )
            calNormalizedIII(tif,tempOutNp,osp.basename(tif),normalType,b,g,r,thre)
        mergeTifs(tempOutNp,osp.join(outDir,outName),nodataValue=-999)
    else:
        tifNp = tifDs.ReadAsArray().astype(float)
        if callback:
            callback(30)
        NormNp = getNormNp(tifNp,normalType,b,g,r)
        if callback:
            callback(60)
        if thre == "":
            geo_transform = tifDs.GetGeoTransform()
            target_ds = gdal.GetDriverByName('GTiff').Create(osp.join(outDir,outName), xsize=cols, ysize=rows, bands=1,
                                                             eType=gdal.GDT_Float32)
            target_ds.SetGeoTransform(geo_transform)
            target_ds.SetProjection(tifDs.GetProjection())
            target_ds.GetRasterBand(1).SetNoDataValue(-999)
            target_ds.GetRasterBand(1).WriteArray(NormNp)
            del target_ds
        else:
            if thre > 0:
                NormNp[NormNp<thre] = 0
                NormNp[NormNp>=thre] = 1
            else:
                NormNp[NormNp>=thre] = 1
                NormNp[NormNp<thre] = 0
            geo_transform = tifDs.GetGeoTransform()
            #gdal_array.SaveArray(NormNp,osp.join(outDir,outName),format="GTiff",prototype=tifPath)
            target_ds = gdal.GetDriverByName('GTiff').Create(osp.join(outDir,outName), xsize=cols, ysize=rows, bands=1,
                                                             eType=gdal.GDT_Byte)
            target_ds.SetGeoTransform(geo_transform)
            target_ds.SetProjection(tifDs.GetProjection())
            target_ds.GetRasterBand(1).WriteArray(NormNp)
            del target_ds
        if callback:
            callback(100)
    return 0
# mergeBand
def mergeBand(tifDir,resTif,crsTif):
    crsDs = gdal.Open(crsTif)
    tifs = os.listdir(tifDir)
    tifs = list(filter(lambda fileName: fileName.endswith('.tif'), tifs))
    tifs = [os.path.join(tifDir, tif) for tif in tifs]
    tifDs = gdal.Open(tifs[0])  # type: gdal.Dataset
    cols = tifDs.RasterXSize  # 列数
    rows = tifDs.RasterYSize
    target_ds = gdal.GetDriverByName('GTiff').Create(resTif, xsize=cols, ysize=rows, bands=len(tifs),eType=gdal.GDT_Byte)
    target_ds.SetGeoTransform(crsDs.GetGeoTransform())
    target_ds.SetProjection(crsDs.GetProjection())
    i = 1
    for tif in tifs:
        tifDs = gdal.Open(tif)  # type: gdal.Dataset
        tifNp = tifDs.ReadAsArray().astype(int)
        target_ds.GetRasterBand(i).WriteArray(tifNp)
        i += 1
    del target_ds

# 建立金字塔
def buildOverView(tif:str):
    if tif.endswith(".tif") or tif.endswith(".TIF") or tif.endswith(".tiff"):
        tifs = [tif]
    elif osp.isdir(tif):
        tifs = [os.path.join(tif, i) for i in os.listdir(tif) if
                           i.split('.')[-1] in ['tif', 'TIF', 'TIFF']]
    else:
        tifs = []
    for tif in tifs:
        ds = gdal.Open(tif, gdal.GA_ReadOnly)
        gdal.SetConfigOption('BIGTIFF_OVERVIEW', 'YES')
        res = ds.BuildOverviews(overviewlist=[1, 2, 4, 8, 16])
        if res != 0:
            if osp.exists(tif + ".ovr"):
                try:
                    os.remove(tif + ".ovr")
                except:
                    pass
        del ds

# 转坐标系
def transformEPSG(srcTif,outTif,srcSRS='4326',dstSRS='3857'):
    options = gdal.WarpOptions(format='GTiff', srcSRS=f'EPSG:{srcSRS}', dstSRS=f'EPSG:{dstSRS}')
    gdal.Warp(outTif,srcTif, options=options)


# 批量修改矢量坐标系
def batchModifyProjectionByTif(tifDir,shpDir,projectTifPath):
    tifDs : gdal.Dataset = gdal.Open(projectTifPath,0)
    project = tifDs.GetProjection()
    #deleteDir(shpDir,False)
    tifDir = checkTifList(tifDir)
    for tif in tifDir:
        print(tif)
        tifDsTemp : gdal.Dataset = gdal.Open(tif,1)
        tifDsTemp.SetProjection(project)
        tifDsTemp.FlushCache()
        del tifDsTemp
        raster2shp(tif,osp.join(shpDir,osp.basename(tif)[:-10]+".shp"),"value",mask=tif)

# 下采样
def downSample(tifPath,tifOut,downSampleScale=2):
    tifDs : gdal.Dataset = gdal.Open(tifPath,0)
    x,y = tifDs.RasterXSize//downSampleScale,tifDs.RasterYSize//downSampleScale
    print(x,y)
    gdal.Warp(tifOut,tifPath,resampleAlg=gdalconst.GRA_NearestNeighbour,width=x,height=y)

# 根据边界裁剪影像
def clipTifByOutBounds(tifPath,outTifPath,outputBounds,outSize=None,callback=None):
    """
    outputBounds (tuple):(minx,miny,maxx,maxy)
    """
    
    if outSize:
        ds = gdal.Warp(outTifPath, tifPath, format='GTiff', outputBounds=outputBounds,
                       dstNodata=0,resampleAlg=gdalconst.GRA_NearestNeighbour,
                       width=outSize[0],height=outSize[1],callback=callback)
    else:
        ds = gdal.Warp(outTifPath,tifPath,format='GTiff',outputBounds=outputBounds,dstNodata=0,callback=callback)
    ds.FlushCache()
    del ds


def createEmptyShapefile(shp_path,wkt,fieldDict:dict={'value':ogr.OFTString,},post="gpkg"):
    if post == "shp":
        driverName = 'ESRI Shapefile'
    elif post == "gpkg":
        driverName = 'GPKG'
    else:
        driverName = 'ESRI Shapefile'
    driver = ogr.GetDriverByName(driverName)
    if osp.exists(shp_path):
        driver.DeleteDataSource(shp_path)
    ds = driver.CreateDataSource(shp_path)

    srs = osr.SpatialReference()
    srs.ImportFromWkt(wkt)

    dst_layer = ds.CreateLayer(osp.basename(shp_path).split(".")[0], geom_type=ogr.wkbPolygon, srs=srs,options=["ENCODING=UTF-8"])

    for dst_fieldname,dst_fieldtype in fieldDict.items():
        fd = ogr.FieldDefn(dst_fieldname, dst_fieldtype)
        dst_layer.CreateField(fd)

    ds.Destroy()






















