# скрипт для извлечения данных из Prosper через OpenServer
# Import modules for OpenServer functions
import win32com.client
import sys
import os
import time
from datetime import datetime
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
    # function for returning app name from tag string
    pos = sv.find(".")
    if pos < 2:
        sys.exit("GetAppName: Badly formed tag string")
    app_name = sv[:pos]
    if app_name.lower() not in ["prosper", "mbal", "gap", "pvt", "resolve", "reveal"]:
        sys.exit("GetAppName: Unrecognised application name in tag string")
    return app_name

def DoCmd(OpenServe, cmd):
    # perform a command and check for errors
    lerr = OpenServe.OSReference.DoCommand(cmd)
    if lerr > 0:
        err = OpenServe.OSReference.GetErrorDescription(lerr)
        OpenServe.Disconnect()
        sys.exit("DoCmd: " + err)

def DoSet(OpenServe, sv, val):
    # set a value and check for errors
    lerr = OpenServe.OSReference.SetValue(sv, val)
    app_name = GetAppName(sv)
    lerr = OpenServe.OSReference.GetLastError(app_name)
    if lerr > 0:
        err = OpenServe.OSReference.GetErrorDescription(lerr)
        OpenServe.Disconnect()
        sys.exit("DoSet: " + err)

def DoGet(OpenServe, gv):
    # get a value and check for errors
    get_value = OpenServe.OSReference.GetValue(gv)
    app_name = GetAppName(gv)
    lerr = OpenServe.OSReference.GetLastError(app_name)
    if lerr > 0:
        err = OpenServe.OSReference.GetErrorDescription(lerr)
        OpenServe.Disconnect()
        sys.exit("DoGet: " + err)
    return get_value

def DoSlowCmd(OpenServe, cmd):
    # perform a command then wait for command to exit and check for errors
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










# Script wrapped in a try statement to ensure license is disconnected in case of error
try:
    # Initialises an 'OpenServer' class
    petex = OpenServer()
    
    # Creates ActiveX reference and holds a license
    petex.Connect()
    
    # Perform functions
    cwd = os.getcwd() # current working directory

    # Имя файа с которым работаем
##    file_name = '\PROSPER\9205 choke sep 2020.12.09 73tubing.Out'
##    OSOpenFile(petex, cwd + file_name, 'PROSPER')
    print('Открываем файл')
    OSOpenFile(petex, r'D:\work\2020.12_models\En_Yaha\ENYAHA_AFTER_EXPERT Jun 2020\PES_YAHA.gap', 'gap')
    #OSOpenFile(petex, cwd + r'\PROSPER\9205 choke sep 2020.12.09 73tubing.Out', 'PROSPER')
    #DoCmd(petex, 'PROSPER.ANL.SYS.CALC')




    

    # список дат прогноза
    def get_date_list(n_dates):
        date_list = []
        for i in range(n_dates):
            date_list.append(DoGet(petex, f"GAP.MOD[i].EQUIP[j].PREDRES.DATES[{i}].DATESTR")[:-1])
        print(date_list)
        return date_list
        
    
    # функция возвращает лист оборудования
    def get_equip_list(equip_type):
        '''
        equip_type => WELL, PIPE, EQUIP, JOINT, INLCHK, VALVE,
             TANK, PUMP, SEP, SINK, COMP, SOURCE...
        '''
        equip = DoGet(petex, f"GAP.MOD[0].{equip_type}[$].Label").split('|')
        equip = [elem for elem in equip if elem != '']
        return equip



    def get_param(equip_list, equip_type, param_name):
        '''
        GAP param_name:
        буферное: GAP.MOD[{PROD}].WELL[{8504}].PREDRES[{01.02.2021}].FWHP
        забойное: GAP.MOD[{PROD}].WELL[{8504}].PREDRES[{01.01.2021}].FBHP
        drawdown: GAP.MOD[{PROD}].WELL[{8504}].PREDRES[{01.01.2021}].DrawDown
        Qн        GAP.MOD[{PROD}].WELL[{8504}].PREDRES[{01.01.2021}].OILRATE
        Qг        GAP.MOD[{PROD}].WELL[{8504}].PREDRES[{01.01.2021}].GASRATE
        Qж        GAP.MOD[{PROD}].WELL[{8504}].PREDRES[{01.01.2021}].LIQRATE
        обв       GAP.MOD[{PROD}].WELL[{8504}].PREDRES[{01.01.2021}].WCT
        температ буф GAP.MOD[{PROD}].WELL[{8503}].PREDRES[{01.01.2021}].FWHT
        лин давл: GAP.MOD[{PROD}].JOINT[{J Choke 8503}].PREDRES[{01.01.2021}].PRES
        '''
        df = pd.DataFrame({'Date': date_list})
        
        for equip in equip_list:
            param_list = []
            for i in range(n_dates):
                #print('2')
                param = DoGet(petex, 'GAP.MOD[{PROD}].' + f'{equip_type}' + '[{' +
                            str(equip) + '}].PREDRES[' + f'{i}].' + f'{param_name}')
                #print('3')
                param_list.append(param)

            df[f'{equip}'] = param_list
            
        return df, param_name

            
        def save_to_excel(self):
            df = pd.DataFrame({f'date': [],
                         f'well': []
                                     })
            pass

    # количество дат в prediction results
    n_dates = int((DoGet(petex, "GAP.MOD[i].EQUIP[j].PREDRES.DATES.COUNT")[:-1]))
    print('no. of dates = ', n_dates)

    date_list = get_date_list(n_dates)

    well_list_1 = get_equip_list('WELL')
    print(well_list_1)

    param_well_list_1 = ['LIQRATE', 'OILRATE', 'PWF', 'WATRATE', 'GASRATE']

    well_list_2 = [7312, 7002]
    equip_type = 'WELL'
    param_list = ['OILRATE', 'FWHP']
    list1 = []

    file = 'output.xlsx'
    try:
        with pd.ExcelWriter(file) as writer:
            for param in param_list:
                df, param_name = get_param(well_list_2, equip_type, param)
                df.to_excel(writer, sheet_name=f'{param_name}')
        print(f'Данные соранены в файл {file}')
                
    except Exception:
        print('                ==============================\n  \
               ########    ОШИБКА   #########\n \
                    Данные не сохранены!!!\n \
                        Файл открыт? \n \
               ===============================')
        
    
    
 



## ================ НИЖЕ НУЖНЫЙ КОД =========================================================


##    print('Пытаемся выполнить DoGet equip')
##    equip = DoGet(petex, f'GAP.MOD[0].EQUIP[{5}]')
##    print(equip)
##
##    print('Пытаемся выполнить DoGet oil rate')
##    rate = DoGet(petex, "GAP.MOD[{PROD}].WELL[{7312}].PREDRES[{01.01.2021}].OILRATE")
##    rate0 = DoGet(petex, "GAP.MOD[{PROD}].WELL[{7312}].PREDRES[0].OILRATE")
##    rate1 = DoGet(petex, "GAP.MOD[{PROD}].WELL[{7312}].PREDRES[1}].OILRATE")
##    print(rate, rate0, rate1)
##
##    # список всего оборудования
##    #equip = DoGet(petex, "GAP.MOD[0].EQUIP[$].Label")
##    #print(equip)
##
##    # создаём лист всех имён скважин + избавляемся от пустых названий
##    wells = DoGet(petex, "GAP.MOD[0].WELL[$].Label").split('|')
##    wells = [elem for elem in wells if elem != '']
##    print(wells)
##
##    # лист всех труб + избавляемся от пустых названий
##    pipes = DoGet(petex, "GAP.MOD[0].PIPE[$].Label").split('|')
##    pipes = [elem for elem in pipes if elem != '']
##    print(pipes)
##
##    # количество дат в prediction results
##    n_dates = int((DoGet(petex, "GAP.MOD[i].EQUIP[j].PREDRES.DATES.COUNT")[:-1]))
##    print(n_dates)
##
##    # список дат прогноза
##    date_list = []
##    for i in range(n_dates):
##        date_list.append(DoGet(petex, f"GAP.MOD[i].EQUIP[j].PREDRES.DATES[{i}].DATESTR")[:-1])
##
##    print(date_list)



## ============ ВЫШЕ НУЖНЫЙ КОД ============================================
    
##    date0 = DoGet(petex, "GAP.MOD[i].EQUIP[j].PREDRES.DATES[0].DATESTR")[:-1]
##    date1 = DoGet(petex, "GAP.MOD[i].EQUIP[j].PREDRES.DATES[1].DATESTR")[:-1]
##    print(date0, date1)

##    # длина периода прогноза в днях
##    pred_date = DoGet(petex, 'GAP.MOD[0].PREDINFO.PERIOD')
##    print(f'Прогноз ={pred_date} дней')
##
##    # длина периода прогноза в днях
##    pred_start_date = DoGet(petex, 'GAP.MOD[0].PREDINFO.START.DATESTR')
##    print(f'Начальная дата прогноза: {pred_start_date}')
##
##    # длина периода прогноза в днях
##    pred_end_date = DoGet(petex, 'GAP.MOD[0].PREDINFO.END')
##    print(f'Количество шагов в прогнозе {pred_end_date}')

## ================= НИЖЕ НУЖНЫЙ КОД ===========================

##    well_rates = pd.DataFrame({f'date': [],
##                         f'well': []
##                                     })
##    PROD = '{PROD}'
##    well_name = '{7312}'
##    for i in range(n_dates):
##        well_rate = DoGet(petex, f'GAP.MOD[{PROD}].WELL[{well_name}].PREDRES[{i}].OILRATE')
##        well_rates.loc[i] = [i,
##                       well_rate]
##    print(well_rates)
##        
##
##    # печать всех колонок датафрейма на экран
##    pd.options.display.max_columns = None

## ================== ВЫШЕ НУЖНЫЙ КОД ========================
    
    #print(data)

##    print(f'Дебит нефти пересчитан ({density_units} => т/сут) через плотность\
##= {round(float(density), 0)} {density_units}')
##
##    # пишем данные в файл
##    try:
##        writer = pd.ExcelWriter('prosper_output.xlsx')
##        data.to_excel(writer,
##                      sheet_name=f'{datetime.now().strftime("%Y-%m-%d %H-%M-%S")}',
##                      index=False)
##        writer.save()
##        print('ГОТОВО: данные записаны в файл')
##       
##    except PermissionError:
##        print('                ==============================\n  \
##               ########    ОШИБКА   #########\n \
##                    Данные не сохранены!!!\n \
##                        Файл открыт? \n \
##               ===============================')

finally:
    # Required to close the license otherwise remains checked out
    petex.Disconnect()
