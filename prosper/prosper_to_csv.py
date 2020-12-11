﻿# скрипт для извлечения данных из Prosper через OpenServer
# Import modules for OpenServer functions
import win32com.client
import sys
import os
import time
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
    #file_name = '9204 choke asep 2020.12.10 62tubing.Out'
    OSOpenFile(petex, cwd + r'\PROSPER\9205 choke sep 2020.12.09 73tubing.Out', 'PROSPER')
    #DoCmd(petex, 'PROSPER.ANL.SYS.CALC')

    # коэф. перевода кгс/см2 в BARa
    rgs_cm2_to_bara = 0.98062
    
    # извлекаем плотность и ед.измерения
    density = DoGet(petex, f'PROSPER.PVT.Input.Api')
    density_units = DoGet(petex, f'PROSPER.PVT.Input.Api.UNITNAME')
    liq_units = DoGet(petex, f'PROSPER.OUT.SYS.Results[0].Sol.LiqRate.UNITNAME')
    thp_units = DoGet(petex, f'PROSPER.OUT.SYS.Results[0].Sol.WHPressure.UNITNAME')
    bhp_units = DoGet(petex, f'PROSPER.OUT.SYS.Results[0].Sol.BHP.UNITNAME')
    choke_inuts = DoGet(petex, f'PROSPER.ANL.SYS.Sens.SensDB.Sens[146].Vals[0].UNITNAME')

    # создаём pandas датафрейм
    data = pd.DataFrame({f'choke: {choke_inuts}': [],
                         f'liq rate: {liq_units}': [],
                         f'oil rate: t/d': [],
                         f'THP: BARa':[],
                         f'BHP: BARa': [],
                         f'THP: {thp_units}':[],
                         f'BHP: {bhp_units}': []})
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
                       round(float(well_head_pres) * rgs_cm2_to_bara, 1),
                       round(float(sol_node_pres) * rgs_cm2_to_bara, 1),
                       round(float(well_head_pres), 1),
                       round(float(sol_node_pres), 1)]
        i += 1

    # печать всех колонок датафрейма
    pd.options.display.max_columns = None
    print(data)
    print(f'Дебит нефти пересчитан ({density_units} => т/сут) через плотность\
= {round(float(density), 0)} {density_units}')

    #writer = pd.ExcelWriter('prosper_output.xlsx')
    #data.to_excel(writer, sheet_name='well name')
    #writer.save()

    # пишем данные в файл
    try:
        data.to_csv('prosper_output.csv', index=False, sep=' ')
        print('ГОТОВО: данные записаны в файл')
        
    except PermissionError:
        print('                ==============================\n  \
               ########    ОШИБКА   #########\n \
                    Данные не сохранены!!!\n \
                        Файл открыт? \n \
               ===============================')

finally:
    # Required to close the license otherwise remains checked out
    petex.Disconnect()
