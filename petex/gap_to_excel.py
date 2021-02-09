# скрипт для извлечения данных из Prosper через OpenServer
import win32com.client
import sys
import os
import time
import tqdm
import pandas as pd

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


# функция возвращает список дат прогноза
def get_date_list(n_dates):
    date_list = []
    for i in range(n_dates):
        date_list.append(DoGet(petex, f"GAP.MOD[i].EQUIP[j].PREDRES.DATES[{i}].DATESTR")[:-1])
    #print(date_list)
    return date_list
        
    
# функция возвращает лист оборудования
def get_equip_list(equip_type):
    equip = DoGet(petex, f"GAP.MOD[0].{equip_type}[$].Label").split('|')
    equip = [elem for elem in equip if elem != '']
    return equip


# извлечение параметров работы оборудование и возврат в виде датафрейма
def get_param(equip_list, equip_type, param_name):
    '''
    GAP param_name:
    буферное: GAP.MOD[{PROD}].WELL[{8504}].PREDRES[{01.02.2021}].FWHP
    drawdown: GAP.MOD[{PROD}].WELL[{8504}].PREDRES[{01.01.2021}].DrawDown
    Qн        GAP.MOD[{PROD}].WELL[{8504}].PREDRES[{01.01.2021}].OILRATE
    температ буф GAP.MOD[{PROD}].WELL[{8503}].PREDRES[{01.01.2021}].FWHT
    лин давл: GAP.MOD[{PROD}].JOINT[{J Choke 8503}].PREDRES[{01.01.2021}].PRES
    '''
    df = pd.DataFrame({'Date': date_list})
    
    for equip in equip_list:
        param_list = []
        for i in range(n_dates):

            param = DoGet(petex, 'GAP.MOD[{PROD}].' + f'{equip_type}' + '[{' +
                        str(equip) + '}].PREDRES[' + f'{i}].' + f'{param_name}')
            param = float(param) if param != None else param
            param = None if param == 3.4E+35 else param

            param_list.append(param)

 
        df[f'{equip}'] = param_list
        
    return df, param_name



# Скрипт обёрнут в исключение try для отключения от лицензии в случае ошибки
try:
    # Initialises an 'OpenServer' class
    petex = OpenServer()
    
    # Creates ActiveX reference and holds a license
    petex.Connect()
    
    # Perform functions
    cwd = os.getcwd() # current working directory


## ====================  СЕКЦИЯ ПАРАМЕТРОВ НАСТРОЙКИ СКРИПТА ======================

    # Имя файла с которым работаем
##    file_name = '\PROSPER\9205 choke sep 2020.12.09 73tubing.Out'
##    OSOpenFile(petex, cwd + file_name, 'PROSPER')
    print('Открываем файл . . .')
    OSOpenFile(petex, r'D:\work\2020.12_models\PES_ACH2\PES_ACH.gap', 'gap')
    # OSOpenFile(petex, r'D:\work\2020.12_models\En_Yaha\ENYAHA_AFTER_EXPERT Jun 2020\PES_YAHA.gap', 'gap')
    print('Файл открыт')

    # задаём имя выходного файла
    output_file = 'output_grom_gap.xlsx'
    
    # задаём тип оборудование для извлечения
    '''
    типы оборудований: WELL, PIPE, EQUIP, JOINT, INLCHK,
                       VALVE, TANK, PUMP, SEP, SINK, COMP, SOURCE...
    '''
    equip_type = 'WELL'

    # задаём список параметров для извлечения
    # для скважин: OPFREQ - частота ЭЦН
    param_list = ['CUMGAS']
    #param_list = ['OILRATE', 'GASRATE', 'WATRATE', 'LIQRATE',  'FWHP', 'FBHP', 'DrawDown', 'WCT', 'FWHT', 'OPFREQ']
    # для Joint
    #param_list = ['OILRATE', 'GASRATE', 'WATRATE', 'LIQRATE', 'PRES', 'WCT']
    # для SINK (УКПГ/УПН)
    #param_list = ['OILRATE', 'GASRATE', 'WATRATE', 'LIQRATE', 'PRES', 'NUMACTIVEWELLS']
    # для PIPE
    #param_list = ['OILRATE', 'GASRATE', 'WATRATE', 'LIQRATE', 'PRESSUREDROP', 'PRESIN', 'PRESOUT']
    # для PIPE
    #param_list = ['OILRATE', 'GASRATE', 'WATRATE', 'LIQRATE', 'PRES', 'WCT', 'PRESSUREDROP', 'CHOKESIZE']

## ====================  КОНЕЦ СЕКЦИИ ПАРАМЕТРОВ НАСТРОЙКИ СКРИПТА ======================
    

    # извлекаем количество дат в прогнозе
    n_dates = int((DoGet(petex, "GAP.MOD[i].EQUIP[j].PREDRES.DATES.COUNT")[:-1]))
    
    # извлекаем список дат прогноза
    date_list = get_date_list(n_dates)

    # извлекаем список оборудования указанного выше типа
    equip_list = get_equip_list(equip_type)
    #equip_list = ['7301', '7306_2']
    print('Извлекаем параметры для списка оборудования: ', equip_list)

    # тест
    #print(DoGet(petex, 'GAP.MOD[{PROD}].WELL[{7003}].PREDRES[0].OILRATE'))

    # извлекаем данные и сохраняем в файл
    try:
        with pd.ExcelWriter(output_file) as writer:
            #for param in tqdm(param_list):
            for param in param_list:
                df, param_name = get_param(equip_list, equip_type, param)
                df.to_excel(writer, sheet_name=f'{param_name}')
        print(f'Данные соранены в файл {output_file}')
                
    except Exception:
        print('                ==============================\n  \
               ########    ОШИБКА   #########\n \
                    Данные не сохранены!!!\n \
                        Файл открыт? \n \
               ===============================')

finally:
    # требуется отключиться от лицензии иначе она удерживается
    petex.Disconnect()
