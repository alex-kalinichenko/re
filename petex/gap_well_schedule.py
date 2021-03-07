# скрипт для записи дат ввода скважин в GAP из Excel через OpenServer

import win32com.client
import sys
import os
import time
import tqdm
import pandas as pd
from pandas import read_excel
import openpyxl
import xlrd


class OpenServer():
    # "Class for holding ActiveX reference. Allows license disconnection"
    def __init__(self):
        self.status = "Disconnected"
        self.OSReference = None
    
    def Connect(self):
        self.OSReference = win32com.client.Dispatch("PX32.OpenServer.1")
        self.status = "Connected"
        print("OpenServer connected")
        
    def Disconnect(self):
        self.OSReference = None
        self.status = "Disconnected"
        print("OpenServer disconnected")

def GetAppName(sv):
    # возвращает имя приложения из строки
    pos = sv.find(".")
    if pos < 2:
        sys.exit("GetAppName: Badly formed tag string")
    app_name = sv[:pos]
    if app_name.lower() not in ["prosper", "mbal", "gap", "pvt", "resolve", "reveal"]:
        sys.exit("GetAppName: Unrecognised application name in tag string")
    return app_name

def DoCmd(OpenServe, cmd):
    # производит команду и проверяет на ошибки
    lerr = OpenServe.OSReference.DoCommand(cmd)
    if lerr > 0:
        err = OpenServe.OSReference.GetErrorDescription(lerr)
        OpenServe.Disconnect()
        sys.exit("DoCmd: " + err)

def DoSet(OpenServe, sv, val):
    # устанавливает значение и проверяет на ошибки
    lerr = OpenServe.OSReference.SetValue(sv, val)
    app_name = GetAppName(sv)
    lerr = OpenServe.OSReference.GetLastError(app_name)
    if lerr > 0:
        err = OpenServe.OSReference.GetErrorDescription(lerr)
        OpenServe.Disconnect()
        sys.exit("DoSet: " + err)

def DoGet(OpenServe, gv):
    # получает значение и проверяет на ошибки
    get_value = OpenServe.OSReference.GetValue(gv)
    app_name = GetAppName(gv)
    lerr = OpenServe.OSReference.GetLastError(app_name)
    if lerr > 0:
        err = OpenServe.OSReference.GetErrorDescription(lerr)
        #OpenServe.Disconnect()
        #sys.exit("DoGet: " + err)
        #print("DoGet: " + err)
        # if error rerurn 0
        return None
    return get_value

def DoSlowCmd(OpenServe, cmd):
    # производит команду затем ждёт команды выхода и проверяет на ошибки
    step = 0.001
    app_name = GetAppName(cmd)
    lerr = OpenServe.OSReference.DoCommandAsync(cmd)
    if lerr > 0:
        err = OpenServe.OSReference.GetErrorDescription(lerr)
        OpenServe.Disconnect()
        sys.exit("DoSlowCmd: " + err)
    while OpenServe.OSReference.IsBusy(app_name) > 0:
        if step < 2:
            step = step*2
        time.sleep(step)
    lerr = OpenServe.OSReference.GetLastError(app_name)
    if lerr > 0:
        err = OpenServe.OSReference.GetErrorDescription(lerr)
        OpenServe.Disconnect()
        sys.exit("DoSlowCmd: " + err)

def DoGAPFunc(OpenServe, gv):
    DoSlowCmd(gv)
    DoGAPFunc = DoGet(OpenServe, "GAP.LASTCMDRET")
    lerr = OpenServe.OSReference.GetLastError("GAP")
    if lerr > 0:
        err = OpenServe.OSReference.GetErrorDescription(lerr)
        OpenServe.Disconnect()
        sys.exit("DoGAPFunc: " + err)
    return DoGAPFunc

def OSOpenFile(OpenServe, theModel, appname):
    DoSlowCmd(OpenServe, appname + '.OPENFILE ("' + theModel + '")')
    lerr = OpenServe.OSReference.GetLastError(appname)
    if lerr > 0:
        err = OpenServe.OSReference.GetErrorDescription(lerr)
        OpenServe.Disconnect()
        sys.exit("OSOpenFile: " + err)

def OSSaveFile(OpenServe, theModel, appname):
    DoSlowCmd(OpenServe, appname + '.SAVEFILE ("' + theModel + '")')
    lerr = OpenServe.OSReference.GetLastError(appname)
    if lerr > 0:
        err = OpenServe.OSReference.GetErrorDescription(lerr)
        OpenServe.Disconnect()
        sys.exit("OSSaveFile: " + err)



# Скрипт обёрнут в исключение try для отключения от лицензии в случае ошибки
try:
    # Initialises an 'OpenServer' class
    petex = OpenServer()
    
    # Creates ActiveX reference and holds a license
    petex.Connect()
    
    # Perform functions
    cwd = os.getcwd() # current working directory



    # открываем файл
    df = pd.read_excel('schedule.xlsx', engine='openpyxl')

    zero_date = pd.to_datetime('01.01.1900', format='%d.%m.%Y')
    

    # итерируемся по датафрейму
    for row_num in range(df.shape[0]):
        #print('row_num = ', row_num)
        
        # извлекаем номер скважины из датафрейма
        well = df.iloc[row_num, 0]
        #print(well)

        # вычитаем из даты датафрейма дату начала эпохи
        start_date = (df.iloc[row_num, 1] - zero_date)
        #print('start date = ', df.iloc[row_num, 1])
        #print('start date = ', start_date)

        # извлекаем из таймстепа количество дней и прибавляем 1 (GAP <=> Excel)
        start_date_num = start_date.days + 1
        #print('start date num = ', start_date_num)

        # устнавливаем для скважины дату старта скважины в первую [0] строку schedule
        DoSet(petex, 'GAP.MOD[{PROD}].WELL[{' + f'{well}' + '}].SCHEDULE[0].Time', start_date_num)
        DoSet(petex, 'GAP.MOD[{PROD}].WELL[{' + f'{well}' + '}].SCHEDULE[0].Type', 'WELL_ON')                                                                                     
    print('\n Готово! \n График бурения записан в GAP \n')


finally:
    # требуется отключиться от лицензии иначе она удерживается
    petex.Disconnect()

