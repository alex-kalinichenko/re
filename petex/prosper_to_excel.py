# скрипт для экспорта данных из Prosper через OpenServer в Excel

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
        OpenServe.Disconnect()
        sys.exit("DoGet: " + err)
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

    # Имя файа с которым работаем
    file_name = r'\PROSPER\20210112_9213_73tubing.Out'
    OSOpenFile(petex, cwd + file_name, 'PROSPER')
    #OSOpenFile(petex, cwd + r'\PROSPER\9205 choke sep 2020.12.09 73tubing.Out', 'PROSPER')
    #DoCmd(petex, 'PROSPER.ANL.SYS.CALC')

    # коэф. перевода кгс/см2 в BARa
    kgs_cm2_to_bara = 0.98062

    print('========>  Prosper файл ПЕРЕКЛЮЧЕН в BARa? <=========')
    
    # извлекаем плотность и ед.измерения
    density = DoGet(petex, f'PROSPER.PVT.Input.Api')
    density_units = DoGet(petex, f'PROSPER.PVT.Input.Api.UNITNAME')
    liq_units = DoGet(petex, f'PROSPER.OUT.SYS.Results[0].Sol.LiqRate.UNITNAME')
    thp_units = DoGet(petex, f'PROSPER.OUT.SYS.Results[0].Sol.WHPressure.UNITNAME')
    bhp_units = DoGet(petex, f'PROSPER.OUT.SYS.Results[0].Sol.BHP.UNITNAME')
    choke_units = DoGet(petex, f'PROSPER.ANL.SYS.Sens.SensDB.Sens[146].Vals[0].UNITNAME')

    # создаём pandas датафрейм
    # двойной пробел в THP, BHP чтобы различались названия колонок в случает
    # совпадения ед.измерения (в этом случае ValueError: cannot set a row with mismatched columns)
    data = pd.DataFrame({f'choke: {choke_units}': [],
                         f'liq rate: {liq_units}': [],
                         f'oil rate: t/d': [],
                         f'THP:  {thp_units}':[],
                         f'BHP:  {bhp_units}': [],
                         f'THP: kgs/cm2':[],
                         f'BHP: kgs/cm2': []})
    
    i = 0
    choke = 0.1 # объявляем переменную

    while choke:
        # извлекаем штуцеры
        choke = DoGet(petex, f'PROSPER.ANL.SYS.Sens.SensDB.Sens[146].Vals[{i}]')
        try:
            choke = float(choke)
        except:
            print('Ошибка извлечения штуцеров')
            break

        # извлекаем параметры режима с этим штуцером
        try:
            liq_rate = DoGet(petex, f'PROSPER.OUT.SYS.Results[{i}].Sol.LiqRate')
            oil_rate =  DoGet(petex, f'PROSPER.OUT.SYS.Results[{i}].Sol.OilRate')
            well_head_pres = DoGet(petex, f'PROSPER.OUT.SYS.Results[{i}].Sol.WHPressure')
            sol_node_pres = DoGet(petex, f'PROSPER.OUT.SYS.Results[{i}].Sol.BHP')
        except BaseException:
            print(f'Количество штуцеров в расчёте: {i}')
            break # прерываем если штуцеры закончились

        # добавляем в датафрейм: choke, liq rate, oil rate, THP, BHP
        data.loc[i] = [round(choke, 1),
                       round(float(liq_rate), 1), 
                       round(float(oil_rate) * float(density) / 1000, 1), 
                       round(float(well_head_pres), 1), 
                       round(float(sol_node_pres), 1), 
                       round(float(well_head_pres) / kgs_cm2_to_bara, 1), 
                       round(float(sol_node_pres) / kgs_cm2_to_bara, 1)]
        i += 1

    # печать всех колонок датафрейма на экран
    pd.options.display.max_columns = None
    print(data)

    print(f'Дебит нефти пересчитан ({density_units} => т/сут) через плотность\
= {round(float(density), 0)} {density_units}')

    # пишем данные в файл
    try:
        writer = pd.ExcelWriter('prosper_to_excel_output.xlsx')
        data.to_excel(writer,
                      sheet_name=f'{datetime.now().strftime("%Y-%m-%d %H-%M-%S")}',
                      index=False)
        writer.save()
        print('ГОТОВО: данные записаны в файл')
       
    except PermissionError:
        print('                ==============================\n  \
               ########    ОШИБКА   #########\n \
                    Данные не сохранены!!!\n \
                        Файл открыт? \n \
               ===============================')

finally:
    # требуется отключиться от лицензии иначе она удерживается
    petex.Disconnect()
