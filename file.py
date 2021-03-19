'''
文件相关操作
'''
import json,xlwt,xlrd
from xml.dom.minidom import parse
from lxml import etree
from datetime import datetime
from configparser import ConfigParser
import configparser
import os
import re
import time
import shutil
import base64
import chardet
import xmltodict
import traceback
import os.path
import zipfile
from pathlib import Path

def strtohex(data):
    '字符串转16进制字节数组'
    input_s = data
    send_list = []
    while input_s != '':
        try:
            num = int(input_s[0:2], 16)
        except ValueError:
            return None
        input_s = input_s[2:].strip()
        send_list.append(num)
    input_s = bytes(send_list)
    return input_s   

def pathSplit(path):
    return os.path.dirname(path),os.path.basename(path)
def xmlToJObj(path):
    with open(path,mode='r',encoding='utf8') as f:
        content = f.read()
        converteJson = xmltodict.parse(xml_input = content, encoding = 'utf-8')
        strJson = json.dumps(converteJson,ensure_ascii=False)
        return json.loads(strJson)
   
def loadSucessXML(path,tax_type):
    '返回已开票结果'
    tree = etree.parse(path)
    root=tree.getroot()
    responseList=root.xpath('//RESPONSE_COMMON_FPKJ')
    result=''
    for i in range(len(responseList)):
        response=responseList[i]
        result={'returncode':'9999','returnmsg':'','data':{}}
        dataDict={'fpqqlsh':'','fp_dm':'','fp_hm':'','kprq':'','jqbh':'','fp_mw':'','jym':'','ewm':'','bz':'','ewm_url':''}
        node_tag_list=['RETURNCODE','RETURNMSG','FPQQLSH','FP_DM','FP_HM','KPRQ','JQBH','FP_MW','JYM','EWM','BZ']
        data_tag_list=['returncode','returnmsg','fpqqlsh','fp_dm','fp_hm','kprq','jqbh','fp_mw','jym','ewm','bz']
        for node in response.getchildren():
            for i in range(2):
                if node.tag==node_tag_list[i]:
                    result[data_tag_list[i]]=node.text
            for i in range(2,10):
                if node.tag==node_tag_list[i]:
                    dataDict[data_tag_list[i]]=node.text
        result['data']=dataDict
        if tax_type=='2':
            rq=result['data']['kprq']
            year=rq[0:4]
            month=rq[4:6]
            day=rq[6:8]
            rq='%s年%s月%s日' % (year,month,day)
            result['data']['kprq']=rq
        if result['returncode']=='0000':
            break
    return result 

def checkMission(missionInfo):
    '检查任务信息是否完整'
    missionKeys=['attachParam','taskSn','messageTime','taskType','taxdisk']
    result={'returncode':'0000','returnmsg':''}
    #检查参数完整
    # 检查一级字段
    for i in range(len(missionKeys)):
        if missionKeys[i] not in missionInfo and i!=4:
            result['returnmsg']+='%s,' % missionKeys[i]
            result['returncode']='0011'
    if result['returncode']=='0011':
        return result
    attachParam=missionInfo['attachParam']
    attachParamKeys=['router_ip','router_n2n_ip','m8_ip','busid','n2n_server_ip','n2n_server_port']
    for i in range(len(attachParamKeys)):
        if attachParamKeys[i] not in attachParam:
            result['returnmsg']+='%s,' % attachParamKeys[i]
            result['returncode']='0011'
    #临时添加cupboard_mac字段
    if not attachParam.get('cupboard_mac'):
        attachParam['cupboard_mac'] = ''
    #
    taxdisk=missionInfo['taxdisk']
    taxdiskKeys1=['tax_no','ukey_pwd','digit_cert_pwd','business_address','phone','director_name']
    taxdiskKeys2=['mail_address','mail_server_addr','mail_server_port','smtp_auth_code']
    for i in range(len(taxdiskKeys1)):
        if taxdiskKeys1[i] not in taxdisk:
            result['returnmsg']+='%s,' % taxdiskKeys1[i]
            result['returncode']='0011'    
    # 检查开票字段
    if missionInfo['taskType']=='DZKP':
        if 'invoices' not in missionInfo:
            result['returnmsg']+='%s,' % 'invoices'
            result['returncode']='0011'    
        invoices=missionInfo['invoices']
        if len(invoices)==0:
            result['returnmsg']+='没有开票数据,'
            result['returncode']='0011'
            return result
        if 'fpqqlsh' not in invoices[0]:
            result['returnmsg']+='fpqqlsh,'
            result['returncode']='0011'
            return result
        for i in range(len(taxdiskKeys2)):
            if taxdiskKeys2[i] not in taxdisk:
                result['returnmsg']+='%s,' % 'taxdiskKeys2[i]'
                result['returncode']='0011'
        #临时设置发票类型为0(普通票) 用于航信开票
        missionInfo['invoices'][0]['type'] = 0
    elif missionInfo['taskType']=='GZSP':
        pass
    return result     

def spawnXlsData(xmxx,path):
    '生成开票信息xls格式'
    captions=['税收分类编码','商品名称','规格型号','计量单位','数量','单价','金额','税率','优惠政策','免税类型','含税标志']
    items=[captions]
    for index in range(len(xmxx)):
        item=[xmxx[index]['spbm'],xmxx[index]['xmmc'],'',xmxx[index]['dw'],xmxx[index]['xmsl'],xmxx[index]['xmdj'],xmxx[index]['xmje'],xmxx[index]['sl'],'','','']
        items.append(item)
    book=xlwt.Workbook()
    sheet=book.add_sheet('sheet1')
    for row in range(len(items)):
        for col in range(len(items[row])):
            sheet.write(row,col,items[row][col])
    book.save(path)

def xmlToDict(xmlStr):
    converteJson = xmltodict.parse(xml_input = xmlStr, encoding = 'utf-8')
    strJson = json.dumps(converteJson,ensure_ascii=False)
    ss = json.loads(strJson)
    return ss

#文件读写
def loadTxt(path):
    '读取文本'
    content = ''
    with open(path,mode='r',encoding='utf8',errors='ignore') as f:
        content=f.read()
        if content.startswith(u'\ufeff'):
            content = content.encode('utf8')[3:].decode('utf8')
    return content
def loadFile_bytes(path):
    '读取文件'
    pass
def saveFile(path,content,encoding='utf-8'):
    '保存文本格式文件'
    f=open(path,mode='w',encoding=encoding)
    f.write(content)
    f.close()
def saveFile_bytes(path,content):
    '保存数据格式文件'
    f=open(path,mode='wb+')
    f.write(content)
    f.close()
# ini配置文件读写
def getConfig(path,encoding = 'gbk'):
    '返回所有item'
    config = configparser.ConfigParser()
    config.read(path,encoding=encoding)
    conf = {}
    for section in config.sections():
        sectionDict = {}
        for item in config.items(section):
            sectionDict.update({item[0]:item[1]})
        conf.update({section:sectionDict})    
    return conf    
def setConfig(path,**kwargs):
    'kp软件更改system文件'
    cp=ConfigParser()
    cp.read(path)
    for k,v in kwargs.items():
        if k not in cp.sections():
            cp.add_section(k)
        for option,value in v.items():
            cp.set(k,option,value)
    cp.write(open(path,'w'))
#文件拷贝
def fileCopy(srcpath,dstpath):
    if not os.path.isfile(srcpath):
        return {'code':1,'info':'源文件不存在'}
    else:
        fpath,fname = os.path.split(dstpath)
        if not os.path.exists(fpath):
            # os.makedirs(fpath)
            return {'code':2,'info':'目标路径不存在'}
        try:
            shutil.copy(srcpath,dstpath)
            return{'code':0,'info':'成功'}
        except:
            print(traceback.format_exc())
            return {'code':3,'info':'拷贝文件失败'}
#删除文件或文件夹
def remove(path):
    '删除文件'
    try:
        shutil.rmtree(path)
        return True
    except:
        return False
def clearDirAll(dir):
    '清除文件夹下所有文件及子文件夹'
    if not os.path.exists(dir): return {'code':0,'msg':'目录不存在'}
    for fileName in os.listdir(dir):
        filePath = dir+'/'+fileName
        try:
            if os.path.isfile(filePath):
                os.remove(filePath)
            else:
                clear_logs_iter(filePath)
        except:
            pass
    return {'code':1,'msg':''}
def cleanDir(tDir:str,keepNum:'保留数量'=0):
    '按创建时间清理文件夹内的文件'
    if tDir[-1] != '\\':
        tDir = tDir + '\\'
    if not os.path.exists(tDir): return {'code':1,'msg':'目录不存在'}
    fileNameList = os.listdir(tDir)
    if keepNum == 0:
        for fileName in fileNameList:
            try:
                filePath = tDir + fileName
                if Path(filePath).is_file(): 
                    os.remove(filePath)
                elif Path(filePath).is_dir():
                    shutil.rmtree(filePath)
            except:
                print(traceback.format_exc())
                return
        return
    foList = []
    for fileName in fileNameList:
        ctime = os.path.getctime(tDir+fileName)
        foList.append((fileName,ctime))
    foList.sort(key=takeSecond,reverse=False)
    while len(foList)>keepNum:
        try:
            filePath = tDir + foList[0][0]
            if Path(filePath).is_file(): 
                os.remove(filePath)
            elif Path(filePath).is_dir():
                shutil.rmtree(filePath)
            del foList[0]
        except:
            print(traceback.format_exc())
            return
def cleanDirDir(tDir,regExp = r"[0-9A-HJ-NPQRTUWXY]{2}\d{6}[0-9A-HJ-NPQRTUWXY]{10}"):
    '清理指定文件夹内文件夹'
    if tDir[-1] != '\\':
        tDir = tDir + '\\'
    if not os.path.exists(tDir): return {'code':1,'msg':'目录不存在'}
    fileNameList = os.listdir(tDir)
    for fileName in fileNameList:
        filePath = tDir + fileName
        if Path(filePath).is_dir():
            if re.match(regExp,fileName):
                shutil.rmtree(filePath)
    return {'code':0,'msg':'清理完成'}
# def takeSecond(ele):
#     return ele[1]
#清卡时间判断
def clear_time(timeStr):
    '''清卡时间判断'''
    isUpload = False
    isLock = False
    resultDay = datetime.strptime(timeStr,'%Y%m%d%H%M%S')
    today = datetime.today()
    if today.year == resultDay.year:
        if today.month < resultDay.month:
            isUpload = True
        elif today.month>resultDay.month:
            isUpload = False
            isLock = True
        elif today.month == resultDay.month:
            if today.day>resultDay.day:
                isUpload = False
                isLock = True
    elif today.year < resultDay.year:
        isUpload = True
    # 0.未清卡 1.已清卡 2.已锁死
    if isLock:
        return 2
    if isUpload:
        return 1
    return 0

def decompress(zipfilePath,decompressDir):
    if Path(zipfilePath).is_file():
        pass
    else:
        return False
    count = 0
    while True:
        if count >= 10:
            return False
        if count > 0:
            print('重试%d次' %count)
        try:
            f = zipfile.ZipFile(zipfilePath,'r')
            for file in f.namelist():
                f.extract(file,decompressDir)
            break
        except:
            print('解压失败:%s' %traceback.format_exc())
            time.sleep(1)
    return True
def deleteSingle(fPath):
    if Path(fPath).is_file():
        print('is file')
    elif Path(fPath).is_dir():
        print('is dir')
    else:
        print('file not exist')
if __name__ == '__main__':
    path = r'C:\Program Files (x86)\增值税发票税控开票软件(税控盘版)\system.ini'
    print(pathSplit(path))